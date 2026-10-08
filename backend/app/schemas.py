import re
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_password_strength(value: str) -> str:
    if len(value) < 12 or len(value) > 128:
        raise ValueError("Password must be between 12 and 128 characters")
    if not re.search(r"[a-z]", value) or not re.search(r"[A-Z]", value) or not re.search(r"\d", value) or not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must include upper and lower case letters, a number, and a symbol")
    return value


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class EmailIn(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    roles: list[str]
    authorities: list[str]


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
