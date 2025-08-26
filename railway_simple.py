#!/usr/bin/env python3
"""
Ultra-simplified Railway application
This version removes all potential issues and focuses on core functionality
"""
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Models
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    company = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('message_template.id'))
    status = db.Column(db.String(20), default='draft')
    total_contacts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='success')

class WhatsAppConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(100), default='default')
    status = db.Column(db.String(20), default='disconnected')
    last_check = db.Column(db.DateTime, default=datetime.utcnow)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "change-this-secret-key")

# Railway configuration
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///app.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Routes
@app.route('/')
def index():
    """Main dashboard"""
    try:
        # Get or create connection record
        connection = WhatsAppConnection.query.first()
        if not connection:
            connection = WhatsAppConnection()
            db.session.add(connection)
            db.session.commit()
        
        # Get statistics
        stats = {
            'contacts': Contact.query.count(),
            'templates': MessageTemplate.query.count(),
            'campaigns': Campaign.query.count()
        }
        
        # Get recent logs
        recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
        
        return render_template('index.html', 
                             connection=connection, 
                             stats=stats, 
                             recent_logs=recent_logs)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return f"App is starting up... Error: {str(e)}", 503

@app.route('/contacts')
def contacts():
    """Contact management page"""
    try:
        page = request.args.get('page', 1, type=int)
        contacts = Contact.query.paginate(page=page, per_page=20, error_out=False)
        return render_template('contacts.html', contacts=contacts)
    except Exception as e:
        logger.error(f"Error in contacts route: {e}")
        return f"Error loading contacts: {str(e)}", 500

@app.route('/contacts/add', methods=['POST'])
def add_contact():
    """Add new contact"""
    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        company = request.form.get('company', '').strip()
        
        if not name or not phone:
            flash('Nome e telefone são obrigatórios', 'error')
            return redirect(url_for('contacts'))
        
        contact = Contact(name=name, phone=phone, email=email, company=company)
        db.session.add(contact)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(action='contact_added', details=f'Contato {name} adicionado')
        db.session.add(log)
        db.session.commit()
        
        flash('Contato adicionado com sucesso!', 'success')
        return redirect(url_for('contacts'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding contact: {e}")
        flash('Erro ao adicionar contato', 'error')
        return redirect(url_for('contacts'))

@app.route('/templates')
def templates():
    """Message templates page"""
    try:
        templates = MessageTemplate.query.order_by(MessageTemplate.created_at.desc()).all()
        return render_template('templates.html', templates=templates)
    except Exception as e:
        logger.error(f"Error in templates route: {e}")
        return f"Error loading templates: {str(e)}", 500

@app.route('/templates/add', methods=['POST'])
def add_template():
    """Add new template"""
    try:
        name = request.form.get('name', '').strip()
        content = request.form.get('content', '').strip()
        
        if not name or not content:
            flash('Nome e conteúdo são obrigatórios', 'error')
            return redirect(url_for('templates'))
        
        template = MessageTemplate(name=name, content=content)
        db.session.add(template)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(action='template_created', details=f'Template {name} criado')
        db.session.add(log)
        db.session.commit()
        
        flash('Template criado com sucesso!', 'success')
        return redirect(url_for('templates'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding template: {e}")
        flash('Erro ao criar template', 'error')
        return redirect(url_for('templates'))

@app.route('/campaigns')
def campaigns():
    """Campaigns page"""
    try:
        campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
        templates = MessageTemplate.query.all()
        contacts = Contact.query.all()
        return render_template('campaigns.html', 
                             campaigns=campaigns, 
                             templates=templates, 
                             contacts=contacts)
    except Exception as e:
        logger.error(f"Error in campaigns route: {e}")
        return f"Error loading campaigns: {str(e)}", 500

@app.route('/history')
def history():
    """Activity history page"""
    try:
        page = request.args.get('page', 1, type=int)
        logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).paginate(
            page=page, per_page=50, error_out=False)
        return render_template('history.html', logs=logs)
    except Exception as e:
        logger.error(f"Error in history route: {e}")
        return f"Error loading history: {str(e)}", 500

@app.route('/whatsapp')
def whatsapp_page():
    """WhatsApp connection page"""
    return render_template('whatsapp.html')

@app.route('/connection/check')
def check_connection():
    """Check WhatsApp connection status"""
    return jsonify({
        'status': 'disconnected',
        'message': 'WhatsApp Web disponível apenas em desenvolvimento'
    })

@app.route('/connection/connect')
def connect_whatsapp():
    """Connect to WhatsApp"""
    return jsonify({
        'success': False,
        'message': 'WhatsApp Web não disponível no Railway'
    })

@app.route('/contacts/import', methods=['POST'])
def import_contacts():
    """Import contacts (Railway version - simplified)"""
    flash('Importação de contatos disponível no Replit', 'info')
    return redirect(url_for('contacts'))

@app.route('/campaigns/create', methods=['POST'])
def create_campaign():
    """Create campaign (Railway version - simplified)"""
    flash('Criação de campanhas disponível no Replit', 'info')
    return redirect(url_for('campaigns'))

# Health check route for Railway
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

# Custom filter for templates
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    if not value:
        return []
    try:
        return json.loads(value) if isinstance(value, str) else value
    except:
        return []

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html'), 500

# Initialize database
def create_tables():
    """Create database tables"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")

# Initialize app
create_tables()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)