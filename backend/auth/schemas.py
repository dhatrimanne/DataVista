from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class UserProfile(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    theme: str = "system"
    preferred_gemini_model: str | None = None
    created_at: str
    last_login_at: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class MessageResponse(BaseModel):
    message: str


class UserProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserPreferencesUpdate(BaseModel):
    theme: str = Field(pattern="^(system|light|dark)$")
    preferred_gemini_model: str | None = Field(default=None, max_length=120)
