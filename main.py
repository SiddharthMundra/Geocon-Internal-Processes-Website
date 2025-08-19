from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime, timedelta
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import calendar
import uuid
import shutil

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-this')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create necessary directories
for folder in ['uploads', 'data', 'data/proposals', 'data/projects', 'data/users', 
               'data/system', 'data/analytics', 'data/audit', 'data/documents']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'}

# Email Configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

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
    'executed_contracts': 'data/legal/executed_contracts.json',  # NEW
    'insurance_requests': 'data/legal/insurance_requests.json'   # NEW
}

# Default system settings with expanded options
DEFAULT_SETTINGS = {
    'legal_team_emails': [
        'legal1@geoconinc.com',
        'legal2@geoconinc.com',
        'legal3@geoconinc.com'
    ],
    'authorized_lastnames': [
        'smith', 'johnson', 'williams', 'brown', 'jones', 
        'garcia', 'miller', 'davis', 'rodriguez', 'martinez',
        'hernandez', 'lopez', 'gonzalez', 'wilson', 'anderson',
        'thomas', 'taylor', 'moore', 'jackson', 'martin',
        'lee', 'perez', 'thompson', 'white', 'harris',
        'sanchez', 'clark', 'ramirez', 'lewis', 'robinson',
        'walker', 'young', 'allen', 'king', 'wright',
        'scott', 'torres', 'nguyen', 'hill', 'flores',
        'green', 'adams', 'nelson', 'baker', 'hall',
        'rivera', 'campbell', 'mitchell', 'carter', 'roberts'
    ],
    'project_managers': [
        'Shawn Weedon',
        'Rebecca Silva',
        'Kathlyn Ortega',
        'Richard Church',
        'Jason Muir',
        'David Martinez',
        'Sarah Johnson',
        'Michael Chen',
        'Jennifer Lopez',
        'Robert Taylor'
    ],
    'office_codes': {
        'SD': 'San Diego',
        'OC': 'Orange County',
        'MU': 'Murrieta',
        'RD': 'Redlands',
        'LA': 'Los Angeles',
        'EB': 'East Bay',
        'SA': 'Sacramento',
        'FA': 'Fairfield',
        'CV': 'Coachella Valley'
    },
    'proposal_types': {
        'P': 'Proposal',
        'S': 'Submittal',
        'C': 'Change Order'
    },
    'service_types': {
        'GT': 'Geotechnical',
        'EV': 'Environmental',
        'SI': 'Special Inspection',
        'GE': 'Geotech and Enviro',
        'GS': 'Geotech and SI',
        'GES': 'Geotech, Enviro and SI',
        'MT': 'Materials Testing',
    },

    'project_scopes' : [
        "ADL SURVEY - 43",
        "AIR QUALITY STUDIES - 30",
        "ASB/LEAD PT/MOLD/WASTE SURVEYS - 31",
        "CONSTRUCTION MANAGEMENT - 32",
        "CONSULTATION - 16",
        "DISTRESS ANALYSIS - 93",
        "DRILLING - 20",
        "EARTHWORK PACKAGE - 25",
        "EXPERT TESTIMONY - 17",
        "FACILITY AUDITS - 34",
        "FIELD INSTRUMENTATION - 18",
        "FOUNDATION DESIGN - 14",
        "FOUNDATION INSPECTION - 13",
        "GEOENVIRONMENTAL INVESTIGATION - 1",
        "GEOLOGICAL FEASIBILITY STUDY - 9",
        "GEOLOGICAL RECONNAISSANCE - 6",
        "GEOLOGICAL/FAULT INVESTIGATION - 7",
        "GEOPHYSICAL SURVEYS - 36",
        "GEOTECHNICAL FEASIBILITY STUDY - 8",
        "GEOTECHNICAL INVESTIGATION - 4",
        "HEALTH RISK ASSESSMENT - 39",
        "INDUSTRIAL HYGIENE/HEALTH&SAFETY - 37",
        "IN-PLACE DENSITY TESTING - 12",
        "LAB TESTING - 19",
        "MARINE SCIENCE STUDIES - 38",
        "OTHER (DESCRIBE) - 26",
        "PAVEMENT DESIGN - 15",
        "PERC TESTING - 22",
        "PHASE I ESA - 33",
        "PHASE II ESA - 35",
        "REGULATORY COMPLIANCE SUPPORT - 40",
        "REMEDIATION CONTRACTING - 41",
        "RESEARCH - 21",
        "RIVERS;CANALS;WATERWAYS;FLODD CONTR - 92",
        "SEIS. INV. - 23",
        "SEISMICITY STUDY - 24",
        "SOIL & GEOLOGICAL INVESTIGATION - 2",
        "SOIL & GEOLOGICAL RECON - 3",
        "SOIL CLASS/GR - 5",
        "SPECIAL INSPECTION/MATERIAL TESTING - 94",
        "SPECIAL INSPECTION/SOIL TESTING - 95",
        "SUBDIVISION - 91",
        "TESTING & OBSERVATION - GRADING - 10",
        "TESTING & OBSERVATION- IMPROVEMENTS - 11",
        "UNDERGROUND STORAGE TANK STUDIES - 42",
        "WATER RESOURCES;HYDROLOGY - 81",
        "WATER SUPPLY; TREATMENT AND DIST - 85"
        ],

    'project_types' : [
        "AEROSPACE FACILITY - 7",
        "AFFORDABLE HOUSING - 9",
        "AGRICULTURAL/OPEN SPACE - 4",
        "Agricultural/Ranch Land - 101",
        "AIRPORTS,TERMINALS & HANGERS - 6",
        "AIRPORTS; NAVIAIDS, AIRCRAFT FUEL - 5",
        "APARTMENT - 94",
        "AUDITORIUMS AND THEATERS - 8",
        "BARRACKS; THEATRES - 10",
        "BIG BOX STORES - 12",
        "BRIDGES - 11",
        "CHURCHES - 14",
        "CNG FUELING STATION; SCHOOLS - 100",
        "COMMERCIAL BUILDINGS [LOW RISE] - 17",
        "COMMERCIAL IND. LAND DEVELOPMENT - 72",
        "COMMUNICATIONS SYSTEMS; TV; MICWAVE - 18",
        "COMPUTER FACILITIES - 20",
        "CONDOMINIUM HOMEOWNERS ASSOCIATION - 97",
        "DAMS [CONCRETE; ARCH] - 24",
        "DAMS [EARTH; ROCK]; DIKES; LEVEES - 25",
        "DINING HALLS; CLUBS; RESTAURANTS - 27",
        "DISTRESS ANALYSIS - 93",
        "ECOLOGICAL & ARCHEOLOGICAL INV'S - 28",
        "FALLOUT SHELTERS; BLAST RES. DESIGN - 34",
        "FIELD HOUSES; GYMS; STADIUMS - 35",
        "FIRE STATIONS - 26",
        "FIRE STATIONS - 36",
        "FISHERIES; FISH LADDERS - 37",
        "FORESTRY & FOREST PRODUCTS - 38",
        "GARAGES; VEH MAIN FAC. PARKING LOTS - 39",
        "HARBORS;JETTIES;PIERS;SHIP TERMINAL - 42",
        "HIGHRISES;AIR-RIGHTS-TYPE BLDGS. - 45",
        "HOSPITALS & MEDICAL FACILITIES - 48",
        "HOTELS, MOTELS, RESTARAUNTS - 49",
        "HOUSING - 89",
        "HWYS;STR;AIRFIELD PAVING;PKING LOTS - 46",
        "IN HOUSE LAB TESTING - 51",
        "IND. BLDGS., MANUFACTURING PLANTS - 52",
        "INDUSTRIAL WASTE TREATMENT - 54",
        "INSTRUMENTATION - 50",
        "JUDICIAL & COURTROOM FACILTIES - 57",
        "LABORATORIES; MEDICAL RESEARCH/FAC. - 58",
        "LIBRARIES; MUSEUMS; GALLERIES - 60",
        "MATERIALS HANDLING SYSTEMS; CONVEY; - 63",
        "MINES/QUARIES - 53",
        "MISC. MILITARY - 47",
        "MISSILE FAC., [SILOS; FUELS; TRANS] - 68",
        "MIXED USE - 1",
        "NUCLEAR FACILITIES - 71",
        "ORDNANCE;MUNITIONS;SPEICAL WEAPONS - 74",
        "OVERHEAD - 0",
        "PIPELINES-CROSSCOUNTRY,LIQUID GAS - 77",
        "POSTAL FACILITIES - 82",
        "POWER GEN., ALTERNATE ENERGY - 83",
        "PRISONS & CORRECTIONAL FACILITIES - 84",
        "RAILROAD; RAPID TRANSIT - 87",
        "REC. FAC., PARKS, MARINAS, ETC. - 88",
        "RESOURCE RECOVERY; RECYCLING - 90",
        "RIVERS;CANALS;WATERWAYS;FLOOD CONTR - 92",
        "SCHOOLS - COMMUNITY COLLEGE - 31",
        "SCHOOLS - K-12 PRIVATE - 30",
        "SCHOOLS - K-12 PUBLIC - 29",
        "SCHOOLS - UNIVERSITY PRIVATE - 33",
        "SCHOOLS - UNIVERSITY PUBLIC - 32",
        "SEWAGE COLLECTION; TREATMENT & DISP - 96",
        "SHERIFF; BORDER CROSS, MISC PUBLIC - 19",
        "SINGLE FAMILY - 98",
        "SOILS/SPECIAL INSPECTION - 44",
        "SOLAR, WIND, RENEWABLE ENERGY - 102",
        "SOLID WASTES;INCINERATION;LAND FILL - 99",
        "SPECIAL INSPECTION - 43",
        "STORM WATER HANDLING & FACILITIES - 75",
        "STUDY ZONE/MUNICIPALITY - 95",
        "SUBDIVISION - 91",
        "SUBSTATIONS, TRANSMISSION LINES - 76",
        "SWIMMING POOLS - 73",
        "TOWERS-SELF SUPPORTING & GUYED SYS - 78",
        "TUNNELS AND SUBWAYS - 79",
        "UNSPECIFIED - 0",
        "WAREHOUSES AND DEPOTS - 80",
        "WATER RES., HYDROLOGY; GROUND WATER - 81",
        "WATER SUPPLY,TREATMENT & DISTRIBUT - 85",
        "WIND TUNNELS;RES.TEST FAC. DESIGN - 86"
    ],

    'team_assignments': {
        'Kim Goodrich': '01',
        'Theresa Bautista': '02',
        'Mike Johnson': '03',
        'Sarah Wilson': '04',
        'Robert Brown': '05'
    },
    'legal_dept_email': 'legal@geoconinc.com'
}


# Add these new constants after the existing DEFAULT_SETTINGS (around line 120)

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

# Add these to DEFAULT_SETTINGS
DEFAULT_SETTINGS['analytics_users'] = [
    'admin@geoconinc.com',
    'shawn.weedon@geoconinc.com',
    'rebecca.silva@geoconinc.com'
]

# Initialize database files

# 2. Update the init_databases function to include the new databases
def init_databases():
    # Create legal directory if it doesn't exist
    if not os.path.exists('data/legal'):
        os.makedirs('data/legal')
    
    for db_name, db_path in DATABASES.items():
        if not os.path.exists(db_path):
            with open(db_path, 'w') as f:
                if db_name == 'counters':
                    json.dump({
                        'total_projects': 0,
                        'office_counters': {code: 0 for code in DEFAULT_SETTINGS['office_codes'].keys()},
                        'last_reset': datetime.now().strftime('%Y-%m-%d')
                    }, f)
                elif db_name == 'analytics':
                    json.dump({
                        'monthly_proposals': {},
                        'monthly_wins': {},
                        'monthly_revenue': {},
                        'office_performance': {},
                        'pm_performance': {}
                    }, f)
                elif db_name == 'settings':
                    json.dump(DEFAULT_SETTINGS, f, indent=2)
                elif db_name in ['audit_log', 'deletion_log', 'email_log', 'activity_log']:
                    json.dump([], f)
                else:
                    json.dump({}, f)

init_databases()


# Database helper functions with better error handling
def load_json(filename):
    """Load JSON file with error handling"""
    try:
        # Handle both old format and new format
        if not filename.startswith('data/'):
            # Map old filenames to new structure
            old_to_new = {
                'proposals_db.json': DATABASES['proposals'],
                'projects_db.json': DATABASES['projects'],
                'users_db.json': DATABASES['users'],
                'counters_db.json': DATABASES['counters'],
                'analytics_db.json': DATABASES['analytics'],
                'system_settings.json': DATABASES['settings'],
                'deletion_logs.json': DATABASES['deletion_log']
            }
            filename = old_to_new.get(filename, filename)
        
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Initialize if file doesn't exist
        if filename in DATABASES.values():
            init_databases()
            return load_json(filename)
        return {} if not filename.endswith('_log.json') else []
    except json.JSONDecodeError:
        return {} if not filename.endswith('_log.json') else []
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return {} if not filename.endswith('_log.json') else []

def save_json(filename, data):
    """Save JSON file with backup"""
    try:
        # Handle both old format and new format
        if not filename.startswith('data/'):
            # Map old filenames to new structure
            old_to_new = {
                'proposals_db.json': DATABASES['proposals'],
                'projects_db.json': DATABASES['projects'],
                'users_db.json': DATABASES['users'],
                'counters_db.json': DATABASES['counters'],
                'analytics_db.json': DATABASES['analytics'],
                'system_settings.json': DATABASES['settings'],
                'deletion_logs.json': DATABASES['deletion_log']
            }
            filename = old_to_new.get(filename, filename)
        
        # Create backup before saving
        if os.path.exists(filename):
            backup_name = f"{filename}.backup"
            shutil.copy2(filename, backup_name)
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        # Restore from backup if save failed
        backup_name = f"{filename}.backup"
        if os.path.exists(backup_name):
            shutil.copy2(backup_name, filename)

def log_activity(action, details, user_email=None):
    """Log user activity for audit trail"""
    activity_log = load_json(DATABASES['activity_log'])
    if not isinstance(activity_log, list):
        activity_log = []
    
    activity_log.append({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user': user_email or session.get('user_email', 'system'),
        'action': action,
        'details': details,
        'ip_address': request.remote_addr if request else None
    })
    
    # Keep only last 10000 entries
    if len(activity_log) > 10000:
        activity_log = activity_log[-10000:]
    
    save_json(DATABASES['activity_log'], activity_log)

def get_system_setting(key, default=None):
    """Get system setting with fallback"""
    settings = load_json(DATABASES['settings'])
    return settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key, None))

def set_system_setting(key, value):
    """Set system setting with audit log"""
    settings = load_json(DATABASES['settings'])
    old_value = settings.get(key)
    settings[key] = value
    save_json(DATABASES['settings'], settings)
    
    log_activity('setting_changed', {
        'setting': key,
        'old_value': str(old_value)[:100] if old_value else None,
        'new_value': str(value)[:100] if value else None
    })

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_authorized_email(email):
    """Check if email is from geoconinc.com domain"""
    return email.endswith('@geoconinc.com')

def get_shared_documents(proposal_number, project_number=None):
    """Get all documents for both proposal and associated project"""
    proposals = load_json(DATABASES['proposals'])
    projects = load_json(DATABASES['projects'])
    
    all_documents = []
    
    # Get proposal documents
    if proposal_number in proposals:
        proposal_docs = proposals[proposal_number].get('documents', [])
        for doc in proposal_docs:
            doc['source'] = 'proposal'
            doc['source_number'] = proposal_number
        all_documents.extend(proposal_docs)
    
    # Get project documents if project exists
    if project_number and project_number in projects:
        project_docs = projects[project_number].get('documents', [])
        for doc in project_docs:
            doc['source'] = 'project'
            doc['source_number'] = project_number
        all_documents.extend(project_docs)
    
    # Sort by upload date (newest first)
    all_documents.sort(key=lambda x: x.get('uploaded_date', ''), reverse=True)
    
    return all_documents

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def legal_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        legal_team = get_system_setting('legal_team_emails', [])
        if session.get('user_email') not in legal_team and not session.get('is_admin'):
            flash('Only legal team members can perform this action.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# def update_analytics(action, data):
#     """Update analytics data with better tracking"""
#     analytics = load_json(DATABASES['analytics'])
#     month_key = datetime.now().strftime('%Y-%m')
    
#     if action == 'new_proposal':
#         analytics.setdefault('monthly_proposals', {})[month_key] = \
#             analytics.get('monthly_proposals', {}).get(month_key, 0) + 1
        
#         # Track by office
#         office = data.get('office')
#         if office:
#             analytics.setdefault('office_performance', {}).setdefault(office, {})
#             analytics['office_performance'][office].setdefault('proposals', {})[month_key] = \
#                 analytics['office_performance'][office].get('proposals', {}).get(month_key, 0) + 1
    
#     elif action == 'proposal_won':
#         analytics.setdefault('monthly_wins', {})[month_key] = \
#             analytics.get('monthly_wins', {}).get(month_key, 0) + 1
        
#         fee = float(data.get('fee', 0))
#         analytics.setdefault('monthly_revenue', {})[month_key] = \
#             analytics.get('monthly_revenue', {}).get(month_key, 0) + fee
        
#         # Track by PM
#         pm = data.get('project_manager')
#         if pm:
#             analytics.setdefault('pm_performance', {}).setdefault(pm, {})
#             analytics['pm_performance'][pm]['wins'] = \
#                 analytics['pm_performance'][pm].get('wins', 0) + 1
#             analytics['pm_performance'][pm]['revenue'] = \
#                 analytics['pm_performance'][pm].get('revenue', 0) + fee
    
#     save_json(DATABASES['analytics'], analytics)

# def get_analytics():
#     """Get comprehensive analytics data"""
#     proposals = load_json(DATABASES['proposals'])
#     projects = load_json(DATABASES['projects'])
#     analytics = load_json(DATABASES['analytics'])
    
#     # Calculate different categories
#     active_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'pending'}
#     pending_legal_projects = {k: v for k, v in projects.items() if v.get('status') == 'pending_legal'}
#     active_projects = {k: v for k, v in projects.items() if v.get('status') == 'active'}
#     completed_projects = {k: v for k, v in projects.items() if v.get('status') == 'completed'}
#     lost_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'lost'}
#     dead_jobs = {k: v for k, v in projects.items() if v.get('status') == 'dead'}
    
#     # Total counts
#     total_active_items = len(active_proposals) + len(pending_legal_projects) + len(active_projects)
#     total_completed_items = len(completed_projects) + len(lost_proposals) + len(dead_jobs)
    
#     # Win rate calculation
#     total_decided = len(completed_projects) + len(lost_proposals) + len(dead_jobs)
#     won_items = len(completed_projects)
#     win_rate = (won_items / total_decided * 100) if total_decided > 0 else 0
    
#     # Revenue calculation
#     total_revenue = 0
#     revenue_by_office = {}
    
#     for project in completed_projects.values():
#         proposal_number = project.get('proposal_number')
#         if proposal_number and proposal_number in proposals:
#             proposal = proposals[proposal_number]
#             office = proposal.get('office', 'Unknown')
#             fee = float(proposal.get('fee', 0))
#             total_revenue += fee
#             revenue_by_office[office] = revenue_by_office.get(office, 0) + fee
    
#     # Project manager performance
#     pm_performance = {}
#     for proposal in proposals.values():
#         pm = proposal.get('project_manager', 'Unknown')
#         if pm not in pm_performance:
#             pm_performance[pm] = {'total': 0, 'won': 0, 'revenue': 0}
#         pm_performance[pm]['total'] += 1
        
#         # Check if won
#         if proposal.get('status') == 'converted_to_project':
#             pm_performance[pm]['won'] += 1
#             pm_performance[pm]['revenue'] += float(proposal.get('fee', 0))
    
#     # Average time to win
#     win_times = []
#     for project in completed_projects.values():
#         proposal_number = project.get('proposal_number')
#         if proposal_number and proposal_number in proposals:
#             try:
#                 proposal_date = proposals[proposal_number].get('date', '')
#                 completion_date = project.get('completion_date', '').split(' ')[0]
#                 if proposal_date and completion_date:
#                     proposal_created = datetime.strptime(proposal_date, '%Y-%m-%d')
#                     project_completed = datetime.strptime(completion_date, '%Y-%m-%d')
#                     win_times.append((project_completed - proposal_created).days)
#             except:
#                 pass
    
#     avg_time_to_win = sum(win_times) / len(win_times) if win_times else 0
    
#     return {
#         'win_rate': round(win_rate, 1),
#         'won_proposals': won_items,
#         'total_proposals': total_decided,
#         'active_proposals': len(active_proposals),
#         'pending_legal_projects': len(pending_legal_projects),
#         'active_projects': len(active_projects),
#         'completed_projects': len(completed_projects),
#         'lost_proposals': len(lost_proposals),
#         'dead_jobs': len(dead_jobs),
#         'total_active_items': total_active_items,
#         'total_completed_items': total_completed_items,
#         'total_revenue': total_revenue,
#         'revenue_by_office': revenue_by_office,
#         'pm_performance': pm_performance,
#         'avg_time_to_win': round(avg_time_to_win, 1),
#         'monthly_data': analytics
#     }

def get_next_proposal_number(office, proposal_type, service_type):
    """Generate proposal number with proper counter management"""
    counters = load_json(DATABASES['counters'])
    
    year = datetime.now().year
    
    # Initialize office counter if not exists
    if 'office_counters' not in counters:
        counters['office_counters'] = {}
    
    counter = counters['office_counters'].get(office, 0) + 1
    counters['office_counters'][office] = counter
    
    save_json(DATABASES['counters'], counters)
    
    # Format: OC-2024-0001-P-GT
    proposal_number = f"{office}-{year}-{counter:04d}-{proposal_type}-{service_type}"
    
    log_activity('proposal_number_generated', {'number': proposal_number})
    return proposal_number

def get_next_project_number(team_number):
    """Generate project number with proper counter management"""
    counters = load_json(DATABASES['counters'])
    
    total = counters.get('total_projects', 0) + 1
    counters['total_projects'] = total
    
    save_json(DATABASES['counters'], counters)
    
    # Format: G-000001-02-01
    project_number = f"G-{total:06d}-{team_number}-01"
    
    log_activity('project_number_generated', {'number': project_number})
    return project_number

def send_email(to_email, subject, body):
    """Send email notification with logging"""
    email_log = load_json(DATABASES['email_log'])
    if not isinstance(email_log, list):
        email_log = []
    
    # Log email
    email_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'to': to_email,
        'subject': subject,
        'status': 'sent',
        'mode': 'development'
    }
    
    # Development mode - print to terminal
    print(f"\n{'='*50}")
    print(f"EMAIL NOTIFICATION")
    print(f"{'='*50}")
    print(f"TO: {to_email}")
    print(f"SUBJECT: {subject}")
    print(f"{'='*50}")
    print(f"BODY:\n{body}")
    print(f"{'='*50}\n")
    
    email_log.append(email_entry)
    
    # Keep only last 1000 emails
    if len(email_log) > 1000:
        email_log = email_log[-1000:]
    
    save_json(DATABASES['email_log'], email_log)
    return True

def check_follow_up_reminders():
    """Check for proposals that need follow-up reminders"""
    proposals = load_json(DATABASES['proposals'])
    today = datetime.now().date()
    
    for proposal_num, proposal in proposals.items():
        if (proposal.get('follow_up_date') and 
            proposal.get('status') == 'pending' and 
            not proposal.get('follow_up_reminder_sent')):
            try:
                follow_up_date = datetime.strptime(proposal['follow_up_date'], '%Y-%m-%d').date()
                if follow_up_date <= today:
                    # Send reminder
                    pm_email = f"{proposal['project_manager'].lower().replace(' ', '.')}@geoconinc.com"
                    subject = f"Follow-up Reminder: {proposal['proposal_number']}"
                    body = f"""
                    Follow-up Reminder for Proposal {proposal['proposal_number']}
                    Project: {proposal['project_name']}
                    Client: {proposal['client']}
                    Fee: ${proposal['fee']}
                    Please follow up with the client.
                    """
                    
                    if send_email(pm_email, subject, body):
                        proposal['follow_up_reminder_sent'] = True
                        proposals[proposal_num] = proposal
            except:
                pass
    
    save_json(DATABASES['proposals'], proposals)

# Replace the existing index route in main.py with this updated version


@app.route('/admin')
@admin_required
def admin_panel():
    """Admin configuration panel"""
    log_activity('admin_panel_view', {})
    settings = load_json(DATABASES['settings'])
    return render_template('admin_panel.html', settings=settings)

@app.route('/admin/update_setting', methods=['POST'])
@admin_required
def update_setting():
    """Update system setting"""
    setting_key = request.form.get('setting_key')
    setting_value = request.form.get('setting_value')
    
    if setting_key in ['authorized_lastnames', 'legal_team_emails', 'project_managers', 
                       'project_scopes', 'project_types']:
        # Convert comma-separated string to list
        setting_value = [x.strip() for x in setting_value.split(',') if x.strip()]
    elif setting_key in ['office_codes', 'proposal_types', 'service_types', 'team_assignments']:
        # Parse JSON
        try:
            setting_value = json.loads(setting_value)
        except:
            flash('Invalid JSON format', 'error')
            return redirect(url_for('admin_panel'))
    
    set_system_setting(setting_key, setting_value)
    flash(f'Setting {setting_key} updated successfully!', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/past_projects')
@login_required
def past_projects():
    """View completed projects, lost proposals, and dead jobs"""
    log_activity('past_projects_view', {})
    
    projects = load_json(DATABASES['projects'])
    proposals = load_json(DATABASES['proposals'])
    
    # Filter categories
    completed_projects = {k: v for k, v in projects.items() if v.get('status') == 'completed'}
    lost_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'lost'}
    dead_jobs = {k: v for k, v in projects.items() if v.get('status') == 'dead'}
    
    return render_template('past_projects.html', 
                         projects=completed_projects,
                         lost_proposals=lost_proposals,
                         dead_jobs=dead_jobs,
                         user_email=session.get('user_email'))
@app.route('/mark_proposal_lost/<proposal_number>', methods=['GET', 'POST'])
@login_required
def mark_proposal_lost(proposal_number):
    """Mark proposal as lost"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Admin can mark any proposal as lost
    if not user_can_edit(proposal):
        flash('Only the project manager or admin can mark this proposal as lost.', 'error')
        return redirect(url_for('view_proposal', proposal_number=proposal_number))
    
    if request.method == 'POST':
        loss_note = request.form.get('loss_note', '')
        
        # Update proposal status
        proposal['status'] = 'lost'
        proposal['loss_date'] = datetime.now().strftime('%Y-%m-%d')
        proposal['loss_note'] = loss_note
        proposal['marked_lost_by'] = session['user_email']
        
        proposals[proposal_number] = proposal
        save_json(DATABASES['proposals'], proposals)
        
        log_activity('proposal_marked_lost', {
            'proposal_number': proposal_number,
            'reason': loss_note[:100] if loss_note else 'No reason provided'
        })
        
        flash(f'Proposal {proposal_number} marked as lost and moved to Past Projects.', 'success')
        return redirect(url_for('index'))
    
    return render_template('mark_lost.html', proposal=proposal)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simplified login - all @geoconinc.com emails use password: geocon123"""
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password')
        
        # Admin bypass
        if email == 'admin@geoconinc.com' and password == 'admin123':
            session['user_email'] = 'admin@geoconinc.com'
            session['user_name'] = 'System Administrator'
            session['is_admin'] = True
            session['is_legal'] = True
            
            log_activity('admin_login', {}, 'admin@geoconinc.com')
            flash('Logged in as Administrator', 'success')
            return redirect(url_for('admin_panel'))
        
        # Check if email is from geoconinc.com
        if not is_authorized_email(email):
            flash('Only @geoconinc.com email addresses are allowed.', 'error')
            return redirect(url_for('login'))
        
        # Check password
        if password != 'geocon123':
            flash('Invalid password.', 'error')
            return redirect(url_for('login'))
        
        # Extract name from email
        username = email.split('@')[0]
        name = username.replace('.', ' ').title()
        
        # Check if user is in legal team
        legal_team = get_system_setting('legal_team_emails', [])
        session['user_email'] = email
        session['user_name'] = name
        session['is_admin'] = False
        session['is_legal'] = email in legal_team
        
        log_activity('user_login', {}, email)
        flash(f'Welcome {name}!', 'success')
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    log_activity('user_logout', {})
    session.clear()
    return redirect(url_for('login'))


# FIX 5: Update the mark_won_form route
@app.route('/mark_won_form/<proposal_number>')
@login_required
def mark_won_form(proposal_number):
    """Show form for marking proposal as won"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Admin can mark any proposal as won
    if not user_can_edit(proposal):
        flash('Only the project manager or admin can mark this proposal as won.', 'error')
        return redirect(url_for('index'))
    
    return render_template('mark_won_form.html', proposal=proposal)

# @app.route('/mark_won/<proposal_number>', methods=['POST'])
# @login_required
# def mark_won(proposal_number):
#     """Mark proposal as won and create project"""
#     proposals = load_json(DATABASES['proposals'])
    
#     if proposal_number not in proposals:
#         flash('Proposal not found.', 'error')
#         return redirect(url_for('index'))
    
#     proposal = proposals[proposal_number]
    
#     # Check permissions
#     if (proposal.get('project_manager') != session.get('user_name') and 
#         not session.get('is_admin')):
#         flash('Only the project manager can mark this proposal as won.', 'error')
#         return redirect(url_for('index'))
    
#     # Get form data
#     needs_legal_review = request.form.get('needs_legal_review') == 'yes'
#     coi_needed = request.form.get('coi_needed') == 'yes'
#     project_folder_path = request.form.get('project_folder_path', '')
    
#     # Generate project number
#     team_number = proposal.get('team_number', '00')
#     project_number = get_next_project_number(team_number)
    
#     # Update proposal
#     proposal['status'] = 'converted_to_project'
#     proposal['win_loss'] = 'W'
#     proposal['project_number'] = project_number
#     proposal['won_date'] = datetime.now().strftime('%Y-%m-%d')
#     proposal['won_by'] = session['user_email']
#     proposal['project_folder_path'] = project_folder_path
    
#     # Create project
#     project_status = 'pending_legal' if needs_legal_review else 'active'
    
#     project_data = {
#         'project_number': project_number,
#         'proposal_number': proposal_number,
#         'date': datetime.now().strftime('%Y-%m-%d'),
#         'project_name': proposal.get('project_name', 'Unknown'),
#         'client': proposal.get('client', 'Unknown'),
#         'contact': f"{proposal.get('contact_first', '')} {proposal.get('contact_last', '')}",
#         'project_manager': proposal.get('project_manager', 'Unknown'),
#         'team_number': team_number,
#         'status': project_status,
#         'needs_legal_review': needs_legal_review,
#         'coi_needed': coi_needed,
#         'project_folder_path': project_folder_path,
#         'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#         'documents': [],
#         'email_history': []
#     }
    
#     # Auto-approve if no legal review needed
#     if not needs_legal_review:
#         project_data['legal_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         project_data['legal_approved_by'] = 'Auto-approved (No legal review required)'
#         project_data['geocon_updated'] = True
#         project_data['geocon_update_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
#         print(f"\n🚀 POWER AUTOMATE SCRIPT RUN - Project: {project_number}")
#         print(f"Project moved directly to active (no legal review required)")
    
#     # Save updates
#     proposals[proposal_number] = proposal
#     save_json(DATABASES['proposals'], proposals)
    
#     projects = load_json(DATABASES['projects'])
#     projects[project_number] = project_data
#     save_json(DATABASES['projects'], projects)
    
#     # Update analytics
#     update_analytics('proposal_won', proposal)
    
#     log_activity('proposal_won', {
#         'proposal_number': proposal_number,
#         'project_number': project_number,
#         'needs_legal': needs_legal_review
#     })
    
#     # Send notifications
#     if needs_legal_review:
#         legal_email = get_system_setting('legal_dept_email', 'legal@geoconinc.com')
#         subject = f"Legal Review Required: Project {project_number}"
#         body = f"""
#         Legal Review Required for Project {project_number}
#         Proposal: {proposal_number}
#         Project: {proposal.get('project_name', 'Unknown')}
#         Client: {proposal.get('client', 'Unknown')}
#         PM: {proposal.get('project_manager', 'Unknown')}
#         Fee: ${proposal.get('fee', 0)}
#         COI Needed: {'Yes' if coi_needed else 'No'}
#         """
#         send_email(legal_email, subject, body)
#         flash(f'Proposal marked as won! Project {project_number} created and sent for legal review.', 'success')
#     else:
#         flash(f'Proposal marked as won! Project {project_number} created and moved to Active Projects.', 'success')
    
#     return redirect(url_for('index'))

    
@app.route('/project_info_form/<project_number>')
@login_required
def project_info_form(project_number):
    """Display form to enter additional project information"""
    projects = load_json(DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    
    # Check if project is in correct status
    if project.get('status') != 'pending_additional_info':
        # Allow admin to override and edit anyway
        if not session.get('is_admin'):
            flash('This project does not require additional information.', 'error')
            return redirect(url_for('index'))
    
    # Get proposal data for pre-filling
    proposals = load_json(DATABASES['proposals'])
    proposal = proposals.get(project.get('proposal_number'), {})
    
    # Pre-fill some fields from proposal
    if proposal:
        project['project_city'] = project.get('project_city') or proposal.get('project_city', '')
        project['latitude'] = project.get('latitude') or proposal.get('project_latitude', '')
        project['longitude'] = project.get('longitude') or proposal.get('project_longitude', '')
        project['project_director'] = project.get('project_director') or proposal.get('project_director', '')
    
    return render_template('project_info_form.html',
                         project=project,
                         proposal=proposal,
                         today=datetime.now().strftime('%Y-%m-%d'),
                         revenue_codes=PROJECT_REVENUE_CODES,
                         scopes=PROJECT_SCOPES_DETAILED,
                         types=PROJECT_TYPES_DETAILED,
                         teams=PROJECT_TEAMS,
                         states=US_STATES,
                         counties=CA_COUNTIES)


@app.route('/mark_project_complete/<project_number>')
@login_required
def mark_project_complete(project_number):
    """Mark project as complete"""
    projects = load_json(DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    
    # Admin can complete any project
    if not user_can_edit(project):
        flash('Only the project manager or admin can mark this project as complete.', 'error')
        return redirect(url_for('view_project', project_number=project_number))
    
    # Update status
    project['status'] = 'completed'
    project['completion_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    project['completed_by'] = session['user_email']
    
    projects[project_number] = project
    save_json(DATABASES['projects'], projects)
    
    # ADD THIS LINE - Update analytics when project is completed
    update_analytics('project_completed', project)
    
    log_activity('project_completed', {'project_number': project_number})
    
    flash(f'Project {project_number} marked as complete and moved to Past Projects.', 'success')
    return redirect(url_for('index'))

@app.route('/new_proposal')
@login_required
def new_proposal():
    """New proposal form"""
    return render_template('new_proposal.html',
                         offices=get_system_setting('office_codes', {}),
                         proposal_types=get_system_setting('proposal_types', {}),
                         service_types=get_system_setting('service_types', {}),
                         project_scopes=get_system_setting('project_scopes', []),
                         project_types=get_system_setting('project_types', []),
                         project_managers=get_system_setting('project_managers', []),
                         project_directors=list(get_system_setting('team_assignments', {}).keys()))

@app.route('/edit_proposal/<proposal_number>')
@login_required
def edit_proposal(proposal_number):
    """Edit proposal form"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Admin can edit any proposal
    if not user_can_edit(proposal):
        flash('You do not have permission to edit this proposal.', 'error')
        return redirect(url_for('view_proposal', proposal_number=proposal_number))
    
    return render_template('edit_proposal.html',
                         proposal=proposal,
                         offices=get_system_setting('office_codes', {}),
                         proposal_types=get_system_setting('proposal_types', {}),
                         service_types=get_system_setting('service_types', {}),
                         project_scopes=get_system_setting('project_scopes', []),
                         project_types=get_system_setting('project_types', []),
                         project_managers=get_system_setting('project_managers', []),
                         project_directors=list(get_system_setting('team_assignments', {}).keys()))



@app.route('/admin/update_project_directors', methods=['POST'])
@admin_required
def update_project_directors():
    """Update project directors with auto-assigned team numbers"""
    directors_input = request.form.get('project_directors', '')
    
    # Parse comma-separated directors
    directors = [d.strip() for d in directors_input.split(',') if d.strip()]
    
    # Auto-assign team numbers (01, 02, 03, etc.)
    team_assignments = {}
    for i, director in enumerate(directors, 1):
        team_assignments[director] = f"{i:02d}"  # Format as 01, 02, 03...
    
    # Save to settings
    set_system_setting('team_assignments', team_assignments)
    
    flash(f'Updated {len(directors)} project directors with auto-assigned team numbers!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/update_proposal/<proposal_number>', methods=['POST'])
@login_required
def update_proposal(proposal_number):
    """Update existing proposal"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Check permissions
    if (proposal.get('created_by') != session['user_email'] and 
        proposal.get('project_manager') != session.get('user_name') and 
        not session.get('is_admin')):
        flash('You do not have permission to edit this proposal.', 'error')
        return redirect(url_for('view_proposal', proposal_number=proposal_number))
    
    # Update fields
    proposal.update({
        'project_name': request.form.get('project_name', ''),
        'project_latitude': request.form.get('project_latitude', ''),
        'project_longitude': request.form.get('project_longitude', ''),
        'client': request.form.get('client', ''),
        'contact_first': request.form.get('contact_first', ''),
        'contact_last': request.form.get('contact_last', ''),
        'contact_email': request.form.get('contact_email', ''),
        'contact_phone': request.form.get('contact_phone', ''),
        'project_manager': request.form.get('project_manager', ''),
        'project_director': request.form.get('project_director', ''),
        'team_number': request.form.get('team_number', ''),
        'project_scope': request.form.get('project_scope', ''),
        'project_type': request.form.get('project_type', ''),
        'fee': request.form.get('fee', 0),
        'due_date': request.form.get('due_date', ''),
        'follow_up_date': request.form.get('follow_up_date', ''),
        'notes': request.form.get('notes', ''),
        'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_modified_by': session['user_email']
    })
    
    proposals[proposal_number] = proposal
    save_json(DATABASES['proposals'], proposals)
    
    log_activity('proposal_updated', {'proposal_number': proposal_number})
    
    flash(f'Proposal {proposal_number} updated successfully!', 'success')
    return redirect(url_for('view_proposal', proposal_number=proposal_number))




@app.route('/submit_proposal', methods=['POST'])
@login_required
def submit_proposal():
    """Submit new proposal - FIXED VERSION"""
    # Get form data
    office = request.form.get('office', '')
    proposal_type = request.form.get('proposal_type', '')
    service_type = request.form.get('service_type', '')
    
    # Generate proposal number
    proposal_number = get_next_proposal_number(office, proposal_type, service_type)
    
    # Get project director and team number - FIXED: Get these BEFORE using them
    project_director = request.form.get('project_director', '')
    team_number = request.form.get('team_number', '')
    
    # If team number not provided, try to get from assignments
    if not team_number and project_director:
        team_assignments = get_system_setting('team_assignments', {})
        team_number = team_assignments.get(project_director, '00')
    
    # Create proposal data
    proposal_data = {
        'proposal_number': proposal_number,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'office': office,
        'office_name': get_system_setting('office_codes', {}).get(office, office),
        'proposal_type': proposal_type,
        'proposal_type_name': get_system_setting('proposal_types', {}).get(proposal_type, proposal_type),
        'service_type': service_type,
        'service_type_name': get_system_setting('service_types', {}).get(service_type, service_type),
        'project_name': request.form.get('project_name', ''),
        'project_latitude': request.form.get('project_latitude', ''),
        'project_longitude': request.form.get('project_longitude', ''),
        'client': request.form.get('client', ''),
        'contact_first': request.form.get('contact_first', ''),
        'contact_last': request.form.get('contact_last', ''),
        'contact_email': request.form.get('contact_email', ''),
        'contact_phone': request.form.get('contact_phone', ''),
        'project_manager': request.form.get('project_manager', ''),
        'project_director': project_director,  # Now properly defined
        'team_number': team_number,  # Now properly defined
        'project_scope': request.form.get('project_scope', ''),
        'project_type': request.form.get('project_type', ''),
        'fee': request.form.get('fee', 0),
        'due_date': request.form.get('due_date', ''),
        'follow_up_date': request.form.get('follow_up_date', ''),
        'notes': request.form.get('notes', ''),
        'status': 'pending',
        'created_by': session['user_email'],
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'documents': [],
        'email_history': []
    }
    
    # Handle file upload
    if 'proposal_file' in request.files:
        file = request.files['proposal_file']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{proposal_number}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            proposal_data['documents'].append({
                'filename': filename,
                'original_name': file.filename,
                'uploaded_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'uploaded_by': session['user_email'],
                'type': 'proposal'
            })
    
    # Save proposal
    proposals = load_json(DATABASES['proposals'])
    proposals[proposal_number] = proposal_data
    save_json(DATABASES['proposals'], proposals)
    
    # Update analytics
    update_analytics('new_proposal', proposal_data)
    
    log_activity('proposal_created', {
        'proposal_number': proposal_number,
        'client': proposal_data.get('client', 'Unknown')
    })
    
    # Send notification
    pm = proposal_data.get('project_manager', '')
    if pm:
        pm_email = f"{pm.lower().replace(' ', '.')}@geoconinc.com"
        subject = f"New Proposal Created: {proposal_number}"
        body = f"""
        New Proposal Created: {proposal_number}
        Project: {proposal_data.get('project_name', 'Unknown')}
        Client: {proposal_data.get('client', 'Unknown')}
        Due Date: {proposal_data.get('due_date', 'Not specified')}
        Fee: ${proposal_data.get('fee', 0)}
        """
        send_email(pm_email, subject, body)
    
    flash(f'Proposal {proposal_number} created successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/mark_sent/<proposal_number>')
@login_required
def mark_sent(proposal_number):
    """Mark proposal as sent to client"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Check permissions
    if (proposal.get('project_manager') != session.get('user_name') and 
        not session.get('is_admin')):
        flash('Only the project manager can mark this proposal as sent.', 'error')
        return redirect(url_for('index'))
    
    # Update proposal
    proposal['proposal_sent'] = True
    proposal['proposal_sent_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    proposal['proposal_sent_by'] = session['user_email']
    
    # Add to email history
    if 'email_history' not in proposal:
        proposal['email_history'] = []
    
    proposal['email_history'].append({
        'type': 'proposal_sent',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'by': session['user_email'],
        'to': proposal.get('contact_email', ''),
        'subject': f"Proposal: {proposal.get('project_name', 'Unknown')}"
    })
    
    proposals[proposal_number] = proposal
    save_json(DATABASES['proposals'], proposals)
    
    log_activity('proposal_sent', {'proposal_number': proposal_number})
    
    flash(f'Proposal {proposal_number} marked as sent to client.', 'success')
    return redirect(url_for('view_proposal', proposal_number=proposal_number))

@app.route('/proposal/<proposal_number>')
@login_required
def view_proposal(proposal_number):
    """View proposal details"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Get associated project if exists
    projects = load_json(DATABASES['projects'])
    associated_project = None
    if proposal.get('project_number'):
        associated_project = projects.get(proposal['project_number'])
    
    # Get all shared documents
    all_documents = get_shared_documents(proposal_number, proposal.get('project_number'))
    
    log_activity('proposal_viewed', {'proposal_number': proposal_number})
    
    return render_template('view_proposal.html', 
                         proposal=proposal, 
                         project=associated_project,
                         all_documents=all_documents)

@app.route('/project/<project_number>')
@login_required
def view_project(project_number):
    """View project details"""
    projects = load_json(DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    
    # Get associated proposal
    proposals = load_json(DATABASES['proposals'])
    associated_proposal = proposals.get(project.get('proposal_number'))
    
    # Get all shared documents
    all_documents = get_shared_documents(project.get('proposal_number'), project_number)
    
    log_activity('project_viewed', {'project_number': project_number})
    
    return render_template('view_project.html', 
                         project=project, 
                         proposal=associated_proposal,
                         all_documents=all_documents)

@app.route('/upload_document/<entity_type>/<entity_number>', methods=['POST'])
@login_required
def upload_document(entity_type, entity_number):
    """Upload document to proposal or project"""
    if 'document' not in request.files:
        flash('No file selected.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    file = request.files['document']
    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"{entity_number}_{timestamp}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Update database
        if entity_type == 'proposal':
            db = load_json(DATABASES['proposals'])
        else:
            db = load_json(DATABASES['projects'])
        
        if entity_number in db:
            if 'documents' not in db[entity_number]:
                db[entity_number]['documents'] = []
            
            db[entity_number]['documents'].append({
                'filename': filename,
                'original_name': file.filename,
                'uploaded_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'uploaded_by': session['user_email'],
                'type': request.form.get('doc_type', 'other')
            })
            
            save_json(DATABASES['proposals'] if entity_type == 'proposal' else DATABASES['projects'], db)
            
            log_activity('document_uploaded', {
                'entity_type': entity_type,
                'entity_number': entity_number,
                'filename': file.filename
            })
            
            flash('Document uploaded successfully!', 'success')
        else:
            flash('Entity not found.', 'error')
    else:
        flash('Invalid file type.', 'error')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/download_document/<filename>')
@login_required
def download_document(filename):
    """Download a document"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            # Extract original name from filename
            parts = filename.split('_', 2)
            download_name = parts[2] if len(parts) > 2 else filename
            
            log_activity('document_downloaded', {'filename': filename})
            
            return send_file(filepath, as_attachment=True, download_name=download_name)
        else:
            flash('File not found.', 'error')
            return redirect(request.referrer or url_for('index'))
    except Exception as e:
        flash('Error downloading file.', 'error')
        return redirect(request.referrer or url_for('index'))

@app.route('/delete_proposal/<proposal_number>', methods=['GET', 'POST'])
@login_required
def delete_proposal(proposal_number):
    """Delete proposal with confirmation"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Admin can delete any proposal
    if not user_can_edit(proposal):
        flash('You do not have permission to delete this proposal.', 'error')
        return redirect(url_for('view_proposal', proposal_number=proposal_number))
    
    # Check for associated project
    if proposal.get('project_number'):
        flash('Cannot delete proposal with associated project. Delete the project first.', 'error')
        return redirect(url_for('view_proposal', proposal_number=proposal_number))
    
    if request.method == 'POST':
        deletion_note = request.form.get('deletion_note', '')
        
        # Log deletion
        deletion_log = load_json(DATABASES['deletion_log'])
        if not isinstance(deletion_log, list):
            deletion_log = []
        
        deletion_log.append({
            'type': 'proposal',
            'number': proposal_number,
            'deleted_by': session['user_email'],
            'deleted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'deletion_note': deletion_note,
            'data_snapshot': proposal
        })
        
        save_json(DATABASES['deletion_log'], deletion_log)
        
        # Delete associated documents
        for doc in proposal.get('documents', []):
            try:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass
        
        # Delete proposal
        del proposals[proposal_number]
        save_json(DATABASES['proposals'], proposals)
        
        log_activity('proposal_deleted', {
            'proposal_number': proposal_number,
            'reason': deletion_note[:100] if deletion_note else 'No reason provided'
        })
        
        flash(f'Proposal {proposal_number} has been deleted.', 'success')
        return redirect(url_for('index'))
    
    return render_template('confirm_delete.html', 
                         entity_type='proposal',
                         entity_number=proposal_number,
                         entity_data=proposal)

@app.route('/delete_project/<project_number>', methods=['GET', 'POST'])
@login_required
def delete_project(project_number):
    """Delete project with confirmation"""
    projects = load_json(DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    
    # Admin can delete any project
    if not user_can_edit(project):
        flash('You do not have permission to delete this project.', 'error')
        return redirect(url_for('view_project', project_number=project_number))
    
    if request.method == 'POST':
        deletion_note = request.form.get('deletion_note', '')
        
        # Log deletion
        deletion_log = load_json(DATABASES['deletion_log'])
        if not isinstance(deletion_log, list):
            deletion_log = []
        
        deletion_log.append({
            'type': 'project',
            'number': project_number,
            'deleted_by': session['user_email'],
            'deleted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'deletion_note': deletion_note,
            'data_snapshot': project
        })
        
        save_json(DATABASES['deletion_log'], deletion_log)
        
        # Delete associated documents
        for doc in project.get('documents', []):
            try:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass
        
        # Get associated proposal
        proposal_number = project.get('proposal_number')
        proposals = load_json(DATABASES['proposals'])
        
        # Delete project
        del projects[project_number]
        save_json(DATABASES['projects'], projects)
        
        # Revert proposal status if exists
        if proposal_number and proposal_number in proposals:
            proposals[proposal_number]['status'] = 'pending'
            proposals[proposal_number].pop('project_number', None)
            proposals[proposal_number].pop('won_date', None)
            proposals[proposal_number].pop('won_by', None)
            save_json(DATABASES['proposals'], proposals)
        
        log_activity('project_deleted', {
            'project_number': project_number,
            'reason': deletion_note[:100] if deletion_note else 'No reason provided'
        })
        
        flash(f'Project {project_number} has been deleted.', 'success')
        return redirect(url_for('index'))
    
    return render_template('confirm_delete.html', 
                         entity_type='project',
                         entity_number=project_number,
                         entity_data=project)

# @app.route('/analytics')
# @login_required
# def analytics():
#     """View analytics dashboard"""
#     log_activity('analytics_view', {})
    
#     analytics_data = get_analytics()
    
#     # Prepare chart data
#     months = []
#     proposals_data = []
#     wins_data = []
#     revenue_data = []
    
#     # Get last 6 months
#     for i in range(5, -1, -1):
#         date = datetime.now() - timedelta(days=i*30)
#         month_key = date.strftime('%Y-%m')
#         month_name = date.strftime('%b %Y')
        
#         months.append(month_name)
#         monthly_data = analytics_data.get('monthly_data', {})
#         proposals_data.append(monthly_data.get('monthly_proposals', {}).get(month_key, 0))
#         wins_data.append(monthly_data.get('monthly_wins', {}).get(month_key, 0))
#         revenue_data.append(monthly_data.get('monthly_revenue', {}).get(month_key, 0))
    
#     return render_template('analytics.html',
#                          analytics=analytics_data,
#                          months=months,
#                          offices=get_system_setting('office_codes', {}),
#                          proposals_data=proposals_data,
#                          wins_data=wins_data,
#                          revenue_data=revenue_data)


# Replace the update_analytics function in main.py (around line 460)

def update_analytics(action, data):
    """Update analytics data with better tracking"""
    analytics = load_json(DATABASES['analytics'])
    month_key = datetime.now().strftime('%Y-%m')
    
    if action == 'new_proposal':
        # Track new proposals (NOT as wins!)
        analytics.setdefault('monthly_proposals', {})[month_key] = \
            analytics.get('monthly_proposals', {}).get(month_key, 0) + 1
        
        # Track by office
        office = data.get('office')
        if office:
            analytics.setdefault('office_performance', {}).setdefault(office, {})
            analytics['office_performance'][office].setdefault('proposals', {})[month_key] = \
                analytics['office_performance'][office].get('proposals', {}).get(month_key, 0) + 1
    
    elif action == 'proposal_won':
        # Track actual wins (when proposal is converted to project)
        analytics.setdefault('monthly_wins', {})[month_key] = \
            analytics.get('monthly_wins', {}).get(month_key, 0) + 1
        
        fee = float(data.get('fee', 0))
        analytics.setdefault('monthly_revenue', {})[month_key] = \
            analytics.get('monthly_revenue', {}).get(month_key, 0) + fee
        
        # Track by PM
        pm = data.get('project_manager')
        if pm:
            analytics.setdefault('pm_performance', {}).setdefault(pm, {})
            analytics['pm_performance'][pm]['wins'] = \
                analytics['pm_performance'][pm].get('wins', 0) + 1
            analytics['pm_performance'][pm]['revenue'] = \
                analytics['pm_performance'][pm].get('revenue', 0) + fee
            
        # Track by office
        office = data.get('office')
        if office:
            analytics.setdefault('office_performance', {}).setdefault(office, {})
            analytics['office_performance'][office]['wins'] = \
                analytics['office_performance'][office].get('wins', 0) + 1
            analytics['office_performance'][office]['revenue'] = \
                analytics['office_performance'][office].get('revenue', 0) + fee
    
    elif action == 'project_completed':
        # Track completed projects
        analytics.setdefault('monthly_completed', {})[month_key] = \
            analytics.get('monthly_completed', {}).get(month_key, 0) + 1
    
    save_json(DATABASES['analytics'], analytics)


# Replace the get_analytics function in main.py (around line 510)

def get_analytics():
    """Get comprehensive analytics data"""
    proposals = load_json(DATABASES['proposals'])
    projects = load_json(DATABASES['projects'])
    analytics = load_json(DATABASES['analytics'])
    
    # Calculate different categories
    active_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'pending'}
    pending_legal_projects = {k: v for k, v in projects.items() if v.get('status') == 'pending_legal'}
    active_projects = {k: v for k, v in projects.items() if v.get('status') == 'active'}
    completed_projects = {k: v for k, v in projects.items() if v.get('status') == 'completed'}
    lost_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'lost'}
    dead_jobs = {k: v for k, v in projects.items() if v.get('status') == 'dead'}
    
    # Total counts
    total_active_items = len(active_proposals) + len(pending_legal_projects) + len(active_projects)
    total_completed_items = len(completed_projects) + len(lost_proposals) + len(dead_jobs)
    
    # Win rate calculation - based on proposals that have been decided
    won_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'converted_to_project'}
    total_decided = len(won_proposals) + len(lost_proposals)
    win_rate = (len(won_proposals) / total_decided * 100) if total_decided > 0 else 0
    
    # Revenue calculation by office
    total_revenue = 0
    revenue_by_office = {}
    
    for proposal_num, proposal in proposals.items():
        if proposal.get('status') == 'converted_to_project':
            office = proposal.get('office', 'Unknown')
            fee = float(proposal.get('fee', 0))
            total_revenue += fee
            revenue_by_office[office] = revenue_by_office.get(office, 0) + fee
    
    # Project manager performance
    pm_performance = {}
    for proposal in proposals.values():
        pm = proposal.get('project_manager', 'Unknown')
        if pm not in pm_performance:
            pm_performance[pm] = {'total': 0, 'won': 0, 'revenue': 0}
        pm_performance[pm]['total'] += 1
        
        # Check if won
        if proposal.get('status') == 'converted_to_project':
            pm_performance[pm]['won'] += 1
            pm_performance[pm]['revenue'] += float(proposal.get('fee', 0))
    
    # Average time to win
    win_times = []
    for proposal in won_proposals.values():
        try:
            proposal_date = proposal.get('date', '')
            won_date = proposal.get('won_date', '')
            if proposal_date and won_date:
                proposal_created = datetime.strptime(proposal_date, '%Y-%m-%d')
                proposal_won = datetime.strptime(won_date, '%Y-%m-%d')
                win_times.append((proposal_won - proposal_created).days)
        except:
            pass
    
    avg_time_to_win = sum(win_times) / len(win_times) if win_times else 0
    
    return {
        'win_rate': round(win_rate, 1),
        'won_proposals': len(won_proposals),
        'total_proposals': total_decided,
        'active_proposals': len(active_proposals),
        'pending_legal_projects': len(pending_legal_projects),
        'active_projects': len(active_projects),
        'completed_projects': len(completed_projects),
        'lost_proposals': len(lost_proposals),
        'dead_jobs': len(dead_jobs),
        'total_active_items': total_active_items,
        'total_completed_items': total_completed_items,
        'total_revenue': total_revenue,
        'revenue_by_office': revenue_by_office,
        'pm_performance': pm_performance,
        'avg_time_to_win': round(avg_time_to_win, 1),
        'monthly_data': analytics
    }


# Update th



# API endpoints for future integration
@app.route('/api/proposals', methods=['GET'])
@login_required
def api_get_proposals():
    """API endpoint to get proposals (for future Azure integration)"""
    proposals = load_json(DATABASES['proposals'])
    
    # Filter based on query parameters
    status = request.args.get('status')
    office = request.args.get('office')
    pm = request.args.get('project_manager')
    
    filtered = {}
    for prop_num, proposal in proposals.items():
        if status and proposal.get('status') != status:
            continue
        if office and proposal.get('office') != office:
            continue
        if pm and proposal.get('project_manager') != pm:
            continue
        filtered[prop_num] = proposal
    
    return jsonify({
        'status': 'success',
        'count': len(filtered),
        'data': filtered
    })

@app.route('/api/projects', methods=['GET'])
@login_required
def api_get_projects():
    """API endpoint to get projects (for future Azure integration)"""
    projects = load_json(DATABASES['projects'])
    
    # Filter based on query parameters
    status = request.args.get('status')
    pm = request.args.get('project_manager')
    
    filtered = {}
    for proj_num, project in projects.items():
        if status and project.get('status') != status:
            continue
        if pm and project.get('project_manager') != pm:
            continue
        filtered[proj_num] = project
    
    return jsonify({
        'status': 'success',
        'count': len(filtered),
        'data': filtered
    })

@app.route('/api/analytics', methods=['GET'])
@login_required
def api_get_analytics():
    """API endpoint to get analytics (for future Azure integration)"""
    analytics = get_analytics()
    return jsonify({
        'status': 'success',
        'data': analytics
    })

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '2.0.0'
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
    return render_template('500.html'), 500

# Template context processors
@app.context_processor
def inject_settings():
    """Inject common settings into all templates"""
    return {
        'current_year': datetime.now().year,
        'system_version': '2.0.0',
        'company_name': 'Geocon Inc.'
    }


# Add these routes to main.py after the existing routes

# 3. Update the mark_won route to properly handle projects that don't need legal review
@app.route('/mark_won/<proposal_number>', methods=['POST'])
@login_required
def mark_won(proposal_number):
    """Mark proposal as won and create project - FIXED VERSION"""
    proposals = load_json(DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Check permissions
    if (proposal.get('project_manager') != session.get('user_name') and 
        not session.get('is_admin')):
        flash('Only the project manager can mark this proposal as won.', 'error')
        return redirect(url_for('index'))
    
    # Get form data
    needs_legal_review = request.form.get('needs_legal_review') == 'yes'
    project_folder_path = request.form.get('project_folder_path', '')
    
    # Generate project number
    team_number = proposal.get('team_number', '00')
    project_number = get_next_project_number(team_number)
    
    # Update proposal
    proposal['status'] = 'converted_to_project'
    proposal['win_loss'] = 'W'
    proposal['project_number'] = project_number
    proposal['won_date'] = datetime.now().strftime('%Y-%m-%d')
    proposal['won_by'] = session['user_email']
    proposal['project_folder_path'] = project_folder_path
    
    # FIXED: Set correct status based on legal review need
    if needs_legal_review:
        project_status = 'pending_legal'
    else:
        # If no legal review needed, go to pending_additional_info
        project_status = 'pending_additional_info'
    
    project_data = {
        'project_number': project_number,
        'proposal_number': proposal_number,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'project_name': proposal.get('project_name', 'Unknown'),
        'client': proposal.get('client', 'Unknown'),
        'contact': f"{proposal.get('contact_first', '')} {proposal.get('contact_last', '')}",
        'project_manager': proposal.get('project_manager', 'Unknown'),
        'team_number': team_number,
        'status': project_status,
        'needs_legal_review': needs_legal_review,
        'project_folder_path': project_folder_path,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'documents': [],
        'email_history': [],
        'office': proposal.get('office', ''),
        'fee': proposal.get('fee', 0),
        
        # Legal Queue Fields
        'legal_status': 'new_request' if needs_legal_review else None,
        'contract_type': request.form.get('contract_type', ''),
        'requested_review_date': request.form.get('requested_review_date', ''),
        'contract_entity': request.form.get('contract_entity', proposal.get('client', '')),
        'client_contact_name': request.form.get('client_contact_name', ''),
        'client_contact_email': request.form.get('client_contact_email', ''),
        'client_contact_phone': request.form.get('client_contact_phone', ''),
        'contracted_before': request.form.get('contracted_before', 'no'),
        'previous_project_number': request.form.get('previous_project_number', ''),
        'need_subcontractors': request.form.get('need_subcontractors', 'no'),
        'legal_can_contact': request.form.get('legal_can_contact', 'yes'),
        'file_lien_notice': request.form.get('file_lien_notice', 'no'),
        'coi_needed': request.form.get('coi_needed') == 'yes',
        'documents_location': request.form.get('documents_location', ''),
        'notes_comments': request.form.get('notes_comments', ''),
        'legal_status_history': []
    }
    
    # FIXED: Handle projects that don't need legal review
    if not needs_legal_review:
        project_data['legal_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        project_data['legal_approved_by'] = 'Auto-approved (No legal review required)'
        
        # Send notification to PM
        pm_email = f"{proposal['project_manager'].lower().replace(' ', '.')}@geoconinc.com"
        subject = f"Action Required: Complete Project Information for {project_number}"
        body = f"""
        Project {project_number} has been created and requires additional information.
        
        Project: {proposal.get('project_name', 'Unknown')}
        Client: {proposal.get('client', 'Unknown')}
        
        ACTION REQUIRED: Please complete the additional project information in the system
        to finalize the project setup in Geocon's system.
        
        Login to the system and look for the project in "Projects Pending Additional Information" section.
        """
        send_email(pm_email, subject, body)
        
        flash(f'Proposal marked as won! Project {project_number} created. Please complete additional information.', 'success')
    else:
        # Add initial status to history for legal review
        project_data['legal_status_history'].append({
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'new_request',
            'user': session['user_email'],
            'notes': 'Project submitted for legal review'
        })
        
        legal_email = get_system_setting('legal_dept_email', 'legal@geoconinc.com')
        subject = f"Legal Review Required: Project {project_number}"
        body = f"""
        Legal Review Required for Project {project_number}
        
        Project: {proposal.get('project_name', 'Unknown')}
        Client: {proposal.get('client', 'Unknown')}
        PM: {proposal.get('project_manager', 'Unknown')}
        Fee: ${proposal.get('fee', 0)}
        Contract Type: {project_data.get('contract_type', 'Not specified')}
        Review By Date: {project_data.get('requested_review_date', 'Not specified')}
        Project Folder: {project_folder_path}
        
        Please review in the Legal Queue system.
        """
        send_email(legal_email, subject, body)
        flash(f'Proposal marked as won! Project {project_number} created and sent for legal review.', 'success')
    
    # Save updates
    proposals[proposal_number] = proposal
    save_json(DATABASES['proposals'], proposals)
    
    projects = load_json(DATABASES['projects'])
    projects[project_number] = project_data
    save_json(DATABASES['projects'], projects)
    
    # Update analytics
    update_analytics('proposal_won', proposal)
    
    log_activity('proposal_won', {
        'proposal_number': proposal_number,
        'project_number': project_number,
        'needs_legal': needs_legal_review
    })
    
    return redirect(url_for('index'))


# 5. Updated legal_queue route with multiple tabs support
@app.route('/legal_queue')
@legal_required
def legal_queue():
    """View legal department tabs - review queue, executed contracts, insurance requests"""
    log_activity('legal_queue_view', {})
    
    projects = load_json(DATABASES['projects'])
    proposals = load_json(DATABASES['proposals'])
    executed_contracts = load_json(DATABASES['executed_contracts'])
    insurance_requests = load_json(DATABASES['insurance_requests'])
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    office_filter = request.args.get('office', '')
    pm_filter = request.args.get('pm', '')
    tab = request.args.get('tab', 'review-queue')
    
    # Filter projects for review queue
    review_queue = {}
    for proj_num, project in projects.items():
        # Include projects that need legal review or have legal status
        if project.get('needs_legal_review') or project.get('legal_status'):
            # Exclude signed projects from review queue
            if project.get('legal_status') == 'signed':
                continue
                
            # Apply filters
            if status_filter and project.get('legal_status', 'new_request') != status_filter:
                continue
            if office_filter and project.get('office') != office_filter:
                continue
            if pm_filter and project.get('project_manager') != pm_filter:
                continue
            
            # Add proposal fee if available
            if project.get('proposal_number') in proposals:
                project['fee'] = proposals[project['proposal_number']].get('fee', 0)
            
            review_queue[proj_num] = project
    
    # Calculate statistics
    stats = {
        'new_request': sum(1 for p in review_queue.values() if p.get('legal_status', 'new_request') == 'new_request'),
        'under_review': sum(1 for p in review_queue.values() if p.get('legal_status') == 'under_review'),
        'questions_to_pm': sum(1 for p in review_queue.values() if p.get('legal_status') == 'questions_to_pm'),
        'edits_to_client': sum(1 for p in review_queue.values() if p.get('legal_status') == 'edits_to_client'),
        'negotiating': sum(1 for p in review_queue.values() if p.get('legal_status') == 'negotiating'),
        'signed': sum(1 for p in projects.values() if p.get('legal_status') == 'signed'),
        'on_hold': sum(1 for p in review_queue.values() if p.get('legal_status') == 'on_hold'),
    }
    
    # Get list of project managers for filter
    project_managers = get_system_setting('project_managers', [])
    
    return render_template('legal_queue.html',
                         review_queue=review_queue,
                         executed_contracts=executed_contracts,
                         insurance_requests=insurance_requests,
                         stats=stats,
                         offices=get_system_setting('office_codes', {}),
                         project_managers=project_managers,
                         tab=tab)


# 6. Add route for adding executed contracts
@app.route('/add_executed_contract', methods=['GET', 'POST'])
@legal_required
def add_executed_contract():
    """Add a new executed contract record"""
    if request.method == 'POST':
        contracts = load_json(DATABASES['executed_contracts'])
        
        contract_id = str(uuid.uuid4())
        contract_data = {
            'id': contract_id,
            'date_added': datetime.now().strftime('%Y-%m-%d'),
            'project_number': request.form.get('project_number', ''),
            'project_name': request.form.get('project_name', ''),
            'client': request.form.get('client', ''),
            'contract_type': request.form.get('contract_type', ''),
            'documents_location': request.form.get('documents_location', ''),
            'notes': request.form.get('notes', ''),
            'added_by': session['user_email']
        }
        
        contracts[contract_id] = contract_data
        save_json(DATABASES['executed_contracts'], contracts)
        
        log_activity('executed_contract_added', {'contract_id': contract_id})
        flash('Executed contract record added successfully!', 'success')
        return redirect(url_for('legal_queue', tab='executed-contracts'))
    
    return render_template('add_executed_contract.html')

# 7. Add route for adding insurance requests
@app.route('/add_insurance_request', methods=['GET', 'POST'])
@legal_required
def add_insurance_request():
    """Add a new insurance request"""
    if request.method == 'POST':
        requests = load_json(DATABASES['insurance_requests'])
        
        request_id = str(uuid.uuid4())
        request_data = {
            'id': request_id,
            'status': 'pending',
            'date_requested': request.form.get('date_requested', datetime.now().strftime('%Y-%m-%d')),
            'completion_date': request.form.get('completion_date', ''),
            'requested_by': request.form.get('requested_by', ''),
            'office': request.form.get('office', ''),
            'project_number': request.form.get('project_number', ''),
            'project_name': request.form.get('project_name', ''),
            'certificate_holder': request.form.get('certificate_holder', ''),
            'client_contact_name': request.form.get('client_contact_name', ''),
            'client_contact_email': request.form.get('client_contact_email', ''),
            'can_legal_contact': request.form.get('can_legal_contact', 'Yes'),
            'handled_by': request.form.get('handled_by', ''),
            'documents_location': request.form.get('documents_location', ''),
            'notes': request.form.get('notes', ''),
            'added_by': session['user_email']
        }
        
        requests[request_id] = request_data
        save_json(DATABASES['insurance_requests'], requests)
        
        log_activity('insurance_request_added', {'request_id': request_id})
        flash('Insurance request added successfully!', 'success')
        return redirect(url_for('legal_queue', tab='insurance-requests'))
    
    return render_template('add_insurance_request.html',
                         offices=get_system_setting('office_codes', {}))

# 8. Mark insurance request as issued
@app.route('/mark_insurance_issued/<request_id>')
@legal_required
def mark_insurance_issued(request_id):
    """Mark an insurance request as issued"""
    requests = load_json(DATABASES['insurance_requests'])
    
    if request_id in requests:
        requests[request_id]['status'] = 'issued'
        requests[request_id]['issued_date'] = datetime.now().strftime('%Y-%m-%d')
        requests[request_id]['issued_by'] = session['user_email']
        save_json(DATABASES['insurance_requests'], requests)
        
        log_activity('insurance_request_issued', {'request_id': request_id})
        flash('Insurance request marked as issued!', 'success')
    
    return redirect(url_for('legal_queue', tab='insurance-requests'))

# Legal Queue Detail view
@app.route('/legal_queue_detail/<project_number>')
@legal_required
def legal_queue_detail(project_number):
    """View detailed legal queue information for a project"""
    log_activity('legal_queue_detail_view', {'project_number': project_number})
    
    projects = load_json(DATABASES['projects'])
    proposals = load_json(DATABASES['proposals'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('legal_queue'))
    
    project = projects[project_number]
    
    # Get associated proposal for fee
    if project.get('proposal_number') in proposals:
        proposal = proposals[project['proposal_number']]
        project['fee'] = proposal.get('fee', 0)
        project['office'] = proposal.get('office', '')
    
    return render_template('legal_queue_detail.html', project=project)


# Update Legal Status
@app.route('/update_legal_status/<project_number>', methods=['GET', 'POST'])
@legal_required
def update_legal_status(project_number):
    """Update the legal status of a project"""
    projects = load_json(DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('legal_queue'))
    
    project = projects[project_number]
    
    if request.method == 'POST':
        new_status = request.form.get('new_status')
        status_notes = request.form.get('status_notes', '')
        
        # Store old status
        old_status = project.get('legal_status', 'new_request')
        
        # Update status
        project['legal_status'] = new_status
        project['reviewed_by'] = session['user_email']
        project['last_status_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Add to status history
        if 'legal_status_history' not in project:
            project['legal_status_history'] = []
        
        project['legal_status_history'].append({
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': new_status,
            'old_status': old_status,
            'user': session['user_email'],
            'notes': status_notes
        })
        
        # If marked as signed, update project status
        if new_status == 'signed':
            project['status'] = 'active'
            project['legal_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            project['legal_approved_by'] = session['user_email']
            project['legal_signed'] = True
            project['legal_signed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            project['geocon_updated'] = True
            project['geocon_update_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\n🚀 POWER AUTOMATE SCRIPT RUN - Project: {project_number}")
            print(f"Project legally approved and signed")
            
            # Send notification to PM
            pm_email = f"{project['project_manager'].lower().replace(' ', '.')}@geoconinc.com"
            subject = f"Contract Signed: Project {project_number}"
            body = f"""
            Good news! The contract for project {project_number} has been signed.
            
            Project: {project['project_name']}
            Client: {project['client']}
            Status: Active
            
            The project is now active and ready to proceed.
            """
            send_email(pm_email, subject, body)
            
        # If marked as not signed, update project status
        elif new_status == 'not_signed':
            project['status'] = 'dead'
            project['legal_reviewed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            project['legal_reviewed_by'] = session['user_email']
            project['legal_signed'] = False
            project['not_signed_reason'] = status_notes
            
            # Send notification to PM
            pm_email = f"{project['project_manager'].lower().replace(' ', '.')}@geoconinc.com"
            subject = f"Contract Not Signed: Project {project_number}"
            body = f"""
            The contract for project {project_number} will not be signed.
            
            Project: {project['project_name']}
            Client: {project['client']}
            Reason: {status_notes}
            
            The project has been moved to Dead Jobs.
            """
            send_email(pm_email, subject, body)
        
        # If questions to PM, send notification
        elif new_status == 'questions_to_pm':
            pm_email = f"{project['project_manager'].lower().replace(' ', '.')}@geoconinc.com"
            subject = f"Legal Questions: Project {project_number}"
            body = f"""
            The legal team has questions regarding project {project_number}.
            
            Project: {project['project_name']}
            Client: {project['client']}
            
            Questions/Notes: {status_notes}
            
            Please respond to the legal team as soon as possible.
            """
            send_email(pm_email, subject, body)
        
        # Save updates
        projects[project_number] = project
        save_json(DATABASES['projects'], projects)
        
        log_activity('legal_status_updated', {
            'project_number': project_number,
            'old_status': old_status,
            'new_status': new_status,
            'notes': status_notes[:100] if status_notes else ''
        })
        
        flash(f'Legal status updated to: {new_status.replace("_", " ").title()}', 'success')
        return redirect(url_for('legal_queue'))
    
    return render_template('update_legal_status.html', project=project)

# Add these new routes to main.py after the existing routes


# ============================================================================
# SECTION 1: ADD THESE CONSTANTS AFTER YOUR EXISTING DEFAULT_SETTINGS (around line 120)
# ============================================================================

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

# ============================================================================
# SECTION 2: UPDATE YOUR DEFAULT_SETTINGS DICTIONARY
# Add this to your existing DEFAULT_SETTINGS (around line 180)
# ============================================================================

# Add to DEFAULT_SETTINGS:
DEFAULT_SETTINGS['analytics_users'] = [
    'admin@geoconinc.com',
    'shawn.weedon@geoconinc.com',
    'rebecca.silva@geoconinc.com'
]

# ============================================================================
# SECTION 3: ADD THIS NEW FUNCTION AFTER get_analytics() (around line 550)
# ============================================================================

def get_enhanced_analytics():
    """Get enhanced analytics with last month proposals and legal queue count"""
    proposals = load_json(DATABASES['proposals'])
    projects = load_json(DATABASES['projects'])
    analytics = load_json(DATABASES['analytics'])
    
    # Get last month's data
    last_month = (datetime.now() - timedelta(days=30))
    last_month_key = last_month.strftime('%Y-%m')
    last_month_name = last_month.strftime('%B %Y')
    
    # Count proposals created last month
    last_month_proposals = 0
    for proposal in proposals.values():
        try:
            if proposal.get('date', '').startswith(last_month_key):
                last_month_proposals += 1
        except:
            pass
    
    # Count legal queue items
    legal_queue_count = 0
    for project in projects.values():
        if (project.get('status') == 'pending_legal' or 
            (project.get('legal_status') and project.get('legal_status') not in ['signed', 'not_signed'])):
            legal_queue_count += 1
    
    # Calculate different categories
    active_proposals = len([p for p in proposals.values() if p.get('status') == 'pending'])
    pending_info_projects = len([p for p in projects.values() if p.get('status') == 'pending_additional_info'])
    pending_legal_projects = len([p for p in projects.values() if p.get('status') == 'pending_legal'])
    
    # Total active items
    total_active_items = active_proposals + pending_info_projects + pending_legal_projects
    
    # Win rate calculation
    won_proposals = len([p for p in proposals.values() if p.get('status') == 'converted_to_project'])
    lost_proposals = len([p for p in proposals.values() if p.get('status') == 'lost'])
    total_decided = won_proposals + lost_proposals
    win_rate = (won_proposals / total_decided * 100) if total_decided > 0 else 0
    
    return {
        'last_month_proposals': last_month_proposals,
        'last_month_name': last_month_name,
        'total_active_items': total_active_items,
        'win_rate': round(win_rate, 1),
        'won_proposals': won_proposals,
        'lost_proposals': lost_proposals,
        'legal_queue_count': legal_queue_count
    }

# ============================================================================
# SECTION 4: REPLACE YOUR EXISTING index() ROUTE (around line 1000)
# ============================================================================

def user_can_edit(entity, field='project_manager'):
    """Check if current user can edit an entity - admin can edit everything"""
    if session.get('is_admin'):
        return True
    
    # Check various permission fields
    if entity.get(field) == session.get('user_name'):
        return True
    if entity.get('created_by') == session.get('user_email'):
        return True
    if entity.get('project_manager') == session.get('user_name'):
        return True
        
    return False

@app.route('/')
@login_required
def index():
    """Main dashboard with enhanced filters and analytics - FIXED VERSION"""
    log_activity('dashboard_view', {})
    
    proposals = load_json(DATABASES['proposals'])
    projects = load_json(DATABASES['projects'])
    
    # Filter active items
    active_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'pending'}
    
    # Filter projects by different statuses
    pending_legal_projects = {}
    pending_additional_info_projects = {}
    active_projects = {}  # ADD THIS
    
    for k, v in projects.items():
        # Projects pending legal review
        if v.get('status') == 'pending_legal':
            # Show to admin or project manager
            if session.get('is_admin') or v.get('project_manager') == session.get('user_name'):
                pending_legal_projects[k] = v
        
        # Projects pending additional information - FIXED: Admin can see all
        elif v.get('status') == 'pending_additional_info':
            # Calculate days pending
            if v.get('legal_approved_date'):
                try:
                    approved_date = datetime.strptime(v['legal_approved_date'].split(' ')[0], '%Y-%m-%d')
                    days_pending = (datetime.now() - approved_date).days
                    v['days_pending'] = days_pending
                except:
                    v['days_pending'] = 0
            
            # Admin sees all, others see only their own
            if session.get('is_admin') or v.get('project_manager') == session.get('user_name'):
                pending_additional_info_projects[k] = v
        
        # Active projects (marked as won but no legal review needed) - FIXED
        elif v.get('status') == 'active' and not v.get('needs_legal_review'):
            # Show active projects that went straight to active
            if session.get('is_admin') or v.get('project_manager') == session.get('user_name'):
                active_projects[k] = v
        
        # Projects pending additional information - admin sees all
        if v.get('status') == 'pending_additional_info':
            # Calculate days pending
            if v.get('legal_approved_date'):
                try:
                    approved_date = datetime.strptime(v['legal_approved_date'].split(' ')[0], '%Y-%m-%d')
                    days_pending = (datetime.now() - approved_date).days
                    v['days_pending'] = days_pending
                except:
                    v['days_pending'] = 0
            
            # Admin sees all, others see only their own
            if session.get('is_admin') or v.get('project_manager') == session.get('user_name'):
                pending_additional_info_projects[k] = v
        
        # Projects pending additional information (after legal approval)
        if v.get('status') == 'pending_additional_info':
            # Calculate days pending
            if v.get('legal_approved_date'):
                try:
                    approved_date = datetime.strptime(v['legal_approved_date'].split(' ')[0], '%Y-%m-%d')
                    days_pending = (datetime.now() - approved_date).days
                    v['days_pending'] = days_pending
                except:
                    v['days_pending'] = 0
            pending_additional_info_projects[k] = v
    
    # Get search and filter parameters
    search_query = request.args.get('search', '').lower()
    status_filter = request.args.get('status', '')
    office_filter = request.args.get('office', '')
    pm_filter = request.args.get('pm_filter', '')  # New PM/Director filter
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Apply filters to proposals
    filtered_proposals = {}
    for prop_num, proposal in active_proposals.items():
        # Search filter
        if search_query:
            search_fields = [
                proposal.get('proposal_number', '').lower(),
                proposal.get('client', '').lower(),
                proposal.get('project_manager', '').lower(),
                proposal.get('project_name', '').lower()
            ]
            if not any(search_query in field for field in search_fields):
                continue
        
        # Status filter
        if status_filter and proposal.get('status') != status_filter:
            continue
        
        # Office filter
        if office_filter and proposal.get('office') != office_filter:
            continue
        
        # PM/Director filter
        if pm_filter:
            if (proposal.get('project_manager') != pm_filter and 
                proposal.get('project_director') != pm_filter):
                continue
        
        # Date range filter
        if date_from and proposal.get('date', '') < date_from:
            continue
        if date_to and proposal.get('date', '') > date_to:
            continue
        
        filtered_proposals[prop_num] = proposal
    
    # Get enhanced analytics
    analytics = get_enhanced_analytics()
    
    # Check if user can view full analytics
    analytics_users = get_system_setting('analytics_users', [])
    can_view_analytics = (session.get('user_email') in analytics_users or 
                          session.get('is_admin'))
    
    # Get project managers for filter
    project_managers = get_system_setting('project_managers', [])
    
    # Check for follow-up reminders
    check_follow_up_reminders()
    
    return render_template('dashboard.html', 
                         proposals=filtered_proposals, 
                         pending_legal_projects=pending_legal_projects,
                         pending_additional_info_projects=pending_additional_info_projects,
                         user_email=session.get('user_email'),
                         user_name=session.get('user_name'),
                         offices=get_system_setting('office_codes', {}),
                         project_managers=project_managers,
                         search_query=search_query,
                         status_filter=status_filter,
                         office_filter=office_filter,
                         pm_filter=pm_filter,
                         date_from=date_from,
                         date_to=date_to,
                         analytics=analytics,
                         can_view_analytics=can_view_analytics)

# ============================================================================
# SECTION 5: REPLACE YOUR EXISTING analytics() ROUTE (around line 2170)
# ============================================================================

@app.route('/analytics')
@login_required
def analytics():
    """View analytics dashboard - restricted access"""
    # Check if user has analytics access
    analytics_users = get_system_setting('analytics_users', [])
    if (session.get('user_email') not in analytics_users and 
        not session.get('is_admin')):
        flash('You do not have permission to view analytics.', 'error')
        return redirect(url_for('index'))
    
    log_activity('analytics_view', {})
    
    analytics_data = get_analytics()
    
    # Prepare chart data
    months = []
    proposals_data = []
    completed_data = []
    revenue_data = []
    
    # Get last 6 months
    for i in range(5, -1, -1):
        date = datetime.now() - timedelta(days=i*30)
        month_key = date.strftime('%Y-%m')
        month_name = date.strftime('%b %Y')
        
        months.append(month_name)
        monthly_data = analytics_data.get('monthly_data', {})
        proposals_data.append(monthly_data.get('monthly_proposals', {}).get(month_key, 0))
        completed_data.append(monthly_data.get('monthly_completed', {}).get(month_key, 0))
        revenue_data.append(monthly_data.get('monthly_revenue', {}).get(month_key, 0))
    
    # Calculate total revenue for percentage calculations
    total_revenue = analytics_data.get('total_revenue', 0)
    
    return render_template('analytics.html',
                         analytics=analytics_data,
                         months=months,
                         offices=get_system_setting('office_codes', {}),
                         proposals_data=proposals_data,
                         completed_data=completed_data,
                         revenue_data=revenue_data,
                         total_revenue=total_revenue)

# ============================================================================
# SECTION 6: ADD THESE NEW ROUTES (Add after your existing routes, around line 2200)
# ============================================================================



@app.route('/submit_project_info/<project_number>', methods=['POST'])
@login_required
def submit_project_info(project_number):
    """Submit additional project information and complete project setup"""
    projects = load_json(DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    action = request.form.get('action')
    
    # Collect all form data
    project_data_update = {
        'client_id': request.form.get('client_id', ''),
        'project_setup_date': request.form.get('project_setup_date', ''),
        'revenue_code': request.form.get('revenue_code', ''),
        'scope': request.form.get('scope', ''),
        'type': request.form.get('type', ''),
        'team_number': request.form.get('team_number', ''),
        'project_director': request.form.get('project_director', ''),
        'property_owner': request.form.get('property_owner', ''),
        'client_po': request.form.get('client_po', ''),
        'project_client_contact': request.form.get('project_client_contact', ''),
        'start_date': request.form.get('start_date', ''),
        'end_date': request.form.get('end_date', ''),
        'latitude': request.form.get('latitude', ''),
        'longitude': request.form.get('longitude', ''),
        'project_address': request.form.get('project_address', ''),
        'project_city': request.form.get('project_city', ''),
        'project_state': request.form.get('project_state', ''),
        'project_county': request.form.get('project_county', ''),
        'project_country': request.form.get('project_country', ''),
        'civil': request.form.get('civil', ''),
        'structural': request.form.get('structural', ''),
        'architect': request.form.get('architect', ''),
        'general_contractor': request.form.get('general_contractor', ''),
        'eir': request.form.get('eir', ''),
        'developer': request.form.get('developer', ''),
        'cm': request.form.get('cm', ''),
        'landscape_architect': request.form.get('landscape_architect', ''),
        'dsa_number': request.form.get('dsa_number', ''),
        'ior_number': request.form.get('ior_number', ''),
        'project_fee_type': request.form.get('project_fee_type', ''),
        'project_value': request.form.get('project_value', ''),
        'labor_budget': request.form.get('labor_budget', ''),
        'expense_budget': request.form.get('expense_budget', ''),
        'lab_budget': request.form.get('lab_budget', ''),
        'total_budget': request.form.get('total_budget', ''),
        'bill_rate_schedule': request.form.get('bill_rate_schedule', ''),
        'lab_rate_schedule': request.form.get('lab_rate_schedule', ''),
        'prevailing_wage': 'prevailing_wage' in request.form,
        'billing_contact': request.form.get('billing_contact', ''),
        'billing_email': request.form.get('billing_email', ''),
        'send_invoice_via': request.form.get('send_invoice_via', ''),
        'workfile': request.form.get('workfile', ''),
        'proposal': request.form.get('proposal', ''),
        'contract': request.form.get('contract', ''),
        'ins_certificate': request.form.get('ins_certificate', ''),
        'preliminary': request.form.get('preliminary', ''),
        'need_by_date': request.form.get('need_by_date', ''),
        'co': request.form.get('co', ''),
        'writeup_worthy': 'writeup_worthy' in request.form,
        'billing_comments': request.form.get('billing_comments', ''),
        'accounting_note': request.form.get('accounting_note', ''),
        'project_details': request.form.get('project_details', '')
    }
    
    # Update project with new data
    project.update(project_data_update)
    
    if action == 'submit':
        # Mark project as completed and trigger Power Automate
        project['status'] = 'completed'
        project['info_submitted_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        project['info_submitted_by'] = session['user_email']
        project['geocon_system_updated'] = True
        project['power_automate_triggered'] = True
        project['completion_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Print to terminal
        print("\n" + "="*60)
        print("🚀 POWER AUTOMATE SCRIPT TRIGGERED")
        print("="*60)
        print(f"Project Number: {project_number}")
        print(f"Project Name: {project['project_name']}")
        print(f"Client: {project['client']}")
        print(f"Project Manager: {project['project_manager']}")
        print(f"Revenue Code: {project_data_update['revenue_code']}")
        print(f"Project City: {project_data_update['project_city']}")
        print(f"Project State: {project_data_update['project_state']}")
        print("Status: Project information submitted to Geocon system")
        print("="*60 + "\n")
        
        # Update analytics
        update_analytics('project_completed', project)
        
        # Log activity
        log_activity('project_info_submitted', {
            'project_number': project_number,
            'action': 'submitted_to_geocon'
        })
        
        flash(f'Project {project_number} information submitted successfully! Project moved to Past Projects.', 'success')
        
    elif action == 'save_draft':
        # Save as draft
        project['info_draft_saved'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        project['info_draft_saved_by'] = session['user_email']
        
        log_activity('project_info_draft_saved', {
            'project_number': project_number
        })
        
        flash(f'Draft saved for project {project_number}.', 'success')
        return redirect(url_for('project_info_form', project_number=project_number))
    
    # Save project
    projects[project_number] = project
    save_json(DATABASES['projects'], projects)
    
    return redirect(url_for('index'))


@app.route('/admin/analytics_users', methods=['POST'])
@admin_required
def update_analytics_users():
    """Update list of users who can view analytics"""
    analytics_users = request.form.get('analytics_users', '')
    
    # Convert to list
    users_list = [u.strip() for u in analytics_users.split(',') if u.strip()]
    
    set_system_setting('analytics_users', users_list)
    flash('Analytics access users updated successfully!', 'success')
    
    return redirect(url_for('admin_panel'))

# ============================================================================
# SECTION 7: REPLACE YOUR EXISTING legal_action() ROUTE (around line 1800)
# ============================================================================

@app.route('/legal_action/<project_number>', methods=['GET', 'POST'])
@legal_required
def legal_action(project_number):
    """Legal team action on project - updated to require additional info after signing"""
    projects = load_json(DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'signed':
            # Change: Set to pending_additional_info instead of active
            project['status'] = 'pending_additional_info'
            project['legal_status'] = 'signed'
            project['legal_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            project['legal_approved_by'] = session['user_email']
            project['legal_signed'] = True
            project['legal_signed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Send notification to PM
            pm_email = f"{project['project_manager'].lower().replace(' ', '.')}@geoconinc.com"
            subject = f"Action Required: Complete Project Information for {project_number}"
            body = f"""
            The contract for project {project_number} has been signed by legal.
            
            Project: {project['project_name']}
            Client: {project['client']}
            
            ACTION REQUIRED: Please complete the additional project information in the system
            to finalize the project setup in Geocon's system.
            
            Login to the system and look for the project in "Projects Pending Additional Information" section.
            """
            send_email(pm_email, subject, body)
            
            flash(f'Project {project_number} signed! Pending additional information from PM.', 'success')
            
        elif action == 'not_signed':
            # Mark as dead job
            project['status'] = 'dead'
            project['legal_reviewed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            project['legal_reviewed_by'] = session['user_email']
            project['legal_signed'] = False
            project['not_signed_reason'] = request.form.get('not_signed_reason', '')
            
            flash(f'Project {project_number} marked as not signed and moved to Dead Jobs.', 'success')
        
        projects[project_number] = project
        save_json(DATABASES['projects'], projects)
        
        log_activity('legal_action', {
            'project_number': project_number,
            'action': action
        })
        
        return redirect(url_for('index'))
    
    return render_template('legal_action.html', project=project)

# Startup tasks
def run_startup_tasks():
    """Run tasks on server startup"""
    print("\n" + "="*60)
    print("GEOCON PROPOSAL MANAGEMENT SYSTEM v2.0")
    print("="*60)
    print("\n📁 Database Structure:")
    print("  - Proposals: data/proposals/")
    print("  - Projects: data/projects/")
    print("  - Users: data/users/")
    print("  - System: data/system/")
    print("  - Analytics: data/analytics/")
    print("  - Audit Logs: data/audit/")
    print("  - Documents: data/documents/")
    
    print("\n🔐 Login Credentials:")
    print("  - Regular Users: any@geoconinc.com / geocon123")
    print("  - Administrator: admin@geoconinc.com / admin123")
    
    legal_team = get_system_setting('legal_team_emails', [])
    print(f"\n⚖️ Legal Team: {', '.join(legal_team[:3])}")
    
    print("\n📧 Email Mode: Development (Terminal Output)")
    print("\n🌐 Server: http://localhost:5000")
    print("="*60 + "\n")
    
    # Clean up old sessions
    log_activity('server_startup', {
        'version': '2.0.0',
        'mode': 'development'
    }, 'system')

if __name__ == '__main__':
    run_startup_tasks()

    app.run(debug=True, port=5000)
