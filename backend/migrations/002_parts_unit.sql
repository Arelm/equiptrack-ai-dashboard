-- Unit of measure on the parts catalogue.
--
-- Without it, "quantity 5" is ambiguous: five metres of 1/2" copper, five
-- pieces of Armaflex, and five kilos of R-32 are different things, and the
-- technician has no way to tell the form which he means.
--
-- Additive and idempotent.

BEGIN;

ALTER TABLE "PartsInventory" ADD COLUMN IF NOT EXISTS "unit" TEXT NOT NULL DEFAULT 'pcs';
ALTER TABLE "PartsInventory" ADD COLUMN IF NOT EXISTS "category" TEXT;

DO $$
BEGIN
  ALTER TABLE "PartsInventory" ADD CONSTRAINT "PartsInventory_unit_check"
    CHECK ("unit" IN ('pcs', 'm', 'kg', 'length', 'set', 'litre'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Quantity becomes decimal: refrigerant is charged in fractions of a kilo and
-- pipe is cut to fractions of a metre. An integer column would force the
-- technician to round, and rounded stock is stock you cannot reconcile.
ALTER TABLE "PartsInventory" ALTER COLUMN "quantity" TYPE NUMERIC(12,2);
ALTER TABLE "PartsUsed" ALTER COLUMN "quantityUsed" TYPE NUMERIC(12,2);
ALTER TABLE "StockMovement" ALTER COLUMN "delta" TYPE NUMERIC(12,2);

COMMIT;