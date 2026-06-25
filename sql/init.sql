CREATE DATABASE IF NOT EXISTS insightpilot
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE insightpilot;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  is_admin TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS datasets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name VARCHAR(120) NOT NULL,
  original_name VARCHAR(255) NOT NULL,
  stored_name VARCHAR(255) NOT NULL,
  file_type VARCHAR(20) NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  processed_path VARCHAR(500),
  size_bytes BIGINT DEFAULT 0,
  row_count INT DEFAULT 0,
  col_count INT DEFAULT 0,
  columns_json LONGTEXT,
  quality_json LONGTEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX idx_dataset_user(user_id),
  CONSTRAINT fk_dataset_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cleaning_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  dataset_id INT NOT NULL,
  user_id INT NOT NULL,
  operation VARCHAR(50) NOT NULL,
  params_json LONGTEXT,
  before_rows INT,
  after_rows INT,
  created_at DATETIME NOT NULL,
  INDEX idx_clean_dataset(dataset_id),
  CONSTRAINT fk_clean_dataset FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
  CONSTRAINT fk_clean_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS analysis_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  dataset_id INT NOT NULL,
  user_id INT NOT NULL,
  name VARCHAR(120) NOT NULL,
  analysis_type VARCHAR(50) NOT NULL,
  params_json LONGTEXT,
  result_json LONGTEXT,
  chart_json LONGTEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'success',
  error_message LONGTEXT,
  created_at DATETIME NOT NULL,
  INDEX idx_analysis_dataset(dataset_id),
  CONSTRAINT fk_analysis_dataset FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
  CONSTRAINT fk_analysis_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ai_conversations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  dataset_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT fk_conv_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_conv_dataset FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ai_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  conversation_id INT NOT NULL,
  role VARCHAR(20) NOT NULL,
  content LONGTEXT NOT NULL,
  plan_json LONGTEXT,
  created_at DATETIME NOT NULL,
  CONSTRAINT fk_message_conv FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reports (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  dataset_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  summary LONGTEXT,
  content_html LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT fk_report_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_report_dataset FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
