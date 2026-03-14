"""Admin API endpoints for the Next.js admin frontend."""

from fastapi import APIRouter, Depends

from regulahub.api.deps import verify_api_key

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_api_key)])
