SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT NOT NULL,
    language VARCHAR(8) NOT NULL DEFAULT 'en',
    language_selected TINYINT(1) NOT NULL DEFAULT 0,
    started TINYINT(1) NOT NULL DEFAULT 0,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_bot TINYINT(1) NOT NULL DEFAULT 0,
    bot_blocked TINYINT(1) NOT NULL DEFAULT 0,
    owner_note VARCHAR(1200),
    PRIMARY KEY (user_id),
    KEY idx_users_started (started),
    KEY idx_users_username (username),
    KEY idx_users_blocked (bot_blocked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT NOT NULL,
    title VARCHAR(512),
    chat_type VARCHAR(32),
    language VARCHAR(8) NOT NULL DEFAULT 'en',
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    bot_in_chat TINYINT(1) NOT NULL DEFAULT 1,
    moderate_admins TINYINT(1) NOT NULL DEFAULT 1,
    threshold DECIMAL(5,4) NOT NULL DEFAULT 0.7500,
    action VARCHAR(16) NOT NULL DEFAULT 'delete',
    warn_limit INT NOT NULL DEFAULT 3,
    escalation VARCHAR(16) NOT NULL DEFAULT 'none',
    mute_minutes INT NOT NULL DEFAULT 10,
    custom_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id),
    KEY idx_chats_active (bot_in_chat, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS detections (
    media_key VARCHAR(255) NOT NULL,
    content_sha256 CHAR(64),
    detector_signature VARCHAR(255) NOT NULL DEFAULT '',
    nsfw TINYINT(1) NOT NULL,
    confidence DECIMAL(8,7) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (media_key),
    KEY idx_detections_hash (content_sha256),
    KEY idx_detections_signature (detector_signature),
    KEY idx_detections_last_used (last_used_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS warnings (
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id, user_id),
    KEY idx_warnings_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS exempt_users (
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id, user_id),
    KEY idx_exempt_chat (chat_id),
    KEY idx_exempt_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS blocked_media (
    chat_id BIGINT NOT NULL,
    media_key VARCHAR(255) NOT NULL,
    content_sha256 CHAR(64),
    kind VARCHAR(32),
    blocked_by BIGINT NOT NULL,
    blocked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id, media_key),
    KEY idx_blocked_chat (chat_id),
    KEY idx_blocked_hash (content_sha256)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_users (
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_bot TINYINT(1) NOT NULL DEFAULT 0,
    message_count BIGINT NOT NULL DEFAULT 0,
    last_message_id BIGINT,
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id, user_id),
    KEY idx_chat_users_chat_seen (chat_id, last_seen),
    KEY idx_chat_users_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_stats (
    chat_id BIGINT NOT NULL,
    checked BIGINT NOT NULL DEFAULT 0,
    nsfw BIGINT NOT NULL DEFAULT 0,
    actions BIGINT NOT NULL DEFAULT 0,
    deleted BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS daily_stats (
    chat_id BIGINT NOT NULL,
    day DATE NOT NULL,
    checked BIGINT NOT NULL DEFAULT 0,
    nsfw BIGINT NOT NULL DEFAULT 0,
    actions BIGINT NOT NULL DEFAULT 0,
    deleted BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, day),
    KEY idx_daily_stats_day (day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT NOT NULL AUTO_INCREMENT,
    chat_id BIGINT,
    actor_id BIGINT,
    actor_name VARCHAR(512),
    event_type VARCHAR(64) NOT NULL,
    details VARCHAR(1800),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_audit_logs_chat (chat_id, created_at),
    KEY idx_audit_logs_actor (actor_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stats (
    stat_key VARCHAR(64) NOT NULL,
    value BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (stat_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO stats (stat_key, value) VALUES ('checked', 0);
INSERT IGNORE INTO stats (stat_key, value) VALUES ('nsfw', 0);
