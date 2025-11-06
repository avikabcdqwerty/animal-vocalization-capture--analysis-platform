import logging
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Float,
    JSON,
    create_engine,
    Index,
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base, Session

# Logger setup
logger = logging.getLogger("models")
logger.setLevel(logging.INFO)

Base = declarative_base()

# --- User Model ---
class User(Base):
    """
    User model for authentication and RBAC.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    roles = Column(JSON, nullable=False, default=lambda: ["researcher"])  # e.g., ["researcher"], ["admin"]
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    audio_files = relationship("AudioFile", back_populates="uploader")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, roles={self.roles})>"

# --- Audio File Model ---
class AudioFile(Base):
    """
    Audio file metadata model.
    """
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    species = Column(String(128), nullable=False, index=True)
    location = Column(String(256), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    s3_object_key = Column(String(512), nullable=False, unique=True)
    original_filename = Column(String(256), nullable=False)
    file_format = Column(String(16), nullable=False)  # WAV, MP3, FLAC
    file_size = Column(Integer, nullable=False)  # in bytes
    is_encrypted = Column(Boolean, default=True, nullable=False)
    quality_flag = Column(String(32), nullable=True)  # e.g., "ok", "noisy", "overlap", etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    uploader = relationship("User", back_populates="audio_files")
    analysis_results = relationship("AnalysisResult", back_populates="audio_file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AudioFile(id={self.id}, species={self.species}, uploader_id={self.uploader_id})>"

Index("ix_audio_files_species_timestamp", AudioFile.species, AudioFile.timestamp)

# --- Analysis Result Model ---
class AnalysisResult(Base):
    """
    ML analysis results for an audio file.
    """
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    audio_file_id = Column(Integer, ForeignKey("audio_files.id"), nullable=False, index=True)
    translation = Column(String(2048), nullable=True)
    behavioral_tags = Column(JSON, nullable=True)  # e.g., ["aggression", "mating_call"]
    accuracy = Column(Float, nullable=True)  # 0.0 - 1.0
    quality_issues = Column(JSON, nullable=True)  # e.g., {"noise": true, "overlap": false}
    partial = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    audio_file = relationship("AudioFile", back_populates="analysis_results")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, audio_file_id={self.audio_file_id}, accuracy={self.accuracy})>"

# --- Database Session Utilities ---

# Example: engine = create_engine(DATABASE_URL)
# Example: SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_user_by_id(user_id: int, db: Optional[Session] = None) -> Optional[User]:
    """
    Utility to fetch a user by ID.
    """
    if db is None:
        logger.error("Database session is required for get_user_by_id")
        return None
    return db.query(User).filter(User.id == user_id).first()

def get_audio_file_by_id(audio_file_id: int, db: Optional[Session] = None) -> Optional[AudioFile]:
    """
    Utility to fetch an audio file by ID.
    """
    if db is None:
        logger.error("Database session is required for get_audio_file_by_id")
        return None
    return db.query(AudioFile).filter(AudioFile.id == audio_file_id).first()

def get_analysis_result_by_id(result_id: int, db: Optional[Session] = None) -> Optional[AnalysisResult]:
    """
    Utility to fetch an analysis result by ID.
    """
    if db is None:
        logger.error("Database session is required for get_analysis_result_by_id")
        return None
    return db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()

# Exported symbols
__all__ = [
    "Base",
    "User",
    "AudioFile",
    "AnalysisResult",
    "get_user_by_id",
    "get_audio_file_by_id",
    "get_analysis_result_by_id",
]