-- Migration: Create videos table
-- Stores videos in the moderation queue with their current status

CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    video_id BIGINT UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    assigned_to VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_status CHECK (status IN ('pending', 'spam', 'not spam'))
);

-- Indexes for filtering and ordering
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_assigned_to ON videos(assigned_to);
CREATE INDEX idx_videos_created_at ON videos(created_at);

-- Keep updated_at in sync on UPDATE (DEFAULT applies only on INSERT)
CREATE OR REPLACE FUNCTION videos_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS videos_updated_at ON videos;
CREATE TRIGGER videos_updated_at
    BEFORE UPDATE ON videos
    FOR EACH ROW
    EXECUTE FUNCTION videos_set_updated_at();
