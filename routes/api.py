from flask import Blueprint, request, jsonify, send_file, session, flash
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from models.database import load_json, save_json, log_activity
from models.analytics import get_analytics
from utils.decorators import login_required
from utils.helpers import allowed_file
from config import Config

api_bp = Blueprint('api', __name__)

@api_bp.route('/proposals', methods=['GET'])
@login_required
def api_get_proposals():
    """API endpoint to get proposals (for future Azure integration)"""
    proposals = load_json(Config.DATABASES['proposals'])
    
    # Filter based on query parameters
    status = request.args.get('status')
    office = request.args.get('office')
    pm = request.args.get('project_manager')
    
    filtered = {}
    for prop_num, proposal in proposals.items():
        if status and proposal.get('status') != status:
            continue
        if office and proposal.get('office') != office:
            continue
        if pm and proposal.get('project_manager') != pm:
            continue
        filtered[prop_num] = proposal
    
    return jsonify({
        'status': 'success',
        'count': len(filtered),
        'data': filtered
    })

@api_bp.route('/projects', methods=['GET'])
@login_required
def api_get_projects():
    """API endpoint to get projects (for future Azure integration)"""
    projects = load_json(Config.DATABASES['projects'])
    
    # Filter based on query parameters
    status = request.args.get('status')
    pm = request.args.get('project_manager')
    
    filtered = {}
    for proj_num, project in projects.items():
        if status and project.get('status') != status:
            continue
        if pm and project.get('project_manager') != pm:
            continue
        filtered[proj_num] = project
    
    return jsonify({
        'status': 'success',
        'count': len(filtered),
        'data': filtered
    })

@api_bp.route('/analytics', methods=['GET'])
@login_required
def api_get_analytics():
    """API endpoint to get analytics (for future Azure integration)"""
    analytics = get_analytics()
    return jsonify({
        'status': 'success',
        'data': analytics
    })

@api_bp.route('/upload_document/<entity_type>/<entity_number>', methods=['POST'])
@login_required
def upload_document(entity_type, entity_number):
    """Upload document to proposal or project"""
    if 'document' not in request.files:
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        flash('No file selected.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    file = request.files['document']
    if not file or not file.filename:
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        flash('No file selected.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"{entity_number}_{timestamp}_{file.filename}")
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Update database
        if entity_type == 'proposal':
            db = load_json(Config.DATABASES['proposals'])
        else:
            db = load_json(Config.DATABASES['projects'])
        
        if entity_number in db:
            if 'documents' not in db[entity_number]:
                db[entity_number]['documents'] = []
            
            doc_info = {
                'filename': filename,
                'original_name': file.filename,
                'uploaded_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'uploaded_by': session['user_email'],
                'type': request.form.get('doc_type', 'other')
            }
            
            db[entity_number]['documents'].append(doc_info)
            
            save_json(Config.DATABASES['proposals'] if entity_type == 'proposal' else Config.DATABASES['projects'], db)
            
            log_activity('document_uploaded', {
                'entity_type': entity_type,
                'entity_number': entity_number,
                'filename': file.filename
            })
            
            if request.is_json:
                return jsonify({'status': 'success', 'message': 'Document uploaded successfully', 'document': doc_info})
            flash('Document uploaded successfully!', 'success')
        else:
            if request.is_json:
                return jsonify({'status': 'error', 'message': 'Entity not found'}), 404
            flash('Entity not found.', 'error')
    else:
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400
        flash('Invalid file type.', 'error')
    
    if request.is_json:
        return jsonify({'status': 'success'})
    return redirect(request.referrer or url_for('index'))

@api_bp.route('/download_document/<filename>')
@login_required
def download_document(filename):
    """Download a document"""
    try:
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            # Extract original name from filename
            parts = filename.split('_', 2)
            download_name = parts[2] if len(parts) > 2 else filename
            
            log_activity('document_downloaded', {'filename': filename})
            
            return send_file(filepath, as_attachment=True, download_name=download_name)
        else:
            if request.is_json:
                return jsonify({'status': 'error', 'message': 'File not found'}), 404
            flash('File not found.', 'error')
            return redirect(request.referrer or url_for('index'))
    except Exception as e:
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'Error downloading file'}), 500
        flash('Error downloading file.', 'error')
        return redirect(request.referrer or url_for('index'))

@api_bp.route('/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '2.0.0'
    })