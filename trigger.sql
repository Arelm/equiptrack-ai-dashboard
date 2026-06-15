 CREATE OR REPLACE FUNCTION deduct_parts_inventory()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE "PartsInventory"
  SET quantity = quantity - NEW."quantityUsed",
      "updatedAt" = NOW()
  WHERE id = NEW."partId";

  INSERT INTO "Alert" (id, type, message, severity, "isRead", "organizationId", "assetId", "createdAt")
  SELECT
    gen_random_uuid()::text,
    'PART_LOW',
    'Parts inventory low: ' || p.name || ' has ' || (p.quantity - NEW."quantityUsed") || ' units remaining',
    'HIGH',
    false,
    p."organizationId",
    NULL,
    NOW()
  FROM "PartsInventory" p
  WHERE p.id = NEW."partId"
    AND (p.quantity - NEW."quantityUsed") <= p."reorderLevel";

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_deduct_parts
AFTER INSERT ON "PartsUsed"
FOR EACH ROW
EXECUTE FUNCTION deduct_parts_inventory();
