import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from typing import List

from ..schemas import SupportedSpeciesResponse
from ..auth import get_current_active_researcher

# Logger setup
logger = logging.getLogger("species")
logger.setLevel(logging.INFO)

router = APIRouter()

# Supported species list (should be loaded from config/db in production)
SUPPORTED_SPECIES = [
    "canis_lupus",        # Gray Wolf
    "panthera_leo",       # Lion
    "delphinus_delphis",  # Common Dolphin
    "gorilla_gorilla",    # Gorilla
    "elephas_maximus",    # Asian Elephant
    # ... add more as needed
]

@router.get(
    "/",
    response_model=SupportedSpeciesResponse,
    summary="List supported animal species",
    tags=["Species"],
    status_code=status.HTTP_200_OK,
)
async def list_supported_species(
    current_user=Depends(get_current_active_researcher),
):
    """
    Returns the list of supported animal species for vocalization capture and analysis.
    """
    logger.info(f"User {current_user.id} requested supported species list.")
    return SupportedSpeciesResponse(supported_species=SUPPORTED_SPECIES)

# Exported router
__all__ = ["router"]