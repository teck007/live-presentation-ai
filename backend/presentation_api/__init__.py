"""Presentation API package. Crea app FastAPI y registra routers con prefijo /api."""
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.presentation_api.controllers import contact, credits, presentation, transcription, trial

load_dotenv()

app = FastAPI(title="Live Presentation - Presentation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcription.router)
app.include_router(presentation.router, prefix="/api")
app.include_router(credits.router, prefix="/api")
app.include_router(contact.router, prefix="/api")
app.include_router(trial.router, prefix="/api")

__all__ = ["app"]
