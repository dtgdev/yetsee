from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


class AuthError(ValueError):
    pass


def register_user(db: Session, *, email: str, password: str, display_name: str | None) -> User:
    normalized = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized))
    if existing:
        raise AuthError("Email already registered")

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> tuple[User, str]:
    normalized = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized))
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    if not user.is_active:
        raise AuthError("User is inactive")
    return user, create_access_token(user.id)
