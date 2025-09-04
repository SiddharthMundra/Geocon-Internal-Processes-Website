from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
import json

from models.database import load_json, save_json, log_activity
from models.analytics import get_analytics
from utils.decorators import login_required, admin_required
from utils.helpers import get_system_setting, set_system_setting
from config import Config

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')  # Changed from '/'
@admin_required
def admin_panel():
    """Admin configuration panel"""
    log_activity('admin_panel_view', {})
    settings = load_json(Config.DATABASES['settings'])
    return render_template('admin_panel.html', settings=settings)

@admin_bp.route('/admin/update_setting', methods=['POST'])  # Changed from '/update_setting'
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
            return redirect(url_for('admin.admin_panel'))
    
    set_system_setting(setting_key, setting_value)
    flash(f'Setting {setting_key} updated successfully!', 'success')
    
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/update_project_directors', methods=['POST'])
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
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/admin/analytics')  # Changed from '/analytics'
@admin_required
def update_analytics_users():
    """Update list of users who can view analytics"""
    analytics_users = request.form.get('analytics_users', '')
    
    # Convert to list
    users_list = [u.strip() for u in analytics_users.split(',') if u.strip()]
    
    set_system_setting('analytics_users', users_list)
    flash('Analytics access users updated successfully!', 'success')
    
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/analytics')
@admin_required
def analytics():
    """View analytics dashboard - accessible only to admins"""
    
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
                         total_revenue=analytics_data.get('total_revenue', 0))