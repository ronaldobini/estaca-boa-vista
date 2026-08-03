-- Estaca Boa Vista: líderes e chamados
-- Aplicar em produção via auto-migrate ou manualmente.

CREATE TABLE IF NOT EXISTS bini_estaca_leaders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  role VARCHAR(48) NOT NULL,
  ward_slug VARCHAR(32) NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  UNIQUE KEY uq_bini_estaca_leader_user (user_id),
  KEY ix_bini_estaca_leader_role (role),
  KEY ix_bini_estaca_leader_ward (ward_slug),
  CONSTRAINT fk_bini_estaca_leader_user
    FOREIGN KEY (user_id) REFERENCES bini_users(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bini_estaca_callings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ward_slug VARCHAR(32) NOT NULL,
  person_name VARCHAR(255) NOT NULL,
  calling_title VARCHAR(255) NOT NULL,
  notes VARCHAR(500) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'indication',
  created_by_user_id INT NULL,
  created_by_role VARCHAR(48) NULL,
  indication_approved_by INT NULL,
  indication_approved_at DATETIME(6) NULL,
  hc_supported_by INT NULL,
  hc_supported_at DATETIME(6) NULL,
  interviewed_by INT NULL,
  interviewed_at DATETIME(6) NULL,
  sacrament_supported_by INT NULL,
  sacrament_supported_at DATETIME(6) NULL,
  designated_by INT NULL,
  designated_at DATETIME(6) NULL,
  rejected_by INT NULL,
  rejected_at DATETIME(6) NULL,
  rejected_at_status VARCHAR(32) NULL,
  rejection_reason VARCHAR(500) NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  KEY ix_bini_estaca_call_ward (ward_slug),
  KEY ix_bini_estaca_call_status (status),
  KEY ix_bini_estaca_call_created (created_at),
  CONSTRAINT fk_bini_estaca_call_creator
    FOREIGN KEY (created_by_user_id) REFERENCES bini_users(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
