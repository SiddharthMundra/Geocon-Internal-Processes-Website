import json
import os
import shutil
from datetime import datetime
from flask import request, session
from config import Config

def load_json(filename):
    """Load JSON file with error handling"""
    try:
        # Handle both old format and new format
        if not filename.startswith('data/'):
            # Map old filenames to new structure
            old_to_new = {
                'proposals_db.json': Config.DATABASES['proposals'],
                'projects_db.json': Config.DATABASES['projects'],
                'users_db.json': Config.DATABASES['users'],
                'counters_db.json': Config.DATABASES['counters'],
                'analytics_db.json': Config.DATABASES['analytics'],
                'system_settings.json': Config.DATABASES['settings'],
                'deletion_logs.json': Config.DATABASES['deletion_log']
            }
            filename = old_to_new.get(filename, filename)
        
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Initialize if file doesn't exist
        if filename in Config.DATABASES.values():
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
                'proposals_db.json': Config.DATABASES['proposals'],
                'projects_db.json': Config.DATABASES['projects'],
                'users_db.json': Config.DATABASES['users'],
                'counters_db.json': Config.DATABASES['counters'],
                'analytics_db.json': Config.DATABASES['analytics'],
                'system_settings.json': Config.DATABASES['settings'],
                'deletion_logs.json': Config.DATABASES['deletion_log']
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

def init_databases():
    """Initialize all database files"""
    # Create necessary directories
    for folder in ['uploads', 'data', 'data/proposals', 'data/projects', 'data/users', 
                   'data/system', 'data/analytics', 'data/audit', 'data/documents', 'data/legal']:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    # Initialize database files
    for db_name, db_path in Config.DATABASES.items():
        if not os.path.exists(db_path):
            with open(db_path, 'w') as f:
                if db_name == 'counters':
                    json.dump({
                        'total_projects': 0,
                        'office_counters': {},
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
                    from utils.helpers import DEFAULT_SETTINGS
                    json.dump(DEFAULT_SETTINGS, f, indent=2)
                elif db_name in ['audit_log', 'deletion_log', 'email_log', 'activity_log']:
                    json.dump([], f)
                else:
                    json.dump({}, f)

def log_activity(action, details, user_email=None):
    """Log user activity for audit trail"""
    activity_log = load_json(Config.DATABASES['activity_log'])
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
    
    save_json(Config.DATABASES['activity_log'], activity_log)

def get_shared_documents(proposal_number, project_number=None):
    """Get all documents for both proposal and associated project"""
    proposals = load_json(Config.DATABASES['proposals'])
    projects = load_json(Config.DATABASES['projects'])
    
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