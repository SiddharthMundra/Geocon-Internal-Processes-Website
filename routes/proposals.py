from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

from models.database import load_json, save_json, log_activity
from models.analytics import get_enhanced_analytics, update_analytics
from utils.decorators import login_required
from utils.helpers import (get_system_setting, get_next_proposal_number,
                          check_follow_up_reminders)
from utils.email_service import send_email
from config import Config

proposals_bp = Blueprint('proposals', __name__)

@login_required
def index():
    """Main dashboard with auto-filtering by logged-in user's PM name"""
    log_activity('dashboard_view', {})
    
    proposals = load_json(Config.DATABASES['proposals'])
    projects = load_json(Config.DATABASES['projects'])
    
    # Get the PM name for filtering from session
    logged_in_pm = session.get('pm_filter_name', '')
    is_admin = session.get('is_admin', False)
    
    # Filter active items - Auto-filter by PM unless admin
    active_proposals = {}
    for k, v in proposals.items():
        if v.get('status') == 'pending':
            # Admin sees all, others see only their own
            if is_admin or v.get('project_manager') == logged_in_pm:
                active_proposals[k] = v
    
    # Filter projects by different statuses - Auto-filter by PM unless admin
    pending_legal_projects = {}
    pending_additional_info_projects = {}
    active_projects = {}
    
    for k, v in projects.items():
        # Projects pending legal review
        if v.get('status') == 'pending_legal':
            if is_admin or v.get('project_manager') == logged_in_pm:
                pending_legal_projects[k] = v
        
        # Projects pending additional information
        elif v.get('status') == 'pending_additional_info':
            # Calculate days pending
            if v.get('legal_approved_date'):
                try:
                    approved_date = datetime.strptime(v['legal_approved_date'].split(' ')[0], '%Y-%m-%d')
                    days_pending = (datetime.now() - approved_date).days
                    v['days_pending'] = days_pending
                except:
                    v['days_pending'] = 0
            else:
                v['days_pending'] = 0
            
            # Admin sees all, others see only their own
            if is_admin or v.get('project_manager') == logged_in_pm:
                pending_additional_info_projects[k] = v
        
        # Active projects
        elif v.get('status') == 'active' and not v.get('needs_legal_review'):
            if is_admin or v.get('project_manager') == logged_in_pm:
                active_projects[k] = v
    
    # Get search and filter parameters (but PM filter is auto-set)
    search_query = request.args.get('search', '').lower()
    status_filter = request.args.get('status', '')
    office_filter = request.args.get('office', '')
    # Force PM filter to logged-in user unless admin overrides
    pm_filter = request.args.get('pm_filter', '') if is_admin else logged_in_pm
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Apply additional filters to already-filtered proposals
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
        
        # PM filter (only applies if admin wants to override)
        if is_admin and pm_filter and (proposal.get('project_manager') != pm_filter and 
                                       proposal.get('project_director') != pm_filter):
            continue
        
        # Date range filter
        if date_from and proposal.get('date', '') < date_from:
            continue
        if date_to and proposal.get('date', '') > date_to:
            continue
        
        filtered_proposals[prop_num] = proposal
    
    # Initialize filtered project collections
    filtered_pending_legal = {}
    filtered_pending_additional_info = {}
    
    # Apply filters to pending legal projects
    for proj_num, project in pending_legal_projects.items():
        # Search filter
        if search_query:
            search_fields = [
                project.get('project_number', '').lower(),
                project.get('client', '').lower(),
                project.get('project_manager', '').lower(),
                project.get('project_name', '').lower()
            ]
            if not any(search_query in field for field in search_fields):
                continue
        
        # Status filter - only show if status filter matches or is empty
        if status_filter and status_filter != 'pending_legal':
            continue
        
        # Office filter
        if office_filter and project.get('office') != office_filter:
            continue
        
        # PM filter (only applies if admin wants to override)
        if is_admin and pm_filter and (project.get('project_manager') != pm_filter and 
                                       project.get('project_director') != pm_filter):
            continue
        
        # Date range filter
        if date_from and project.get('date', '') < date_from:
            continue
        if date_to and project.get('date', '') > date_to:
            continue
        
        filtered_pending_legal[proj_num] = project
    
    # Apply filters to pending additional info projects
    for proj_num, project in pending_additional_info_projects.items():
        # Search filter
        if search_query:
            search_fields = [
                project.get('project_number', '').lower(),
                project.get('client', '').lower(),
                project.get('project_manager', '').lower(),
                project.get('project_name', '').lower()
            ]
            if not any(search_query in field for field in search_fields):
                continue
        
        # Status filter - only show if status filter matches or is empty
        if status_filter and status_filter != 'pending_additional_info':
            continue
        
        # Office filter
        if office_filter and project.get('office') != office_filter:
            continue
        
        # PM filter (only applies if admin wants to override)
        if is_admin and pm_filter and (project.get('project_manager') != pm_filter and 
                                       project.get('project_director') != pm_filter):
            continue
        
        # Date range filter
        if date_from and project.get('date', '') < date_from:
            continue
        if date_to and project.get('date', '') > date_to:
            continue
        
        filtered_pending_additional_info[proj_num] = project
    
    # Get enhanced analytics - but only for this user's data unless admin
    analytics = get_enhanced_analytics()
    
    # Check if user can view full analytics - only admins can view analytics
    can_view_analytics = is_admin
    
    # Get project managers for filter dropdown (only show to admin)
    project_managers = get_system_setting('project_managers', [])
    
    # Check for follow-up reminders
    check_follow_up_reminders()
    
    return render_template('dashboard.html', 
                         proposals=filtered_proposals, 
                         pending_legal_projects=filtered_pending_legal,
                         pending_additional_info_projects=filtered_pending_additional_info,
                         user_email=session.get('user_email'),
                         user_name=session.get('user_name'),
                         logged_in_pm=logged_in_pm,
                         is_admin=is_admin,
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

# Remove permission restrictions from all other routes
@proposals_bp.route('/new_proposal')
@login_required  # Only login required, no other restrictions
def new_proposal():
    """New proposal form - accessible to all users"""
    counters = load_json(Config.DATABASES['counters'])
    
    # Get the next proposal number
    max_counter = 0
    if 'office_counters' in counters:
        for office, count in counters['office_counters'].items():
            if count > max_counter:
                max_counter = count
    
    next_number = max_counter + 1
    
    return render_template('new_proposal.html',
                         offices=get_system_setting('office_codes', {}),
                         proposal_types=get_system_setting('proposal_types', {}),
                         service_types=get_system_setting('service_types', {}),
                         project_scopes=get_system_setting('project_scopes', []),
                         project_types=get_system_setting('project_types', []),
                         project_managers=get_system_setting('project_managers', []),
                         project_directors=list(get_system_setting('team_assignments', {}).keys()),
                         team_assignments=get_system_setting('team_assignments', {}),
                         next_proposal_number=next_number)

@proposals_bp.route('/submit_proposal', methods=['POST'])
@login_required  # No other restrictions
def submit_proposal():
    """Submit new proposal - accessible to all users"""
    # Get form data
    office = request.form.get('office', '')
    proposal_type = request.form.get('proposal_type', '')
    service_type = request.form.get('service_type', '')
    
    # Get pre-generated proposal number from form
    proposal_number = request.form.get('proposal_number', '')
    
    # If no proposal number provided, generate one
    if not proposal_number:
        proposal_number = get_next_proposal_number(office, proposal_type, service_type)
    
    # Get fee and remove commas for storage
    fee_input = request.form.get('fee', '0')
    fee = fee_input.replace(',', '') if fee_input else '0'
    
    # Get project director and team number
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
        'project_city': request.form.get('project_city', ''),
        'project_latitude': request.form.get('project_latitude', ''),
        'project_longitude': request.form.get('project_longitude', ''),
        'project_folder_path': request.form.get('project_folder_path', ''),
        'client': request.form.get('client', ''),
        'contact_first': request.form.get('contact_first', ''),
        'contact_last': request.form.get('contact_last', ''),
        'contact_email': request.form.get('contact_email', ''),
        'contact_phone': request.form.get('contact_phone', ''),
        'project_manager': request.form.get('project_manager', ''),
        'project_director': project_director,
        'team_number': team_number,
        'bd_member': request.form.get('bd_member', ''),
        'marketing_proposal_manager': request.form.get('marketing_proposal_manager', ''),
        'project_scope': request.form.get('project_scope', ''),
        'project_type': request.form.get('project_type', ''),
        'fee': fee,  # Store without commas
        'due_date': request.form.get('due_date', ''),
        'follow_up_date': request.form.get('follow_up_date', ''),
        'notes': request.form.get('notes', ''),
        'status': 'pending',
        'created_by': session['user_email'],
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'email_history': []
    }
    
    # Save proposal
    proposals = load_json(Config.DATABASES['proposals'])
    proposals[proposal_number] = proposal_data
    save_json(Config.DATABASES['proposals'], proposals)
    
    # Update analytics
    update_analytics('new_proposal', proposal_data)
    
    log_activity('proposal_created', {
        'proposal_number': proposal_number,
        'client': proposal_data.get('client', 'Unknown')
    })
    
    flash(f'Proposal {proposal_number} created successfully!', 'success')
    return redirect(url_for('index'))

@proposals_bp.route('/edit_proposal/<proposal_number>')
@login_required  # No other restrictions
def edit_proposal(proposal_number):
    """Edit proposal form - accessible to all users"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    return render_template('edit_proposal.html',
                         proposal=proposal,
                         offices=get_system_setting('office_codes', {}),
                         proposal_types=get_system_setting('proposal_types', {}),
                         service_types=get_system_setting('service_types', {}),
                         project_scopes=get_system_setting('project_scopes', []),
                         project_types=get_system_setting('project_types', []),
                         project_managers=get_system_setting('project_managers', []),
                         project_directors=list(get_system_setting('team_assignments', {}).keys()))

@proposals_bp.route('/update_proposal/<proposal_number>', methods=['POST'])
@login_required  # No other restrictions
def update_proposal(proposal_number):
    """Update existing proposal - accessible to all users"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Get fee and remove commas for storage
    fee_input = request.form.get('fee', '0')
    fee = fee_input.replace(',', '') if fee_input else '0'
    
    # Update fields
    proposal.update({
        'project_name': request.form.get('project_name', ''),
        'project_latitude': request.form.get('project_latitude', ''),
        'project_longitude': request.form.get('project_longitude', ''),
        'project_folder_path': request.form.get('project_folder_path', ''),
        'client': request.form.get('client', ''),
        'contact_first': request.form.get('contact_first', ''),
        'contact_last': request.form.get('contact_last', ''),
        'contact_email': request.form.get('contact_email', ''),
        'contact_phone': request.form.get('contact_phone', ''),
        'project_manager': request.form.get('project_manager', ''),
        'project_director': request.form.get('project_director', ''),
        'team_number': request.form.get('team_number', ''),
        'bd_member': request.form.get('bd_member', ''),
        'marketing_proposal_manager': request.form.get('marketing_proposal_manager', ''),
        'project_scope': request.form.get('project_scope', ''),
        'project_type': request.form.get('project_type', ''),
        'fee': fee,  # Store without commas
        'due_date': request.form.get('due_date', ''),
        'follow_up_date': request.form.get('follow_up_date', ''),
        'notes': request.form.get('notes', ''),
        'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_modified_by': session['user_email']
    })
    
    proposals[proposal_number] = proposal
    save_json(Config.DATABASES['proposals'], proposals)
    
    log_activity('proposal_updated', {'proposal_number': proposal_number})
    
    flash(f'Proposal {proposal_number} updated successfully!', 'success')
    return redirect(url_for('proposals.view_proposal', proposal_number=proposal_number))

# Continue with all other routes - removing permission restrictions but keeping @login_required
@proposals_bp.route('/proposal/<proposal_number>')
@login_required
def view_proposal(proposal_number):
    """View proposal details - accessible to all users"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Get associated project if exists
    projects = load_json(Config.DATABASES['projects'])
    associated_project = None
    if proposal.get('project_number'):
        associated_project = projects.get(proposal['project_number'])
    
    log_activity('proposal_viewed', {'proposal_number': proposal_number})
    
    return render_template('view_proposal.html', 
                         proposal=proposal, 
                         project=associated_project)

@proposals_bp.route('/get_next_number')
@login_required
def get_next_proposal_number_ajax():
    """Get the next proposal number for display in form"""
    counters = load_json(Config.DATABASES['counters'])
    
    # Get the highest counter across all offices
    max_counter = 0
    if 'office_counters' in counters:
        for office, count in counters['office_counters'].items():
            if count > max_counter:
                max_counter = count
    
    return jsonify({'next_number': max_counter + 1})

@proposals_bp.route('/mark_sent/<proposal_number>')
@login_required  # No other restrictions
def mark_sent(proposal_number):
    """Mark proposal as sent to client - accessible to all users"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Keep status as 'pending' but add sent flag
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
    save_json(Config.DATABASES['proposals'], proposals)
    
    log_activity('proposal_sent', {'proposal_number': proposal_number})
    
    flash(f'Proposal {proposal_number} marked as sent to client.', 'success')
    return redirect(url_for('index'))

@proposals_bp.route('/mark_proposal_lost/<proposal_number>', methods=['GET', 'POST'])
@login_required  # No other restrictions
def mark_proposal_lost(proposal_number):
    """Mark proposal as lost - accessible to all users"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    if request.method == 'POST':
        loss_note = request.form.get('loss_note', '')
        
        # Update proposal status
        proposal['status'] = 'lost'
        proposal['loss_date'] = datetime.now().strftime('%Y-%m-%d')
        proposal['loss_note'] = loss_note
        proposal['marked_lost_by'] = session['user_email']
        
        proposals[proposal_number] = proposal
        save_json(Config.DATABASES['proposals'], proposals)
        
        log_activity('proposal_marked_lost', {
            'proposal_number': proposal_number,
            'reason': loss_note[:100] if loss_note else 'No reason provided'
        })
        
        flash(f'Proposal {proposal_number} marked as lost and moved to Past Projects.', 'success')
        return redirect(url_for('index'))
    
    return render_template('mark_lost.html', proposal=proposal)

@proposals_bp.route('/delete/<proposal_number>', methods=['GET', 'POST'])
@login_required  # No other restrictions
def delete_proposal_route(proposal_number):
    from routes.delete import delete_proposal
    return delete_proposal(proposal_number)