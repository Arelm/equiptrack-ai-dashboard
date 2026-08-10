"""Fleet-wide analytics.

Distinct from reports.py, which handles a single maintenance report against a
single work order. This router answers questions about the whole fleet over a
period: what failed, where, and which units keep coming back.

The queries live in report_data.py, so the terminal script, the CSV export and
this endpoint can never drift apart.

Access is Manager/Admin only for now. The organisation is always taken from
the caller's token, never from a query parameter, so opening this to a client
later cannot leak another client's fleet.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import RoleEnum
from report_data import FilterError, collect_report, resolve_period
from routers.auth import require_role

router = APIRouter()

MANAGER_ROLES = (RoleEnum.MANAGER.value, RoleEnum.ADMIN.value)


@router.get("/fleet-report")
def fleet_report(
    start: str | None = Query(None, description="Start date, YYYY-MM-DD"),
    end: str | None = Query(None, description="End date, YYYY-MM-DD, inclusive"),
    month: str | None = Query(None, description="Whole calendar month, YYYY-MM"),
    year: str | None = Query(None, description="Whole calendar year, YYYY"),
    site: str | None = Query(None, description="Filter to one site, by name"),
    asset: str | None = Query(None, description="Filter to assets by name"),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGER_ROLES)),
):
    """Fleet, activity, fault ranking, repeat offenders and per-site detail.

    Defaults to the current month when no period is given.
    """
    try:
        period_start, period_end = resolve_period(
            start=start, end=end, month=month, year=year
        )
    except (FilterError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    organization_id = user.get("orgId")
    if not organization_id:
        raise HTTPException(
            status_code=403, detail="Your account is not linked to an organisation."
        )

    # Borrow the raw psycopg2 connection from the SQLAlchemy session so the
    # report runs inside the request's existing transaction. It is read-only
    # and collect_report closes only its own cursor, never the connection.
    raw_conn = db.connection().connection

    try:
        return collect_report(
            raw_conn,
            period_start,
            period_end,
            site=site,
            asset=asset,
            organization_id=organization_id,
        )
    except FilterError as e:
        raise HTTPException(status_code=404, detail=str(e))
