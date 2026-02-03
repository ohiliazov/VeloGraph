from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import bikes

app = FastAPI(title="VeloGraph API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bikes.router, prefix="/api/bikes", tags=["bikes"])


@app.get("/")
async def root():
    return {"message": "Welcome to VeloGraph API"}
