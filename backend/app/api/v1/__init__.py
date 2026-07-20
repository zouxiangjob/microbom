# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1.file import router as file_router

api_router = APIRouter()
api_router.include_router(file_router)
