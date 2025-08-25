from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import uuid

from models.database import load_json, save_json, log_activity
from utils.decorators import login_required
from utils.helpers import get_system_setting
from utils.email_service import send_email
from config import Config
import uuid

legal_bp = Blueprint('legal', __name__)




@legal_bp.route('/add_pw_dir_question', methods=['GET', 'POST'])
@login_required
def add_pw_dir_question():
    """Add a new PW & DIR question"""
    if request.method == 'POST':
        pw_dir_questions = load_json(Config.DATABASES['pw_dir_questions'])
        
        question_id = str(uuid.uuid4())
        question_data = {
            'id': question_id,
            'dept_status': 'incomplete',
            'date_requested': request.form.get('date_requested', datetime.now().strftime('%Y-%m-%d')),
            'completion_date': request.form.get('completion_date', ''),
            'requested_by': request.form.get('requested_by', ''),
            'office': request.form.get('office', ''),
            'project_number': request.form.get('project_number', ''),
            'project_name': request.form.get('project_name', ''),
            'question_topic': request.form.get('question_topic', ''),
            'reviewed_by': request.form.get('reviewed_by', ''),
            'notes': request.form.get('notes', ''),
            'added_by': session['user_email']
        }
        
        pw_dir_questions[question_id] = question_data
        save_json(Config.DATABASES['pw_dir_questions'], pw_dir_questions)
        
        log_activity('pw_dir_question_added', {'question_id': question_id})
        flash('PW & DIR question added successfully!', 'success')
        return redirect(url_for('legal.legal_queue', tab='pw-dir-questions'))
    
    return render_template('add_pw_dir_question.html',
                         offices=get_system_setting('office_codes', {}))

@legal_bp.route('/legal_queue')  # Changed from '/queue'
@login_required
def legal_queue():
    """View legal department tabs"""
    log_activity('legal_queue_view', {})
    
    projects = load_json(Config.DATABASES['projects'])
    proposals = load_json(Config.DATABASES['proposals'])
    executed_contracts = load_json(Config.DATABASES['executed_contracts'])
    insurance_requests = load_json(Config.DATABASES['insurance_requests'])
    sub_requests = load_json(Config.DATABASES['sub_requests'])
    pw_dir_questions = load_json(Config.DATABASES['pw_dir_questions'])
    
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
                         sub_requests=sub_requests,
                         pw_dir_questions=pw_dir_questions,
                         stats=stats,
                         offices=get_system_setting('office_codes', {}),
                         project_managers=project_managers,
                         tab=tab)

@legal_bp.route('/legal_queue_detail/<project_number>')  # Changed from '/queue_detail/<project_number>'
@login_required
def legal_queue_detail(project_number):
    """View detailed legal queue information for a project"""
    log_activity('legal_queue_detail_view', {'project_number': project_number})
    
    projects = load_json(Config.DATABASES['projects'])
    proposals = load_json(Config.DATABASES['proposals'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('legal.legal_queue'))
    
    project = projects[project_number]
    
    # Get associated proposal for fee
    if project.get('proposal_number') in proposals:
        proposal = proposals[project['proposal_number']]
        project['fee'] = proposal.get('fee', 0)
        project['office'] = proposal.get('office', '')
    
    return render_template('legal_queue_detail.html', project=project)

@legal_bp.route('/update_legal_status/<project_number>', methods=['GET', 'POST'])  # Changed from '/update_status/<project_number>'
@login_required
def update_legal_status(project_number):
    """Update the legal status of a project"""
    projects = load_json(Config.DATABASES['projects'])
    
    if project_number not in projects:
        flash('Project not found.', 'error')
        return redirect(url_for('legal.legal_queue'))
    
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
            project['status'] = 'pending_additional_info'  # Ensure this is set
            project['legal_status'] = 'signed'
            project['legal_approved_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            project['legal_approved_by'] = session['user_email']
            project['legal_signed'] = True
            project['legal_signed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Make sure the project is visible to the PM
            project['needs_additional_info'] = True  # Add this flag
            
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
        save_json(Config.DATABASES['projects'], projects)
        
        log_activity('legal_status_updated', {
            'project_number': project_number,
            'old_status': old_status,
            'new_status': new_status,
            'notes': status_notes[:100] if status_notes else ''
        })
        
        flash(f'Legal status updated to: {new_status.replace("_", " ").title()}', 'success')
        return redirect(url_for('legal.legal_queue'))
    
    return render_template('update_legal_status.html', project=project)

@legal_bp.route('/add_executed_contract', methods=['GET', 'POST'])
@login_required
def add_executed_contract():
    """Add a new executed contract record"""
    if request.method == 'POST':
        contracts = load_json(Config.DATABASES['executed_contracts'])
        
        contract_id = str(uuid.uuid4())
        contract_data = {
            'id': contract_id,
            'date_added': datetime.now().strftime('%Y-%m-%d'),
            'project_number': request.form.get('project_number', ''),
            'project_name': request.form.get('project_name', ''),
            'client': request.form.get('client', ''),
            'contract_type': request.form.get('contract_type', ''),
            'notes': request.form.get('notes', ''),
            'added_by': session['user_email']
        }
        
        contracts[contract_id] = contract_data
        save_json(Config.DATABASES['executed_contracts'], contracts)
        
        log_activity('executed_contract_added', {'contract_id': contract_id})
        flash('Executed contract record added successfully!', 'success')
        return redirect(url_for('legal.legal_queue', tab='executed-contracts'))
    
    return render_template('add_executed_contract.html')

@legal_bp.route('/add_insurance_request', methods=['GET', 'POST'])
@login_required
def add_insurance_request():
    """Add a new insurance request"""
    if request.method == 'POST':
        requests = load_json(Config.DATABASES['insurance_requests'])
        
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
            'notes': request.form.get('notes', ''),
            'added_by': session['user_email']
        }
        
        requests[request_id] = request_data
        save_json(Config.DATABASES['insurance_requests'], requests)
        
        log_activity('insurance_request_added', {'request_id': request_id})
        flash('Insurance request added successfully!', 'success')
        return redirect(url_for('legal.legal_queue', tab='insurance-requests'))
    
    return render_template('add_insurance_request.html',
                         offices=get_system_setting('office_codes', {}))

@legal_bp.route('/mark_insurance_issued/<request_id>')
@login_required
def mark_insurance_issued(request_id):
    """Mark an insurance request as issued"""
    requests = load_json(Config.DATABASES['insurance_requests'])
    
    if request_id in requests:
        requests[request_id]['status'] = 'issued'
        requests[request_id]['issued_date'] = datetime.now().strftime('%Y-%m-%d')
        requests[request_id]['issued_by'] = session['user_email']
        save_json(Config.DATABASES['insurance_requests'], requests)
        
        log_activity('insurance_request_issued', {'request_id': request_id})
        flash('Insurance request marked as issued!', 'success')
    
    return redirect(url_for('legal.legal_queue', tab='insurance-requests'))

@legal_bp.route('/legal_action/<project_number>', methods=['GET', 'POST'])  # Changed from '/action/<project_number>'
@login_required
def legal_action(project_number):
    """Legal team action on project - updated to require additional info after signing"""
    projects = load_json(Config.DATABASES['projects'])
    
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
            project['needs_additional_info'] = True  # Add this flag
            
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
        save_json(Config.DATABASES['projects'], projects)
        
        log_activity('legal_action', {
            'project_number': project_number,
            'action': action
        })
        
        return redirect(url_for('index'))
    
    return render_template('legal_action.html', project=project)

@legal_bp.route('/edit_sub_request/<request_id>', methods=['GET', 'POST'])
@login_required
def edit_sub_request(request_id):
    """Edit a sub request - legal department can update status and reviewed_by"""
    sub_requests = load_json(Config.DATABASES['sub_requests'])
    
    if request_id not in sub_requests:
        flash('Sub request not found.', 'error')
        return redirect(url_for('legal.legal_queue', tab='sub-requests'))
    
    sub_request = sub_requests[request_id]
    
    if request.method == 'POST':
        # Update the sub request
        sub_request.update({
            'dept_status': request.form.get('dept_status', sub_request.get('dept_status')),
            'reviewed_by': request.form.get('reviewed_by', sub_request.get('reviewed_by')),
            'notes': request.form.get('notes', sub_request.get('notes')),
            'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_modified_by': session['user_email']
        })
        
        sub_requests[request_id] = sub_request
        save_json(Config.DATABASES['sub_requests'], sub_requests)
        
        log_activity('sub_request_updated', {'request_id': request_id})
        flash('Sub request updated successfully!', 'success')
        return redirect(url_for('legal.legal_queue', tab='sub-requests'))
    
    return render_template('edit_sub_request.html', 
                         sub_request=sub_request,
                         offices=get_system_setting('office_codes', {}))

@legal_bp.route('/edit_pw_dir_question/<question_id>', methods=['GET', 'POST'])
@login_required
def edit_pw_dir_question(question_id):
    """Edit a PW & DIR question - legal department can update status and reviewed_by"""
    pw_dir_questions = load_json(Config.DATABASES['pw_dir_questions'])
    
    if question_id not in pw_dir_questions:
        flash('PW & DIR question not found.', 'error')
        return redirect(url_for('legal.legal_queue', tab='pw-dir-questions'))
    
    question = pw_dir_questions[question_id]
    
    if request.method == 'POST':
        # Update the question
        question.update({
            'dept_status': request.form.get('dept_status', question.get('dept_status')),
            'reviewed_by': request.form.get('reviewed_by', question.get('reviewed_by')),
            'notes': request.form.get('notes', question.get('notes')),
            'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_modified_by': session['user_email']
        })
        
        pw_dir_questions[question_id] = question
        save_json(Config.DATABASES['pw_dir_questions'], pw_dir_questions)
        
        log_activity('pw_dir_question_updated', {'question_id': question_id})
        flash('PW & DIR question updated successfully!', 'success')
        return redirect(url_for('legal.legal_queue', tab='pw-dir-questions'))
    
    return render_template('edit_pw_dir_question.html', 
                         question=question,
                         offices=get_system_setting('office_codes', {}))
