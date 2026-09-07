"""
FastAPI REST API — Multi-Profile Edition.

Auth model:
  - Admin key (config.py → ADMIN_API_KEY): can create/delete/list profiles
  - Per-profile key (stored in DB): can only access that profile's data

Run with: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
Swagger:   http://localhost:8000/docs
"""
import io
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd

from database import (
    init_db,
    get_all_profiles, get_profile_by_slug, get_profile_by_api_key,
    delete_profile, update_profile,
    get_businesses, get_business_by_id, update_lead_status,
    get_all_businesses_df, get_stats, get_scraped_jobs_df,
    get_distinct_states, get_distinct_niches,
)
from profiles_manager import create_new_profile, get_template_names, get_template
from niches import ALL_NICHES, ALL_INDUSTRY_NICHES, LEAD_STATUSES
from pincodes import get_states, get_pincodes_for_state
from config import ADMIN_API_KEY, APP_NAME, APP_VERSION, API_PORT

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title=f"{APP_NAME} API",
    description=(
        "Multi-profile business data scraper REST API.\n\n"
        "**Admin endpoints** require `X-API-Key: <ADMIN_KEY>`.\n\n"
        "**Profile endpoints** (e.g. `/api/profiles/beauty-saloon/businesses`) "
        "require the profile's own API key."
    ),
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def require_admin(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key.")
    return x_api_key


def require_profile_key(slug: str, x_api_key: str = Header(..., alias="X-API-Key")):
    """Allow access if the key matches either the profile key OR the admin key."""
    if x_api_key == ADMIN_API_KEY:
        profile = get_profile_by_slug(slug)
    else:
        profile = get_profile_by_api_key(x_api_key)
        if not profile or profile["slug"] != slug:
            raise HTTPException(status_code=401, detail="Invalid API key for this profile.")
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found.")
    return profile


def df_to_records(df: pd.DataFrame) -> list:
    return df.fillna("").to_dict(orient="records")


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
def root():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "admin_endpoints": "/api/profiles",
        "status": "running",
    }


# ════════════════════════════════════════════════════════════════════════════
# PROFILE MANAGEMENT  (admin key required)
# ════════════════════════════════════════════════════════════════════════════

class CreateProfileRequest(BaseModel):
    name: str
    description: str = ""
    icon: str = "📁"
    niches: list[str] = []
    template: Optional[str] = None  # use a pre-built template


@app.get("/api/profiles", tags=["Profiles (Admin)"], dependencies=[Depends(require_admin)])
def list_profiles():
    """List all profiles with their slugs, icons, niches, and API keys."""
    profiles = get_all_profiles()
    return {"total": len(profiles), "profiles": profiles}


@app.post("/api/profiles", tags=["Profiles (Admin)"], dependencies=[Depends(require_admin)])
def create_profile_endpoint(body: CreateProfileRequest):
    """
    Create a new profile. Optionally use a `template` name to pre-fill niches.

    Available templates: Beauty & Saloon, Car Dealers, Restaurants & Food,
    Clinics & Healthcare, Real Estate, Education & Coaching, Hotels & Travel,
    Electronics & Repair
    """
    niches = body.niches
    description = body.description
    icon = body.icon

    if body.template:
        tmpl = get_template(body.template)
        if not tmpl:
            raise HTTPException(status_code=400, detail=f"Template '{body.template}' not found.")
        niches = niches or tmpl.get("niches", [])
        description = description or tmpl.get("description", "")
        icon = icon if icon != "📁" else tmpl.get("icon", "📁")

    if not body.name:
        raise HTTPException(status_code=400, detail="Profile name is required.")

    profile = create_new_profile(body.name, description, icon, niches)
    return {"success": True, "profile": profile}


@app.get("/api/profiles/templates", tags=["Profiles (Admin)"], dependencies=[Depends(require_admin)])
def list_templates():
    """List all available pre-built profile templates."""
    templates = {}
    for name in get_template_names():
        t = get_template(name)
        templates[name] = {"icon": t.get("icon"), "description": t.get("description"),
                           "niche_count": len(t.get("niches", []))}
    return {"templates": templates}


@app.patch("/api/profiles/{slug}", tags=["Profiles (Admin)"], dependencies=[Depends(require_admin)])
def update_profile_endpoint(slug: str, name: str = None, description: str = None,
                             icon: str = None, niches: list[str] = None):
    """Update a profile's metadata or niche list."""
    profile = get_profile_by_slug(slug)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found.")
    update_profile(slug, name=name, description=description, icon=icon, niches=niches)
    return {"success": True, "profile": get_profile_by_slug(slug)}


@app.delete("/api/profiles/{slug}", tags=["Profiles (Admin)"], dependencies=[Depends(require_admin)])
def delete_profile_endpoint(slug: str):
    """
    ⚠️ Delete a profile AND all its scraped data permanently.
    """
    profile = get_profile_by_slug(slug)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found.")
    delete_profile(slug)
    return {"success": True, "message": f"Profile '{slug}' and all its data deleted."}


# ════════════════════════════════════════════════════════════════════════════
# PROFILE DATA  (per-profile key OR admin key)
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/profiles/{slug}/stats", tags=["Profile Data"])
def profile_stats(slug: str, x_api_key: str = Header(..., alias="X-API-Key")):
    """Stats for a specific profile."""
    profile = require_profile_key(slug, x_api_key)
    return {**get_stats(profile_id=profile["id"]), "profile": profile["name"]}


@app.get("/api/profiles/{slug}/businesses", tags=["Profile Data"])
def profile_businesses(
    slug: str,
    state: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    has_phone: Optional[bool] = Query(None),
    has_website: Optional[bool] = Query(None),
    lead_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """
    Get businesses for this profile with optional filters.

    Example: /api/profiles/beauty-saloon/businesses?state=Delhi&has_phone=true
    """
    profile = require_profile_key(slug, x_api_key)
    df = get_businesses(
        profile_id=profile["id"],
        state=state, pincode=pincode, niche=niche,
        has_phone=has_phone, has_website=has_website,
        lead_status=lead_status, page=page, limit=limit
    )
    return {
        "profile": profile["name"],
        "page": page, "limit": limit,
        "total_returned": len(df),
        "businesses": df_to_records(df),
    }


@app.get("/api/profiles/{slug}/businesses/{business_id}", tags=["Profile Data"])
def profile_get_business(slug: str, business_id: int,
                         x_api_key: str = Header(..., alias="X-API-Key")):
    """Get a single business profile by ID."""
    profile = require_profile_key(slug, x_api_key)
    biz = get_business_by_id(business_id)
    if not biz or biz.get("profile_id") != profile["id"]:
        raise HTTPException(status_code=404, detail="Business not found in this profile.")
    return biz


@app.patch("/api/profiles/{slug}/businesses/{business_id}/status", tags=["Profile Data"])
def profile_update_lead_status(
    slug: str, business_id: int,
    lead_status: str = Query(...),
    notes: Optional[str] = Query(None),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Update lead status and notes for a business in this profile."""
    profile = require_profile_key(slug, x_api_key)
    if lead_status not in LEAD_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {LEAD_STATUSES}")
    biz = get_business_by_id(business_id)
    if not biz or biz.get("profile_id") != profile["id"]:
        raise HTTPException(status_code=404, detail="Business not found in this profile.")
    update_lead_status(business_id, lead_status, notes)
    return {"success": True, "id": business_id, "new_status": lead_status}


@app.get("/api/profiles/{slug}/export/csv", tags=["Profile Data"])
def profile_export_csv(
    slug: str,
    state: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    has_phone: Optional[bool] = Query(None),
    has_website: Optional[bool] = Query(None),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Download profile businesses as CSV."""
    profile = require_profile_key(slug, x_api_key)
    df = get_businesses(
        profile_id=profile["id"],
        state=state, niche=niche,
        has_phone=has_phone, has_website=has_website,
        limit=200000
    )
    if df.empty:
        raise HTTPException(status_code=404, detail="No data found.")
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    filename = f"{slug}_{state or 'all'}_{niche or 'all'}.csv".replace(" ", "_")
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/profiles/{slug}/jobs", tags=["Profile Data"])
def profile_jobs(slug: str, x_api_key: str = Header(..., alias="X-API-Key")):
    """Get scraping job history for this profile."""
    profile = require_profile_key(slug, x_api_key)
    df = get_scraped_jobs_df(profile_id=profile["id"])
    return {"profile": profile["name"], "total_jobs": len(df), "jobs": df_to_records(df)}


# ════════════════════════════════════════════════════════════════════════════
# GLOBAL REFERENCE ENDPOINTS  (admin key)
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/stats", tags=["Global (Admin)"], dependencies=[Depends(require_admin)])
def global_stats():
    """Overall stats across all profiles."""
    return get_stats()


@app.get("/api/niches", tags=["Global (Admin)"], dependencies=[Depends(require_admin)])
def all_niches():
    """All niches grouped by industry."""
    return {"industries": ALL_INDUSTRY_NICHES, "total": len(ALL_NICHES)}


@app.get("/api/states", tags=["Global (Admin)"], dependencies=[Depends(require_admin)])
def all_states():
    return {"scraped_states": get_distinct_states(), "all_states": get_states()}


@app.get("/api/states/{state}/pincodes", tags=["Global (Admin)"], dependencies=[Depends(require_admin)])
def pincodes_for_state(state: str):
    pincodes = get_pincodes_for_state(state)
    if not pincodes:
        raise HTTPException(status_code=404, detail=f"State '{state}' not found.")
    return {"state": state, "total": len(pincodes), "pincodes": pincodes}


@app.get("/api/lead-statuses", tags=["Global (Admin)"], dependencies=[Depends(require_admin)])
def lead_statuses():
    return {"lead_statuses": LEAD_STATUSES}
