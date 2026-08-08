-- 006_workorder_client_ticket.sql
-- Captures client-raised tickets that reach technicians as printed A4 sheets
-- from the client helpdesk portal. Technicians enter them into EquipTrack
-- later the same day, so reportedAt and createdAt will differ.
--
-- externalRef     the client case number, e.g. CASE-336864
-- reportedBy      name of the person who raised it on the client portal
-- clientCategory  trade label as printed ("AC Works", "Electrical").
--                 Deliberately free text, NOT the FaultCategory enum:
--                 that is the technician diagnosis and stays on MaintenanceLog.
-- sourceType      PORTAL_PRINTOUT | PHONE | INTERNAL_INSPECTION

ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "externalRef"    TEXT;
ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "reportedBy"     TEXT;
ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "clientCategory" TEXT;
ALTER TABLE "WorkOrder" ADD COLUMN IF NOT EXISTS "sourceType"     TEXT;

CREATE INDEX IF NOT EXISTS "WorkOrder_externalRef_idx" ON "WorkOrder" ("externalRef");
