from functools import wraps
from flask import session, redirect, url_for, flash
from utils.helpers import get_system_setting

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('auth.login'))
        if not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def legal_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('auth.login'))
        legal_team = get_system_setting('legal_team_emails', [])
        if session.get('user_email') not in legal_team and not session.get('is_admin'):
            flash('Only legal team members can perform this action.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

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