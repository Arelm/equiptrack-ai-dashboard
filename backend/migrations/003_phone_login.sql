-- Phone number as a login identifier.
--
-- Nine field technicians do not have work email addresses and will not
-- remember ones invented for them. They know their phone number. Email stays
-- as the identity key in the database — it is already the unique column and
-- half the system references it — but a technician never has to type it.
--
-- Stored normalised: +234XXXXXXXXXX, no spaces, no dashes. The API normalises
-- on the way in so 08012345678, +2348012345678 and 234 801 234 5678 all
-- resolve to one stored value.
--
-- Additive and idempotent.

BEGIN;

-- Two people cannot share a number. Without this, a login by phone could match
-- more than one row and the system would have to guess which.
CREATE UNIQUE INDEX IF NOT EXISTS "User_phone_unique_idx"
  ON "User" ("phone")
  WHERE "phone" IS NOT NULL;

COMMIT;