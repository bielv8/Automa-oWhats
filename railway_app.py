#!/usr/bin/env python3
"""
Railway-specific application entry point
This file ensures proper Railway deployment without development-only code
"""
import os
import logging
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from models_railway import db, Contact, MessageTemplate, Campaign, CampaignContact, WhatsAppConnection, ActivityLog
import csv
import io
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-please-change")

# Railway/production configuration
port = int(os.environ.get("PORT", 5000))
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///whatsapp_automation.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Add custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

# Initialize the app with the extension
db.init_app(app)

# Simple WhatsApp service for Railway (no Selenium in production)
class SimpleWhatsAppService:
    def __init__(self):
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
    
    def check_connection(self):
        return {
            'status': 'disconnected',
            'message': 'Conexão WhatsApp disponível apenas em desenvolvimento'
        }
    
    def connect_to_whatsapp(self):
        return {
            'success': False,
            'message': 'WhatsApp Web não disponível no Railway. Use em desenvolvimento.'
        }

whatsapp_service = SimpleWhatsAppService()

# Routes
@app.route('/')
def index():
    # Get connection status
    connection = WhatsAppConnection.query.first()
    if not connection:
        connection = WhatsAppConnection(session_name="default")
        db.session.add(connection)
        db.session.commit()
    
    # Get recent activity
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    # Get statistics
    total_contacts = Contact.query.count()
    total_templates = MessageTemplate.query.count()
    active_campaigns = Campaign.query.filter(Campaign.status.in_(['running', 'scheduled'])).count()
    
    return render_template('index.html', 
                         connection=connection,
                         recent_logs=recent_logs,
                         stats={
                             'contacts': total_contacts,
                             'templates': total_templates,
                             'campaigns': active_campaigns
                         })

@app.route('/contacts')
def contacts():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Contact.query
    if search:
        query = query.filter(Contact.name.contains(search) | Contact.phone.contains(search))
    
    contacts = query.order_by(Contact.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('contacts.html', contacts=contacts, search=search)

@app.route('/contacts/add', methods=['GET', 'POST'])
def add_contact():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        company = request.form.get('company')
        
        # Validate phone number
        if not validate_phone(phone):
            flash('Número de telefone inválido', 'error')
            return redirect(url_for('contacts'))
        
        contact = Contact(
            name=name,
            phone=clean_phone(phone),
            email=email,
            company=company
        )
        
        try:
            db.session.add(contact)
            db.session.commit()
            
            # Log activity
            log_activity('contact_added', f'Contato {name} adicionado')
            
            flash('Contato adicionado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao adicionar contato', 'error')
            app.logger.error(f'Error adding contact: {e}')
    
    return redirect(url_for('contacts'))

@app.route('/templates')
def templates():
    templates = MessageTemplate.query.order_by(MessageTemplate.created_at.desc()).all()
    return render_template('templates.html', templates=templates)

@app.route('/campaigns')
def campaigns():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    templates = MessageTemplate.query.all()
    contacts = Contact.query.all()
    return render_template('campaigns.html', campaigns=campaigns, templates=templates, contacts=contacts)

@app.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False)
    
    return render_template('history.html', logs=logs)

@app.route('/whatsapp')
def whatsapp_page():
    return render_template('whatsapp.html')

@app.route('/connection/check')
def check_connection():
    return jsonify(whatsapp_service.check_connection())

@app.route('/connection/connect')
def connect_whatsapp():
    return jsonify(whatsapp_service.connect_to_whatsapp())

@app.route('/contacts/import', methods=['POST'])
def import_contacts():
    flash('Importação de contatos disponível apenas em desenvolvimento', 'warning')
    return redirect(url_for('contacts'))

@app.route('/templates/add', methods=['POST'])
def add_template():
    name = request.form.get('name')
    content = request.form.get('content')
    subject = request.form.get('subject')
    
    if name and content:
        template = MessageTemplate(
            name=name,
            subject=subject or '',
            content=content,
            variables=json.dumps(extract_variables(content))
        )
        
        try:
            db.session.add(template)
            db.session.commit()
            log_activity('template_created', f'Template {name} criado')
            flash('Template criado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar template', 'error')
            app.logger.error(f'Error creating template: {e}')
    
    return redirect(url_for('templates'))

@app.route('/campaigns/create', methods=['POST'])
def create_campaign():
    name = request.form.get('name')
    template_id = request.form.get('template_id')
    contact_ids = request.form.getlist('contact_ids')
    
    if not contact_ids:
        flash('Selecione pelo menos um contato', 'error')
        return redirect(url_for('campaigns'))
    
    campaign = Campaign(
        name=name,
        template_id=template_id,
        total_contacts=len(contact_ids)
    )
    
    try:
        db.session.add(campaign)
        db.session.commit()
        
        # Add contacts to campaign
        for contact_id in contact_ids:
            campaign_contact = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact_id
            )
            db.session.add(campaign_contact)
        
        db.session.commit()
        log_activity('campaign_created', f'Campanha {name} criada com {len(contact_ids)} contatos')
        flash('Campanha criada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Erro ao criar campanha', 'error')
        app.logger.error(f'Error creating campaign: {e}')
    
    return redirect(url_for('campaigns'))

def extract_variables(content):
    """Extract variables from template content"""
    if not content:
        return []
    import re
    variables = re.findall(r'\{\{(\w+)\}\}', content)
    return list(set(variables))

# Helper functions
def validate_phone(phone):
    if not phone:
        return False
    clean = re.sub(r'\D', '', phone)
    return len(clean) >= 10 and len(clean) <= 15

def clean_phone(phone):
    if not phone:
        return ''
    clean = re.sub(r'\D', '', phone)
    if len(clean) == 11 and clean.startswith('0'):
        clean = '55' + clean[1:]
    elif len(clean) == 10:
        clean = '55' + clean
    elif len(clean) == 11 and not clean.startswith('55'):
        clean = '55' + clean
    return clean

def log_activity(action, details, status='success'):
    log = ActivityLog(
        action=action,
        details=details,
        status=status
    )
    db.session.add(log)
    db.session.commit()

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=False)