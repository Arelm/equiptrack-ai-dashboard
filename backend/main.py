from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import assets, workorders, alerts, technicians, ai

app = FastAPI(
    title="EquipTrack AI API",
    description="Enterprise Field Service & Asset Maintenance Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://equiptrack-ai-dashboard.vercel.app",
        "https://equiptrack-ai-dashboard-git-main-inah-okois-projects.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
app.include_router(workorders.router, prefix="/api/workorders", tags=["Work Orders"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(technicians.router, prefix="/api/technicians", tags=["Technicians"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])

@app.get("/")
def root():
    return {"message": "EquipTrack AI API is running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}