import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from ..schemas import (
    AnalysisResultRead,
    AnalysisResponse,
    ErrorResponse,
)
from ..models import (
    AudioFile,
    AnalysisResult,
    get_audio_file_by_id,
    get_analysis_result_by_id,
)
from ..auth import get_current_active_researcher, AuthError
from ..ml_worker import run_analysis_task
from .. import models

# Logger setup
logger = logging.getLogger("audio_analysis")
logger.setLevel(logging.INFO)

router = APIRouter()

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
    "/trigger/{audio_file_id}",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Trigger ML analysis for an uploaded audio file",
    tags=["Audio Analysis"],
)
async def trigger_audio_analysis(
    audio_file_id: int,
    current_user=Depends(get_current_active_researcher),
    db: Session = Depends(get_db),
):
    """
    Trigger ML analysis (translation, behavioral tagging, quality checks) for an uploaded audio file.
    Returns analysis result if already available, or triggers background job.
    """
    logger.info(f"User {current_user.id} requests analysis for audio_file_id={audio_file_id}")

    audio_file = get_audio_file_by_id(audio_file_id, db)
    if not audio_file:
        logger.warning(f"Audio file not found: {audio_file_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found.",
        )
    if audio_file.uploader_id != current_user.id:
        logger.warning(f"User {current_user.id} unauthorized for audio_file_id={audio_file_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this audio file.",
        )

    # Check if analysis already exists
    analysis_result = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.audio_file_id == audio_file_id)
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )
    if analysis_result:
        logger.info(f"Returning existing analysis result for audio_file_id={audio_file_id}")
        return AnalysisResponse(
            analysis_result=AnalysisResultRead.from_orm(analysis_result),
            message="Analysis already completed.",
        )

    # Trigger Celery ML analysis task
    try:
        task = run_analysis_task.delay(audio_file_id)
        logger.info(f"Triggered ML analysis task: {task.id} for audio_file_id={audio_file_id}")
    except Exception as e:
        logger.error(f"Failed to trigger ML analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger ML analysis.",
        )

    return AnalysisResponse(
        analysis_result=None,
        message="Analysis job started. Please check back for results.",
    )

@router.get(
    "/result/{audio_file_id}",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Get ML analysis result for an audio file",
    tags=["Audio Analysis"],
)
async def get_audio_analysis_result(
    audio_file_id: int,
    current_user=Depends(get_current_active_researcher),
    db: Session = Depends(get_db),
):
    """
    Retrieve ML analysis result for an audio file.
    """
    logger.info(f"User {current_user.id} requests analysis result for audio_file_id={audio_file_id}")

    audio_file = get_audio_file_by_id(audio_file_id, db)
    if not audio_file:
        logger.warning(f"Audio file not found: {audio_file_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found.",
        )
    if audio_file.uploader_id != current_user.id:
        logger.warning(f"User {current_user.id} unauthorized for audio_file_id={audio_file_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this audio file.",
        )

    analysis_result = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.audio_file_id == audio_file_id)
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )
    if not analysis_result:
        logger.info(f"No analysis result yet for audio_file_id={audio_file_id}")
        return AnalysisResponse(
            analysis_result=None,
            message="Analysis not yet completed.",
        )

    return AnalysisResponse(
        analysis_result=AnalysisResultRead.from_orm(analysis_result),
        message="Analysis completed.",
    )

# Exported router
__all__ = ["router"]