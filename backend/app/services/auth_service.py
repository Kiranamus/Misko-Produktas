from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import os

from app.services.email_service import send_password_reset_email

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


INVALID_TOKEN_ERROR = HTTPException(status_code=401, detail="Neteisingas prisijungimo tokenas.")
PASSWORD_RULES_MESSAGE = (
    "Slaptažodis turi būti bent 8 simbolių, turėti bent vieną didžiąją raidę, "
    "bent vieną skaičių ir bent vieną specialų simbolį."
)


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
        raise HTTPException(status_code=401, detail="Naudotojas nerastas.")
    return user


def validate_password_strength(password: str) -> None:
    has_upper = any(char.isupper() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_special = any(not char.isalnum() for char in password)

    if len(password) < 8 or not has_upper or not has_digit or not has_special:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PASSWORD_RULES_MESSAGE,
        )


def build_frontend_url(frontend_url: str) -> str:
    parsed = urlsplit(frontend_url.strip())
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def register_user(db: Session, user_data: RegisterRequest) -> dict:
    validate_password_strength(user_data.password)

    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naudotojas su šiuo el. pašto adresu jau egzistuoja.",
        )

    db_user = User(
        username=user_data.email,
        email=user_data.email,
        full_name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        email_verified=True,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {
        "message": "Paskyra sukurta sėkmingai. Dabar galite prisijungti.",
        "user_id": db_user.id,
    }


def login_user(db: Session, user_data: LoginRequest) -> dict:
    user = get_user_by_login(db, user_data.username)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neteisingas el. paštas arba slaptažodis.",
        )

    return build_login_response(user)


def create_password_reset_token(
    db: Session, request: ForgotPasswordRequest
) -> ForgotPasswordResponse:
    user = get_user_by_login(db, request.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El. paštas nerastas duomenų bazėje.",
        )

    token = assign_password_reset_token(user)
    db.commit()

    frontend_url = build_frontend_url(os.getenv("FRONTEND_URL", "https://forestforyou.eu"))
    reset_link = f"{frontend_url}/#/reset-password-confirm?token={token}"

    try:
        send_password_reset_email(user.email, reset_link)
    except Exception as e:
        print("EMAIL SEND ERROR:", e)
        raise HTTPException(
            status_code=500,
            detail=f"Nepavyko išsiųsti el. laiško: {str(e)}"
        )

    return ForgotPasswordResponse(token="email_sent")


def reset_user_password(db: Session, request: ResetPasswordRequest) -> dict:
    user = db.query(User).filter(
        User.reset_token == request.token,
        User.reset_token_expires > datetime.utcnow(),
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nuoroda nebegalioja arba yra neteisinga.",
        )

    validate_password_strength(request.new_password)
    clear_password_reset_state(user, request.new_password)
    db.commit()

    return {"message": "Slaptažodis pakeistas sėkmingai."}
