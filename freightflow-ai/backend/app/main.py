from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .database import Base, engine
from .seed_data import seed
from .routers import ingestion, tenders, lanes

Base.metadata.create_all(bind=engine)
seed()

app = FastAPI(
    title="FreightFlow AI",
    description="AI-powered automation middleware for freight brokers.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router)
app.include_router(tenders.router)
app.include_router(lanes.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "freightflow-ai-backend"}
