-- depends: 0004_create_projects

CREATE TABLE IF NOT EXISTS issues (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id         uuid        NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    github_issue_id    bigint      NOT NULL,
    number             integer     NOT NULL,
    title              text        NOT NULL,
    body               text,
    state              text        NOT NULL CHECK (state IN ('open', 'closed')),
    state_reason       text,
    html_url           text        NOT NULL,
    author_login       text,
    assignees          jsonb       NOT NULL DEFAULT '[]',
    labels             jsonb       NOT NULL DEFAULT '[]',
    milestone          text,
    comments_count     integer     NOT NULL DEFAULT 0,
    github_created_at  timestamptz NOT NULL,
    github_updated_at  timestamptz NOT NULL,
    github_closed_at   timestamptz,
    synced_at          timestamptz NOT NULL DEFAULT now(),
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, github_issue_id)
);

CREATE INDEX IF NOT EXISTS issues_project_id_state_idx
    ON issues (project_id, state);
CREATE INDEX IF NOT EXISTS issues_project_id_github_updated_at_idx
    ON issues (project_id, github_updated_at DESC);
