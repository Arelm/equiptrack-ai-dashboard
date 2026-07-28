-- Client site details on Location.
--
-- Locations are not JDAEM sites. They are client sites: Sterling Oil
-- plots on the Island, each one identified by a plot number such as
-- 217B or OML13A, each with its own site supervisor. A technician
-- sent to a plot needs to know whose site it is, which area it is in
-- and who to call on arrival.
--
-- Supervisors are Sterling Oil staff working under a labour
-- contractor. They are contacts, not system users, so they are stored
-- as plain columns here and get no login and no row in "User".
-- The contractor changes; the plot does not.
--
-- "area" is deliberately free text rather than a CHECK constraint.
-- The list (V.I., Banana Island, Ikeja, Elegushi, Lekki, Other) is
-- enforced in the form, so a new area never requires a migration.
--
-- "client" is text for the same reason. Sterling Oil is the only
-- client today. If a second one arrives with its own contacts and
-- contracts, it earns its own table then, not before.
--
-- Existing rows are backfilled as active so nothing disappears from
-- the app the moment this runs.
--
-- Additive and idempotent.

BEGIN;

ALTER TABLE "Location"
  ADD COLUMN IF NOT EXISTS "client"          TEXT,
  ADD COLUMN IF NOT EXISTS "supervisorName"  TEXT,
  ADD COLUMN IF NOT EXISTS "supervisorPhone" TEXT,
  ADD COLUMN IF NOT EXISTS "area"            TEXT,
  ADD COLUMN IF NOT EXISTS "isActive"        BOOLEAN NOT NULL DEFAULT TRUE;

-- Retired plots are hidden, not deleted, so their work order history
-- stays intact. Every list in the app filters on this, so an index
-- keeps that cheap as the site count grows.
CREATE INDEX IF NOT EXISTS "Location_active_idx"
  ON "Location" ("organizationId", "isActive");

COMMIT;
