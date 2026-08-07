from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, resources, projects, opportunities, matching, skills, mansioni, role_groups, promotions, project_changes

app = FastAPI(
    title="StaffMatch AI",
    description="Staffing intelligente per progetti SAP/IT — Accenture Italy",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(projects.router)
app.include_router(opportunities.router)
app.include_router(matching.router)
app.include_router(skills.router)
app.include_router(mansioni.router)
app.include_router(role_groups.router)
app.include_router(promotions.router)
app.include_router(project_changes.router)

@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "app": "StaffMatch AI", "version": "1.0.0"}
