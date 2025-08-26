#!/usr/bin/env python3
"""
WhatsApp Automation Desktop Application
Versão standalone para rodar localmente no desktop
"""
import os
import sys
import json
import csv
import io
import re
import sqlite3
import logging
import threading
import webbrowser
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.serving import run_simple
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WhatsAppDesktopApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "whatsapp-desktop-secret-key"
        self.db_path = "whatsapp_desktop.db"
        self.setup_database()
        self.setup_routes()
        
    def setup_database(self):
        """Cria as tabelas do banco de dados SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de contatos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                company TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subject TEXT,
                content TEXT NOT NULL,
                variables TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de campanhas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                template_id INTEGER,
                status TEXT DEFAULT 'draft',
                total_contacts INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES templates(id)
            )
        ''')
        
        # Tabela de logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'success'
            )
        ''')
        
        # Tabela de conexão WhatsApp
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whatsapp_connection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT DEFAULT 'desktop',
                status TEXT DEFAULT 'disconnected',
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                phone_number TEXT,
                profile_name TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def get_db_connection(self):
        """Obtém conexão com o banco"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def log_activity(self, action, details, status='success'):
        """Registra atividade no log"""
        conn = self.get_db_connection()
        conn.execute(
            'INSERT INTO activity_logs (action, details, status) VALUES (?, ?, ?)',
            (action, details, status)
        )
        conn.commit()
        conn.close()
    
    def setup_routes(self):
        """Configura todas as rotas da aplicação"""
        
        @self.app.route('/')
        def index():
            conn = self.get_db_connection()
            
            # Estatísticas
            stats = {
                'contacts': conn.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],
                'templates': conn.execute('SELECT COUNT(*) FROM templates').fetchone()[0],
                'campaigns': conn.execute('SELECT COUNT(*) FROM campaigns').fetchone()[0]
            }
            
            # Logs recentes
            recent_logs = conn.execute(
                'SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10'
            ).fetchall()
            
            # Status da conexão
            connection = conn.execute(
                'SELECT * FROM whatsapp_connection ORDER BY id DESC LIMIT 1'
            ).fetchone()
            
            conn.close()
            
            return render_template('index.html',
                                 stats=stats,
                                 recent_logs=recent_logs,
                                 connection=connection)
        
        @self.app.route('/contacts')
        def contacts():
            conn = self.get_db_connection()
            search = request.args.get('search', '')
            
            if search:
                contacts = conn.execute(
                    'SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ? ORDER BY created_at DESC',
                    (f'%{search}%', f'%{search}%')
                ).fetchall()
            else:
                contacts = conn.execute(
                    'SELECT * FROM contacts ORDER BY created_at DESC'
                ).fetchall()
            
            conn.close()
            return render_template('contacts.html', contacts=contacts, search=search)
        
        @self.app.route('/contacts/add', methods=['POST'])
        def add_contact():
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            company = request.form.get('company', '').strip()
            
            if not name or not phone:
                flash('Nome e telefone são obrigatórios', 'error')
                return redirect(url_for('contacts'))
            
            # Valida e limpa telefone
            clean_phone_number = self.clean_phone(phone)
            if not clean_phone_number:
                flash('Número de telefone inválido', 'error')
                return redirect(url_for('contacts'))
            
            try:
                conn = self.get_db_connection()
                conn.execute(
                    'INSERT INTO contacts (name, phone, email, company) VALUES (?, ?, ?, ?)',
                    (name, clean_phone_number, email, company)
                )
                conn.commit()
                conn.close()
                
                self.log_activity('contact_added', f'Contato {name} adicionado')
                flash('Contato adicionado com sucesso!', 'success')
            except Exception as e:
                logger.error(f"Error adding contact: {e}")
                flash('Erro ao adicionar contato', 'error')
            
            return redirect(url_for('contacts'))
        
        @self.app.route('/contacts/import', methods=['POST'])
        def import_contacts():
            if 'file' not in request.files:
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(url_for('contacts'))
            
            file = request.files['file']
            if not file or not file.filename or not file.filename.lower().endswith('.csv'):
                flash('Selecione um arquivo CSV válido', 'error')
                return redirect(url_for('contacts'))
            
            try:
                # Lê o arquivo CSV
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                
                imported_count = 0
                error_count = 0
                conn = self.get_db_connection()
                
                for row in csv_input:
                    try:
                        name = row.get('nome', row.get('name', '')).strip()
                        phone = row.get('telefone', row.get('phone', '')).strip()
                        email = row.get('email', '').strip()
                        company = row.get('empresa', row.get('company', '')).strip()
                        
                        if not name or not phone:
                            error_count += 1
                            continue
                        
                        clean_phone_number = self.clean_phone(phone)
                        if not clean_phone_number:
                            error_count += 1
                            continue
                        
                        # Verifica se já existe
                        existing = conn.execute(
                            'SELECT id FROM contacts WHERE phone = ?',
                            (clean_phone_number,)
                        ).fetchone()
                        
                        if existing:
                            error_count += 1
                            continue
                        
                        conn.execute(
                            'INSERT INTO contacts (name, phone, email, company) VALUES (?, ?, ?, ?)',
                            (name, clean_phone_number, email, company)
                        )
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing row: {e}")
                        error_count += 1
                
                conn.commit()
                conn.close()
                
                self.log_activity('contacts_imported', 
                                f'{imported_count} contatos importados, {error_count} erros')
                flash(f'{imported_count} contatos importados! {error_count} erros.', 'success')
                
            except Exception as e:
                logger.error(f"Error importing CSV: {e}")
                flash('Erro ao importar arquivo CSV', 'error')
            
            return redirect(url_for('contacts'))
        
        @self.app.route('/templates')
        def templates():
            conn = self.get_db_connection()
            templates = conn.execute(
                'SELECT * FROM templates ORDER BY created_at DESC'
            ).fetchall()
            conn.close()
            return render_template('templates.html', templates=templates)
        
        @self.app.route('/templates/add', methods=['POST'])
        def add_template():
            name = request.form.get('name', '').strip()
            subject = request.form.get('subject', '').strip()
            content = request.form.get('content', '').strip()
            
            if not name or not content:
                flash('Nome e conteúdo são obrigatórios', 'error')
                return redirect(url_for('templates'))
            
            # Extrai variáveis do template
            variables = self.extract_variables(content)
            
            try:
                conn = self.get_db_connection()
                conn.execute(
                    'INSERT INTO templates (name, subject, content, variables) VALUES (?, ?, ?, ?)',
                    (name, subject, content, json.dumps(variables))
                )
                conn.commit()
                conn.close()
                
                self.log_activity('template_created', f'Template {name} criado')
                flash('Template criado com sucesso!', 'success')
            except Exception as e:
                logger.error(f"Error creating template: {e}")
                flash('Erro ao criar template', 'error')
            
            return redirect(url_for('templates'))
        
        @self.app.route('/campaigns')
        def campaigns():
            conn = self.get_db_connection()
            campaigns = conn.execute(
                'SELECT c.*, t.name as template_name FROM campaigns c LEFT JOIN templates t ON c.template_id = t.id ORDER BY c.created_at DESC'
            ).fetchall()
            templates = conn.execute('SELECT * FROM templates ORDER BY name').fetchall()
            contacts = conn.execute('SELECT * FROM contacts ORDER BY name').fetchall()
            conn.close()
            
            return render_template('campaigns.html',
                                 campaigns=campaigns,
                                 templates=templates,
                                 contacts=contacts)
        
        @self.app.route('/campaigns/create', methods=['POST'])
        def create_campaign():
            name = request.form.get('name', '').strip()
            template_id = request.form.get('template_id')
            contact_ids = request.form.getlist('contact_ids')
            
            if not name or not template_id or not contact_ids:
                flash('Preencha todos os campos obrigatórios', 'error')
                return redirect(url_for('campaigns'))
            
            try:
                conn = self.get_db_connection()
                conn.execute(
                    'INSERT INTO campaigns (name, template_id, total_contacts, status) VALUES (?, ?, ?, ?)',
                    (name, template_id, len(contact_ids), 'draft')
                )
                conn.commit()
                conn.close()
                
                self.log_activity('campaign_created', 
                                f'Campanha {name} criada com {len(contact_ids)} contatos')
                flash('Campanha criada com sucesso!', 'success')
            except Exception as e:
                logger.error(f"Error creating campaign: {e}")
                flash('Erro ao criar campanha', 'error')
            
            return redirect(url_for('campaigns'))
        
        @self.app.route('/history')
        def history():
            conn = self.get_db_connection()
            logs = conn.execute(
                'SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 100'
            ).fetchall()
            conn.close()
            return render_template('history.html', logs=logs)
        
        @self.app.route('/whatsapp')
        def whatsapp_page():
            return render_template('whatsapp.html')
        
        @self.app.route('/connection/check')
        def check_connection():
            return jsonify({
                'status': 'disconnected',
                'message': 'WhatsApp Web integration available in development mode'
            })
        
        @self.app.route('/connection/connect')
        def connect_whatsapp():
            return jsonify({
                'success': False,
                'message': 'WhatsApp Web automation requires Selenium WebDriver setup'
            })
        
        @self.app.route('/shutdown', methods=['POST'])
        def shutdown():
            """Endpoint para fechar a aplicação"""
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                return 'Not running with the Werkzeug Server'
            func()
            return 'Servidor sendo desligado...'
        
        # Filtro personalizado para templates
        @self.app.template_filter('from_json')
        def from_json_filter(value):
            if not value:
                return []
            try:
                return json.loads(value) if isinstance(value, str) else value
            except:
                return []
    
    def clean_phone(self, phone):
        """Limpa e valida número de telefone"""
        if not phone:
            return None
        
        # Remove caracteres não numéricos
        clean = re.sub(r'\D', '', phone)
        
        # Valida tamanho
        if len(clean) < 10 or len(clean) > 15:
            return None
        
        # Adiciona código do país se necessário
        if len(clean) == 11 and clean.startswith('0'):
            clean = '55' + clean[1:]
        elif len(clean) == 10:
            clean = '55' + clean
        elif len(clean) == 11 and not clean.startswith('55'):
            clean = '55' + clean
        
        return clean
    
    def extract_variables(self, content):
        """Extrai variáveis do template"""
        if not content:
            return []
        
        variables = re.findall(r'\{\{(\w+)\}\}', content)
        return list(set(variables))
    
    def run(self, host='127.0.0.1', port=5000, debug=False):
        """Executa a aplicação"""
        try:
            print(f"\n🚀 WhatsApp Automation Desktop")
            print(f"📱 Acesse: http://{host}:{port}")
            print(f"🔧 Para parar: Ctrl+C ou acesse /shutdown")
            print(f"💾 Database: {self.db_path}")
            print("\n" + "="*50)
            
            # Abre o navegador automaticamente
            if not debug:
                threading.Timer(1.5, lambda: webbrowser.open(f'http://{host}:{port}')).start()
            
            # Executa o servidor
            run_simple(host, port, self.app, 
                      use_reloader=debug, 
                      use_debugger=debug,
                      threaded=True)
                      
        except KeyboardInterrupt:
            print("\n\n👋 Aplicação encerrada pelo usuário")
        except Exception as e:
            print(f"\n❌ Erro ao executar aplicação: {e}")

def main():
    """Função principal"""
    print("🔄 Inicializando WhatsApp Automation Desktop...")
    
    try:
        app = WhatsAppDesktopApp()
        app.run(debug=False)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        input("Pressione Enter para sair...")

if __name__ == '__main__':
    main()