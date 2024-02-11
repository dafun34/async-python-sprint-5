from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from passlib.hash import bcrypt

from src.core.config import get_settings
from src.db.db import async_session
from src.services.user import UserService

settings = get_settings()

login_manager = LoginManager(secret=settings.auth_secret, token_url="/auth")

router = APIRouter(tags=["Authentication"])


@login_manager.user_loader()
async def load_user(email: str):
    async with async_session() as session:
        user = await UserService.get_user_by_email(
            session=session, email=email
        )
    return user


@router.post("/auth")
async def login(data: OAuth2PasswordRequestForm = Depends()):
    email = data.username
    password = data.password
    user = await load_user(email)
    if not user:
        raise InvalidCredentialsException
    elif not bcrypt.verify(password, user.password):
        raise InvalidCredentialsException
    access_token = login_manager.create_access_token(data=dict(sub=email))
    return {"access_token": access_token, "token_type": "bearer"}
