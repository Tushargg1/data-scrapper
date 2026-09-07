"""
Seed default profiles directly into the database (no HTTP server needed).
Run once: python seed_profiles.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from database import init_db, get_all_profiles
from profiles_manager import create_new_profile, get_template, get_template_names

init_db()

existing = {p["name"] for p in get_all_profiles()}

templates_to_seed = [
    "Beauty & Saloon",
    "Car Dealers",
    "Restaurants & Food",
    "Clinics & Healthcare",
    "Real Estate",
    "Education & Coaching",
    "Hotels & Travel",
    "Electronics & Repair",
]

for tmpl_name in templates_to_seed:
    if tmpl_name in existing:
        print(f"SKIP (already exists): {tmpl_name}")
        continue
    tmpl = get_template(tmpl_name)
    p = create_new_profile(
        name=tmpl_name,
        description=tmpl.get("description", ""),
        icon=tmpl.get("icon", "📁"),
        niches=tmpl.get("niches", [])
    )
    print(f"Created: {p['icon']} {p['name']}")
    print(f"  slug   : {p['slug']}")
    print(f"  api_key: {p['api_key']}")
    print(f"  niches : {len(p['niches'])}")
    print()

print("Done! All profiles seeded.")
