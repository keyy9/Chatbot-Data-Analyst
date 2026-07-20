from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.user_questions import router as user_router
from backend.api.routes.data import router as data_router
from backend.api.routes.admin_operations import router as admin_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.evaluation import router as evaluation_router
from backend.api.routes.user_management import router as user_management_router

from backend.ai import initialize_ai_core

initialize_ai_core()

app = FastAPI(
    title="Conversational Data Analyst",
    version="1.0.0"
)

# Frontend runs on Vite's dev/preview server (separate origin from the API),
# so the browser needs an explicit CORS allow-list to call these routes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(data_router)
app.include_router(admin_router)
app.include_router(evaluation_router)
app.include_router(user_management_router)


@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "AI Backend Ready 🚀"
    }