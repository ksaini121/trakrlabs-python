from authlib.integrations.starlette_client import OAuth
from config.settings import settings

oauth = OAuth()

oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    api_base_url=settings.github_base_url,
    access_token_url=settings.github_access_token_url,
    authorize_url=settings.github_authorize_url,
    client_kwargs={"scope": "read:user user:email"},
)