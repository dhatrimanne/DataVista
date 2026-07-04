from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.auth.dependencies import bearer_scheme, get_current_user
from backend.auth.repository import (
    create_user,
    deactivate_user,
    get_user_by_email,
    revoke_token,
    update_last_login,
    update_password,
    update_preferences,
    update_profile,
)
from backend.auth.schemas import (
    AuthResponse,
    MessageResponse,
    PasswordChange,
    UserCreate,
    UserLogin,
    UserPreferencesUpdate,
    UserProfile,
    UserProfileUpdate,
)
from backend.auth.security import create_access_token, hash_password, verify_password
from backend.dashboard.repository import record_activity


router = APIRouter(prefix="/auth", tags=["Authentication"])


def public_user(user: dict) -> UserProfile:
    return UserProfile(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        theme=user["theme"],
        preferred_gemini_model=user["preferred_gemini_model"],
        created_at=user["created_at"],
        last_login_at=user["last_login_at"],
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate) -> AuthResponse:
    hashed_password = hash_password(payload.password)
    try:
        user = create_user(payload.email, payload.full_name, hashed_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    record_activity(user["id"], "account_created", "Account created.")
    token = create_access_token(str(user["id"]))
    return AuthResponse(access_token=token, user=public_user(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin) -> AuthResponse:
    user = get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled.")

    update_last_login(user["id"])
    user = get_user_by_email(payload.email)
    record_activity(user["id"], "login", "Signed in.")
    token = create_access_token(str(user["id"]), remember_me=payload.remember_me)
    return AuthResponse(access_token=token, user=public_user(user))


@router.post("/logout", response_model=MessageResponse)
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> MessageResponse:
    if credentials:
        revoke_token(credentials.credentials)
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserProfile)
def me(current_user: dict = Depends(get_current_user)) -> UserProfile:
    return public_user(current_user)


@router.patch("/me", response_model=UserProfile)
def edit_profile(payload: UserProfileUpdate, current_user: dict = Depends(get_current_user)) -> UserProfile:
    user = update_profile(current_user["id"], payload.full_name)
    record_activity(current_user["id"], "profile_updated", "Updated profile.")
    return public_user(user)


@router.patch("/password", response_model=MessageResponse)
def change_password(payload: PasswordChange, current_user: dict = Depends(get_current_user)) -> MessageResponse:
    if not verify_password(payload.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    update_password(current_user["id"], hash_password(payload.new_password))
    record_activity(current_user["id"], "password_changed", "Changed password.")
    return MessageResponse(message="Password changed successfully.")


@router.patch("/preferences", response_model=UserProfile)
def change_preferences(payload: UserPreferencesUpdate, current_user: dict = Depends(get_current_user)) -> UserProfile:
    model = payload.preferred_gemini_model.strip() if payload.preferred_gemini_model else None
    user = update_preferences(current_user["id"], payload.theme, model)
    record_activity(current_user["id"], "preferences_updated", "Updated preferences.")
    return public_user(user)


@router.delete("/me", response_model=MessageResponse)
def delete_account(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    deactivate_user(current_user["id"])
    revoke_token(credentials.credentials)
    record_activity(current_user["id"], "account_deleted", "Deleted account.")
    return MessageResponse(message="Account deleted successfully.")
