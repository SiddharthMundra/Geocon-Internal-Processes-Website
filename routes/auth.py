from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import log_activity
from utils.helpers import is_authorized_email, get_system_setting
from utils.decorators import login_required

auth_bp = Blueprint('auth', __name__)

def extract_name_from_email(email):
    """Extract proper name from lastname@geoconinc.com format"""
    if not email or '@' not in email:
        return email
    
    username = email.split('@')[0]
    
    # Handle different formats: lastname, first.lastname, etc.
    if '.' in username:
        # Format: first.lastname -> First Lastname
        parts = username.split('.')
        return ' '.join(part.capitalize() for part in parts)
    else:
        # Format: lastname -> Lastname
        return username.capitalize()

def find_pm_name_in_system(extracted_name):
    """Find the actual PM name in system that matches the extracted name"""
    project_managers = get_system_setting('project_managers', [])
    
    # Try exact match first
    for pm in project_managers:
        if pm.lower() == extracted_name.lower():
            return pm
    
    # Try lastname match (since email format is lastname@geoconinc.com)
    extracted_lastname = extracted_name.split()[-1].lower()  # Get last word as lastname
    for pm in project_managers:
        pm_lastname = pm.split()[-1].lower()  # Get PM's lastname
        if pm_lastname == extracted_lastname:
            return pm
    
    # If no match found, return the extracted name
    return extracted_name

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Simplified login - all @geoconinc.com emails use password: geocon123"""
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password')
        
        # Admin bypass
        if email == 'admin@geoconinc.com' and password == 'admin123':
            session['user_email'] = 'admin@geoconinc.com'
            session['user_name'] = 'System Administrator'
            session['pm_filter_name'] = 'System Administrator'
            session['is_admin'] = True
            session['is_legal'] = True
            
            log_activity('admin_login', {}, 'admin@geoconinc.com')
            flash('Logged in as Administrator', 'success')
            return redirect(url_for('admin.admin_panel'))
        
        # Check if email is from geoconinc.com
        if not is_authorized_email(email):
            flash('Only @geoconinc.com email addresses are allowed.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check password
        if password != 'geocon123':
            flash('Invalid password.', 'error')
            return redirect(url_for('auth.login'))
        
        # Extract name from email and find matching PM
        extracted_name = extract_name_from_email(email)
        pm_name = find_pm_name_in_system(extracted_name)
        
        # Check if user is in legal team
        legal_team = get_system_setting('legal_team_emails', [])
        
        session['user_email'] = email
        session['user_name'] = extracted_name  # For display purposes
        session['pm_filter_name'] = pm_name    # For filtering purposes
        session['is_admin'] = False
        session['is_legal'] = email in legal_team
        
        log_activity('user_login', {'pm_filter_name': pm_name}, email)
        # flash(f'Welcome {extracted_name}! Dashboard filtered for: {pm_name}', 'success')
        return redirect(url_for('index'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    log_activity('user_logout', {})
    session.clear()
    return redirect(url_for('auth.login'))