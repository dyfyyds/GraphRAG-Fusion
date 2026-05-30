-- ============================================================
--  RAG 智能问答系统 - MySQL 初始化脚本
--  创建时间: 2026-05-28
-- ============================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ============================================================
--  1. 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `email` VARCHAR(100) DEFAULT NULL,
    `role` ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    `avatar` VARCHAR(255) DEFAULT NULL,
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1=启用, 0=禁用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    KEY `idx_role` (`role`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  2. 文档表
-- ============================================================
CREATE TABLE IF NOT EXISTS `documents` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_type` ENUM('pdf', 'docx', 'txt', 'md') NOT NULL,
    `file_size` BIGINT NOT NULL DEFAULT 0,
    `status` ENUM('pending', 'parsing', 'building_graph', 'completed', 'failed', 'graph_failed') NOT NULL DEFAULT 'pending',
    `chunk_count` INT NOT NULL DEFAULT 0,
    `error_message` TEXT DEFAULT NULL,
    `uploaded_by` BIGINT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_status` (`status`),
    KEY `idx_uploaded_by` (`uploaded_by`),
    CONSTRAINT `fk_documents_user` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  3. 文档分块表
-- ============================================================
CREATE TABLE IF NOT EXISTS `chunks` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `document_id` BIGINT NOT NULL,
    `content` TEXT NOT NULL,
    `chunk_index` INT NOT NULL DEFAULT 0,
    `page_number` INT DEFAULT NULL,
    `vector_id` VARCHAR(100) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_document_id` (`document_id`),
    KEY `idx_vector_id` (`vector_id`),
    CONSTRAINT `fk_chunks_document` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  4. 对话表
-- ============================================================
CREATE TABLE IF NOT EXISTS `conversations` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `title` VARCHAR(255) NOT NULL DEFAULT '新对话',
    `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0=正常, 1=已删除',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    CONSTRAINT `fk_conversations_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  5. 消息表
-- ============================================================
CREATE TABLE IF NOT EXISTS `messages` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `conversation_id` BIGINT NOT NULL,
    `role` ENUM('user', 'assistant') NOT NULL,
    `content` TEXT NOT NULL,
    `sources` JSON DEFAULT NULL,
    `feedback` TINYINT NOT NULL DEFAULT 0 COMMENT '1=好评, -1=差评, 0=未评',
    `feedback_text` TEXT DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_conversation_id` (`conversation_id`),
    KEY `idx_role` (`role`),
    CONSTRAINT `fk_messages_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  6. 系统配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS `system_config` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `config_key` VARCHAR(100) NOT NULL,
    `config_value` TEXT NOT NULL,
    `description` VARCHAR(255) DEFAULT NULL,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  初始数据：默认管理员账户
--  密码: admin123 (bcrypt 哈希)
-- ============================================================
INSERT INTO `users` (`username`, `password_hash`, `email`, `role`, `status`)
VALUES (
    'admin',
    '$2b$12$dYRUZMoQyiFFIjMoF8ljR.2k.I5lDgwWBq2hKyZEKOSSwO86nECh.',
    'admin@rag-system.local',
    'admin',
    1
) ON DUPLICATE KEY UPDATE `username` = `username`;

-- ============================================================
--  初始数据：系统默认配置
-- ============================================================
INSERT INTO `system_config` (`config_key`, `config_value`, `description`) VALUES
('llm_model', 'mimo-v2.5-pro', '默认 LLM 模型名称'),
('llm_config', '{"model": "mimo-v2.5-pro", "api_url": "https://token-plan-cn.xiaomimimo.com/v1", "temperature": 0.7, "top_p": 0.9, "max_tokens": 4096}', 'LLM 模型配置'),
('embedding_model', '{"model": "BAAI/bge-m3", "dimension": 1024, "api_url": "https://api.siliconflow.cn/v1"}', 'Embedding 模型配置'),
('model_profiles', '[{"name":"默认 LLM","type":"llm","model":"mimo-v2.5-pro","api_url":"https://token-plan-cn.xiaomimimo.com/v1"},{"name":"默认 Embedding","type":"embedding","model":"BAAI/bge-m3","api_url":"https://api.siliconflow.cn/v1","dimension":1024}]', '已保存模型配置'),
('retrieval_config', '{"top_k": 5, "similarity_threshold": 0.7, "vector_weight": 0.6, "graph_weight": 0.4}', '检索配置'),
('kg_config', '{"model": "mimo-v2.5-pro", "entity_types": "组织,法规,政策,文件", "relation_types": "发布,引用,规范,约束"}', '知识图谱抽取配置'),
('chunk_config', '{"chunk_size": 512, "chunk_overlap": 50}', '分块配置'),
('upload_config', '{"max_file_size_mb": 50, "max_files_per_upload": 10}', '上传限制配置')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`);
