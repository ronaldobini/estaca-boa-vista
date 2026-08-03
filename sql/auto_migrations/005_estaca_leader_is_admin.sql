-- Admin da ferramenta Estaca: flag paralelo ao chamado de liderança
ALTER TABLE bini_estaca_leaders
  ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0 AFTER ward_slug;

UPDATE bini_estaca_leaders
SET is_admin = 1, role = 'stake_presidency', ward_slug = NULL
WHERE role = 'admin';
