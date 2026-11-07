from pydantic import BaseModel, Field


class UserReply(BaseModel):
    text: str = Field(max_length=300)
    follow_up: str | None = None


class FamilyAlert(BaseModel):
    summary: str = Field(max_length=400)
    suggested_level: int = Field(ge=1, le=3)
    send: bool


class Turn(BaseModel):
    user: UserReply
    family: FamilyAlert