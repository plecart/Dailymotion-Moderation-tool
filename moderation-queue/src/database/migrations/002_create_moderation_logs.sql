-- Migration: Create moderation_logs table
-- Stores audit trail of all moderation actions on videos

CREATE TABLE IF NOT EXISTS moderation_logs (
    id SERIAL PRIMARY KEY,
    video_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    moderator VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT moderation_logs_video_id_fkey FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE,
    CONSTRAINT valid_log_status CHECK (status IN ('pending', 'spam', 'not spam'))
);

CREATE INDEX IF NOT EXISTS idx_moderation_logs_video_id ON moderation_logs(video_id);
CREATE INDEX IF NOT EXISTS idx_moderation_logs_created_at ON moderation_logs(created_at);
