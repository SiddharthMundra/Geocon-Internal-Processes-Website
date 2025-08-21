from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

from models.database import load_json, save_json, log_activity, get_shared_documents
from models.analytics import get_enhanced_analytics, update_analytics
from utils.decorators import login_required, user_can_edit
from utils.helpers import (get_system_setting, get_next_proposal_number, allowed_file,
                          check_follow_up_reminders)
from utils.email_service import send_email
from config import Config

proposals_bp = Blueprint('proposals', __name__, url_prefix='/proposals')

@login_required
def index():
    """Main dashboard with enhanced filters and analytics - FIXED VERSION"""
    log_activity('dashboard_view', {})
    
    proposals = load_json(Config.DATABASES['proposals'])
    projects = load_json(Config.DATABASES['projects'])
    
    # Filter active items
    active_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'pending'}
    
    # Filter projects by different statuses
    pending_legal_projects = {}
    pending_additional_info_projects = {}
    active_projects = {}
    
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
            else:
                # For projects that went straight to pending_additional_info without legal
                v['days_pending'] = 0
            
            # Admin sees all, others see only their own
            if session.get('is_admin') or v.get('project_manager') == session.get('user_name'):
                pending_additional_info_projects[k] = v
        
        # Active projects (marked as won but no legal review needed) - FIXED
        elif v.get('status') == 'active' and not v.get('needs_legal_review'):
            # Show active projects that went straight to active
            if session.get('is_admin') or v.get('project_manager') == session.get('user_name'):
                active_projects[k] = v
    
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

@proposals_bp.route('/new')
@login_required
def new_proposal():
    """New proposal form with proposal number preview"""
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

@proposals_bp.route('/submit', methods=['POST'])
@login_required
def submit_proposal():
    """Submit new proposal - no permissions, anyone can create"""
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
        'documents': [],
        'email_history': []
    }
    
    # Handle file upload
    if 'proposal_file' in request.files:
        file = request.files['proposal_file']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{proposal_number}_{file.filename}")
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            proposal_data['documents'].append({
                'filename': filename,
                'original_name': file.filename,
                'uploaded_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'uploaded_by': session['user_email'],
                'type': 'proposal'
            })
    
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

@proposals_bp.route('/edit/<proposal_number>')
@login_required
def edit_proposal(proposal_number):
    """Edit proposal form - anyone can edit"""
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

@proposals_bp.route('/update/<proposal_number>', methods=['POST'])
@login_required
def update_proposal(proposal_number):
    """Update existing proposal - anyone can update"""
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

@proposals_bp.route('/view/<proposal_number>')
@login_required
def view_proposal(proposal_number):
    """View proposal details"""
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
    
    # Get all shared documents
    all_documents = get_shared_documents(proposal_number, proposal.get('project_number'))
    
    log_activity('proposal_viewed', {'proposal_number': proposal_number})
    
    return render_template('view_proposal.html', 
                         proposal=proposal, 
                         project=associated_project,
                         all_documents=all_documents)

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
@login_required
def mark_sent(proposal_number):
    """Mark proposal as sent to client - anyone can do this"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Keep status as 'pending' but add sent flag
    # Don't change the main status to 'sent' as that might break other logic
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

@proposals_bp.route('/mark_lost/<proposal_number>', methods=['GET', 'POST'])
@login_required
def mark_proposal_lost(proposal_number):
    """Mark proposal as lost - anyone can do this"""
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
@login_required
def delete_proposal_route(proposal_number):
    from routes.delete import delete_proposal
    return delete_proposal(proposal_number)