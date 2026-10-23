from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User, UserSettings
from ..schemas import (AuthOut, ChangePasswordIn, LoginIn, RefreshIn, RegisterIn, TokenOut, UpdateMeIn,
                       UserOut)
from ..security import (create_access_token, get_current_user, hash_password, issue_refresh_token,
                        revoke_all_for_user, revoke_token, rotate_refresh_token, utcnow, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens(user: User, refresh: str) -> dict:
    return {"access_token": create_access_token(user), "refresh_token": refresh, "token_type": "bearer",
            "expires_in": settings.access_token_minutes * 60}


@router.post("/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.execute(select(User.id).where(User.email == email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email đã được đăng ký")
    role = "admin" if email in {e.lower() for e in settings.admin_emails} else "user"
    user = User(email=email, password_hash=hash_password(body.password), display_name=body.display_name.strip(),
                role=role, is_active=True, last_login_at=utcnow())
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    refresh, _ = issue_refresh_token(db, user, request)
    db.commit()
    db.refresh(user)
    return {**_tokens(user, refresh), "user": user}


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email.lower())).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khoá")
    user.last_login_at = utcnow()
    refresh, _ = issue_refresh_token(db, user, request)
    db.commit()
    return {**_tokens(user, refresh), "user": user}


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db)):
    """Đổi refresh token lấy cặp token mới. Token cũ bị vô hiệu ngay (xoay vòng)."""
    user, new_refresh = rotate_refresh_token(db, body.refresh_token, request)
    db.commit()
    return _tokens(user, new_refresh)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Đăng xuất thiết bị hiện tại (thu hồi phiên của refresh token này)."""
    revoke_token(db, body.refresh_token, user.id)
    db.commit()


@router.post("/logout-all", status_code=204)
def logout_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Đăng xuất khỏi mọi thiết bị."""
    revoke_all_for_user(db, user.id)
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UpdateMeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.display_name = body.display_name.strip()
    db.commit()
    return user


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mật khẩu cũ không đúng")
    if len(body.new_password.encode("utf-8")) > 72:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mật khẩu tối đa 72 byte")
    user.password_hash = hash_password(body.new_password)
    revoke_all_for_user(db, user.id)   # buộc đăng nhập lại ở mọi thiết bị
    db.commit()
