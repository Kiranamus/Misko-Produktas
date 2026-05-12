from typing import Optional

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    username: str


class ForgotPasswordResponse(BaseModel):
    token: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
