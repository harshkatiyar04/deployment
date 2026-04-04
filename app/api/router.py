from fastapi import APIRouter

from app.api.routers import admin_kyc, auth, notifications, signup, consent
from app.chat import router_client, router_admin

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(signup.router)
api_router.include_router(admin_kyc.router)
api_router.include_router(notifications.router)
api_router.include_router(router_client.router)
api_router.include_router(consent.router)
api_router.include_router(router_admin.router)

