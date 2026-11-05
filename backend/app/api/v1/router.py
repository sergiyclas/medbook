from fastapi import APIRouter

from app.api.v1 import (
    admin,
    appointments,
    auth,
    catalog,
    doctor_cabinet,
    patients,
    reports,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(patients.router)
api_router.include_router(appointments.router)
api_router.include_router(doctor_cabinet.router)
api_router.include_router(admin.router)
api_router.include_router(reports.router)


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
