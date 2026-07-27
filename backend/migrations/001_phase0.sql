-- EquipTrack AI — Phase 0 + Phase 1 migration
-- Additive only. No column is dropped, no existing row is rewritten except the
-- legacy flag in step 8. Safe to re-run: every statement is idempotent.
--
-- Run with:  psql "$DATABASE_URL" -f backend/migrations/001_phase0.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. User: password hash (already present in the live DB, absent from models.py)
-- ---------------------------------------------------------------------------
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "passwordHash" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "phone" TEXT;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "isActive" BOOLEAN NOT NULL DEFAULT TRUE;

-- phone is nullable on purpose: it is required only for WhatsApp notification,
-- which is flagged off until 360dialog production access clears.

-- ---------------------------------------------------------------------------
-- 2. WorkOrder: lifecycle timestamps + legacy flag
-- ---------------------------------------------------------------------------
ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "assignedAt"  TIMESTAMP;
ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "acceptedAt"  TIMESTAMP;
ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "reportedAt"  TIMESTAMP;
ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "isLegacy"    BOOLEAN NOT NULL DEFAULT FALSE;

-- Four states, five timestamps. Acceptance is a timestamp, not a status value,
-- so WorkOrderStatusEnum is left exactly as it is.

-- ---------------------------------------------------------------------------
-- 3. WorkOrderAssignment: history, not overwrite
-- ---------------------------------------------------------------------------
ALTER TABLE "WorkOrderAssignment" ADD COLUMN IF NOT EXISTS "assignedBy"   TEXT;
ALTER TABLE "WorkOrderAssignment" ADD COLUMN IF NOT EXISTS "acceptedAt"   TIMESTAMP;
ALTER TABLE "WorkOrderAssignment" ADD COLUMN IF NOT EXISTS "unassignedAt" TIMESTAMP;
ALTER TABLE "WorkOrderAssignment" ADD COLUMN IF NOT EXISTS "reason"       TEXT;

-- One active assignment per work order = the row where unassignedAt IS NULL.
CREATE UNIQUE INDEX IF NOT EXISTS "WorkOrderAssignment_active_idx"
  ON "WorkOrderAssignment" ("workOrderId")
  WHERE "unassignedAt" IS NULL;

CREATE INDEX IF NOT EXISTS "WorkOrderAssignment_user_idx"
  ON "WorkOrderAssignment" ("userId")
  WHERE "unassignedAt" IS NULL;

-- ---------------------------------------------------------------------------
-- 4. MaintenanceLog: explicit parts declaration + one report per job
-- ---------------------------------------------------------------------------
ALTER TABLE "MaintenanceLog" ADD COLUMN IF NOT EXISTS "partsUsedDeclared" BOOLEAN;

-- NULL  = we never asked (legacy rows)
-- FALSE = technician declared no parts needed
-- TRUE  = at least one PartsUsed row
-- These are three different facts. Never collapse them.

CREATE UNIQUE INDEX IF NOT EXISTS "MaintenanceLog_workorder_idx"
  ON "MaintenanceLog" ("workOrderId");

-- ---------------------------------------------------------------------------
-- 5. PartsUsed: source + catalogue escape hatch
-- ---------------------------------------------------------------------------
ALTER TABLE "PartsUsed" ADD COLUMN IF NOT EXISTS "source"      TEXT;
ALTER TABLE "PartsUsed" ADD COLUMN IF NOT EXISTS "partNameRaw" TEXT;

-- partId becomes nullable so "Part not listed" can be recorded rather than lost.
ALTER TABLE "PartsUsed" ALTER COLUMN "partId" DROP NOT NULL;

DO $$
BEGIN
  ALTER TABLE "PartsUsed" ADD CONSTRAINT "PartsUsed_source_check"
    CHECK ("source" IS NULL OR "source" IN
      ('van_stock', 'company_store', 'purchased_on_site', 'client_supplied'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  ALTER TABLE "PartsUsed" ADD CONSTRAINT "PartsUsed_identified_check"
    CHECK ("partId" IS NOT NULL OR "partNameRaw" IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  ALTER TABLE "PartsUsed" ADD CONSTRAINT "PartsUsed_quantity_check"
    CHECK ("quantityUsed" > 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ---------------------------------------------------------------------------
-- 6. StockMovement: append-only ledger
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "StockMovement" (
  "id"             TEXT PRIMARY KEY,
  "partId"         TEXT NOT NULL REFERENCES "PartsInventory"("id"),
  "delta"          INTEGER NOT NULL,
  "reason"         TEXT NOT NULL,
  "refType"        TEXT,
  "refId"          TEXT,
  "locationId"     TEXT REFERENCES "Location"("id"),
  "createdBy"      TEXT REFERENCES "User"("id"),
  "note"           TEXT,
  "createdAt"      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- locationId is nullable and unused in Phase 1 (single company pool).
-- It exists now so per-van stock in Phase 2 is additive, not a migration.

DO $$
BEGIN
  ALTER TABLE "StockMovement" ADD CONSTRAINT "StockMovement_reason_check"
    CHECK ("reason" IN
      ('job_consumption', 'receipt', 'adjustment', 'return', 'correction'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  ALTER TABLE "StockMovement" ADD CONSTRAINT "StockMovement_delta_check"
    CHECK ("delta" <> 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS "StockMovement_part_idx" ON "StockMovement" ("partId", "createdAt");
CREATE INDEX IF NOT EXISTS "StockMovement_ref_idx"  ON "StockMovement" ("refType", "refId");

-- ---------------------------------------------------------------------------
-- 7. AuditLog: resolve overrides first, everything else later
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "AuditLog" (
  "id"         TEXT PRIMARY KEY,
  "actorId"    TEXT REFERENCES "User"("id"),
  "action"     TEXT NOT NULL,
  "entityType" TEXT NOT NULL,
  "entityId"   TEXT NOT NULL,
  "reason"     TEXT,
  "metadata"   TEXT,
  "createdAt"  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS "AuditLog_entity_idx" ON "AuditLog" ("entityType", "entityId");
CREATE INDEX IF NOT EXISTS "AuditLog_action_idx" ON "AuditLog" ("action", "createdAt");

-- ---------------------------------------------------------------------------
-- 8. Cutover: everything that already exists predates the rules
-- ---------------------------------------------------------------------------
UPDATE "WorkOrder" SET "isLegacy" = TRUE WHERE "createdAt" < NOW();

-- Legacy work orders bypass the assignment and report gates. They happened
-- before the rules existed and no amount of blocking changes that. They are
-- excluded from compliance metrics and included in operational ones.

-- Existing PartsUsed rows keep quantityUsed as recorded and get no source:
-- NULL source means "recorded before we asked", which is the honest reading.

COMMIT;