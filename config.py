import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-this')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    
    # Email Configuration
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    SMTP_SERVER = "smtp.office365.com"
    SMTP_PORT = 587
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'}
    
    # Database files - Modular structure for better scalability
    DATABASES = {
        'proposals': 'data/proposals/proposals_db.json',
        'projects': 'data/projects/projects_db.json',
        'users': 'data/users/users_db.json',
        'counters': 'data/system/counters_db.json',
        'analytics': 'data/analytics/analytics_db.json',
        'settings': 'data/system/system_settings.json',
        'audit_log': 'data/audit/audit_log.json',
        'deletion_log': 'data/audit/deletion_log.json',
        'documents': 'data/documents/documents_db.json',
        'email_log': 'data/system/email_log.json',
        'activity_log': 'data/audit/activity_log.json',
        'executed_contracts': 'data/legal/executed_contracts.json',
        'sub_requests': 'data/sub_requests.json',
        'pw_dir_questions': 'data/pw_dir_questions.json',
        'insurance_requests': 'data/legal/insurance_requests.json'
    }

# Project Information Form Fields
PROJECT_REVENUE_CODES = [
    "Contracting - Public Funding - C02",
    "Contracting - Private Funding - C03",
    "Contracting - Caltrans - C01",
    "Environmental ESA - Public Funding - E04",
    "Environmental ESA - Private Funding - E01",
    "Environmental Other - Public Funding - E02",
    "Environmental Other - Private Funding - E05",
    "Environmental - Caltrans - E03",
    "Geotechnical - Public Funding - G02",
    "Geotechnical - Private Funding - G01",
    "Materials - Public Funding - M02",
    "Materials - Private Funding - M01"
]

PROJECT_SCOPES_DETAILED = [
    "ADL Survey - 43",
    "Air Quality Studies - 30",
    "Asb/Lead Pt/Mold/Waste Surveys - 31",
    "Construction Management - 32",
    "Consultation - 16",
    "Distress Analysis - 93",
    "Drilling - 20",
    "Earthwork Package - 25",
    "Expert Testimony - 17",
    "Facility Audits - 34",
    "Field Instrumentation - 18",
    "Foundation Design - 14",
    "Foundation Inspection - 13",
    "Geoenvironmental Investigation - 01",
    "Geological/Fault Investigation - 07",
    "Geological Reconnaissance - 06",
    "Geophysical Surveys - 36",
    "Geotechnical Feasibility Study - 09",
    "Geotechnical Investigation - 04",
    "Health Risk Assessment - 39",
    "Industrial Hygiene/Health & Safety - 37",
    "In-place Density Testing - 12",
    "Lab Testing - 19",
    "Marine Science Studies - 38",
    "Other (describe) - 26",
    "Pavement Design - 15",
    "Perc Testing - 22",
    "Phase I ESA - 33",
    "Phase II ESA - 35",
    "Regulatory Compliance Support - 40",
    "Remediation Contracting - 41",
    "Research - 21",
    "Rivers; Canals; Waterways; Flood Control - 92",
    "Seis. Inv. (Instru) - 23",
    "Seismicity Study - 24",
    "Soil & Geological Investigation - 02",
    "Soil & Geological Reconnaissance - 03",
    "Soil Class/GR - 05",
    "Special Inspection/Materials Testing - 94",
    "Special Inspection/Soil Testing - 95",
    "Subdivision - 91",
    "Testing & Observation - Grading - 10",
    "Testing & Observation - Improvements - 11",
    "Underground Storage Tank Studies - 42",
    "Water Resources; Hydrology; Groundwater - 81",
    "Water Supply, Treatment & Dist - 85"
]

PROJECT_TYPES_DETAILED = [
    "Aerospace Facility - 07",
    "Affordable Housing - 09",
    "Agricultural / Open Space - 04",
    "Airports; Terminals & Hangers - 06",
    "Apartment - 94",
    "Auditoriums & Theatres - 08",
    "Big Box Stores - 12",
    "Bridges - 11",
    "Churches - 14",
    "Commercial Buildings (Low Rise) - 17",
    "Commercial/Industrial Land Development - 72",
    "Communication Systems; Towers; TV/Microwave - 18",
    "Condominium - 97",
    "Dams; Dikes; Levees - 25",
    "Dining Halls; Clubs; Restaurants - 27",
    "Ecological / Archeological / Form / Ranch / Wildlife - 28",
    "Field Houses; Gyms; Stadiums - 35",
    "Fire Stations - 26",
    "Fisheries: Fish Ladders - 37",
    "Harbors; Jetties; Piers; Ship Terminal - 42",
    "Highrises - 45",
    "Highways; Streets; Paving - 46",
    "Hospitals; Medical Facilities - 48",
    "Hotels; Motels - 49",
    "In-House Lab Testing",
    "Industrial Buildings; Manufacturing Plants - 52",
    "Judicial & Courtroom Facilities - 57",
    "Libraries; Museums; Galleries - 60",
    "Liquid Gas Pipelines - 77",
    "Mines/Quarries - 53",
    "Misc. Military - 47",
    "Mixed Use - 01",
    "Parking Garages; Veh Maint Fac - 39",
    "Postal Facilities - 82",
    "Power Generators; Alternative Energy - 83",
    "Prisons; Correctional Facilities - 84",
    "Railroad; Rapid Transit - 87",
    "Recreation Facilities (Parks, Marinas) - 88",
    "Rivers; Canals; Waterways; Flood Control - 92",
    "Schools - Community College - 31",
    "Schools - K-12 Private - 30",
    "Schools - K-12 Public - 29",
    "Schools - University Public - 32",
    "Schools - University Private - 33",
    "Sewage/Water Collection; Treatment; Disposal - 96",
    "Sheriff: Border Cross, DMV, CHP - 19",
    "Single Family - 98",
    "Solar, Wind, Renewable Energy - 102",
    "Solid Wastes; Incineration; Landfill - 99",
    "Storm Water Handling Facilities - 75",
    "Study Zone / Municipality - 95",
    "Subdivision - 91",
    "Substations, Transmission Lines - 76",
    "Tunnels & Subways - 79",
    "Water Resources; Hydrology Ground Water - 81",
    "Water Supply, Treatment & Dist - 85"
]

PROJECT_TEAMS = ["Team 1", "Team 2", "Team 3", "Team 4", "Team 5", "Team 6"]

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI", "ID", 
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", 
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", 
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "Other"
]

CA_COUNTIES = [
    "Alameda", "Alpine", "Amador", "Butte", "Contra Costa", "Calaveras", "Colusa", 
    "Del Norte", "El Dorado", "Fresno", "Glenn", "Humboldt", "Imperial", "Inyo", 
    "Kern", "Kings", "Los Angeles", "Lake", "Lassen", "Madera", "Marin", "Mariposa", 
    "Mendocino", "Merced", "Modoc", "Mono", "Monterey", "Napa", "Nevada", "Orange County", 
    "Placer", "Plumas", "Riverside", "Sacramento", "Santa Barbara", "San Bernardino", 
    "San Benito", "Santa Clara", "Santa Cruz", "San Diego", "San Francisco", "Shasta", 
    "Sierra", "Siskiyou", "San Joaquin", "San Luis Obispo", "San Mateo", "Solano", 
    "Sonoma", "Stanislaus", "Sutter", "Tehama", "Trinity", "Tulare", "Tuolumne", 
    "Ventura", "Yolo", "Yuba", "Yuma"
]