-- Responsáveis por passo (3–5) + histórico de eventos do processo
ALTER TABLE bini_estaca_callings
  ADD COLUMN interview_assignee_id INT NULL AFTER designated_at,
  ADD COLUMN sacrament_assignee_id INT NULL AFTER interview_assignee_id,
  ADD COLUMN designation_assignee_id INT NULL AFTER sacrament_assignee_id;

CREATE TABLE IF NOT EXISTS bini_estaca_calling_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  calling_id INT NOT NULL,
  event_type VARCHAR(48) NOT NULL,
  actor_user_id INT NULL,
  actor_role VARCHAR(48) NULL,
  actor_label VARCHAR(128) NULL,
  detail VARCHAR(500) NULL,
  created_at DATETIME(6) NOT NULL,
  KEY ix_bini_estaca_ev_calling (calling_id),
  KEY ix_bini_estaca_ev_type (event_type),
  KEY ix_bini_estaca_ev_created (created_at),
  CONSTRAINT fk_bini_estaca_ev_calling
    FOREIGN KEY (calling_id) REFERENCES bini_estaca_callings(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
