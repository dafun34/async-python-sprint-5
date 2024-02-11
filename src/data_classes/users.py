from pydantic import BaseModel, EmailStr, Field

from src.db.db import get_session

session = get_session()


class UserRegisterData(BaseModel):
    email: EmailStr = Field(description="Email address")
    password: str = Field(description="Password")
