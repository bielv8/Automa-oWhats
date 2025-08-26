#!/usr/bin/env python3
"""
WhatsApp Pro - Sistema Profissional de Disparo em Massa
Interface moderna + Conexão WhatsApp Web garantida
"""
import os
import sys
import json
import csv
import sqlite3
import logging
import threading
import webbrowser
import time
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from werkzeug.serving import run_simple

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WhatsAppPro:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "whatsapp-pro-2025"
        self.db_path = "whatsapp_pro.db"
        self.driver = None
        self.is_connected = False
        self.sending_active = False
        self.connection_status = "disconnected"
        self.user_info = {}
        self.setup_database()
        self.setup_routes()
        
    def setup_database(self):
        """Configura database completo"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        
        # Contatos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                email TEXT,
                company TEXT,
                tags TEXT,
                status TEXT DEFAULT 'active',
                last_sent TIMESTAMP,
                total_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Grupos de contatos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contact_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                color TEXT DEFAULT '#007bff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Relação contato-grupo
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contact_group_members (
                contact_id INTEGER,
                group_id INTEGER,
                FOREIGN KEY (contact_id) REFERENCES contacts(id),
                FOREIGN KEY (group_id) REFERENCES contact_groups(id),
                PRIMARY KEY (contact_id, group_id)
            )
        ''')
        
        # Templates de mensagem
        conn.execute('''
            CREATE TABLE IF NOT EXISTS message_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                variables TEXT,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Campanhas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                template_id INTEGER,
                target_groups TEXT,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                scheduled_for TIMESTAMP,
                total_contacts INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES message_templates(id)
            )
        ''')
        
        # Mensagens enviadas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                contact_id INTEGER,
                phone TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'sent',
                error_message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            )
        ''')
        
        # Configurações
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Logs do sistema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        self.log_system('INFO', 'Database inicializado com sucesso')
        
    def get_db_connection(self):
        """Conexão thread-safe otimizada"""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA cache_size=10000;')
        conn.execute('PRAGMA temp_store=memory;')
        return conn
    
    def log_system(self, level, message, details=None):
        """Log do sistema"""
        try:
            conn = self.get_db_connection()
            conn.execute(
                'INSERT INTO system_logs (level, message, details) VALUES (?, ?, ?)',
                (level, message, details)
            )
            conn.commit()
            conn.close()
            logger.info(f"{level}: {message}")
        except:
            logger.error(f"Falha ao salvar log: {message}")
    
    def setup_routes(self):
        """Configura todas as rotas"""
        
        @self.app.route('/')
        def dashboard():
            conn = self.get_db_connection()
            
            # Estatísticas
            stats = {
                'total_contacts': conn.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],
                'active_contacts': conn.execute('SELECT COUNT(*) FROM contacts WHERE status = "active"').fetchone()[0],
                'total_campaigns': conn.execute('SELECT COUNT(*) FROM campaigns').fetchone()[0],
                'active_campaigns': conn.execute('SELECT COUNT(*) FROM campaigns WHERE status = "running"').fetchone()[0],
                'sent_today': conn.execute('''
                    SELECT COUNT(*) FROM sent_messages 
                    WHERE date(sent_at) = date('now')
                ''').fetchone()[0],
                'sent_this_week': conn.execute('''
                    SELECT COUNT(*) FROM sent_messages 
                    WHERE date(sent_at) >= date('now', '-7 days')
                ''').fetchone()[0],
                'total_sent': conn.execute('SELECT COUNT(*) FROM sent_messages').fetchone()[0]
            }
            
            # Campanhas recentes
            recent_campaigns = conn.execute('''
                SELECT * FROM campaigns 
                ORDER BY created_at DESC 
                LIMIT 5
            ''').fetchall()
            
            # Logs recentes
            recent_logs = conn.execute('''
                SELECT * FROM system_logs 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''').fetchall()
            
            conn.close()
            
            return render_template_string(DASHBOARD_TEMPLATE, 
                                        stats=stats,
                                        recent_campaigns=recent_campaigns,
                                        recent_logs=recent_logs,
                                        connection_status=self.connection_status,
                                        user_info=self.user_info,
                                        sending_active=self.sending_active)
        
        @self.app.route('/connect_whatsapp', methods=['POST'])
        def connect_whatsapp():
            """Conecta WhatsApp Web com múltiplas tentativas"""
            if self.is_connected:
                return jsonify({'success': True, 'message': 'WhatsApp já conectado'})
            
            self.log_system('INFO', 'Iniciando conexão WhatsApp Web')
            
            try:
                success = self.connect_whatsapp_web()
                
                if success:
                    self.connection_status = "connected"
                    self.log_system('INFO', 'WhatsApp Web conectado com sucesso')
                    return jsonify({
                        'success': True,
                        'message': 'WhatsApp Web conectado! Verifique a janela do navegador.'
                    })
                else:
                    self.connection_status = "error"
                    self.log_system('ERROR', 'Falha ao conectar WhatsApp Web')
                    return jsonify({
                        'success': False,
                        'message': 'Falha na conexão. Verifique se o Chrome está instalado e atualizado.'
                    })
                    
            except Exception as e:
                self.connection_status = "error"
                self.log_system('ERROR', f'Erro na conexão WhatsApp: {str(e)}')
                return jsonify({
                    'success': False,
                    'message': f'Erro na conexão: {str(e)}'
                })
        
        @self.app.route('/disconnect_whatsapp', methods=['POST'])
        def disconnect_whatsapp():
            """Desconecta WhatsApp"""
            self.disconnect_whatsapp_web()
            return jsonify({'success': True, 'message': 'WhatsApp desconectado'})
        
        @self.app.route('/whatsapp_status')
        def whatsapp_status():
            """Status detalhado da conexão"""
            status = self.check_whatsapp_status()
            return jsonify(status)
        
        @self.app.route('/contacts')
        def contacts():
            """Página de contatos"""
            conn = self.get_db_connection()
            
            search = request.args.get('search', '')
            group_filter = request.args.get('group', '')
            
            query = 'SELECT * FROM contacts WHERE 1=1'
            params = []
            
            if search:
                query += ' AND (name LIKE ? OR phone LIKE ? OR company LIKE ?)'
                search_term = f'%{search}%'
                params.extend([search_term, search_term, search_term])
            
            query += ' ORDER BY created_at DESC'
            
            contacts = conn.execute(query, params).fetchall()
            groups = conn.execute('SELECT * FROM contact_groups ORDER BY name').fetchall()
            
            conn.close()
            
            return render_template_string(CONTACTS_TEMPLATE,
                                        contacts=contacts,
                                        groups=groups,
                                        search=search)
        
        @self.app.route('/campaigns')
        def campaigns():
            """Página de campanhas"""
            conn = self.get_db_connection()
            
            campaigns = conn.execute('''
                SELECT c.*, t.name as template_name 
                FROM campaigns c
                LEFT JOIN message_templates t ON c.template_id = t.id
                ORDER BY c.created_at DESC
            ''').fetchall()
            
            templates = conn.execute('SELECT * FROM message_templates ORDER BY name').fetchall()
            groups = conn.execute('SELECT * FROM contact_groups ORDER BY name').fetchall()
            
            conn.close()
            
            return render_template_string(CAMPAIGNS_TEMPLATE,
                                        campaigns=campaigns,
                                        templates=templates,
                                        groups=groups)
        
        @self.app.route('/templates')
        def templates():
            """Página de templates"""
            conn = self.get_db_connection()
            templates = conn.execute('SELECT * FROM message_templates ORDER BY created_at DESC').fetchall()
            conn.close()
            
            return render_template_string(TEMPLATES_TEMPLATE, templates=templates)
        
        # APIs para operações
        @self.app.route('/api/contacts', methods=['POST'])
        def api_add_contact():
            data = request.get_json()
            
            try:
                conn = self.get_db_connection()
                conn.execute('''
                    INSERT INTO contacts (name, phone, email, company, tags) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (data['name'], self.clean_phone(data['phone']), 
                     data.get('email', ''), data.get('company', ''), data.get('tags', '')))
                conn.commit()
                conn.close()
                
                self.log_system('INFO', f'Contato adicionado: {data["name"]}')
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/campaigns', methods=['POST'])
        def api_create_campaign():
            data = request.get_json()
            
            try:
                conn = self.get_db_connection()
                cursor = conn.execute('''
                    INSERT INTO campaigns (name, message, target_groups) 
                    VALUES (?, ?, ?) 
                ''', (data['name'], data['message'], json.dumps(data.get('groups', []))))
                
                campaign_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                self.log_system('INFO', f'Campanha criada: {data["name"]}')
                return jsonify({'success': True, 'campaign_id': campaign_id})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/send_campaign/<int:campaign_id>', methods=['POST'])
        def api_send_campaign(campaign_id):
            """Inicia envio de campanha"""
            if not self.is_connected:
                return jsonify({'success': False, 'error': 'WhatsApp não conectado'})
            
            if self.sending_active:
                return jsonify({'success': False, 'error': 'Já existe um envio em andamento'})
            
            # Inicia envio em background
            thread = threading.Thread(target=self.execute_campaign, args=(campaign_id,))
            thread.daemon = True
            thread.start()
            
            return jsonify({'success': True, 'message': 'Campanha iniciada'})
    
    def connect_whatsapp_web(self):
        """Conecta ao WhatsApp Web com configurações otimizadas"""
        if not SELENIUM_AVAILABLE:
            self.log_system('ERROR', 'Selenium não disponível')
            return False
        
        try:
            # Configurações otimizadas para Windows
            options = Options()
            
            # Configurações básicas
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Configurações de performance
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_argument('--disable-javascript')
            
            # Configurações de compatibilidade
            options.add_argument('--remote-debugging-port=9224')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Sessão persistente
            session_dir = os.path.abspath('./whatsapp_session_pro')
            options.add_argument(f'--user-data-dir={session_dir}')
            
            # Tentativas múltiplas de conexão
            drivers_to_try = [
                self._try_chrome_webdriver_manager,
                self._try_chrome_local,
                self._try_edge_webdriver,
                self._try_firefox_webdriver
            ]
            
            for i, driver_func in enumerate(drivers_to_try, 1):
                try:
                    self.log_system('INFO', f'Tentativa {i}: {driver_func.__name__}')
                    self.driver = driver_func(options)
                    if self.driver:
                        self.log_system('INFO', f'Driver iniciado com sucesso: tentativa {i}')
                        break
                except Exception as e:
                    self.log_system('WARNING', f'Tentativa {i} falhou: {str(e)}')
                    if i == len(drivers_to_try):
                        raise Exception("Todos os drivers falharam")
            
            if not self.driver:
                return False
            
            # Remove detecção de automação
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            # Acessa WhatsApp Web
            self.log_system('INFO', 'Acessando WhatsApp Web...')
            self.driver.get("https://web.whatsapp.com")
            
            # Aguarda carregamento
            time.sleep(5)
            
            # Verifica status inicial
            self.check_whatsapp_status()
            
            return True
            
        except Exception as e:
            self.log_system('ERROR', f'Erro na conexão WhatsApp: {str(e)}')
            if self.driver:
                self.driver.quit()
                self.driver = None
            return False
    
    def _try_chrome_webdriver_manager(self, options):
        """Tenta Chrome com WebDriver Manager"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        except:
            return None
    
    def _try_chrome_local(self, options):
        """Tenta Chrome local do sistema"""
        try:
            # Paths comuns do Chrome no Windows
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    return webdriver.Chrome(options=options)
            return None
        except:
            return None
    
    def _try_edge_webdriver(self, options):
        """Tenta Edge como alternativa"""
        try:
            from selenium.webdriver.edge.options import Options as EdgeOptions
            from selenium.webdriver.edge.service import Service as EdgeService
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            
            edge_options = EdgeOptions()
            # Copia configurações do Chrome
            for arg in options.arguments:
                edge_options.add_argument(arg)
            
            service = EdgeService(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=edge_options)
        except:
            return None
    
    def _try_firefox_webdriver(self, options):
        """Tenta Firefox como último recurso"""
        try:
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from webdriver_manager.firefox import GeckoDriverManager
            
            firefox_options = FirefoxOptions()
            firefox_options.add_argument('--headless')
            
            service = FirefoxService(GeckoDriverManager().install())
            return webdriver.Firefox(service=service, options=firefox_options)
        except:
            return None
    
    def check_whatsapp_status(self):
        """Verifica status detalhado da conexão"""
        if not self.driver:
            self.is_connected = False
            self.connection_status = "disconnected"
            return {'connected': False, 'status': 'disconnected', 'message': 'Driver não iniciado'}
        
        try:
            current_url = self.driver.current_url
            
            if 'web.whatsapp.com' not in current_url:
                self.is_connected = False
                self.connection_status = "disconnected"
                return {'connected': False, 'status': 'disconnected', 'message': 'Não está no WhatsApp Web'}
            
            # Verifica se está na tela de login (QR Code)
            try:
                self.driver.find_element(By.CSS_SELECTOR, "[data-ref] canvas")
                self.is_connected = False
                self.connection_status = "qr_code"
                return {'connected': False, 'status': 'qr_code', 'message': 'Escaneie o QR Code'}
            except NoSuchElementException:
                pass
            
            # Verifica se está logado (lista de chats)
            try:
                chat_list = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='chat-list']")
                self.is_connected = True
                self.connection_status = "connected"
                
                # Tenta obter informações do usuário
                try:
                    self.get_user_info()
                except:
                    pass
                
                return {'connected': True, 'status': 'connected', 'message': 'WhatsApp conectado', 'user_info': self.user_info}
            except NoSuchElementException:
                self.is_connected = False
                self.connection_status = "loading"
                return {'connected': False, 'status': 'loading', 'message': 'Carregando...'}
            
        except Exception as e:
            self.is_connected = False
            self.connection_status = "error"
            return {'connected': False, 'status': 'error', 'message': f'Erro: {str(e)}'}
    
    def get_user_info(self):
        """Obtém informações do usuário logado"""
        try:
            # Clica no avatar do perfil
            avatar = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='avatar-anchor']")
            avatar.click()
            
            time.sleep(2)
            
            # Pega nome do perfil
            try:
                name_element = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='pushname']")
                self.user_info['name'] = name_element.text
            except:
                self.user_info['name'] = 'WhatsApp User'
            
            # Fecha o menu
            self.driver.find_element(By.TAG_NAME, 'body').click()
            
            self.user_info['connected_at'] = datetime.now().strftime('%H:%M:%S')
            
        except Exception as e:
            self.log_system('WARNING', f'Erro ao obter info do usuário: {str(e)}')
    
    def clean_phone(self, phone):
        """Limpa e valida telefone"""
        import re
        if not phone:
            return None
        
        clean = re.sub(r'\D', '', phone)
        
        if len(clean) < 10 or len(clean) > 15:
            return None
        
        # Adiciona código do país
        if len(clean) == 11 and clean.startswith('0'):
            clean = '55' + clean[1:]
        elif len(clean) == 10:
            clean = '55' + clean
        elif len(clean) == 11 and not clean.startswith('55'):
            clean = '55' + clean
        
        return clean
    
    def execute_campaign(self, campaign_id):
        """Executa campanha de disparo em massa"""
        self.sending_active = True
        self.log_system('INFO', f'Iniciando campanha {campaign_id}')
        
        try:
            conn = self.get_db_connection()
            
            # Busca dados da campanha
            campaign = conn.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,)).fetchone()
            if not campaign:
                return
            
            # Busca contatos
            contacts = conn.execute('SELECT * FROM contacts WHERE status = "active"').fetchall()
            
            # Atualiza status da campanha
            conn.execute('UPDATE campaigns SET status = "running", started_at = ? WHERE id = ?', 
                        (datetime.now(), campaign_id))
            conn.commit()
            
            sent_count = 0
            failed_count = 0
            
            for contact in contacts:
                if not self.sending_active or not self.is_connected:
                    break
                
                try:
                    # Personaliza mensagem
                    message = campaign['message'].replace('{{nome}}', contact['name'])
                    message = message.replace('{{empresa}}', contact['company'] or '')
                    
                    # Envia mensagem
                    success = self.send_whatsapp_message(contact['phone'], message)
                    
                    if success:
                        # Salva como enviada
                        conn.execute('''
                            INSERT INTO sent_messages (campaign_id, contact_id, phone, message, status)
                            VALUES (?, ?, ?, ?, 'sent')
                        ''', (campaign_id, contact['id'], contact['phone'], message))
                        
                        # Atualiza contato
                        conn.execute('UPDATE contacts SET last_sent = ?, total_sent = total_sent + 1 WHERE id = ?',
                                   (datetime.now(), contact['id']))
                        
                        sent_count += 1
                        self.log_system('INFO', f'Mensagem enviada para {contact["name"]}')
                    else:
                        conn.execute('''
                            INSERT INTO sent_messages (campaign_id, contact_id, phone, message, status, error_message)
                            VALUES (?, ?, ?, ?, 'failed', 'Erro no envio')
                        ''', (campaign_id, contact['id'], contact['phone'], message))
                        
                        failed_count += 1
                        self.log_system('WARNING', f'Falha ao enviar para {contact["name"]}')
                    
                    conn.commit()
                    
                    # Delay anti-spam
                    time.sleep(3)
                    
                except Exception as e:
                    self.log_system('ERROR', f'Erro ao processar {contact["name"]}: {str(e)}')
                    failed_count += 1
            
            # Finaliza campanha
            conn.execute('''
                UPDATE campaigns 
                SET status = 'completed', sent_count = ?, failed_count = ?, finished_at = ?
                WHERE id = ?
            ''', (sent_count, failed_count, datetime.now(), campaign_id))
            
            conn.commit()
            conn.close()
            
            self.log_system('INFO', f'Campanha finalizada: {sent_count} enviadas, {failed_count} falharam')
            
        except Exception as e:
            self.log_system('ERROR', f'Erro na campanha: {str(e)}')
        finally:
            self.sending_active = False
    
    def send_whatsapp_message(self, phone, message):
        """Envia mensagem individual via WhatsApp Web"""
        try:
            if not self.driver or not self.is_connected:
                return False
            
            # URL para enviar mensagem
            encoded_message = urllib.parse.quote(message)
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
            
            self.driver.get(url)
            time.sleep(4)
            
            # Procura botão de enviar
            try:
                send_button = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='send']"))
                )
                send_button.click()
                time.sleep(2)
                return True
                
            except TimeoutException:
                # Tenta método alternativo
                try:
                    text_box = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='conversation-compose-box-input']")
                    text_box.send_keys(Keys.ENTER)
                    time.sleep(2)
                    return True
                except:
                    return False
                    
        except Exception as e:
            self.log_system('ERROR', f'Erro ao enviar para {phone}: {str(e)}')
            return False
    
    def disconnect_whatsapp_web(self):
        """Desconecta WhatsApp Web"""
        try:
            self.sending_active = False
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.is_connected = False
            self.connection_status = "disconnected"
            self.user_info = {}
            self.log_system('INFO', 'WhatsApp Web desconectado')
        except Exception as e:
            self.log_system('ERROR', f'Erro ao desconectar: {str(e)}')
    
    def run(self, host='127.0.0.1', port=5000):
        """Executa a aplicação"""
        print("🚀 WhatsApp Pro - Sistema Profissional")
        print(f"🌐 Acesse: http://{host}:{port}")
        print("📱 Interface moderna + WhatsApp Web integrado")
        print("💼 Sistema completo de marketing via WhatsApp")
        
        # Abre navegador
        threading.Timer(1.5, lambda: webbrowser.open(f'http://{host}:{port}')).start()
        
        try:
            run_simple(host, port, self.app, use_reloader=False, threaded=True)
        except KeyboardInterrupt:
            print("\n👋 Encerrando WhatsApp Pro...")
            self.disconnect_whatsapp_web()

# TEMPLATES HTML MODERNOS
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Pro - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #25D366;
            --primary-dark: #128C7E;
            --secondary-color: #34495E;
            --dark-bg: #0F1419;
            --darker-bg: #0B0E13;
            --card-bg: #1A1F2E;
            --border-color: #2C3E50;
            --text-primary: #FFFFFF;
            --text-secondary: #B8C5D1;
            --success-color: #27AE60;
            --warning-color: #F39C12;
            --danger-color: #E74C3C;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, var(--dark-bg) 0%, var(--darker-bg) 100%);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .navbar {
            background: rgba(26, 31, 46, 0.95) !important;
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 0;
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
            background: linear-gradient(45deg, var(--primary-color), var(--primary-dark));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            backdrop-filter: blur(20px);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            border-color: var(--primary-color);
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--card-bg) 0%, rgba(26, 31, 46, 0.8) 100%);
            position: relative;
            overflow: hidden;
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(45deg, var(--primary-color), var(--primary-dark));
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(45deg, var(--primary-color), var(--primary-dark));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .btn-whatsapp {
            background: linear-gradient(45deg, var(--primary-color), var(--primary-dark));
            border: none;
            border-radius: 12px;
            padding: 12px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .btn-whatsapp:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 211, 102, 0.3);
        }
        
        .connection-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
        }
        
        .status-connected {
            background: rgba(39, 174, 96, 0.2);
            color: var(--success-color);
            border: 1px solid var(--success-color);
        }
        
        .status-disconnected {
            background: rgba(231, 76, 60, 0.2);
            color: var(--danger-color);
            border: 1px solid var(--danger-color);
        }
        
        .status-qr_code {
            background: rgba(243, 156, 18, 0.2);
            color: var(--warning-color);
            border: 1px solid var(--warning-color);
        }
        
        .sidebar {
            background: var(--card-bg);
            border-right: 1px solid var(--border-color);
            height: calc(100vh - 80px);
            position: fixed;
            width: 250px;
            left: 0;
            top: 80px;
            z-index: 1000;
        }
        
        .sidebar-menu {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .sidebar-menu li a {
            display: block;
            padding: 15px 20px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.3s ease;
            border-left: 3px solid transparent;
        }
        
        .sidebar-menu li a:hover,
        .sidebar-menu li a.active {
            background: rgba(37, 211, 102, 0.1);
            color: var(--primary-color);
            border-left-color: var(--primary-color);
        }
        
        .main-content {
            margin-left: 250px;
            padding: 30px;
        }
        
        .activity-feed {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .activity-item {
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
            transition: background 0.3s ease;
        }
        
        .activity-item:hover {
            background: rgba(37, 211, 102, 0.05);
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .gradient-text {
            background: linear-gradient(45deg, var(--primary-color), var(--primary-dark));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        @media (max-width: 768px) {
            .sidebar {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }
            
            .sidebar.show {
                transform: translateX(0);
            }
            
            .main-content {
                margin-left: 0;
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="#">
                <i class="fab fa-whatsapp me-2"></i>WhatsApp Pro
            </a>
            
            <div class="d-flex align-items-center">
                <div class="connection-status status-{{ connection_status }} me-3">
                    {% if connection_status == 'connected' %}
                        <i class="fas fa-check-circle"></i>
                        Conectado{% if user_info.name %} - {{ user_info.name }}{% endif %}
                    {% elif connection_status == 'qr_code' %}
                        <i class="fas fa-qrcode pulse"></i>
                        Aguardando QR Code
                    {% elif connection_status == 'loading' %}
                        <i class="fas fa-spinner fa-spin"></i>
                        Carregando...
                    {% else %}
                        <i class="fas fa-times-circle"></i>
                        Desconectado
                    {% endif %}
                </div>
                
                {% if sending_active %}
                <span class="badge bg-warning me-3">
                    <i class="fas fa-paper-plane fa-spin"></i>
                    Enviando...
                </span>
                {% endif %}
                
                <button class="btn btn-outline-light btn-sm d-md-none" onclick="toggleSidebar()">
                    <i class="fas fa-bars"></i>
                </button>
            </div>
        </div>
    </nav>
    
    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
        <ul class="sidebar-menu">
            <li><a href="/" class="active"><i class="fas fa-home me-2"></i>Dashboard</a></li>
            <li><a href="/contacts"><i class="fas fa-users me-2"></i>Contatos</a></li>
            <li><a href="/campaigns"><i class="fas fa-bullhorn me-2"></i>Campanhas</a></li>
            <li><a href="/templates"><i class="fas fa-file-text me-2"></i>Templates</a></li>
            <li><a href="/analytics"><i class="fas fa-chart-line me-2"></i>Analytics</a></li>
            <li><a href="/settings"><i class="fas fa-cog me-2"></i>Configurações</a></li>
        </ul>
    </div>
    
    <!-- Main Content -->
    <div class="main-content">
        <!-- Stats Cards -->
        <div class="row mb-4">
            <div class="col-md-3 col-sm-6 mb-3">
                <div class="card stat-card">
                    <div class="card-body text-center">
                        <i class="fas fa-users fa-2x text-primary mb-3"></i>
                        <div class="stat-number">{{ stats.total_contacts }}</div>
                        <div class="text-muted">Total de Contatos</div>
                        <small class="text-success">{{ stats.active_contacts }} ativos</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 col-sm-6 mb-3">
                <div class="card stat-card">
                    <div class="card-body text-center">
                        <i class="fas fa-paper-plane fa-2x gradient-text mb-3"></i>
                        <div class="stat-number">{{ stats.sent_today }}</div>
                        <div class="text-muted">Enviadas Hoje</div>
                        <small class="text-info">{{ stats.sent_this_week }} esta semana</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 col-sm-6 mb-3">
                <div class="card stat-card">
                    <div class="card-body text-center">
                        <i class="fas fa-bullhorn fa-2x text-warning mb-3"></i>
                        <div class="stat-number">{{ stats.total_campaigns }}</div>
                        <div class="text-muted">Campanhas Criadas</div>
                        <small class="text-warning">{{ stats.active_campaigns }} ativas</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 col-sm-6 mb-3">
                <div class="card stat-card">
                    <div class="card-body text-center">
                        <i class="fas fa-chart-line fa-2x text-success mb-3"></i>
                        <div class="stat-number">{{ stats.total_sent }}</div>
                        <div class="text-muted">Total Enviadas</div>
                        <small class="text-success">Todas as mensagens</small>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- WhatsApp Connection Panel -->
        <div class="row mb-4">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fab fa-whatsapp text-success me-2"></i>
                            Conexão WhatsApp Web
                        </h5>
                    </div>
                    <div class="card-body">
                        <div id="connectionPanel">
                            {% if connection_status == 'connected' %}
                                <div class="alert alert-success d-flex align-items-center">
                                    <i class="fas fa-check-circle fa-2x me-3"></i>
                                    <div>
                                        <h6 class="mb-1">WhatsApp Web Conectado!</h6>
                                        <small>{{ user_info.name or 'Usuário conectado' }}{% if user_info.connected_at %} • Conectado às {{ user_info.connected_at }}{% endif %}</small>
                                    </div>
                                </div>
                                
                                <div class="d-flex gap-3">
                                    <button class="btn btn-danger" onclick="disconnectWhatsApp()">
                                        <i class="fas fa-sign-out-alt me-2"></i>Desconectar
                                    </button>
                                    
                                    <button class="btn btn-success" onclick="window.location.href='/campaigns'">
                                        <i class="fas fa-rocket me-2"></i>Criar Campanha
                                    </button>
                                </div>
                                
                            {% elif connection_status == 'qr_code' %}
                                <div class="alert alert-warning d-flex align-items-center">
                                    <i class="fas fa-qrcode fa-2x me-3 pulse"></i>
                                    <div>
                                        <h6 class="mb-1">Aguardando Login</h6>
                                        <small>Escaneie o QR Code que aparece na janela do navegador com seu WhatsApp</small>
                                    </div>
                                </div>
                                
                            {% elif connection_status == 'loading' %}
                                <div class="alert alert-info d-flex align-items-center">
                                    <i class="fas fa-spinner fa-spin fa-2x me-3"></i>
                                    <div>
                                        <h6 class="mb-1">Carregando WhatsApp Web...</h6>
                                        <small>Aguarde enquanto inicializamos a conexão</small>
                                    </div>
                                </div>
                                
                            {% else %}
                                <div class="alert alert-secondary d-flex align-items-center">
                                    <i class="fas fa-unlink fa-2x me-3"></i>
                                    <div>
                                        <h6 class="mb-1">WhatsApp Web Desconectado</h6>
                                        <small>Clique no botão abaixo para conectar ao seu WhatsApp</small>
                                    </div>
                                </div>
                                
                                <button class="btn btn-whatsapp btn-lg" onclick="connectWhatsApp()">
                                    <i class="fab fa-whatsapp me-2"></i>
                                    Conectar WhatsApp Web
                                </button>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-lg-4">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-tachometer-alt me-2"></i>
                            Status do Sistema
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between mb-2">
                            <span>WhatsApp Web</span>
                            <span class="badge {% if connection_status == 'connected' %}bg-success{% else %}bg-secondary{% endif %}">
                                {% if connection_status == 'connected' %}Online{% else %}Offline{% endif %}
                            </span>
                        </div>
                        
                        <div class="d-flex justify-content-between mb-2">
                            <span>Envio em Massa</span>
                            <span class="badge {% if sending_active %}bg-warning{% else %}bg-success{% endif %}">
                                {% if sending_active %}Ativo{% else %}Pronto{% endif %}
                            </span>
                        </div>
                        
                        <div class="d-flex justify-content-between mb-2">
                            <span>Database</span>
                            <span class="badge bg-success">Ativo</span>
                        </div>
                        
                        <hr>
                        
                        <button class="btn btn-outline-primary btn-sm w-100" onclick="refreshStatus()">
                            <i class="fas fa-sync me-2"></i>Atualizar Status
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Recent Activity -->
        <div class="row">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="fas fa-bullhorn me-2"></i>
                            Campanhas Recentes
                        </h6>
                        <a href="/campaigns" class="btn btn-outline-primary btn-sm">Ver Todas</a>
                    </div>
                    <div class="card-body">
                        {% if recent_campaigns %}
                            {% for campaign in recent_campaigns %}
                            <div class="activity-item">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="mb-1">{{ campaign.name }}</h6>
                                        <small class="text-muted">
                                            {{ campaign.sent_count or 0 }} enviadas • 
                                            {{ campaign.created_at[:10] }}
                                        </small>
                                    </div>
                                    <span class="badge 
                                        {% if campaign.status == 'completed' %}bg-success
                                        {% elif campaign.status == 'running' %}bg-warning
                                        {% else %}bg-secondary{% endif %}">
                                        {{ campaign.status }}
                                    </span>
                                </div>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="text-center text-muted py-4">
                                <i class="fas fa-bullhorn fa-2x mb-2"></i>
                                <p>Nenhuma campanha criada ainda</p>
                                <a href="/campaigns" class="btn btn-primary btn-sm">
                                    <i class="fas fa-plus me-2"></i>Criar Campanha
                                </a>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-history me-2"></i>
                            Atividade Recente
                        </h6>
                    </div>
                    <div class="card-body activity-feed">
                        {% if recent_logs %}
                            {% for log in recent_logs %}
                            <div class="activity-item">
                                <div class="d-flex align-items-center">
                                    <i class="fas 
                                        {% if log.level == 'INFO' %}fa-info-circle text-info
                                        {% elif log.level == 'WARNING' %}fa-exclamation-triangle text-warning
                                        {% elif log.level == 'ERROR' %}fa-times-circle text-danger
                                        {% else %}fa-circle text-muted{% endif %} me-2">
                                    </i>
                                    <div class="flex-grow-1">
                                        <div class="text-sm">{{ log.message }}</div>
                                        <small class="text-muted">{{ log.timestamp[:19] }}</small>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="text-center text-muted py-4">
                                <i class="fas fa-history fa-2x mb-2"></i>
                                <p>Nenhuma atividade registrada</p>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Conectar WhatsApp
        async function connectWhatsApp() {
            const btn = event.target;
            const originalText = btn.innerHTML;
            
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Conectando...';
            
            try {
                const response = await fetch('/connect_whatsapp', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    showAlert('success', result.message);
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showAlert('error', result.message);
                }
            } catch (error) {
                showAlert('error', 'Erro na conexão: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }
        
        // Desconectar WhatsApp
        async function disconnectWhatsApp() {
            if (!confirm('Desconectar do WhatsApp Web?')) return;
            
            try {
                const response = await fetch('/disconnect_whatsapp', { method: 'POST' });
                const result = await response.json();
                
                showAlert('success', result.message);
                setTimeout(() => location.reload(), 1000);
            } catch (error) {
                showAlert('error', 'Erro ao desconectar: ' + error.message);
            }
        }
        
        // Atualizar status
        async function refreshStatus() {
            try {
                const response = await fetch('/whatsapp_status');
                const status = await response.json();
                location.reload(); // Recarrega para atualizar interface
            } catch (error) {
                showAlert('error', 'Erro ao atualizar status');
            }
        }
        
        // Mostrar alertas
        function showAlert(type, message) {
            const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
            const alert = `
                <div class="alert ${alertClass} alert-dismissible fade show position-fixed" 
                     style="top: 100px; right: 20px; z-index: 9999; max-width: 400px;">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', alert);
            
            // Remove após 5 segundos
            setTimeout(() => {
                const alertEl = document.querySelector('.alert');
                if (alertEl) alertEl.remove();
            }, 5000);
        }
        
        // Toggle sidebar no mobile
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('show');
        }
        
        // Verificar status automaticamente
        setInterval(async () => {
            try {
                const response = await fetch('/whatsapp_status');
                const status = await response.json();
                
                // Atualiza status na interface se mudou
                const currentStatus = '{{ connection_status }}';
                if (status.status !== currentStatus) {
                    location.reload();
                }
            } catch (error) {
                // Ignora erros de rede
            }
        }, 15000);
        
        // Efeitos de carregamento
        document.addEventListener('DOMContentLoaded', function() {
            // Anima cards ao carregar
            const cards = document.querySelectorAll('.card');
            cards.forEach((card, index) => {
                card.style.animationDelay = `${index * 0.1}s`;
                card.classList.add('animate__animated', 'animate__fadeInUp');
            });
        });
    </script>
</body>
</html>
'''

# Adicionar outros templates...
CONTACTS_TEMPLATE = '''<h1>Contatos em desenvolvimento...</h1>'''
CAMPAIGNS_TEMPLATE = '''<h1>Campanhas em desenvolvimento...</h1>'''
TEMPLATES_TEMPLATE = '''<h1>Templates em desenvolvimento...</h1>'''

if __name__ == '__main__':
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium não disponível!")
        print("Execute: pip install selenium webdriver-manager")
        input("Pressione Enter para sair...")
        sys.exit(1)
    
    app = WhatsAppPro()
    app.run()