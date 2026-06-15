from fastapi import APIRouter

from app.api.routers import (
    admin_kyc,
    admin_kia,
    admin_users,
    admin_suppliers,
    admin_support,
    user_support,
    admin_circle_ops,
    admin_overview,
    admin_legal,
    auth,
    legal,
    notifications,
    signup,
    consent,
    admin_audit,
    news,
)
from app.chat import router_client, router_admin
from app.microservices.sponsor_circle.router import router as sponsor_circle_router
from app.microservices.vendor.router import router as vendor_router
from app.microservices.corporate.router import router as corporate_router
from app.microservices.mentor.router import router as mentor_router
from app.microservices.school.router import router as school_router
from app.microservices.school.join_router import join_router as school_join_router
from app.microservices.student.router import router as student_router
from app.microservices.parent.router import router as parent_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(legal.router)
api_router.include_router(signup.router)
api_router.include_router(admin_kyc.router)
api_router.include_router(admin_circle_ops.router)
api_router.include_router(admin_kia.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_suppliers.router)
api_router.include_router(admin_support.router)
api_router.include_router(user_support.router)
api_router.include_router(admin_overview.router)
api_router.include_router(admin_legal.router)
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
api_router.include_router(school_join_router)
api_router.include_router(school_router)
api_router.include_router(student_router)
api_router.include_router(parent_router)
