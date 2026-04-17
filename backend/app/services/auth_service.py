from datetime import datetime, timedelta

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_random_token,
    get_password_hash,
    verify_password,
)
from ..database import User
from ..schemas_auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)


INVALID_TOKEN_ERROR = HTTPException(status_code=401, detail="Invalid token")


def build_authenticated_user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
    }


def build_login_response(user: User) -> dict:
    return {
        "access_token": create_access_token(data={"sub": user.username}),
        "token_type": "bearer",
        "user": build_authenticated_user_payload(user),
    }


def assign_password_reset_token(user: User) -> str:
    user.reset_token = create_random_token()
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
    return user.reset_token


def clear_password_reset_state(user: User, new_password: str) -> None:
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None


def decode_username_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise INVALID_TOKEN_ERROR from exc

    username = payload.get("sub")
    if not username:
        raise INVALID_TOKEN_ERROR

    return username


def get_user_by_login(db: Session, username_or_email: str) -> User | None:
    return db.query(User).filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_current_user_from_token(db: Session, token: str) -> User:
    username = decode_username_from_token(token)
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def register_user(db: Session, user_data: RegisterRequest) -> dict:
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    db_user = User(
        username=user_data.email,
        email=user_data.email,
        full_name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "User created successfully", "user_id": db_user.id}


def login_user(db: Session, user_data: LoginRequest) -> dict:
    user = get_user_by_login(db, user_data.username)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return build_login_response(user)


def create_password_reset_token(
    db: Session, request: ForgotPasswordRequest
) -> ForgotPasswordResponse:
    user = get_user_by_login(db, request.username)
    if not user:
        return ForgotPasswordResponse(token="user_not_found_dummy_token")

    token = assign_password_reset_token(user)
    db.commit()

    return ForgotPasswordResponse(token=token)


def reset_user_password(db: Session, request: ResetPasswordRequest) -> dict:
    user = db.query(User).filter(
        User.reset_token == request.token,
        User.reset_token_expires > datetime.utcnow(),
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    clear_password_reset_state(user, request.new_password)
    db.commit()

    return {"message": "Password reset successfully"}
