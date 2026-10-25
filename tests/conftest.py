import os

# Settings has required fields; give them values before any app module imports it.
for key in (
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "GITHUB_PROJECT_PAT",
    "SECRET_KEY",
    "FRONTEND_URL",
):
    os.environ.setdefault(key, "test-value")
