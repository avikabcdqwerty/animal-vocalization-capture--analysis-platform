import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from ..schemas import (
    AudioFileCreate,
    AudioFileRead,
    AudioUploadResponse,
    ErrorResponse,
)
from ..models import (
    AudioFile,
    get_audio_file_by_id,
    Base,
)
from ..auth import get_current_active_researcher, AuthError
from ..storage import (
    store_encrypted_audio_file,
    get_supported_audio_formats,
)
from .. import models

# Logger setup
logger = logging.getLogger("audio_upload")
logger.setLevel(logging.INFO)

router = APIRouter()

# Supported species list (should be loaded from config/db in production)
SUPPORTED_SPECIES = [
    "canis_lupus",  # Gray Wolf
    "panthera_leo",  # Lion
    "delphinus_delphis",  # Common Dolphin
    "gorilla_gorilla",  # Gorilla
    "elephas_maximus",  # Asian Elephant
    # ... add more as needed
]

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_species(species: str) -> None:
    if species not in SUPPORTED_SPECIES:
        logger.warning(f"Unsupported species attempted: {species}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Species '{species}' is not supported.",
        )

def validate_audio_format(file_format: str) -> None:
    if file_format.lower() not in get_supported_audio_formats():
        logger.warning(f"Unsupported audio format attempted: {file_format}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio format '{file_format}' is not supported.",
        )

def validate_file_size(file: UploadFile) -> None:
    if file.spool_max_size and file.spool_max_size > MAX_FILE_SIZE:
        logger.warning(f"File exceeds max size: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds maximum allowed size (50MB).",
        )

def get_db():
    """
    Dependency to get DB session.
    Should be replaced with actual session management in app startup.
    """
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    import os

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/upload",
    response_model=AudioUploadResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
    },
    summary="Upload an animal vocalization audio file",
    tags=["Audio Upload"],
)
async def upload_audio_file(
    request: Request,
    file: UploadFile = File(..., description="Audio file (WAV, MP3, FLAC, max 50MB)"),
    species: str = Form(..., description="Species (must be supported)"),
    location: str = Form(None, description="Location of recording"),
    timestamp: datetime = Form(None, description="Timestamp of recording (ISO8601)"),
    current_user=Depends(get_current_active_researcher),
    db: Session = Depends(get_db),
):
    """
    Upload an audio file for a supported animal species.
    Stores file encrypted in object storage and metadata in the database.
    """
    logger.info(f"User {current_user.id} uploading file: {file.filename} for species: {species}")

    # Validate species
    validate_species(species)

    # Validate file format
    file_format = file.filename.split(".")[-1].lower()
    validate_audio_format(file_format)

    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        logger.warning(f"File too large: {file.filename} ({len(contents)} bytes)")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds maximum allowed size (50MB).",
        )

    # Generate unique S3 object key
    s3_object_key = f"audio/{species}/{uuid.uuid4()}_{file.filename}"

    # Store file in encrypted object storage
    try:
        store_encrypted_audio_file(
            object_key=s3_object_key,
            file_bytes=contents,
            content_type=file.content_type,
        )
    except Exception as e:
        logger.error(f"Failed to store audio file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store audio file.",
        )

    # Prepare metadata
    audio_file = AudioFile(
        uploader_id=current_user.id,
        species=species,
        location=location,
        timestamp=timestamp or datetime.utcnow(),
        s3_object_key=s3_object_key,
        original_filename=file.filename,
        file_format=file_format,
        file_size=len(contents),
        is_encrypted=True,
        quality_flag=None,
    )

    # Store metadata in DB
    try:
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        logger.info(f"Audio file metadata stored: {audio_file.id}")
    except Exception as e:
        logger.error(f"Failed to store audio metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store audio metadata.",
        )

    # Build response
    response = AudioUploadResponse(
        audio_file=AudioFileRead.from_orm(audio_file),
        message="Audio file uploaded successfully.",
    )
    return response

@router.get(
    "/supported-formats",
    response_model=List[str],
    summary="Get supported audio file formats",
    tags=["Audio Upload"],
)
def get_supported_formats():
    """
    List supported audio file formats.
    """
    return get_supported_audio_formats()

@router.get(
    "/supported-species",
    response_model=List[str],
    summary="Get supported animal species for audio upload",
    tags=["Audio Upload"],
)
def get_supported_species():
    """
    List supported animal species for audio upload.
    """
    return SUPPORTED_SPECIES

# Exported router
__all__ = ["router"]