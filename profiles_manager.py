"""
Profiles Manager — Create, list, update, delete scraper profiles.
Each profile (e.g. "Beauty & Saloon", "Car Dealers") is fully isolated:
  - its own niche list
  - its own data in the DB
  - its own API key
"""
import secrets
import re
from database import (
    create_profile, get_all_profiles, get_profile_by_slug,
    update_profile, delete_profile, slug_exists
)


# ── Pre-built profile templates ──────────────────────────────────────────────
PROFILE_TEMPLATES = {
    "Beauty & Saloon": {
        "icon": "💇",
        "description": "Hair salons, beauty parlours, spas, makeup artists & grooming studios.",
        "niches": [
            "Hair Salon", "Beauty Parlour", "Beauty Salon", "Unisex Salon",
            "Makeover", "Bridal Makeup Studio", "Makeup Artist", "Spa",
            "Nail Salon", "Nail Art Studio", "Barbershop", "Men's Salon",
            "Skin Care Clinic", "Waxing Studio", "Threading Studio",
            "Hair Spa", "Hair Color Studio", "Massage Centre",
        ],
    },
    "Car Dealers": {
        "icon": "🚗",
        "description": "New & used car dealerships, auto repair, vehicle showrooms.",
        "niches": [
            "Car Dealership", "Used Car Dealer", "Auto Repair Shop",
            "Car Service Center", "Car Showroom", "Bike Showroom",
            "Two Wheeler Dealer", "Tyre Shop", "Car Wash",
            "Auto Spare Parts", "Car Accessories", "EV Showroom",
        ],
    },
    "Restaurants & Food": {
        "icon": "🍽️",
        "description": "Restaurants, cafes, dhabas, fast food & cloud kitchens.",
        "niches": [
            "Restaurant", "Cafe", "Dhaba", "Fast Food", "Pizza Place",
            "Chinese Restaurant", "South Indian Restaurant", "Biryani House",
            "Bakery", "Sweet Shop", "Juice Bar", "Ice Cream Parlour",
            "Cloud Kitchen", "Tiffin Service", "Catering Service",
        ],
    },
    "Clinics & Healthcare": {
        "icon": "🏥",
        "description": "Doctors, dentists, physiotherapists, diagnostic labs & hospitals.",
        "niches": [
            "Doctor", "General Physician", "Dentist", "Dental Clinic",
            "Physiotherapist", "Dermatologist", "Pediatrician",
            "Gynaecologist", "Cardiologist", "Diagnostic Lab",
            "Pathology Lab", "Pharmacy", "Ayurvedic Clinic",
            "Homeopathy Clinic", "Nursing Home",
        ],
    },
    "Real Estate": {
        "icon": "🏠",
        "description": "Property dealers, real estate agents, PGs, rental flats.",
        "niches": [
            "Property Dealer", "Real Estate Agent", "Real Estate Agency",
            "PG Accommodation", "Flat for Rent", "House for Rent",
            "Builder", "Housing Society", "Commercial Space",
            "Plot Dealer", "Interior Designer",
        ],
    },
    "Education & Coaching": {
        "icon": "📚",
        "description": "Schools, coaching centres, tuition classes & skill institutes.",
        "niches": [
            "Coaching Centre", "Tuition Classes", "School",
            "College", "Skill Development Centre", "Computer Training",
            "IELTS Coaching", "Dance Academy", "Music School",
            "Yoga Centre", "Gym", "Fitness Studio",
        ],
    },
    "Hotels & Travel": {
        "icon": "🏨",
        "description": "Hotels, guest houses, travel agents & tour operators.",
        "niches": [
            "Hotel", "Guest House", "Lodge", "OYO Hotel",
            "Budget Hotel", "Luxury Hotel", "Travel Agency",
            "Tour Operator", "Bus Booking", "Taxi Service",
            "Cab Service", "Bike Rental",
        ],
    },
    "Electronics & Repair": {
        "icon": "🔧",
        "description": "Mobile shops, laptop repair, electronics stores & appliance service.",
        "niches": [
            "Mobile Shop", "Mobile Repair", "Laptop Repair",
            "Electronics Store", "Computer Shop", "TV Repair",
            "AC Repair", "Refrigerator Repair", "Washing Machine Repair",
            "CCTV Installation", "Electrical Shop",
        ],
    },
}


def generate_api_key(prefix: str = "key") -> str:
    """Generate a cryptographically secure random API key."""
    token = secrets.token_urlsafe(20)
    return f"{prefix}-{token}"


def make_slug(name: str) -> str:
    """Convert a profile name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def create_new_profile(name: str, description: str, icon: str, niches: list) -> dict:
    """Create a new profile and return its full data."""
    slug = make_slug(name)
    # Ensure slug is unique
    base_slug = slug
    counter = 2
    while slug_exists(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1

    api_key = generate_api_key(slug[:8])
    pid = create_profile(name, slug, description, icon, niches, api_key)
    return get_profile_by_slug(slug)


def get_template_names() -> list:
    return list(PROFILE_TEMPLATES.keys())


def get_template(template_name: str) -> dict:
    return PROFILE_TEMPLATES.get(template_name, {})
