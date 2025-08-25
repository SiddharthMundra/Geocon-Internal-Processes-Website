from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import uuid
from models.database import load_json, save_json, log_activity
from models.analytics import update_analytics
from utils.decorators import login_required
from utils.helpers import get_system_setting, get_next_project_number
from utils.email_service import send_email
from config import Config, PROJECT_REVENUE_CODES, PROJECT_SCOPES_DETAILED, PROJECT_TYPES_DETAILED, PROJECT_TEAMS, US_STATES, CA_COUNTIES

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/mark_won/<proposal_number>', methods=['POST'])
@login_required
def mark_won(proposal_number):
    """Mark proposal as won and create project with auto-population for insurance and contracts"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    
    # Get form data
    needs_legal_review = request.form.get('needs_legal_review') == 'yes'
    project_folder_path = request.form.get('project_folder_path', '')
    
    # Get project number from form (either auto-generated or custom)
    project_number = request.form.get('project_number', '')
    
    # If no project number provided, generate one
    if not project_number:
        team_number = proposal.get('team_number', '00')
        project_number = get_next_project_number(team_number)
    
    # Update proposal
    proposal['status'] = 'converted_to_project'
    proposal['win_loss'] = 'W'
    proposal['project_number'] = project_number
    proposal['won_date'] = datetime.now().strftime('%Y-%m-%d')
    proposal['won_by'] = session['user_email']
    proposal['project_folder_path'] = project_folder_path
    
    # IMPORTANT: Set correct status based on legal review need
    if needs_legal_review:
        project_status = 'pending_legal'
    else:
        # If no legal review needed, go directly to pending_additional_info
        project_status = 'pending_additional_info'
    
    # Get COI information if needed
    coi_needed = request.form.get('coi_needed') == 'yes'
    
    project_data = {
        'project_number': project_number,
        'proposal_number': proposal_number,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'project_name': proposal.get('project_name', 'Unknown'),
        'client': proposal.get('client', 'Unknown'),
        'contact': f"{proposal.get('contact_first', '')} {proposal.get('contact_last', '')}",
        'project_manager': proposal.get('project_manager', 'Unknown'),
        'team_number': proposal.get('team_number', '00'),
        'status': project_status,
        'needs_legal_review': needs_legal_review,
        'project_folder_path': project_folder_path,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'email_history': [],
        'office': proposal.get('office', ''),
        'fee': proposal.get('fee', 0),
        
        # Legal Queue Fields (if needed)
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
        'coi_needed': coi_needed,

        'notes_comments': request.form.get('notes_comments', ''),
        'legal_status_history': []
    }
    
    # Handle COI needed - auto-populate insurance request
    if coi_needed:
        insurance_requests = load_json(Config.DATABASES['insurance_requests'])
        
        request_id = str(uuid.uuid4())
        insurance_data = {
            'id': request_id,
            'dept_status': 'new_request',  # Default department status
            'date_requested': datetime.now().strftime('%Y-%m-%d'),
            'completion_date': request.form.get('completion_date', ''),
            'requested_by': proposal.get('project_manager', ''),
            'office': proposal.get('office', ''),
            'project_number': project_number,
            'project_name': proposal.get('project_name', ''),
            'certificate_holder': request.form.get('certificate_holder', ''),
            'client_contact_name': request.form.get('client_contact_name', ''),
            'client_contact_email': request.form.get('client_contact_email', ''),
            'can_legal_contact': request.form.get('legal_can_contact', 'yes'),
            'handled_by': '',  # To be filled by legal team
    
            'notes': request.form.get('insurance_notes', ''),
            'added_by': session['user_email'],
            'auto_generated': True
        }
        
        insurance_requests[request_id] = insurance_data
        save_json(Config.DATABASES['insurance_requests'], insurance_requests)
        
        log_activity('insurance_request_auto_created', {
            'request_id': request_id,
            'project_number': project_number
        })
    
    # Handle projects that don't need legal review - auto-populate executed contracts
    if not needs_legal_review:
        project_data['legal_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        project_data['legal_approved_by'] = 'Auto-approved (No legal review required)'
        
        # Auto-populate executed contracts
        executed_contracts = load_json(Config.DATABASES['executed_contracts'])
        
        contract_id = str(uuid.uuid4())
        contract_data = {
            'id': contract_id,
            'dept_status': 'unfiled',  # Default department status
            'date_added': datetime.now().strftime('%Y-%m-%d'),
            'project_number': project_number,
            'project_name': proposal.get('project_name', ''),
            'client': proposal.get('client', ''),
            'contract_type': request.form.get('contract_type_executed', ''),
    
            'notes': request.form.get('executed_notes', ''),
            'added_by': session['user_email'],
            'auto_generated': True
        }
        
        executed_contracts[contract_id] = contract_data
        save_json(Config.DATABASES['executed_contracts'], executed_contracts)
        
        log_activity('executed_contract_auto_created', {
            'contract_id': contract_id,
            'project_number': project_number
        })
        
        # Send notification to PM
        pm_email = f"{proposal['project_manager'].lower().replace(' ', '.')}@geoconinc.com"
        subject = f"Action Required: Complete Project Information for {project_number}"
        body = f"""
        Project {project_number} has been created and requires additional information.
        
        Project: {proposal.get('project_name', 'Unknown')}
        Client: {proposal.get('client', 'Unknown')}
        
        ACTION REQUIRED: Please complete the additional project information in the system.
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
        
        {'COI Required: Yes' if coi_needed else ''}
        """
        send_email(legal_email, subject, body)
        flash(f'Proposal marked as won! Project {project_number} created and sent for legal review.', 'success')
    
    # Save updates
    proposals[proposal_number] = proposal
    save_json(Config.DATABASES['proposals'], proposals)
    
    projects = load_json(Config.DATABASES['projects'])
    projects[project_number] = project_data
    save_json(Config.DATABASES['projects'], projects)
    
    # Update analytics
    update_analytics('proposal_won', proposal)
    
    log_activity('proposal_won', {
        'proposal_number': proposal_number,
        'project_number': project_number,
        'needs_legal': needs_legal_review,
        'coi_needed': coi_needed
    })
    
    return redirect(url_for('index'))

@projects_bp.route('/mark_won_form/<proposal_number>')
@login_required
def mark_won_form(proposal_number):
    """Show form for marking proposal as won"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    if proposal_number not in proposals:
        flash('Proposal not found.', 'error')
        return redirect(url_for('index'))
    
    proposal = proposals[proposal_number]
    

    
    return render_template('mark_won_form.html', proposal=proposal)

@projects_bp.route('/project/<project_number>')
@login_required
def view_project(project_number):
    """View project details"""
    projects = load_json(Config.DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    
    # Get associated proposal
    proposals = load_json(Config.DATABASES['proposals'])
    associated_proposal = proposals.get(project.get('proposal_number'))
    
    log_activity('project_viewed', {'project_number': project_number})
    
    return render_template('view_project.html', 
                         project=project, 
                         proposal=associated_proposal)

@projects_bp.route('/project_info_form/<project_number>')
@login_required
def project_info_form(project_number):
    """Display form to enter additional project information"""
    projects = load_json(Config.DATABASES['projects'])
    
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
    proposals = load_json(Config.DATABASES['proposals'])
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

@projects_bp.route('/submit_project_info/<project_number>', methods=['POST'])
@login_required
def submit_project_info(project_number):
    """Submit additional project information and complete project setup"""
    projects = load_json(Config.DATABASES['projects'])
    
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
        projects[project_number] = project
        save_json(Config.DATABASES['projects'], projects)
        return redirect(url_for('projects.project_info_form', project_number=project_number))
    
    # Save project
    projects[project_number] = project
    save_json(Config.DATABASES['projects'], projects)
    
    return redirect(url_for('index'))

@projects_bp.route('/mark_project_complete/<project_number>')
@login_required
def mark_project_complete(project_number):
    """Mark project as complete - anyone can do this"""
    projects = load_json(Config.DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('index'))
    
    project = projects[project_number]
    
    # Update status
    project['status'] = 'completed'
    project['completion_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    project['completed_by'] = session['user_email']
    
    projects[project_number] = project
    save_json(Config.DATABASES['projects'], projects)
    
    # Update analytics
    update_analytics('project_completed', project)
    
    log_activity('project_completed', {'project_number': project_number})
    
    flash(f'Project {project_number} marked as complete and moved to Past Projects.', 'success')
    return redirect(url_for('index'))

@projects_bp.route('/past_projects')
@login_required
def past_projects():
    """View completed projects, lost proposals, and dead jobs"""
    log_activity('past_projects_view', {})
    
    projects = load_json(Config.DATABASES['projects'])
    proposals = load_json(Config.DATABASES['proposals'])
    
    # Filter categories
    completed_projects = {k: v for k, v in projects.items() if v.get('status') == 'completed'}
    lost_proposals = {k: v for k, v in proposals.items() if v.get('status') == 'lost'}
    dead_jobs = {k: v for k, v in projects.items() if v.get('status') == 'dead'}
    
    return render_template('past_projects.html', 
                         projects=completed_projects,
                         lost_proposals=lost_proposals,
                         dead_jobs=dead_jobs,
                         user_email=session.get('user_email'))

@projects_bp.route('/get_next_project_number')
@login_required
def get_next_project_number_ajax():
    """Get the next project number for display in form"""
    team_number = request.args.get('team', '00')
    next_number = get_next_project_number(team_number)
    return jsonify({'next_number': next_number})

@projects_bp.route('/delete/<project_number>', methods=['GET', 'POST'])
@login_required
def delete_project_route(project_number):
    from routes.delete import delete_proposal
    return delete_proposal(project_number)