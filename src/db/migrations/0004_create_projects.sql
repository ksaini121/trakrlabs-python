-- depends: 0003_add_user_role

CREATE TABLE IF NOT EXISTS projects (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    title             text        NOT NULL,
    description       text,
    github_repo_name  text        NOT NULL,
    project_admin_id  uuid        NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    created_by        uuid        NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    modified_by       uuid        NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS projects_project_admin_id_idx ON projects (project_admin_id);
CREATE INDEX IF NOT EXISTS projects_created_by_idx ON projects (created_by);
CREATE INDEX IF NOT EXISTS projects_modified_by_idx ON projects (modified_by);
