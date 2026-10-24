from typing import Annotated
from uuid import UUID

from db.connect import Conn
from db.queries import users
from fastapi import Depends, HTTPException, Request


async def get_current_user(request: Request, conn: Conn) -> dict:
    """Load the signed-in user from the session cookie, or answer 401."""
    raw_id = request.session.get("user_id")
    if raw_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id = UUID(raw_id)
    except ValueError:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await users.get_user_by_id(conn, user_id)
    if user is None:
        # The cookie points at a user that no longer exists.
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
