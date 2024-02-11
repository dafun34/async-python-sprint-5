from passlib.hash import bcrypt
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserService:

    @classmethod
    async def get_user_by_email(
        cls, session: AsyncSession, email: str
    ) -> bool:
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def user_register(cls, session: AsyncSession, register_data):
        query = insert(User).values(
            email=register_data.email,
            password=bcrypt.hash(register_data.password),
        )
        await session.execute(query)
        await session.commit()
