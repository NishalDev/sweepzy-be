import sys
import os
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.database import engine, Base, SessionLocal
from config.settings import settings

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # nothing heavy here!
    yield
    
app = FastAPI(lifespan=lifespan)
# volume static file mount
UPLOAD_DIR = Path("uploads")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# CORS: use our parsed list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
#middlewares

#load all routes
def load_routes(directory: Path):
    import importlib.util
    routers = []
    for item in directory.rglob("*_routes.py"):
        spec = importlib.util.spec_from_file_location(item.stem, str(item))
        module = importlib.util.module_from_spec(spec)
        sys.modules[item.stem] = module
        spec.loader.exec_module(module)
        if hasattr(module, "router"):
            routers.append(module.router)
    return routers

for router in load_routes(Path(__file__).parent / "api"):
    app.include_router(router, prefix="/api")
    
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def home():
    return {"message": "Welcome"}

# ✅ Add this block to run locally
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)