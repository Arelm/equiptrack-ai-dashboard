"""EquipTrack fault report - data layer.

Runs the queries and returns plain Python structures. No printing, no
formatting. Every output format (terminal, CSV, PDF, the dashboard API)
renders from the dict this returns, so the SQL lives in one place only.

Faults come from filed reports only, because that is the only place a
diagnosis exists. Jobs closed without a report are counted separately so the
numbers reconcile.

Usage
-----
    import psycopg2
    from report_data import collect_report, resolve_period

    start, end = resolve_period(month="2026-08")
    conn = psycopg2.connect(DATABASE_URL)
    data = collect_report(conn, start, end, site="264")

Pass organization_id to scope every section to one client's fleet. The API
layer always passes it, taken from the caller's token rather than from a
query parameter, so a signed-in user can never read another org's data.
"""

import calendar
from datetime import date


class FilterError(Exception):
    """Raised when a site or asset filter matches nothing."""


# --- Period ---------------------------------------------------------------
def resolve_period(start=None, end=None, month=None, year=None):
    """Work out the reporting window. Defaults to the current month.

    Returns (start_date, end_date) as YYYY-MM-DD strings, end inclusive.
    """
    if month:
        y, m = (int(x) for x in month.split("-"))
        last = calendar.monthrange(y, m)[1]
        return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last:02d}"

    if year:
        y = int(year)
        return f"{y:04d}-01-01", f"{y:04d}-12-31"

    if start and end:
        return start, end

    if start or end:
        raise FilterError("Give both start and end, or use month / year.")

    today = date.today()
    last = calendar.monthrange(today.year, today.month)[1]
    return (
        f"{today.year:04d}-{today.month:02d}-01",
        f"{today.year:04d}-{today.month:02d}-{last:02d}",
    )


# --- Filters --------------------------------------------------------------
def _resolve_filters(cur, site, asset, organization_id):
    """Turn a site / asset filter into a concrete list of asset ids.

    Every section then filters on the same list, so the fleet count, the
    fault ranking and the location breakdown can never disagree with each
    other.
    """
    location_ids = None
    site_label = "all sites"

    if site:
        sql = 'SELECT id, name FROM "Location" WHERE name ILIKE %s'
        sql_params = [f"%{site}%"]
        if organization_id:
            sql += ' AND "organizationId" = %s'
            sql_params.append(organization_id)
        cur.execute(sql + " ORDER BY name;", sql_params)
        hits = cur.fetchall()
        if not hits:
            raise FilterError(f"No site matches '{site}'.")
        location_ids = [h[0] for h in hits]
        site_label = ", ".join(h[1] for h in hits)

    asset_ids = None
    if site or asset or organization_id:
        sql = 'SELECT id FROM "Asset" WHERE TRUE'
        sql_params = []
        if organization_id:
            sql += ' AND "organizationId" = %s'
            sql_params.append(organization_id)
        if location_ids:
            sql += ' AND "locationId" = ANY(%s)'
            sql_params.append(location_ids)
        if asset:
            sql += " AND name ILIKE %s"
            sql_params.append(f"%{asset}%")

        cur.execute(sql + ";", sql_params)
        asset_ids = [r[0] for r in cur.fetchall()]
        if not asset_ids:
            raise FilterError("No assets match that filter.")

    return location_ids, asset_ids, site_label


# --- Main entry point -----------------------------------------------------
def collect_report(conn, start, end, site=None, asset=None, organization_id=None):
    """Run every section and return the results as a dict."""
    cur = conn.cursor()

    location_ids, asset_ids, site_label = _resolve_filters(
        cur, site, asset, organization_id
    )
    filtered = asset_ids is not None

    # End date is inclusive of the whole day.
    params = {"start": start, "end": end + " 23:59:59"}
    if filtered:
        params["assets"] = asset_ids

    # SQL fragments, empty when no filter is active.
    ml_f = ' AND ml."assetId" = ANY(%(assets)s)' if filtered else ""
    wo_f = ' AND wo."assetId" = ANY(%(assets)s)' if filtered else ""

    report = {
        "period": {"start": start, "end": end},
        "filters": {
            "site": site,
            "asset": asset,
            "organization_id": organization_id,
            "site_label": site_label,
            "asset_label": asset or "all assets",
        },
    }

    # --- 1. Fleet ---------------------------------------------------------
    if filtered:
        cur.execute('SELECT count(*) FROM "Asset" WHERE id = ANY(%(assets)s);', params)
    else:
        cur.execute('SELECT count(*) FROM "Asset";')
    total_assets = cur.fetchone()[0]

    if filtered:
        cur.execute(
            'SELECT status, count(*) FROM "Asset" WHERE id = ANY(%(assets)s)'
            " GROUP BY status ORDER BY 2 DESC;",
            params,
        )
    else:
        cur.execute(
            'SELECT status, count(*) FROM "Asset" GROUP BY status ORDER BY 2 DESC;'
        )
    by_status = [{"status": s, "count": n} for s, n in cur.fetchall()]

    cur.execute(
        f"""
        SELECT count(DISTINCT ml."assetId") FROM "MaintenanceLog" ml
        WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
          AND ml."assetId" IS NOT NULL{ml_f};
    """,
        params,
    )
    touched = cur.fetchone()[0]

    report["fleet"] = {
        "total": total_assets,
        "by_status": by_status,
        "touched": touched,
        "touched_pct": (touched / total_assets * 100) if total_assets else 0,
    }

    # --- 2. Activity ------------------------------------------------------
    cur.execute(
        f"""
        SELECT count(*) FROM "MaintenanceLog" ml
        WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s{ml_f};
    """,
        params,
    )
    reports_filed = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT count(*) FROM "WorkOrder" wo
        WHERE wo."completedAt" BETWEEN %(start)s AND %(end)s{wo_f};
    """,
        params,
    )
    jobs_completed = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT count(*) FROM "WorkOrder" wo
        WHERE wo."completedAt" BETWEEN %(start)s AND %(end)s{wo_f}
          AND NOT EXISTS (
            SELECT 1 FROM "MaintenanceLog" ml WHERE ml."workOrderId" = wo.id
          );
    """,
        params,
    )
    closed_without_report = cur.fetchone()[0]

    report["activity"] = {
        "reports_filed": reports_filed,
        "jobs_completed": jobs_completed,
        "closed_without_report": closed_without_report,
    }

    # --- 3. Fault ranking -------------------------------------------------
    cur.execute(
        f"""
        SELECT ml."faultCategory", count(*) AS n
        FROM "MaintenanceLog" ml
        WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
          AND ml."faultCategory" IS NOT NULL{ml_f}
        GROUP BY ml."faultCategory"
        ORDER BY n DESC;
    """,
        params,
    )
    report["faults"] = [{"category": f, "count": n} for f, n in cur.fetchall()]

    # --- 4. Repeat offenders ----------------------------------------------
    cur.execute(
        f"""
        SELECT a.name, l.name, ml."faultCategory", count(*) AS n
        FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        LEFT JOIN "Location" l ON l.id = a."locationId"
        WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
          AND ml."faultCategory" IS NOT NULL{ml_f}
        GROUP BY a.name, l.name, ml."faultCategory"
        HAVING count(*) > 1
        ORDER BY n DESC;
    """,
        params,
    )
    report["repeat_offenders"] = [
        {"asset": a, "location": loc, "category": f, "count": n}
        for a, loc, f, n in cur.fetchall()
    ]

    # --- 5. Workload ------------------------------------------------------
    cur.execute(
        f"""
        SELECT a.name, l.name, count(*) AS n
        FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        LEFT JOIN "Location" l ON l.id = a."locationId"
        WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s{ml_f}
        GROUP BY a.name, l.name
        ORDER BY n DESC
        LIMIT 20;
    """,
        params,
    )
    report["workload"] = [
        {"asset": a, "location": loc, "jobs": n} for a, loc, n in cur.fetchall()
    ]

    # --- 6. By location ---------------------------------------------------
    loc_sql = (
        'SELECT l.id, l.name, l.client FROM "Location" l'
        ' WHERE l."isActive" IS NOT FALSE'
    )
    loc_params = []
    if organization_id:
        loc_sql += ' AND l."organizationId" = %s'
        loc_params.append(organization_id)
    if location_ids:
        loc_sql += " AND l.id = ANY(%s)"
        loc_params.append(location_ids)
    loc_sql += " ORDER BY l.name;"
    cur.execute(loc_sql, loc_params)

    locations = []
    for loc_id, loc_name, client in cur.fetchall():
        p = dict(params, loc=loc_id)

        cur.execute(
            f"""
            SELECT count(*) FROM "MaintenanceLog" ml
            JOIN "Asset" a ON a.id = ml."assetId"
            WHERE a."locationId" = %(loc)s
              AND ml."createdAt" BETWEEN %(start)s AND %(end)s{ml_f};
        """,
            p,
        )
        jobs = cur.fetchone()[0]

        if filtered:
            cur.execute(
                'SELECT count(*) FROM "Asset" WHERE "locationId" = %s AND id = ANY(%s);',
                (loc_id, asset_ids),
            )
        else:
            cur.execute(
                'SELECT count(*) FROM "Asset" WHERE "locationId" = %s;', (loc_id,)
            )
        units = cur.fetchone()[0]

        entry = {
            "id": loc_id,
            "name": loc_name,
            "client": client,
            "units": units,
            "jobs": jobs,
            "faults": [],
            "worst_units": [],
        }

        if jobs:
            cur.execute(
                f"""
                SELECT ml."faultCategory", count(*) AS n
                FROM "MaintenanceLog" ml
                JOIN "Asset" a ON a.id = ml."assetId"
                WHERE a."locationId" = %(loc)s
                  AND ml."createdAt" BETWEEN %(start)s AND %(end)s
                  AND ml."faultCategory" IS NOT NULL{ml_f}
                GROUP BY ml."faultCategory" ORDER BY n DESC LIMIT 5;
            """,
                p,
            )
            entry["faults"] = [
                {"category": f, "count": n} for f, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT a.name, count(*) AS n
                FROM "MaintenanceLog" ml
                JOIN "Asset" a ON a.id = ml."assetId"
                WHERE a."locationId" = %(loc)s
                  AND ml."createdAt" BETWEEN %(start)s AND %(end)s{ml_f}
                GROUP BY a.name ORDER BY n DESC LIMIT 3;
            """,
                p,
            )
            entry["worst_units"] = [
                {"asset": a, "jobs": n} for a, n in cur.fetchall()
            ]

        locations.append(entry)

    report["locations"] = locations

    cur.close()
    return report
