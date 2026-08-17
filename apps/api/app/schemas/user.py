from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str | None
    is_active: bool
