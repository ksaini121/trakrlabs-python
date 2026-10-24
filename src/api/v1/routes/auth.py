from api.deps import CurrentUser
from api.v1.schema.user import UserOut
from config.settings import settings
from core.oauth import oauth
from db.connect import Conn
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()


@router.get("/github/login")
async def github_login(request: Request):
    redirect_uri = str(request.url_for("github_callback"))
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback")
async def github_callback(request: Request, conn: Conn):
    await auth_service.github_callback(request, conn)
    return RedirectResponse(settings.frontend_url)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.post("/logout", status_code=204)
async def logout(request: Request):
    request.session.clear()
