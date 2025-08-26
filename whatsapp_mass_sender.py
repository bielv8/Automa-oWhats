#!/usr/bin/env python3
"""
WhatsApp Mass Sender - Sistema de disparo em massa
Conecta no seu WhatsApp Web e envia mensagens automaticamente
"""
import os
import sys
import json
import csv
import sqlite3
import logging
import threading
import webbrowser
import base64
import time
import urllib.parse
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from werkzeug.serving import run_simple

# Imports para WhatsApp Web
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WhatsAppMassSender:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "whatsapp-mass-sender-key"
        self.db_path = "whatsapp_mass.db"
        self.driver = None
        self.is_connected = False
        self.sending_active = False
        self.setup_database()
        self.setup_routes()
        
    def setup_database(self):
        """Cria database para contatos e campanhas"""
        conn = sqlite3.connect(self.db_path, timeout=20.0)
        
        # Tabela de contatos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'pending',
                last_sent TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de mensagens enviadas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                phone TEXT,
                message TEXT,
                status TEXT DEFAULT 'sent',
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            )
        ''')
        
        # Tabela de campanhas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                message_template TEXT NOT NULL,
                total_contacts INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database inicializado")
    
    def get_db_connection(self):
        """Conexão thread-safe com database"""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL;')
        return conn
    
    def setup_routes(self):
        """Configura rotas da aplicação"""
        
        @self.app.route('/')
        def index():
            conn = self.get_db_connection()
            stats = {
                'contacts': conn.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],
                'sent_today': conn.execute('''
                    SELECT COUNT(*) FROM sent_messages 
                    WHERE date(sent_at) = date('now')
                ''').fetchone()[0],
                'total_sent': conn.execute('SELECT COUNT(*) FROM sent_messages').fetchone()[0]
            }
            conn.close()
            
            return render_template_string(MAIN_TEMPLATE, 
                                        stats=stats, 
                                        connected=self.is_connected,
                                        sending=self.sending_active)
        
        @self.app.route('/connect', methods=['POST'])
        def connect_whatsapp():
            """Conecta ao WhatsApp Web"""
            try:
                if self.is_connected:
                    return jsonify({'success': True, 'message': 'Já está conectado'})
                
                success = self.start_whatsapp_connection()
                
                if success:
                    return jsonify({
                        'success': True, 
                        'message': 'WhatsApp Web conectado! Escaneie o QR Code no navegador que abriu.'
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'message': 'Erro ao conectar. Verifique se o Chrome está instalado.'
                    })
                    
            except Exception as e:
                logger.error(f"Erro na conexão: {e}")
                return jsonify({'success': False, 'message': f'Erro: {str(e)}'})
        
        @self.app.route('/disconnect', methods=['POST'])
        def disconnect_whatsapp():
            """Desconecta do WhatsApp Web"""
            self.disconnect()
            return jsonify({'success': True, 'message': 'WhatsApp desconectado'})
        
        @self.app.route('/status')
        def connection_status():
            """Verifica status da conexão"""
            if self.driver:
                try:
                    # Verifica se ainda está na página do WhatsApp
                    current_url = self.driver.current_url
                    if 'web.whatsapp.com' in current_url:
                        # Verifica se está logado
                        chats = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='chat-list']")
                        self.is_connected = len(chats) > 0
                    else:
                        self.is_connected = False
                except:
                    self.is_connected = False
            
            return jsonify({
                'connected': self.is_connected,
                'sending': self.sending_active,
                'driver_active': self.driver is not None
            })
        
        @self.app.route('/contacts')
        def contacts():
            conn = self.get_db_connection()
            contacts = conn.execute('SELECT * FROM contacts ORDER BY created_at DESC').fetchall()
            conn.close()
            return render_template_string(CONTACTS_TEMPLATE, contacts=contacts)
        
        @self.app.route('/add_contact', methods=['POST'])
        def add_contact():
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            
            if not name or not phone:
                flash('Nome e telefone são obrigatórios', 'error')
                return redirect(url_for('contacts'))
            
            # Limpa telefone
            clean_phone = self.clean_phone(phone)
            if not clean_phone:
                flash('Número de telefone inválido', 'error')
                return redirect(url_for('contacts'))
            
            try:
                conn = self.get_db_connection()
                conn.execute('INSERT INTO contacts (name, phone) VALUES (?, ?)', (name, clean_phone))
                conn.commit()
                conn.close()
                flash('Contato adicionado com sucesso!', 'success')
            except sqlite3.IntegrityError:
                flash('Este telefone já está cadastrado', 'error')
            except Exception as e:
                flash(f'Erro ao adicionar: {e}', 'error')
            
            return redirect(url_for('contacts'))
        
        @self.app.route('/import_csv', methods=['POST'])
        def import_csv():
            if 'file' not in request.files:
                flash('Selecione um arquivo CSV', 'error')
                return redirect(url_for('contacts'))
            
            file = request.files['file']
            if not file.filename.endswith('.csv'):
                flash('Arquivo deve ser CSV', 'error')
                return redirect(url_for('contacts'))
            
            try:
                content = file.read().decode('utf-8')
                csv_reader = csv.DictReader(content.splitlines())
                
                imported = 0
                errors = 0
                conn = self.get_db_connection()
                
                for row in csv_reader:
                    try:
                        name = row.get('nome', row.get('name', '')).strip()
                        phone = row.get('telefone', row.get('phone', '')).strip()
                        
                        if name and phone:
                            clean_phone = self.clean_phone(phone)
                            if clean_phone:
                                conn.execute('INSERT OR IGNORE INTO contacts (name, phone) VALUES (?, ?)', 
                                           (name, clean_phone))
                                imported += 1
                            else:
                                errors += 1
                        else:
                            errors += 1
                    except:
                        errors += 1
                
                conn.commit()
                conn.close()
                flash(f'Importados: {imported} contatos. Erros: {errors}', 'success')
                
            except Exception as e:
                flash(f'Erro na importação: {e}', 'error')
            
            return redirect(url_for('contacts'))
        
        @self.app.route('/send_mass', methods=['POST'])
        def send_mass_messages():
            """Envia mensagens em massa"""
            if not self.is_connected:
                return jsonify({'success': False, 'message': 'WhatsApp não está conectado'})
            
            if self.sending_active:
                return jsonify({'success': False, 'message': 'Já está enviando mensagens'})
            
            message = request.form.get('message', '').strip()
            if not message:
                return jsonify({'success': False, 'message': 'Mensagem não pode estar vazia'})
            
            # Inicia envio em background
            thread = threading.Thread(target=self.send_to_all_contacts, args=(message,))
            thread.daemon = True
            thread.start()
            
            return jsonify({'success': True, 'message': 'Envio iniciado! Acompanhe o progresso.'})
        
        @self.app.route('/sending_progress')
        def sending_progress():
            """Retorna progresso do envio"""
            conn = self.get_db_connection()
            total = conn.execute('SELECT COUNT(*) FROM contacts WHERE status = "pending"').fetchone()[0]
            sent_today = conn.execute('''
                SELECT COUNT(*) FROM sent_messages 
                WHERE date(sent_at) = date('now')
            ''').fetchone()[0]
            conn.close()
            
            return jsonify({
                'sending': self.sending_active,
                'total_contacts': total,
                'sent_today': sent_today
            })
    
    def clean_phone(self, phone):
        """Limpa e formata número de telefone"""
        import re
        if not phone:
            return None
        
        # Remove tudo exceto números
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
    
    def start_whatsapp_connection(self):
        """Inicia conexão com WhatsApp Web"""
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium não disponível")
            return False
        
        try:
            # Configura Chrome para Windows
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9223')
            options.add_argument('--user-data-dir=./whatsapp_session')
            
            # Tenta diferentes métodos de inicialização
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except:
                # Fallback para Chrome local
                self.driver = webdriver.Chrome(options=options)
            
            # Abre WhatsApp Web
            logger.info("Abrindo WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")
            
            # Aguarda carregamento
            time.sleep(3)
            
            # Verifica se precisa fazer login
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']"))
                )
                self.is_connected = True
                logger.info("WhatsApp já está logado!")
            except TimeoutException:
                logger.info("Precisa fazer login - QR Code disponível na tela")
                self.is_connected = False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conectar WhatsApp: {e}")
            return False
    
    def send_to_all_contacts(self, message_template):
        """Envia mensagem para todos os contatos"""
        if not self.driver or not self.is_connected:
            logger.error("WhatsApp não conectado")
            return
        
        self.sending_active = True
        logger.info("Iniciando envio em massa")
        
        try:
            conn = self.get_db_connection()
            contacts = conn.execute('SELECT * FROM contacts WHERE status = "pending"').fetchall()
            
            for contact in contacts:
                if not self.sending_active:
                    break
                
                try:
                    # Personaliza mensagem
                    message = message_template.replace('{{nome}}', contact['name'])
                    
                    # Envia mensagem
                    success = self.send_message(contact['phone'], message)
                    
                    if success:
                        # Salva como enviada
                        conn.execute('''
                            INSERT INTO sent_messages (contact_id, phone, message) 
                            VALUES (?, ?, ?)
                        ''', (contact['id'], contact['phone'], message))
                        
                        # Atualiza status do contato
                        conn.execute('UPDATE contacts SET status = "sent", last_sent = ? WHERE id = ?', 
                                   (datetime.now(), contact['id']))
                        
                        logger.info(f"Mensagem enviada para {contact['name']}")
                    else:
                        logger.warning(f"Falha ao enviar para {contact['name']}")
                    
                    conn.commit()
                    
                    # Delay entre mensagens (evita spam)
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar para {contact['name']}: {e}")
                    time.sleep(1)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Erro no envio em massa: {e}")
        finally:
            self.sending_active = False
            logger.info("Envio em massa finalizado")
    
    def send_message(self, phone, message):
        """Envia uma mensagem para um número específico"""
        try:
            if not self.driver:
                return False
            
            # URL do WhatsApp Web para enviar mensagem
            encoded_message = urllib.parse.quote(message)
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
            
            # Navega para a URL
            self.driver.get(url)
            
            # Aguarda a página carregar
            time.sleep(3)
            
            # Procura o botão de enviar
            try:
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='send']"))
                )
                send_button.click()
                
                # Aguarda confirmação de envio
                time.sleep(1)
                return True
                
            except TimeoutException:
                logger.warning(f"Timeout ao enviar para {phone}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {phone}: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do WhatsApp"""
        try:
            self.sending_active = False
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.is_connected = False
            logger.info("WhatsApp desconectado")
        except Exception as e:
            logger.error(f"Erro ao desconectar: {e}")
    
    def run(self, host='127.0.0.1', port=5000):
        """Executa a aplicação"""
        print("🚀 WhatsApp Mass Sender")
        print(f"📱 Acesse: http://{host}:{port}")
        print("💬 Sistema de disparo em massa ativo!")
        
        # Abre navegador automaticamente
        threading.Timer(1, lambda: webbrowser.open(f'http://{host}:{port}')).start()
        
        try:
            run_simple(host, port, self.app, use_reloader=False, threaded=True)
        except KeyboardInterrupt:
            print("\n👋 Encerrando sistema...")
            self.disconnect()

# Templates HTML
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Mass Sender</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #1a1a1a; color: #fff; }
        .card { background-color: #2d2d2d; border: 1px solid #444; }
        .btn-whatsapp { background-color: #25d366; border-color: #25d366; color: white; }
        .btn-whatsapp:hover { background-color: #128c7e; border-color: #128c7e; color: white; }
        .status-connected { color: #25d366; }
        .status-disconnected { color: #dc3545; }
        .status-sending { color: #ffc107; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <span class="navbar-brand">📱 WhatsApp Mass Sender</span>
            <span class="navbar-text">
                {% if connected %}
                    <i class="fas fa-circle status-connected"></i> Conectado
                {% else %}
                    <i class="fas fa-circle status-disconnected"></i> Desconectado
                {% endif %}
                {% if sending %}
                    | <i class="fas fa-paper-plane status-sending"></i> Enviando...
                {% endif %}
            </span>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- Estatísticas -->
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body text-center">
                        <i class="fas fa-users fa-2x mb-2 text-primary"></i>
                        <h5>{{ stats.contacts }}</h5>
                        <small>Contatos Cadastrados</small>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body text-center">
                        <i class="fas fa-paper-plane fa-2x mb-2 text-success"></i>
                        <h5>{{ stats.sent_today }}</h5>
                        <small>Enviadas Hoje</small>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body text-center">
                        <i class="fas fa-chart-line fa-2x mb-2 text-info"></i>
                        <h5>{{ stats.total_sent }}</h5>
                        <small>Total Enviadas</small>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <!-- Conexão WhatsApp -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fab fa-whatsapp"></i> Conexão WhatsApp</h5>
                    </div>
                    <div class="card-body">
                        <div id="connectionStatus" class="mb-3">
                            {% if connected %}
                                <div class="alert alert-success">
                                    <i class="fas fa-check-circle"></i> WhatsApp Web conectado!
                                </div>
                            {% else %}
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle"></i> WhatsApp Web não conectado
                                </div>
                            {% endif %}
                        </div>
                        
                        <div class="d-grid gap-2">
                            {% if not connected %}
                                <button id="connectBtn" class="btn btn-whatsapp btn-lg" onclick="connectWhatsApp()">
                                    <i class="fab fa-whatsapp"></i> Conectar WhatsApp Web
                                </button>
                            {% else %}
                                <button id="disconnectBtn" class="btn btn-danger" onclick="disconnectWhatsApp()">
                                    <i class="fas fa-sign-out-alt"></i> Desconectar
                                </button>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Envio em Massa -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-bullhorn"></i> Disparo em Massa</h5>
                    </div>
                    <div class="card-body">
                        <form id="massMessageForm" onsubmit="sendMassMessages(event)">
                            <div class="mb-3">
                                <label class="form-label">Mensagem:</label>
                                <textarea name="message" class="form-control" rows="4" 
                                         placeholder="Digite sua mensagem aqui...&#10;&#10;Use {{nome}} para personalizar com o nome do contato"></textarea>
                                <small class="text-muted">Dica: Use {{nome}} para personalizar</small>
                            </div>
                            
                            <div class="d-grid">
                                <button type="submit" class="btn btn-success btn-lg" 
                                       {% if not connected or sending %}disabled{% endif %}>
                                    <i class="fas fa-rocket"></i> 
                                    {% if sending %}
                                        Enviando...
                                    {% else %}
                                        Enviar para Todos
                                    {% endif %}
                                </button>
                            </div>
                        </form>
                        
                        <div id="sendingProgress" class="mt-3" style="display: none;">
                            <div class="progress">
                                <div id="progressBar" class="progress-bar bg-success" style="width: 0%"></div>
                            </div>
                            <small id="progressText" class="text-muted">Enviando mensagens...</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Links de navegação -->
        <div class="row mt-4">
            <div class="col-12 text-center">
                <a href="/contacts" class="btn btn-outline-primary me-2">
                    <i class="fas fa-address-book"></i> Gerenciar Contatos
                </a>
                <button onclick="location.reload()" class="btn btn-outline-secondary">
                    <i class="fas fa-sync"></i> Atualizar Status
                </button>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Conectar WhatsApp
        async function connectWhatsApp() {
            const btn = document.getElementById('connectBtn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Conectando...';
            
            try {
                const response = await fetch('/connect', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    alert('WhatsApp Web conectado! Uma nova janela foi aberta. Escaneie o QR Code com seu celular.');
                    setTimeout(() => location.reload(), 2000);
                } else {
                    alert('Erro: ' + result.message);
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fab fa-whatsapp"></i> Conectar WhatsApp Web';
                }
            } catch (error) {
                alert('Erro na conexão: ' + error.message);
                btn.disabled = false;
                btn.innerHTML = '<i class="fab fa-whatsapp"></i> Conectar WhatsApp Web';
            }
        }
        
        // Desconectar WhatsApp
        async function disconnectWhatsApp() {
            const response = await fetch('/disconnect', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
            location.reload();
        }
        
        // Enviar mensagens em massa
        async function sendMassMessages(event) {
            event.preventDefault();
            
            const form = event.target;
            const message = form.message.value.trim();
            
            if (!message) {
                alert('Digite uma mensagem!');
                return;
            }
            
            if (!confirm('Enviar mensagem para todos os contatos?')) {
                return;
            }
            
            const formData = new FormData(form);
            
            try {
                const response = await fetch('/send_mass', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('Envio iniciado! As mensagens estão sendo enviadas...');
                    document.getElementById('sendingProgress').style.display = 'block';
                    monitorProgress();
                } else {
                    alert('Erro: ' + result.message);
                }
            } catch (error) {
                alert('Erro: ' + error.message);
            }
        }
        
        // Monitor progresso
        function monitorProgress() {
            const interval = setInterval(async () => {
                try {
                    const response = await fetch('/sending_progress');
                    const progress = await response.json();
                    
                    if (!progress.sending) {
                        clearInterval(interval);
                        document.getElementById('sendingProgress').style.display = 'none';
                        location.reload();
                    }
                } catch (error) {
                    clearInterval(interval);
                }
            }, 2000);
        }
        
        // Verifica status automaticamente
        setInterval(async () => {
            try {
                const response = await fetch('/status');
                const status = await response.json();
                // Atualiza interface conforme status
            } catch (error) {
                // Ignora erros de status
            }
        }, 10000);
    </script>
</body>
</html>
'''

CONTACTS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contatos - WhatsApp Mass Sender</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #1a1a1a; color: #fff; }
        .card { background-color: #2d2d2d; border: 1px solid #444; }
        .table-dark { --bs-table-bg: #2d2d2d; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <span class="navbar-brand">📋 Gerenciar Contatos</span>
            <a href="/" class="btn btn-outline-light btn-sm">
                <i class="fas fa-arrow-left"></i> Voltar
            </a>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- Adicionar contato -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-user-plus"></i> Adicionar Contato</h5>
                    </div>
                    <div class="card-body">
                        <form action="/add_contact" method="POST">
                            <div class="mb-3">
                                <input type="text" name="name" class="form-control" placeholder="Nome" required>
                            </div>
                            <div class="mb-3">
                                <input type="text" name="phone" class="form-control" placeholder="Telefone (com DDD)" required>
                            </div>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-plus"></i> Adicionar
                            </button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-file-csv"></i> Importar CSV</h5>
                    </div>
                    <div class="card-body">
                        <form action="/import_csv" method="POST" enctype="multipart/form-data">
                            <div class="mb-3">
                                <input type="file" name="file" class="form-control" accept=".csv" required>
                                <small class="text-muted">Formato: nome,telefone (uma linha por contato)</small>
                            </div>
                            <button type="submit" class="btn btn-success">
                                <i class="fas fa-upload"></i> Importar
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- Lista de contatos -->
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-list"></i> Contatos Cadastrados ({{ contacts|length }})</h5>
            </div>
            <div class="card-body">
                {% if contacts %}
                    <div class="table-responsive">
                        <table class="table table-dark table-striped">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th>Telefone</th>
                                    <th>Status</th>
                                    <th>Último Envio</th>
                                    <th>Cadastrado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for contact in contacts %}
                                <tr>
                                    <td>{{ contact.name }}</td>
                                    <td>{{ contact.phone }}</td>
                                    <td>
                                        {% if contact.status == 'sent' %}
                                            <span class="badge bg-success">Enviado</span>
                                        {% else %}
                                            <span class="badge bg-warning">Pendente</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if contact.last_sent %}
                                            {{ contact.last_sent[:19] }}
                                        {% else %}
                                            -
                                        {% endif %}
                                    </td>
                                    <td>{{ contact.created_at[:19] }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> Nenhum contato cadastrado ainda.
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="position-fixed top-0 end-0 p-3" style="z-index: 11">
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

if __name__ == '__main__':
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium não está instalado!")
        print("Execute: pip install selenium webdriver-manager")
        sys.exit(1)
    
    app = WhatsAppMassSender()
    app.run()