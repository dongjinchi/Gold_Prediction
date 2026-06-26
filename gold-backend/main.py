import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import DB_PATH
from db.models import init_db
from scheduler import start_scheduler, stop_scheduler
from api.routes import router as api_router

app = FastAPI(title="Gold Investment Dashboard API", version="0.1.0")
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db(DB_PATH)
    start_scheduler()
    print(f"Database initialized at {DB_PATH}")
    print("Scheduler started")


@app.on_event("shutdown")
def shutdown():
    stop_scheduler()

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
