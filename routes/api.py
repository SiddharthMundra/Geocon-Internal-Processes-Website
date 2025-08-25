from flask import Blueprint, request, jsonify, session
from datetime import datetime

from models.database import load_json, save_json, log_activity
from models.analytics import get_analytics
from utils.decorators import login_required
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



@api_bp.route('/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '2.0.0'
    })