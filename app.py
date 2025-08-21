from flask import Flask
from config import Config
from models.database import init_databases
from utils.helpers import run_startup_tasks, inject_settings
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize databases
    init_databases()
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.proposals import proposals_bp
    from routes.projects import projects_bp
    from routes.legal import legal_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(proposals_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(legal_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    
    # Main dashboard route
    from routes.proposals import index
    app.add_url_rule('/', 'index', index)
    
    # Template context processors
    app.context_processor(inject_settings)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import request, jsonify, render_template
        if request.path.startswith('/api/'):
            return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import request, jsonify, render_template
        if request.path.startswith('/api/'):
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
        return render_template('500.html'), 500
    
    return app

app = create_app()

if __name__ == '__main__':
    run_startup_tasks()
    app.run(debug=True, port=5000)