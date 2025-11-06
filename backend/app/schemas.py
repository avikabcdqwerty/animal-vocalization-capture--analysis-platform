from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, constr, conint, validator

# --- User Schemas ---

class UserBase(BaseModel):
    email: EmailStr
    roles: List[str] = Field(default_factory=lambda: ["researcher"])

class UserCreate(UserBase):
    password: constr(min_length=8, max_length=128)

class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr]
    password: Optional[constr(min_length=8, max_length=128)]
    roles: Optional[List[str]]
    is_active: Optional[bool]

# --- Token Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    user_id: int
    roles: List[str]
    exp: int

# --- Audio File Schemas ---

class AudioFileBase(BaseModel):
    species: str = Field(..., max_length=128)
    location: Optional[str] = Field(None, max_length=256)
    timestamp: Optional[datetime]
    original_filename: str = Field(..., max_length=256)
    file_format: constr(to_lower=True, regex="^(wav|mp3|flac)$")
    file_size: conint(gt=0, le=50 * 1024 * 1024)  # Max 50MB

    @validator("species")
    def validate_species(cls, v):
        if not v or not v.strip():
            raise ValueError("Species must not be empty")
        return v

class AudioFileCreate(AudioFileBase):
    pass

class AudioFileRead(AudioFileBase):
    id: int
    uploader_id: int
    s3_object_key: str
    is_encrypted: bool
    quality_flag: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- Analysis Result Schemas ---

class AnalysisResultBase(BaseModel):
    translation: Optional[str] = None
    behavioral_tags: Optional[List[str]] = None
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_issues: Optional[Dict[str, Any]] = None
    partial: bool = False

class AnalysisResultCreate(AnalysisResultBase):
    pass

class AnalysisResultRead(AnalysisResultBase):
    id: int
    audio_file_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- API Response Schemas ---

class AudioUploadResponse(BaseModel):
    audio_file: AudioFileRead
    message: str

class AnalysisResponse(BaseModel):
    analysis_result: AnalysisResultRead
    message: Optional[str] = None

class SupportedSpeciesResponse(BaseModel):
    supported_species: List[str]

# --- Error Response Schema ---

class ErrorResponse(BaseModel):
    detail: str

# --- Exported symbols ---

__all__ = [
    "UserBase",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "Token",
    "TokenPayload",
    "AudioFileBase",
    "AudioFileCreate",
    "AudioFileRead",
    "AnalysisResultBase",
    "AnalysisResultCreate",
    "AnalysisResultRead",
    "AudioUploadResponse",
    "AnalysisResponse",
    "SupportedSpeciesResponse",
    "ErrorResponse",
]