from contextlib import asynccontextmanager

from config.settings import settings
from core.scheduler import create_scheduler
from db.connect import close_pool, open_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.v1.routes import auth
from api.v1.routes import issue
from api.v1.routes import project


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await close_pool()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    lifespan=lifespan,
)

# Middleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.is_production,
    max_age=60 * 60 * 24 * 7,
)
# Added last so it is the outermost layer and also covers preflight and error responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url.rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Routers
app.include_router(auth.router)
app.include_router(project.router)
app.include_router(issue.router)
