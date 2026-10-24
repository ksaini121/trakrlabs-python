-- depends: 0002_create_users

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS user_role text NOT NULL DEFAULT 'user'
        CONSTRAINT users_user_role_check CHECK (user_role IN ('user', 'admin'));
