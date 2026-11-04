from fastapi import APIRouter

from app.api.v1 import admin, auth, catalog, patients

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(patients.router)
api_router.include_router(admin.router)


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
