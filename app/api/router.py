from fastapi import APIRouter

from app.api.routers import admin_kyc, auth, notifications, signup, consent, admin_audit, news
from app.chat import router_client, router_admin
from app.microservices.sponsor_circle.router import router as sponsor_circle_router
from app.microservices.vendor.router import router as vendor_router
from app.microservices.corporate.router import router as corporate_router
from app.microservices.mentor.router import router as mentor_router
from app.microservices.school.router import router as school_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(signup.router)
api_router.include_router(admin_kyc.router)
api_router.include_router(notifications.router)
api_router.include_router(router_client.router)
api_router.include_router(consent.router)
api_router.include_router(router_admin.router)
api_router.include_router(admin_audit.router)
api_router.include_router(sponsor_circle_router)
api_router.include_router(news.router)
api_router.include_router(vendor_router)
api_router.include_router(corporate_router)
api_router.include_router(mentor_router)
api_router.include_router(school_router)
