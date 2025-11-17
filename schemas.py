"""
Database Schemas for Little Years Grandparent Portal

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name, e.g. Kid -> "kid".
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
from datetime import date

# Core entities

class Kid(BaseModel):
    name: str = Field(..., description="Full name of the child")
    nickname: Optional[str] = Field(None, description="Nickname")
    birthdate: Optional[date] = Field(None, description="Birth date")
    avatar_url: Optional[str] = Field(None, description="Avatar/photo URL")
    parent_email: str = Field(..., description="Primary parent email")
    allowed_grandparents: List[str] = Field(default_factory=list, description="Emails with viewing access")


class Moment(BaseModel):
    kid_id: str = Field(..., description="Reference to Kid (_id as string)")
    type: Literal["photo", "art", "audio", "video", "note"] = Field("photo", description="Type of moment")
    title: str = Field(..., description="Title of the moment")
    description: Optional[str] = Field(None, description="Short description/caption")
    media_url: Optional[str] = Field(None, description="URL to media (image/audio/video)")
    thumbnail_url: Optional[str] = Field(None, description="Optional thumbnail URL")
    visibility: Literal["public", "private"] = Field("public", description="Visibility for grandparents")
    tags: List[str] = Field(default_factory=list, description="Tags for search/filtering")


# Optional: Public item (e.g., a keepsake or favorite item)
class Item(BaseModel):
    kid_id: str = Field(..., description="Reference to Kid (_id as string)")
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    visibility: Literal["public", "private"] = "public"
