from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse

from src.core.log import LoggerDependency
from src.data_classes.users import UserRegisterData
from src.db.db import SessionDependency
from src.services.user import UserService

router = APIRouter(tags=["Users"])


@router.post("/register")
async def user_register(
    register_data: UserRegisterData,
    session: SessionDependency,
    logger: LoggerDependency,
) -> ORJSONResponse:
    user = await UserService.get_user_by_email(
        session=session, email=register_data.email
    )
    if user:
        logger.warning(f"User with {register_data.email} email already exists")
        raise HTTPException(status_code=422, detail="Email already taken")
    try:
        await UserService.user_register(
            session=session, register_data=register_data
        )
        return ORJSONResponse(
            content={
                "message": (
                    f"User with {register_data.email} successfully register"
                )
            },
            status_code=201,
        )
    except Exception as e:
        logger.error(f"User registration is fail with error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
