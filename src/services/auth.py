import logging

from authlib.integrations.starlette_client import OAuthError
from core.oauth import oauth
from db.queries import users
from fastapi import HTTPException, Request
from psycopg import AsyncConnection

logger = logging.getLogger("uvicorn.error")


class AuthService:
    async def github_callback(self, request: Request, conn: AsyncConnection) -> dict:
        """Finish the GitHub login: get a token, load the profile, save the user, start the session."""
        try:
            token = await oauth.github.authorize_access_token(request)
        except OAuthError as err:
            raise HTTPException(status_code=400, detail=err.description or err.error)

        resp = await oauth.github.get("user", token=token)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Could not load GitHub profile")
        profile = resp.json()

        # The profile email is null when the user hides it, so ask the emails endpoint.
        email = profile.get("email") or await self._primary_email(token)

        user = await users.upsert_user(
            conn,
            github_id=profile["id"],
            username=profile["login"],
            email=email,
            avatar_url=profile.get("avatar_url"),
        )
        await conn.commit()

        request.session.clear()
        request.session["user_id"] = str(user["id"])
        return user

    async def _primary_email(self, token: dict) -> str | None:
        resp = await oauth.github.get("user/emails", token=token)
        if resp.status_code != 200:
            logger.warning(
                "GitHub /user/emails returned %s (granted scope: %r): %s",
                resp.status_code,
                token.get("scope"),
                resp.text,
            )
            return None
        emails = resp.json()
        for item in emails:
            if item["primary"] and item["verified"]:
                return item["email"]
        logger.warning(
            "No primary verified email in %d GitHub email(s) (granted scope: %r)",
            len(emails),
            token.get("scope"),
        )
        return None
