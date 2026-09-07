import streamlit as st
import pandas as pd

from pincodes import get_states, get_pincodes_for_state
from database import (
    init_db, is_already_scraped, mark_as_scraped, save_businesses, save_single_business,
    get_all_businesses_df, get_businesses, get_stats, get_scraped_jobs_df,
    get_business_by_id, update_lead_status,
    get_distinct_states, get_distinct_niches,
    get_all_profiles, get_profile_by_slug, delete_profile,
)
from profiles_manager import (
    create_new_profile, get_template_names, get_template, PROFILE_TEMPLATES
)
from scraper import scrape_google_maps
from niches import ALL_INDUSTRY_NICHES, LEAD_STATUSES
from config import APP_NAME, APP_VERSION, API_PORT, ADMIN_API_KEY

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(page_title=APP_NAME, page_icon="📡", layout="wide")

# ── Session defaults ──────────────────────────────────────────────────────────
if "active_profile" not in st.session_state:
    st.session_state.active_profile = None
if "stop_scraping" not in st.session_state:
    st.session_state.stop_scraping = False


# ── Helpers ───────────────────────────────────────────────────────────────────
def reload_profiles():
    return get_all_profiles()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📡 Biz Scraper Pro")
    st.caption(f"v{APP_VERSION}")
    st.divider()

    profiles = reload_profiles()

    if profiles:
        profile_names = [f"{p['icon']} {p['name']}" for p in profiles]
        selected_idx = st.selectbox(
            "🗂️ Active Profile",
            range(len(profiles)),
            format_func=lambda i: profile_names[i],
            key="sidebar_profile_idx"
        )
        active = profiles[selected_idx]
        st.session_state.active_profile = active
        st.caption(f"Slug: `{active['slug']}`")
        st.caption(f"API Key: `{active['api_key']}`")
    else:
        st.info("No profiles yet. Create one in the **Profiles** tab!")
        st.session_state.active_profile = None

    st.divider()

    if st.session_state.active_profile:
        p = st.session_state.active_profile
        stats = get_stats(profile_id=p["id"])
        c1, c2 = st.columns(2)
        c1.metric("Businesses", stats["total_businesses"])
        c2.metric("Pincodes Done", stats["total_pincodes_done"])
        c1.metric("With Phone", stats["businesses_with_phone"])
        c2.metric("With Website", stats["businesses_with_website"])

    st.divider()
    st.info(f"🌐 REST API:\n`http://localhost:{API_PORT}/docs`")
    st.caption(f"Admin Key:\n`{ADMIN_API_KEY}`")


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_profiles, tab_scrape, tab_leads, tab_data, tab_log, tab_api = st.tabs([
    "🗂️ Profiles", "🔍 Scrape", "👤 Lead Profiles", "📋 Data", "📜 Job Log", "🔌 API Docs"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PROFILE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab_profiles:
    st.header("🗂️ Profile Management")
    st.caption("Each profile is a separate industry workspace with its own data and API key.")

    # ── Existing profiles grid ────────────────────────────────────────────────
    profiles = reload_profiles()
    if not profiles:
        st.info("No profiles yet. Create one below!")
    else:
        cols = st.columns(min(len(profiles), 3))
        for i, prof in enumerate(profiles):
            with cols[i % 3]:
                s = get_stats(profile_id=prof["id"])
                with st.container(border=True):
                    st.markdown(f"## {prof['icon']} {prof['name']}")
                    st.caption(prof["description"] or "No description")
                    st.write(f"**Slug:** `{prof['slug']}`")
                    st.write(f"**API Key:** `{prof['api_key']}`")
                    st.write(f"**Niches:** {len(prof['niches'])} configured")
                    c1, c2 = st.columns(2)
                    c1.metric("Businesses", s["total_businesses"])
                    c2.metric("Pincodes", s["total_pincodes_done"])
                    with st.expander("📋 View & Edit Niches"):
                        st.write("**Current Niches:**")
                        current_niches_str = ", ".join(prof["niches"])
                        new_niche_text = st.text_area(
                            "Edit/Add Niches (comma separated):",
                            value=current_niches_str,
                            key=f"edit_niches_{prof['slug']}",
                            height=100
                        )
                        if st.button("💾 Save Niches", key=f"save_niches_{prof['slug']}"):
                            updated_niche_list = [
                                n.strip() for n in new_niche_text.split(",") if n.strip()
                            ]
                            update_profile(prof["slug"], niches=updated_niche_list)
                            st.success("Niches updated!")
                            st.rerun()

                    with st.expander("🔑 API Endpoint"):
                        st.code(
                            f"GET /api/profiles/{prof['slug']}/businesses\n"
                            f"Header: X-API-Key: {prof['api_key']}",
                            language="bash"
                        )
                    if st.button(f"🗑️ Delete Profile", key=f"del_{prof['slug']}",
                                 type="secondary"):
                        st.session_state[f"confirm_del_{prof['slug']}"] = True

                    if st.session_state.get(f"confirm_del_{prof['slug']}", False):
                        st.warning(f"⚠️ This deletes ALL data for **{prof['name']}**!")
                        col_y, col_n = st.columns(2)
                        if col_y.button("Yes, Delete", key=f"yes_{prof['slug']}", type="primary"):
                            delete_profile(prof["slug"])
                            st.success("Profile deleted.")
                            st.rerun()
                        if col_n.button("Cancel", key=f"no_{prof['slug']}"):
                            st.session_state[f"confirm_del_{prof['slug']}"] = False

    st.divider()

    # ── Create new profile ────────────────────────────────────────────────────
    st.subheader("➕ Create New Profile")

    col_l, col_r = st.columns(2)
    with col_l:
        new_name = st.text_input("Profile Name", placeholder="e.g. Car Dealers Delhi or Saloon Rohini")
        new_icon = st.text_input("Icon (emoji)", value="📁")
        new_desc = st.text_area("Description", placeholder="Short notes or details about this profile", height=80)
        
        custom_input_text = st.text_area(
            "✍️ Type or Paste Custom Niches (separated by comma or new line):",
            placeholder="e.g. Hair Salon, Beauty Parlour, Bridal Makeup, Nail Extension",
            key="custom_input_text",
            height=140,
            help="Type or copy-paste any niches here! They will be combined with any checkboxes you select on the right."
        )

    with col_r:
        st.write("**Or Pick from Available Industry Niches:**")
        custom_niches = []
        for industry, niches in ALL_INDUSTRY_NICHES.items():
            with st.expander(industry):
                for niche in niches:
                    if st.checkbox(niche, key=f"custom_niche_{niche}"):
                        custom_niches.append(niche)
        st.write(f"Selected from checkboxes: **{len(custom_niches)}** niches")

    if st.button("➕ Create Profile", type="primary", use_container_width=True):
        # Parse custom typed/pasted niches
        typed_niches = []
        if custom_input_text.strip():
            raw = custom_input_text.replace("\n", ",")
            typed_niches = [x.strip() for x in raw.split(",") if x.strip()]
        
        all_selected = list(dict.fromkeys(custom_niches + typed_niches))
        
        if new_name.strip() and all_selected:
            p = create_new_profile(new_name.strip(), new_desc, new_icon, all_selected)
            st.success(f"✅ Profile **{p['name']}** created with {len(all_selected)} niches! API Key: `{p['api_key']}`")
            st.rerun()
        elif not new_name.strip():
            st.error("Please enter a Profile Name.")
        else:
            st.error("Please add at least one niche (either typed/pasted or selected from checkboxes).")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SCRAPE
# ══════════════════════════════════════════════════════════════════════════════
with tab_scrape:
    active = st.session_state.active_profile

    if not active:
        st.info("👈 Create and select a **Profile** first from the sidebar or the Profiles tab.")
    else:
        st.header(f"🔍 Scraping under: {active['icon']} {active['name']}")
        st.caption(f"Niches in this profile: {', '.join(active['niches']) or 'None set'}")

        if not active["niches"]:
            st.warning("This profile has no niches. Edit it in the Profiles tab.")
        else:
            state_list = get_states()
            selected_state = st.selectbox("Select State to Scrape", ["-- Choose --"] + state_list)
            max_scrolls = st.slider("Scroll depth", 1, 10, 3)

            col_start, col_stop = st.columns(2)
            start_btn = col_start.button("🚀 Start Scraping", type="primary", use_container_width=True)
            if col_stop.button("⏹ Stop", use_container_width=True):
                st.session_state.stop_scraping = True

            if selected_state != "-- Choose --":
                pincodes = get_pincodes_for_state(selected_state)
                total_jobs = len(pincodes) * len(active["niches"])

                m1, m2, m3 = st.columns(3)
                m1.metric("Pincodes", len(pincodes))
                m2.metric("Niches", len(active["niches"]))
                m3.metric("Total Jobs", total_jobs)

                pincode_grid_ph = st.empty()

                def render_pincode_grid():
                    with pincode_grid_ph.container():
                        with st.expander("📌 Live Pincode Status (✅ = Done)", expanded=True):
                            cols = st.columns(8)
                            for i, pc in enumerate(pincodes):
                                done = is_already_scraped(pc, active["niches"][0], active["id"])
                                cols[i % 8].caption("✅" if done else f"⬜ {pc}")

                render_pincode_grid()

                if start_btn:
                    st.session_state.stop_scraping = False
                    
                    st.subheader("⚡ Live Scraping Progress")
                    metric_cols = st.columns(4)
                    mc_total = metric_cols[0].empty()
                    mc_saved = metric_cols[1].empty()
                    mc_phone = metric_cols[2].empty()
                    mc_web = metric_cols[3].empty()

                    mc_total.metric("Businesses Found", 0)
                    mc_saved.metric("New Saved (Instant DB)", 0)
                    mc_phone.metric("With Phone", 0)
                    mc_web.metric("With Website", 0)

                    log_ph = st.empty()
                    prog = st.progress(0)
                    status_ph = st.empty()
                    logs = []
                    done_jobs = 0
                    
                    counters = {
                        "scraped": 0,
                        "saved": 0,
                        "phones": 0,
                        "webs": 0,
                        "pincode": "",
                        "niche": ""
                    }

                    def on_item_scraped(item):
                        counters["scraped"] += 1
                        if item.get("Phone") not in ["N/A", ""]:
                            counters["phones"] += 1
                        if item.get("Website Available?") == "Yes":
                            counters["webs"] += 1

                        # Instantly commit to SQLite database!
                        is_new = save_single_business(
                            selected_state, counters["pincode"], counters["niche"], item, active["id"]
                        )
                        if is_new:
                            counters["saved"] += 1

                        # Update live metric counters instantly
                        mc_total.metric("Businesses Found", counters["scraped"])
                        mc_saved.metric("New Saved (Instant DB)", counters["saved"])
                        mc_phone.metric("With Phone", counters["phones"])
                        mc_web.metric("With Website", counters["webs"])

                    for pincode in pincodes:
                        counters["pincode"] = pincode
                        if st.session_state.stop_scraping:
                            logs.append("⏹ **Scraping stopped by user.**")
                            break

                        for niche in active["niches"]:
                            counters["niche"] = niche
                            if st.session_state.stop_scraping:
                                break

                            done_jobs += 1
                            prog.progress(done_jobs / max(total_jobs, 1))
                            status_ph.write(f"🔍 **{pincode}** → **{niche}** ({done_jobs}/{total_jobs})")

                            if is_already_scraped(pincode, niche, active["id"]):
                                logs.append(f"⏭️ `{pincode}` / `{niche}` — Already done, skipping.")
                                log_ph.markdown("\n\n".join(logs[-20:]))
                                continue

                            try:
                                initial_saved = counters["saved"]
                                df = scrape_google_maps(niche, pincode, max_scrolls, on_item_scraped=on_item_scraped)
                                new_in_pincode = counters["saved"] - initial_saved
                                mark_as_scraped(selected_state, pincode, niche, len(df), active["id"])
                                render_pincode_grid()
                                logs.append(f"✅ `{pincode}` / `{niche}` — **{len(df)}** found, **{new_in_pincode} new** saved instantly.")
                            except Exception as e:
                                logs.append(f"❌ `{pincode}` / `{niche}` — Error: `{str(e)[:80]}`")
                                mark_as_scraped(selected_state, pincode, niche, 0, active["id"])

                            log_ph.markdown("\n\n".join(logs[-20:]))

                    prog.progress(1.0)
                    st.success(f"🎉 Scraping complete! **{counters['saved']} new businesses** permanently saved to **{active['name']}**.")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LEAD PROFILES
# ══════════════════════════════════════════════════════════════════════════════
with tab_leads:
    active = st.session_state.active_profile
    if not active:
        st.info("Select a profile from the sidebar.")
    else:
        st.header(f"👤 Lead Profiles — {active['icon']} {active['name']}")

        with st.expander("🔎 Filters", expanded=True):
            fc1, fc2, fc3, fc4, fc5 = st.columns(5)
            sc_states  = get_distinct_states(active["id"]) or []
            sc_niches  = get_distinct_niches(active["id"]) or []
            f_state    = fc1.selectbox("State",        ["All"] + sc_states,   key="l_state")
            f_niche    = fc2.selectbox("Niche",        ["All"] + sc_niches,   key="l_niche")
            f_status   = fc3.selectbox("Lead Status",  ["All"] + LEAD_STATUSES, key="l_status")
            f_phone    = fc4.selectbox("Has Phone?",   ["All", "Yes", "No"],  key="l_phone")
            f_web      = fc5.selectbox("Has Website?", ["All", "Yes", "No"],  key="l_web")

        df_leads = get_businesses(
            profile_id=active["id"],
            state=None if f_state == "All" else f_state,
            niche=None if f_niche == "All" else f_niche,
            has_phone=True if f_phone == "Yes" else (False if f_phone == "No" else None),
            has_website=True if f_web == "Yes" else (False if f_web == "No" else None),
            lead_status=None if f_status == "All" else f_status,
            limit=300,
        )

        st.write(f"**{len(df_leads)}** businesses match.")

        if df_leads.empty:
            st.info("No results. Try scraping data first!")
        else:
            # Status summary chips
            status_counts = df_leads["lead_status"].value_counts()
            cols_s = st.columns(min(len(status_counts), 7))
            for i, (s, c) in enumerate(status_counts.items()):
                cols_s[i % 7].metric(s, c)
            st.divider()

            for _, biz in df_leads.iterrows():
                biz_id = int(biz["id"])
                with st.expander(
                    f"{biz['lead_status']}  |  **{biz['name']}**  |  "
                    f"{biz['niche']}  |  📌 {biz['pincode']}  |  ⭐ {biz['rating']}"
                ):
                    left, right = st.columns([2, 1])
                    with left:
                        st.write(f"**📍** {biz['state']} — {biz['pincode']}")
                        st.write(f"**🏷️ Niche:** {biz['niche']}")
                        st.write(f"**⭐ Rating:** {biz['rating']} ({biz['reviews']} reviews)")
                        phone1 = biz.get('phone') or '❌ No phone'
                        phone2 = biz.get('phone_2') or ''
                        phone3 = biz.get('phone_3') or ''
                        phone_str = phone1
                        if phone2: phone_str += f" | {phone2}"
                        if phone3: phone_str += f" | {phone3}"
                        st.write(f"**📞 Phone(s):** {phone_str}")
                        if biz['website_available'] == 'Yes' and biz['website_link'] not in ['N/A', '']:
                            st.write(f"**🌐 Website:** [Visit]({biz['website_link']})")
                        else:
                            st.write("**🌐 Website:** ❌ None — great booking site lead!")
                        st.write(f"**🗺️** [Open in Google Maps]({biz['maps_url']})")
                    with right:
                        new_status = st.selectbox(
                            "Lead Status", LEAD_STATUSES,
                            index=LEAD_STATUSES.index(biz['lead_status'])
                            if biz['lead_status'] in LEAD_STATUSES else 0,
                            key=f"st_{biz_id}"
                        )
                        new_notes = st.text_area(
                            "Notes", value=biz.get('notes') or "",
                            key=f"nt_{biz_id}", height=80
                        )
                        if st.button("💾 Save", key=f"sv_{biz_id}"):
                            update_lead_status(biz_id, new_status, new_notes)
                            st.success("Saved!")
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DATA TABLE
# ══════════════════════════════════════════════════════════════════════════════
with tab_data:
    active = st.session_state.active_profile
    if not active:
        st.info("Select a profile from the sidebar.")
    else:
        st.header(f"📋 Data — {active['icon']} {active['name']}")
        if st.button("🔄 Refresh"):
            st.rerun()

        df_view = get_all_businesses_df(profile_id=active["id"])
        if df_view.empty:
            st.info("No data yet. Go to the Scrape tab!")
        else:
            keep = ["id", "name", "niche", "pincode", "state", "rating", "reviews",
                    "phone", "phone_2", "phone_3", "website_available", "website_link", "lead_status", "maps_url", "scraped_at"]
            df_disp = df_view[[c for c in keep if c in df_view.columns]].copy()
            df_disp.columns = [c.replace("_", " ").title() for c in df_disp.columns]
            st.write(f"**{len(df_disp)}** records")
            st.dataframe(df_disp, use_container_width=True, height=500)
            csv = df_disp.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV", data=csv,
                file_name=f"{active['slug']}_data.csv", mime="text/csv"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — JOB LOG
# ══════════════════════════════════════════════════════════════════════════════
with tab_log:
    active = st.session_state.active_profile
    if not active:
        st.info("Select a profile from the sidebar.")
    else:
        st.header(f"📜 Job Log — {active['icon']} {active['name']}")
        if st.button("🔄 Refresh Log"):
            st.rerun()
        log_df = get_scraped_jobs_df(profile_id=active["id"])
        if log_df.empty:
            st.info("No jobs run yet.")
        else:
            log_df.columns = [c.replace("_", " ").title() for c in log_df.columns]
            st.write(f"**{len(log_df)}** jobs completed.")
            st.dataframe(log_df, use_container_width=True, height=500)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — API DOCS
# ══════════════════════════════════════════════════════════════════════════════
with tab_api:
    st.header("🔌 REST API Reference")
    active = st.session_state.active_profile

    st.info(
        f"**Swagger UI (interactive):** [http://localhost:{API_PORT}/docs](http://localhost:{API_PORT}/docs)\n\n"
        f"**Admin API Key:** `{ADMIN_API_KEY}` — create/manage profiles, global stats\n\n"
        + (f"**{active['icon']} {active['name']} Key:** `{active['api_key']}` — access only this profile's data"
           if active else "")
    )

    st.markdown("---")
    if active:
        slug = active['slug']
        key = active['api_key']
        st.markdown(f"""
### Profile: {active['icon']} {active['name']}

```bash
# Get businesses
curl -H "X-API-Key: {key}" \\
  "http://localhost:{API_PORT}/api/profiles/{slug}/businesses"

# Filter: Delhi, with phone, Hair Salon only
curl -H "X-API-Key: {key}" \\
  "http://localhost:{API_PORT}/api/profiles/{slug}/businesses?state=Delhi&niche=Hair+Salon&has_phone=true"

# Get single business
curl -H "X-API-Key: {key}" \\
  "http://localhost:{API_PORT}/api/profiles/{slug}/businesses/42"

# Update lead status
curl -X PATCH -H "X-API-Key: {key}" \\
  "http://localhost:{API_PORT}/api/profiles/{slug}/businesses/42/status?lead_status=📞+Contacted&notes=Called+owner"

# Download CSV
curl -H "X-API-Key: {key}" \\
  "http://localhost:{API_PORT}/api/profiles/{slug}/export/csv" -o data.csv

# Stats
curl -H "X-API-Key: {key}" \\
  "http://localhost:{API_PORT}/api/profiles/{slug}/stats"
```

### Admin Endpoints
```bash
# List all profiles
curl -H "X-API-Key: {ADMIN_API_KEY}" http://localhost:{API_PORT}/api/profiles

# Create a profile from template
curl -X POST -H "X-API-Key: {ADMIN_API_KEY}" -H "Content-Type: application/json" \\
  -d '{{"name":"Car Dealers","template":"Car Dealers"}}' \\
  http://localhost:{API_PORT}/api/profiles

# Delete a profile
curl -X DELETE -H "X-API-Key: {ADMIN_API_KEY}" \\
  http://localhost:{API_PORT}/api/profiles/{slug}
```

### JavaScript / Mobile
```javascript
const res = await fetch(
  'http://localhost:{API_PORT}/api/profiles/{slug}/businesses?has_phone=true',
  {{ headers: {{ 'X-API-Key': '{key}' }} }}
);
const data = await res.json();
console.log(data.businesses);
```
""")
    else:
        st.write("Select a profile from the sidebar to see example API calls for it.")

    st.markdown("---")
    st.markdown(f"""
### All Endpoints

| Scope | Method | Endpoint | Description |
|---|---|---|---|
| Admin | `GET` | `/api/profiles` | List all profiles |
| Admin | `POST` | `/api/profiles` | Create profile |
| Admin | `PATCH` | `/api/profiles/{{slug}}` | Update profile |
| Admin | `DELETE` | `/api/profiles/{{slug}}` | Delete profile |
| Admin | `GET` | `/api/profiles/templates` | List templates |
| Admin | `GET` | `/api/stats` | Global stats |
| Admin | `GET` | `/api/niches` | All niches |
| Admin | `GET` | `/api/states` | All states |
| Profile | `GET` | `/api/profiles/{{slug}}/businesses` | Get businesses |
| Profile | `GET` | `/api/profiles/{{slug}}/businesses/{{id}}` | Single business |
| Profile | `PATCH` | `/api/profiles/{{slug}}/businesses/{{id}}/status` | Update lead |
| Profile | `GET` | `/api/profiles/{{slug}}/stats` | Profile stats |
| Profile | `GET` | `/api/profiles/{{slug}}/export/csv` | Download CSV |
| Profile | `GET` | `/api/profiles/{{slug}}/jobs` | Job history |
""")
