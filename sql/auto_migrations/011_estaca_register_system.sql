-- Passo final: registo no sistema após designação
ALTER TABLE bini_estaca_callings
  ADD COLUMN system_registered_by INT NULL AFTER designated_at;
ALTER TABLE bini_estaca_callings
  ADD COLUMN system_registered_at DATETIME(6) NULL AFTER system_registered_by;
