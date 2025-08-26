from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import Contact, MessageTemplate, Campaign, CampaignContact, WhatsAppConnection, ActivityLog
from whatsapp_service import WhatsAppService
from whatsapp_selenium import WhatsAppSeleniumService
import csv
import json
import io
from datetime import datetime
import re

whatsapp_service = WhatsAppService()
whatsapp_selenium = WhatsAppSeleniumService()

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

@app.route('/contacts/import', methods=['POST'])
def import_contacts():
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado', 'error')
        return redirect(url_for('contacts'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'error')
        return redirect(url_for('contacts'))
    
    if not (file.filename and file.filename.lower().endswith('.csv')):
        flash('Apenas arquivos CSV são aceitos', 'error')
        return redirect(url_for('contacts'))
    
    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        imported_count = 0
        error_count = 0
        
        for row in csv_input:
            try:
                name = row.get('nome', row.get('name', ''))
                phone = row.get('telefone', row.get('phone', ''))
                email = row.get('email', '')
                company = row.get('empresa', row.get('company', ''))
                
                if not name or not phone:
                    error_count += 1
                    continue
                
                if not validate_phone(phone):
                    error_count += 1
                    continue
                
                # Check if contact already exists
                existing = Contact.query.filter_by(phone=clean_phone(phone)).first()
                if existing:
                    error_count += 1
                    continue
                
                contact = Contact(
                    name=name,
                    phone=clean_phone(phone),
                    email=email,
                    company=company
                )
                
                db.session.add(contact)
                imported_count += 1
                
            except Exception as e:
                error_count += 1
                app.logger.error(f'Error importing contact: {e}')
        
        db.session.commit()
        
        # Log activity
        log_activity('contacts_imported', f'{imported_count} contatos importados, {error_count} erros')
        
        flash(f'{imported_count} contatos importados com sucesso! {error_count} erros encontrados.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Erro ao importar arquivo CSV', 'error')
        app.logger.error(f'Error importing CSV: {e}')
    
    return redirect(url_for('contacts'))

@app.route('/templates')
def templates():
    templates = MessageTemplate.query.order_by(MessageTemplate.created_at.desc()).all()
    return render_template('templates.html', templates=templates)

@app.route('/templates/add', methods=['GET', 'POST'])
def add_template():
    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        content = request.form.get('content')
        
        template = MessageTemplate(
            name=name,
            subject=subject,
            content=content,
            variables=json.dumps(extract_variables(content))
        )
        
        try:
            db.session.add(template)
            db.session.commit()
            
            # Log activity
            log_activity('template_created', f'Template {name} criado')
            
            flash('Template criado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar template', 'error')
            app.logger.error(f'Error creating template: {e}')
    
    return redirect(url_for('templates'))

@app.route('/campaigns')
def campaigns():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    templates = MessageTemplate.query.all()
    contacts = Contact.query.all()
    return render_template('campaigns.html', campaigns=campaigns, templates=templates, contacts=contacts)

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
        
        # Log activity
        log_activity('campaign_created', f'Campanha {name} criada com {len(contact_ids)} contatos')
        
        flash('Campanha criada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Erro ao criar campanha', 'error')
        app.logger.error(f'Error creating campaign: {e}')
    
    return redirect(url_for('campaigns'))

@app.route('/campaigns/<int:campaign_id>/start')
def start_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    if campaign.status != 'draft':
        flash('Campanha já foi iniciada', 'warning')
        return redirect(url_for('campaigns'))
    
    # Start the campaign with real WhatsApp
    result = whatsapp_selenium.start_campaign(campaign)
    
    if result['success']:
        flash('Campanha iniciada com sucesso!', 'success')
    else:
        flash(f'Erro ao iniciar campanha: {result["message"]}', 'error')
    
    return redirect(url_for('campaigns'))

@app.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False)
    
    return render_template('history.html', logs=logs)

@app.route('/whatsapp')
def whatsapp_page():
    """WhatsApp connection management page"""
    return render_template('whatsapp.html')

@app.route('/connection/check')
def check_connection():
    connection = WhatsAppConnection.query.first()
    if not connection:
        connection = WhatsAppConnection(session_name="default")
        db.session.add(connection)
        db.session.commit()
    
    # Use real WhatsApp connection
    status = whatsapp_selenium.check_connection()
    connection.status = status['status']
    connection.last_check = datetime.utcnow()
    
    if status['status'] == 'connected':
        connection.phone_number = status.get('phone_number')
        connection.profile_name = status.get('profile_name')
    
    db.session.commit()
    
    return jsonify(status)

@app.route('/connection/connect')
def connect_whatsapp():
    """Connect to WhatsApp Web"""
    try:
        app.logger.info("Starting WhatsApp connection...")
        result = whatsapp_selenium.connect_to_whatsapp()
        
        # Update database
        connection = WhatsAppConnection.query.first()
        if not connection:
            connection = WhatsAppConnection(session_name="default")
            db.session.add(connection)
        
        if result.get('success'):
            if result.get('status') == 'connected':
                connection.status = 'connected'
                connection.phone_number = result.get('phone_number')
                connection.profile_name = result.get('profile_name')
                log_activity('whatsapp_connected', 'WhatsApp Web conectado com sucesso')
            elif result.get('status') == 'qr_code':
                connection.status = 'connecting'
        else:
            connection.status = 'disconnected'
            log_activity('whatsapp_connection_failed', result.get('message', 'Falha na conexão'), 'error')
        
        connection.last_check = datetime.utcnow()
        db.session.commit()
        
        app.logger.info(f"WhatsApp connection result: {result}")
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error connecting to WhatsApp: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao conectar: {str(e)}'
        }), 500

@app.route('/connection/qr')
def get_qr_code():
    """Get QR code for WhatsApp Web login"""
    try:
        qr_data = whatsapp_selenium.qr_code_data
        if qr_data:
            return jsonify({
                'success': True,
                'qr_code': qr_data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'QR Code não disponível'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter QR Code: {str(e)}'
        }), 500

@app.route('/connection/disconnect')
def disconnect_whatsapp():
    """Disconnect from WhatsApp Web"""
    try:
        whatsapp_selenium.close()
        
        # Update database
        connection = WhatsAppConnection.query.first()
        if connection:
            connection.status = 'disconnected'
            connection.last_check = datetime.utcnow()
            db.session.commit()
        
        log_activity('whatsapp_disconnected', 'WhatsApp Web desconectado')
        
        return jsonify({
            'success': True,
            'message': 'WhatsApp Web desconectado'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao desconectar: {str(e)}'
        }), 500

# Helper functions
def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return False
    
    # Remove all non-digit characters
    clean = re.sub(r'\D', '', phone)
    
    # Check if it's a valid Brazilian phone number
    return len(clean) >= 10 and len(clean) <= 15

def clean_phone(phone):
    """Clean and format phone number"""
    if not phone:
        return ''
    
    # Remove all non-digit characters
    clean = re.sub(r'\D', '', phone)
    
    # Add country code if missing
    if len(clean) == 11 and clean.startswith('0'):
        clean = '55' + clean[1:]
    elif len(clean) == 10:
        clean = '55' + clean
    elif len(clean) == 11 and not clean.startswith('55'):
        clean = '55' + clean
    
    return clean

def extract_variables(content):
    """Extract variables from template content"""
    if not content:
        return []
    
    # Find all {{variable}} patterns
    import re
    variables = re.findall(r'\{\{(\w+)\}\}', content)
    return list(set(variables))

def log_activity(action, details, status='success'):
    """Log activity to database"""
    log = ActivityLog(
        action=action,
        details=details,
        status=status
    )
    db.session.add(log)
    db.session.commit()
