from pydantic import BaseModel, Field


class UserReply(BaseModel):
    text: str = Field(max_length=300)
    follow_up: str | None = None
    request_image: bool = False  # True when a photo of a visible injury would help; the pipeline asks for it


class FamilyAlert(BaseModel):
    summary: str = Field(max_length=400)
    suggested_level: int = Field(ge=1, le=3)
    send: bool


class Turn(BaseModel):
    user: UserReply
    family: FamilyAlert