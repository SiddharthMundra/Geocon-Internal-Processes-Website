from datetime import datetime
from models.database import load_json, save_json, log_activity
from config import Config

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
    'project_scopes': [
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
    'project_types': [
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
    'legal_dept_email': 'legal@geoconinc.com',
    'analytics_users': [
        'admin@geoconinc.com',
        'shawn.weedon@geoconinc.com',
        'rebecca.silva@geoconinc.com'
    ]
}

def is_authorized_email(email):
    """Check if email is from geoconinc.com domain"""
    return email.endswith('@geoconinc.com')

def get_system_setting(key, default=None):
    """Get system setting with fallback"""
    settings = load_json(Config.DATABASES['settings'])
    return settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key, None))

def set_system_setting(key, value):
    """Set system setting with audit log"""
    settings = load_json(Config.DATABASES['settings'])
    old_value = settings.get(key)
    settings[key] = value
    save_json(Config.DATABASES['settings'], settings)
    
    log_activity('setting_changed', {
        'setting': key,
        'old_value': str(old_value)[:100] if old_value else None,
        'new_value': str(value)[:100] if value else None
    })



def get_next_proposal_number(office, proposal_type, service_type):
    """Generate proposal number with proper counter management"""
    counters = load_json(Config.DATABASES['counters'])
    
    year = datetime.now().year
    
    # Initialize office counter if not exists
    if 'office_counters' not in counters:
        counters['office_counters'] = {}
    
    counter = counters['office_counters'].get(office, 0) + 1
    counters['office_counters'][office] = counter
    
    save_json(Config.DATABASES['counters'], counters)
    
    # Format: OC-2024-0001-P-GT
    proposal_number = f"{office}-{year}-{counter:04d}-{proposal_type}-{service_type}"
    
    log_activity('proposal_number_generated', {'number': proposal_number})
    return proposal_number

def get_next_project_number(team_number):
    """Generate project number with proper counter management"""
    counters = load_json(Config.DATABASES['counters'])
    
    total = counters.get('total_projects', 0) + 1
    counters['total_projects'] = total
    
    save_json(Config.DATABASES['counters'], counters)
    
    # Format: G-000001-02-01
    project_number = f"G-{total:06d}-{team_number}-01"
    
    log_activity('project_number_generated', {'number': project_number})
    return project_number

def check_follow_up_reminders():
    """Check for proposals that need follow-up reminders"""
    from utils.email_service import send_email
    
    proposals = load_json(Config.DATABASES['proposals'])
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
    
    save_json(Config.DATABASES['proposals'], proposals)

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


def get_next_project_number(team_number='00'):
    """Generate next project number in format G-XXXXXX-TT-01"""
    counters = load_json(Config.DATABASES['counters'])
    
    # Get the current total projects count
    total_projects = counters.get('total_projects', 0) + 1
    
    # Update the counter
    counters['total_projects'] = total_projects
    save_json(Config.DATABASES['counters'], counters)
    
    # Format: G-XXXXXX-TT-01
    # G = Geocon prefix
    # XXXXXX = 6-digit sequential number
    # TT = Team number (e.g., 01, 02, etc.)
    # 01 = Sub-project number (always 01 for new projects)
    project_number = f"G-{total_projects:06d}-{team_number}-01"
    
    return project_number

def inject_settings():
    """Inject common settings into all templates"""
    return {
        'current_year': datetime.now().year,
        'system_version': '2.0.0',
        'company_name': 'Geocon Inc.'
    }