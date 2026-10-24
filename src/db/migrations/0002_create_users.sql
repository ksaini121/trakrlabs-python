-- depends: 0001_enable_pgvector

CREATE TABLE IF NOT EXISTS users (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id   bigint      NOT NULL UNIQUE,
    username    text        NOT NULL,
    email       text,
    avatar_url  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
