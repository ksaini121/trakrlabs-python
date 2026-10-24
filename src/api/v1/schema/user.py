from uuid import UUID

from pydantic import BaseModel


class UserOut(BaseModel):
    id: UUID
    github_id: int
    username: str
    email: str | None
    avatar_url: str | None
