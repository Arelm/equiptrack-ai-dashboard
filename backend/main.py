from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import (
    assets, workorders, alerts, technicians, ai, organizations,
    locations, transfers, disposals, auth, assignments, reports, parts, analytics,
)

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
    max_age=3600,
)


app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
# Registered before workorders: GET /mine must not be captured by GET /{wo_id}.
app.include_router(assignments.router, prefix="/api/workorders", tags=["Assignments"])
app.include_router(workorders.router, prefix="/api/workorders", tags=["Work Orders"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(technicians.router, prefix="/api/technicians", tags=["Technicians"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["Organizations"])
app.include_router(locations.router, prefix="/api/locations", tags=["Locations"])
app.include_router(transfers.router, prefix="/api/transfers", tags=["Transfers"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(disposals.router, prefix="/api/disposals", tags=["Disposals"])
app.include_router(parts.router, prefix="/api/parts", tags=["Parts"])
app.include_router(reports.router, prefix="/api", tags=["Field Reports"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

@app.get("/")
def root():
    return {"message": "EquipTrack AI API is running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}