"""
FastAPI REST API — Multi-Profile Edition.

Auth model:
  - Admin key (config.py → ADMIN_API_KEY): can create/delete/list profiles
  - Per-profile key (stored in DB): can only access that profile's data

Run with: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
Swagger:   http://localhost:8000/docs
"""
import io
import time
import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
import pandas as pd
from dashboard_html import get_dashboard_html


from database import (
    init_db,
    get_all_profiles, get_profile_by_slug, get_profile_by_api_key,
    delete_profile, update_profile,
    get_businesses, get_business_by_id, update_lead_status,
    get_all_businesses_df, get_stats, get_scraped_jobs_df,
    get_distinct_states, get_distinct_niches,
    register_api_user, get_user_by_code, get_all_api_users,
    update_user_status, get_and_mark_unsent_batch, get_batch_delivery_stats,
    get_businesses_without_phone, clear_all_data,
)
from profiles_manager import create_new_profile, get_template_names, get_template
from niches import ALL_NICHES, ALL_INDUSTRY_NICHES, LEAD_STATUSES
from pincodes import get_states, get_pincodes_for_state
from config import ADMIN_API_KEY, APP_NAME, APP_VERSION, API_PORT
from phone_enricher import (
    start_enrichment_thread, stop_enrichment,
    get_enrich_status, is_enrichment_running,
)

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

import threading
from scraper import ensure_playwright_installed

def _warmup():
    try:
        ensure_playwright_installed()
    except Exception as e:
        print(f"[STARTUP] Playwright warmup error: {e}")

threading.Thread(target=_warmup, daemon=True).start()


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


# ── Health Check (For UptimeRobot / Keep-Alive Bots) ──────────────────────────
@app.api_route("/health", methods=["GET", "HEAD"], tags=["Info"])
@app.api_route("/ping", methods=["GET", "HEAD"], tags=["Info"])
def health(request: Request):
    """Uptime bot health check endpoint — returns 200 OK for both GET and HEAD requests."""
    return Response(
        content=json.dumps({"status": "ok", "service": "data-scrapper", "timestamp": time.time()}),
        status_code=200,
        media_type="application/json"
    )


# ── Root ──────────────────────────────────────────────────────────────────────
@app.api_route("/", methods=["GET", "HEAD"], tags=["Info"])
def root(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)

    from database import get_connection
    try:
        _, is_mysql = get_connection()
        db_engine = "mysql" if is_mysql else "sqlite"
    except Exception:
        db_engine = "unknown"

    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return JSONResponse({
            "app": APP_NAME,
            "version": APP_VERSION,
            "docs": "/docs",
            "admin_endpoints": "/api/profiles",
            "status": "running",
            "db_engine": db_engine,
            "frontend": "https://data-scrapper-henna.vercel.app"
        })

    # Direct browser requests to the React Frontend on Vercel
    return RedirectResponse(url="https://data-scrapper-henna.vercel.app", status_code=302)


@app.api_route("/api/info", methods=["GET", "HEAD"], tags=["Info"])
def api_info(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    from database import get_connection
    try:
        _, is_mysql = get_connection()
        db_engine = "mysql" if is_mysql else "sqlite"
    except Exception:
        db_engine = "unknown"
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "admin_endpoints": "/api/profiles",
        "status": "running",
        "db_engine": db_engine,
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


@app.delete("/api/profiles/{slug}/data", tags=["Profile Data"])
def clear_profile_data_endpoint(slug: str, x_api_key: str = Header(..., alias="X-API-Key")):
    """Clear all scraped businesses and jobs for a profile so you can start fresh."""
    profile = require_profile_key(slug, x_api_key)
    clear_all_data(profile["id"])
    return {"success": True, "message": f"All data for profile '{slug}' cleared successfully."}



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
# PHONE ENRICHMENT  (per-profile key or admin key)
# ════════════════════════════════════════════════════════════════════════════

class EnrichRequest(BaseModel):
    business_ids: list = None   # optional list of IDs; if omitted → all no-phone businesses


@app.post("/api/profiles/{slug}/enrich-phones", tags=["Phone Enrichment"])
def start_enrich(slug: str, body: EnrichRequest = None,
                 x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Start phone enrichment for businesses with no phone number.
    Searches Google, JustDial, and Sulekha in the background.
    Optional body: { "business_ids": [1, 2, 3] } to enrich specific businesses only.
    """
    profile = require_profile_key(slug, x_api_key)
    if is_enrichment_running():
        status = get_enrich_status()
        return {
            "success": False,
            "message": "Enrichment already running.",
            "status": status
        }
    business_ids = (body.business_ids if body else None) or None
    # Count how many businesses will be enriched
    no_phone = get_businesses_without_phone(profile["id"])
    if business_ids:
        count = len([b for b in no_phone if b["id"] in set(business_ids)])
    else:
        count = len(no_phone)
    if count == 0:
        return {"success": False, "message": "No businesses without phone numbers found."}
    err = start_enrichment_thread(profile["id"], business_ids)
    if err:
        return {"success": False, "message": err}
    return {
        "success": True,
        "message": f"Enrichment started for {count} businesses.",
        "total": count
    }


@app.get("/api/profiles/{slug}/enrich-phones/status", tags=["Phone Enrichment"])
def enrich_status(slug: str, x_api_key: str = Header(..., alias="X-API-Key")):
    """Get current phone enrichment progress."""
    require_profile_key(slug, x_api_key)
    return get_enrich_status()


@app.post("/api/profiles/{slug}/enrich-phones/stop", tags=["Phone Enrichment"])
def stop_enrich(slug: str, x_api_key: str = Header(..., alias="X-API-Key")):
    """Stop the running phone enrichment job."""
    require_profile_key(slug, x_api_key)
    stop_enrichment()
    return {"success": True, "message": "Stop signal sent."}


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


# ── User Registration & Batch Models ─────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    username: str
    phone_number: str
    user_code: str
    profile_slug: Optional[str] = None


class UserStatusUpdateRequest(BaseModel):
    status: str  # APPROVED or REJECTED


# ════════════════════════════════════════════════════════════════════════════
# USER REGISTRATION & ACCESS SYSTEM
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/users/register", tags=["User Access & Registration"])
def api_register_user(body: UserRegisterRequest):
    """
    External users register with username, phone_number, and a unique user_code.
    User account is saved as PENDING until admin approves it.
    """
    if not body.username or not body.phone_number or not body.user_code:
        raise HTTPException(status_code=400, detail="username, phone_number, and user_code are required.")

    if get_user_by_code(body.user_code):
        raise HTTPException(status_code=400, detail=f"User code '{body.user_code}' is already registered.")

    profile_id = 1
    if body.profile_slug:
        p = get_profile_by_slug(body.profile_slug)
        if p:
            profile_id = p["id"]

    user = register_api_user(
        username=body.username.strip(),
        phone_number=body.phone_number.strip(),
        user_code=body.user_code.strip(),
        profile_id=profile_id
    )
    return {
        "success": True,
        "message": "Registration submitted successfully! Pending admin approval.",
        "user": user
    }


@app.get("/api/users/status/{user_code}", tags=["User Access & Registration"])
def api_user_status(user_code: str):
    """Check the status of a user registration code (PENDING, APPROVED, REJECTED)."""
    user = get_user_by_code(user_code)
    if not user:
        raise HTTPException(status_code=404, detail=f"User code '{user_code}' not found.")
    return {
        "user_code": user["user_code"],
        "username": user["username"],
        "status": user["status"],
        "created_at": user["created_at"],
        "approved_at": user["approved_at"]
    }


# ════════════════════════════════════════════════════════════════════════════
# 10-BATCH DATA DELIVERY ENDPOINT (APPROVED USERS ONLY)
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/data/batch", tags=["10-Batch Lead Delivery"])
def api_get_batch_data(
    x_user_code: Optional[str] = Header(None, alias="X-User-Code"),
    user_code: Optional[str] = Query(None),
):
    """
    Fetch a batch of max 10 FRESH (UNSENT) businesses.
    Requires header `X-User-Code: <user_code>` (or query param `user_code`).

    1. Validates that the user_code is APPROVED by the admin.
    2. Returns up to 10 businesses that have NEVER been sent to any user yet.
    3. Atomically marks those 10 businesses as SENT in the database.
    """
    code = x_user_code or user_code
    if not code:
        raise HTTPException(status_code=401, detail="User code required. Pass header 'X-User-Code' or query param 'user_code'.")

    user = get_user_by_code(code)
    if not user:
        raise HTTPException(status_code=401, detail=f"Invalid user code '{code}'. Register first at POST /api/users/register.")

    if user["status"] != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. User status is '{user['status']}'. Wait for admin approval."
        )

    profile_id = user.get("profile_id", 1)

    # Fetch exactly 10 unsent leads & mark them sent in a single transaction
    batch = get_and_mark_unsent_batch(user_code=user["user_code"], profile_id=profile_id, limit=10)

    return {
        "success": True,
        "user_code": user["user_code"],
        "username": user["username"],
        "batch_size": len(batch),
        "message": f"Successfully delivered {len(batch)} fresh leads. Marked as sent.",
        "businesses": df_to_records(pd.DataFrame(batch)) if batch else []
    }


# ════════════════════════════════════════════════════════════════════════════
# ADMIN USER APPROVAL ENDPOINTS (Requires Admin Key)
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/users", tags=["User Access (Admin)"], dependencies=[Depends(require_admin)])
def admin_list_users(status: Optional[str] = Query(None)):
    """List all registered API users (filter by status PENDING, APPROVED, REJECTED)."""
    users = get_all_api_users(status=status)
    return {"total": len(users), "users": users}


@app.patch("/api/admin/users/{user_code}/status", tags=["User Access (Admin)"], dependencies=[Depends(require_admin)])
def admin_update_user_status(user_code: str, body: UserStatusUpdateRequest):
    """Approve or reject a user's access request."""
    if body.status not in ["APPROVED", "REJECTED", "PENDING"]:
        raise HTTPException(status_code=400, detail="Status must be APPROVED, REJECTED, or PENDING.")

    user = get_user_by_code(user_code)
    if not user:
        raise HTTPException(status_code=404, detail=f"User code '{user_code}' not found.")

    update_user_status(user_code, body.status)
    return {
        "success": True,
        "user_code": user_code,
        "new_status": body.status,
        "user": get_user_by_code(user_code)
    }


@app.get("/api/admin/delivery-stats", tags=["User Access (Admin)"], dependencies=[Depends(require_admin)])
def admin_delivery_stats():
    """Get lead delivery and inventory stats."""
    return get_batch_delivery_stats()


# ════════════════════════════════════════════════════════════════════════════
# PLAYWRIGHT SCRAPING ENGINE ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

class ScrapeStartRequest(BaseModel):
    profile_id: int = 1
    state: str
    pincodes: list[str]
    niches: list[str]
    max_scrolls: int = 3


@app.post("/api/scrape/start", tags=["Scraping Engine"])
def api_start_scrape(body: ScrapeStartRequest):
    """
    Launch Google Maps Playwright scraper in the background.
    Businesses are parsed with high-speed element clicking and
    saved instantly into Aiven MySQL database without data loss.
    """
    from scrape_manager import start_scraping
    res = start_scraping(
        profile_id=body.profile_id,
        state=body.state.strip(),
        pincodes=[p.strip() for p in body.pincodes if p.strip()],
        niches=[n.strip() for n in body.niches if n.strip()],
        max_scrolls=body.max_scrolls
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@app.get("/api/scrape/status", tags=["Scraping Engine"])
def api_scrape_status():
    """
    Get live progress, counters, current pincode/niche, and recent items
    for the active or latest scraping job.
    """
    from scrape_manager import get_scrape_status
    return get_scrape_status()


@app.post("/api/scrape/stop", tags=["Scraping Engine"])
def api_scrape_stop():
    """Gracefully request the active scraper to stop."""
    from scrape_manager import stop_scraping
    res = stop_scraping()
    return res

