"""
Master niche list with all industries.
Used for dropdowns in the UI and reference in the API.
"""

# ── Beauty & Saloon ───────────────────────────────────────────────────────────
BEAUTY_NICHES = {
    "💇 Hair": [
        "Hair Salon", "Hair Studio", "Unisex Salon", "Hair Spa",
        "Hair Color Studio", "Hair Extension Studio", "Hair Treatment Clinic",
    ],
    "🪒 Barbershop & Men's": [
        "Barbershop", "Gents Salon", "Men's Salon",
        "Men's Grooming Studio", "Beard Styling Studio",
    ],
    "💄 Makeup": [
        "Makeup Artist", "Bridal Makeup Studio", "Makeup Academy", "Makeup Studio",
    ],
    "🌸 Beauty & Skin": [
        "Beauty Parlour", "Beauty Salon", "Skin Care Clinic", "Dermatology Clinic",
        "Facial Studio", "Waxing Studio", "Threading Studio", "Eyebrow Studio",
    ],
    "💅 Nails": [
        "Nail Art Studio", "Nail Salon", "Nail Extension Studio",
    ],
    "🧖 Wellness & Spa": [
        "Spa", "Day Spa", "Massage Centre", "Ayurvedic Spa",
        "Body Scrub Studio", "Wellness Centre",
    ],
    "👰 Bridal": [
        "Bridal Studio", "Wedding Makeup Artist", "Mehndi Artist",
    ],
}

# ── All industries flat map ───────────────────────────────────────────────────
ALL_INDUSTRY_NICHES = {
    "Beauty & Saloon": [n for cat in BEAUTY_NICHES.values() for n in cat],
    "Car Dealers": [
        "Car Dealership", "Used Car Dealer", "Auto Repair Shop",
        "Car Service Center", "Car Showroom", "Bike Showroom",
        "Two Wheeler Dealer", "Tyre Shop", "Car Wash",
        "Auto Spare Parts", "Car Accessories", "EV Showroom",
    ],
    "Restaurants & Food": [
        "Restaurant", "Cafe", "Dhaba", "Fast Food", "Pizza Place",
        "Chinese Restaurant", "South Indian Restaurant", "Biryani House",
        "Bakery", "Sweet Shop", "Juice Bar", "Ice Cream Parlour",
        "Cloud Kitchen", "Tiffin Service", "Catering Service",
    ],
    "Clinics & Healthcare": [
        "Doctor", "General Physician", "Dentist", "Dental Clinic",
        "Physiotherapist", "Dermatologist", "Pediatrician",
        "Gynaecologist", "Cardiologist", "Diagnostic Lab",
        "Pathology Lab", "Pharmacy", "Ayurvedic Clinic",
        "Homeopathy Clinic", "Nursing Home",
    ],
    "Real Estate": [
        "Property Dealer", "Real Estate Agent", "Real Estate Agency",
        "PG Accommodation", "Flat for Rent", "House for Rent",
        "Builder", "Housing Society", "Commercial Space",
        "Plot Dealer", "Interior Designer",
    ],
    "Education & Coaching": [
        "Coaching Centre", "Tuition Classes", "School",
        "College", "Skill Development Centre", "Computer Training",
        "IELTS Coaching", "Dance Academy", "Music School",
        "Yoga Centre", "Gym", "Fitness Studio",
    ],
    "Hotels & Travel": [
        "Hotel", "Guest House", "Lodge", "OYO Hotel",
        "Budget Hotel", "Luxury Hotel", "Travel Agency",
        "Tour Operator", "Bus Booking", "Taxi Service",
        "Cab Service", "Bike Rental",
    ],
    "Electronics & Repair": [
        "Mobile Shop", "Mobile Repair", "Laptop Repair",
        "Electronics Store", "Computer Shop", "TV Repair",
        "AC Repair", "Refrigerator Repair", "Washing Machine Repair",
        "CCTV Installation", "Electrical Shop",
    ],
}

# Flat list of ALL niches across all industries
ALL_NICHES = list({n for niches in ALL_INDUSTRY_NICHES.values() for n in niches})

# Default beauty niches for backward compat
NICHE_CATEGORIES = BEAUTY_NICHES
DEFAULT_NICHES = [
    "Hair Salon", "Beauty Parlour", "Makeover", "Bridal Makeup Studio",
    "Nail Salon", "Spa", "Barbershop", "Men's Salon",
]

LEAD_STATUSES = [
    "🆕 New Lead",
    "📞 Contacted",
    "📅 Demo Scheduled",
    "🤝 Negotiating",
    "✅ Converted",
    "❌ Not Interested",
    "🔁 Follow Up Later",
]
