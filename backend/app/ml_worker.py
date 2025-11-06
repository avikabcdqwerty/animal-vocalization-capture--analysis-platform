import logging
import os
from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime

from .models import (
    AudioFile,
    AnalysisResult,
    Base,
)
from .storage import retrieve_encrypted_audio_file
from .schemas import AnalysisResultBase

# Logger setup
logger = logging.getLogger("ml_worker")
logger.setLevel(logging.INFO)

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

celery_app = Celery(
    "ml_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- ML Analysis Logic ---

def run_quality_checks(audio_bytes: bytes) -> dict:
    """
    Run quality checks on the audio file.
    Returns a dict with flags for noise, overlap, etc.
    """
    # Placeholder: Replace with real DSP/ML logic
    # For demonstration, randomly flag noise/overlap for testing
    import random
    quality_issues = {
        "noise": random.choice([True, False]),
        "overlap": random.choice([True, False]),
    }
    logger.info(f"Quality checks: {quality_issues}")
    return quality_issues

def run_translation_and_tagging(audio_bytes: bytes, species: str) -> (str, list, float):
    """
    Run ML model for translation and behavioral tagging.
    Returns (translation, tags, accuracy).
    """
    # Placeholder: Replace with real ML inference
    # For demonstration, return dummy translation/tags/accuracy
    translation = f"Simulated translation for {species}"
    tags = ["mating_call", "territorial"] if species == "canis_lupus" else ["aggression"]
    accuracy = 0.85  # Simulate >80% accuracy
    logger.info(f"ML translation/tags: {translation}, {tags}, accuracy={accuracy}")
    return translation, tags, accuracy

@celery_app.task(name="run_analysis_task")
def run_analysis_task(audio_file_id: int):
    """
    Celery task to run ML analysis on an audio file.
    Stores results in the database.
    """
    logger.info(f"Starting ML analysis for audio_file_id={audio_file_id}")
    db = SessionLocal()
    try:
        audio_file = db.query(AudioFile).filter(AudioFile.id == audio_file_id).first()
        if not audio_file:
            logger.error(f"Audio file not found: {audio_file_id}")
            return {"error": "Audio file not found"}

        # Retrieve encrypted audio file from storage
        try:
            audio_bytes = retrieve_encrypted_audio_file(audio_file.s3_object_key)
        except Exception as e:
            logger.error(f"Failed to retrieve audio file from storage: {e}")
            return {"error": "Failed to retrieve audio file"}

        # Run quality checks
        quality_issues = run_quality_checks(audio_bytes)
        partial = quality_issues.get("noise", False) or quality_issues.get("overlap", False)

        # Run ML translation/tagging if species is supported
        if audio_file.species not in [
            "canis_lupus",
            "panthera_leo",
            "delphinus_delphis",
            "gorilla_gorilla",
            "elephas_maximus",
        ]:
            logger.warning(f"Unsupported species for ML analysis: {audio_file.species}")
            translation = None
            tags = None
            accuracy = None
            partial = True
        else:
            translation, tags, accuracy = run_translation_and_tagging(audio_bytes, audio_file.species)

        # Store analysis result in DB
        analysis_result = AnalysisResult(
            audio_file_id=audio_file.id,
            translation=translation,
            behavioral_tags=tags,
            accuracy=accuracy,
            quality_issues=quality_issues,
            partial=partial,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(analysis_result)
        db.commit()
        db.refresh(analysis_result)
        logger.info(f"Analysis result stored for audio_file_id={audio_file_id}, result_id={analysis_result.id}")
        return {
            "result_id": analysis_result.id,
            "partial": partial,
            "accuracy": accuracy,
        }
    except Exception as e:
        logger.error(f"ML analysis failed: {e}", exc_info=True)
        return {"error": "ML analysis failed"}
    finally:
        db.close()

# Exported Celery app and task
__all__ = ["celery_app", "run_analysis_task"]