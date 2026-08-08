-- 005_fault_category.sql
-- Records the FaultCategory enum and MaintenanceLog.faultCategory column,
-- which were applied directly to the database in August 2026 without a
-- migration file. Idempotent: safe to run against a database that already
-- has them.

DO $$ BEGIN
    CREATE TYPE "FaultCategory" AS ENUM (
        'REFRIGERANT_LEAKAGE','LOW_REFRIGERANT','CONDENSER_LEAKAGE','EVAPORATOR_LEAKAGE',
        'COMPRESSOR_FAULT','CAPACITOR_FAULT','CONTACTOR_FAULT','FAN_MOTOR_FAULT','BLOWER_FAULT',
        'CAPILLARY_BLOCK','FILTER_BLOCKED','DRAINAGE_BLOCK','AIRFLOW_DUCTING','ELECTRICAL_SUPPLY',
        'LOW_VOLTAGE','PANEL_FAULT','THERMOSTAT_CONTROL','ERROR_CODE','ROUTINE_SERVICE','OTHER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE "MaintenanceLog" ADD COLUMN IF NOT EXISTS "faultCategory" "FaultCategory";
