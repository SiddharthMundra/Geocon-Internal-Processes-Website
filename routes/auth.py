from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.database import log_activity
from utils.helpers import is_authorized_email, get_system_setting
from utils.decorators import login_required

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

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

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    log_activity('user_logout', {})
    session.clear()
    return redirect(url_for('auth.login'))