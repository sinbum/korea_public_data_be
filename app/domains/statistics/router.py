"""
Statistics API router (placeholder).
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/statistics",
    tags=["Statistics"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get("/")
async def get_statistics():
    """Get statistics (placeholder endpoint)"""
    return {"message": "Statistics endpoint not implemented yet"}