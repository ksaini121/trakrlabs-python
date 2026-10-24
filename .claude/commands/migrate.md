---
description: Generate a SQL migration from a changed SQL file and the changed SQL
argument-hint: <path/to/file.sql> <the changed SQL, or a description of it>
---

Create a Postgres migration for this project from the schema change described below.

Input: $ARGUMENTS

The first token is the file that contains the changed SQL. The rest is the changed SQL itself (or a description of it). If either is missing or ambiguous, ask before writing anything.

## Steps

1. Read the given file to see the full current schema context.
2. List `src/db/migrations/` (create it if missing). The next number is the highest existing prefix + 1, zero-padded to 4 digits (`0001`, `0002`, ...). Read the latest migrations so the new one is consistent with what already exists.
3. Work out what actually changed: compare the provided changed SQL against the file and the existing migrations. Migrate only the delta, never re-create objects that already exist.
4. Write two files for the yoyo runner:
   - `src/db/migrations/<NNNN>_<short_snake_case_description>.sql`, starting with the header line `-- depends: <previous migration id>` (the previous file's name without `.sql`, e.g. `-- depends: 0001_enable_pgvector`), then a blank line, then the SQL.
   - `src/db/migrations/<NNNN>_<short_snake_case_description>.rollback.sql` containing the SQL that undoes it. If it cannot be undone safely (data loss), say so and leave the rollback out.

## Rules

- Raw SQL only. No ORM, no Python migrations.
- Never edit an existing migration. Every change is a new file.
- Prefer idempotent forms where Postgres supports them (`IF NOT EXISTS`, `IF EXISTS`).
- Do not wrap in `BEGIN`/`COMMIT`; yoyo runs each migration in a transaction.
- Destructive or lossy changes (`DROP TABLE`, `DROP COLUMN`, type changes, a column rename that would otherwise look like drop + add, adding `NOT NULL` to a populated column) must be called out to the user before writing. For a rename, use `ALTER TABLE ... RENAME COLUMN`. For `NOT NULL` on existing data, add a default or a backfill step.
- pgvector: use the `vector(N)` type. The extension is enabled separately with `CREATE EXTENSION IF NOT EXISTS vector;`; `0001_enable_pgvector` already does this, so don't repeat it.
- Add indexes for new foreign keys, and an `hnsw` or `ivfflat` index for new vector columns used for similarity search, when the intent is clear.

## Output

After writing, show the new file's path and its contents, and list any assumptions or destructive operations in a short note. Do not run the migration; the user applies it with `cd src && uv run python -m db.migrate`.
