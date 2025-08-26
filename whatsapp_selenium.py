import os
import time
import json
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import qrcode
from io import BytesIO
import base64
from app import db
from models import Campaign, CampaignContact, ActivityLog, WhatsAppConnection

class WhatsAppSeleniumService:
    """
    WhatsApp Web automation service using Selenium
    """
    
    def __init__(self):
        self.driver = None
        self.is_connected = False
        self.session_file = 'whatsapp_session.json'
        self.logger = logging.getLogger(__name__)
        self.qr_code_data = None
        
    def start_browser(self):
        """Initialize and start the browser"""
        try:
            # Configure Firefox options
            options = Options()
            options.add_argument('--headless')  # Run in background
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--width=1920')
            options.add_argument('--height=1080')
            
            # Disable notifications and media autoplay
            options.set_preference("dom.webnotifications.enabled", False)
            options.set_preference("media.autoplay.default", 2)
            options.set_preference("dom.disable_beforeunload", True)
            
            # Use system geckodriver
            service = Service()
            
            # Start Firefox
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.implicitly_wait(10)
            
            self.logger.info("Browser started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            return False
    
    def connect_to_whatsapp(self):
        """Connect to WhatsApp Web"""
        try:
            if not self.driver:
                if not self.start_browser():
                    return {'success': False, 'message': 'Falha ao iniciar navegador'}
            
            # Navigate to WhatsApp Web
            self.driver.get('https://web.whatsapp.com')
            
            # Wait for page to load
            time.sleep(5)
            
            # Check if already logged in
            if self.is_logged_in():
                self.is_connected = True
                self.logger.info("Already logged in to WhatsApp Web")
                return {
                    'success': True,
                    'status': 'connected',
                    'message': 'Conectado ao WhatsApp Web'
                }
            
            # Look for QR code
            qr_code = self.get_qr_code()
            if qr_code:
                return {
                    'success': True,
                    'status': 'qr_code',
                    'qr_code': qr_code,
                    'message': 'Escaneie o código QR com seu celular'
                }
            
            # Wait for login
            return self.wait_for_login()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to WhatsApp: {e}")
            return {
                'success': False,
                'message': f'Erro ao conectar: {str(e)}'
            }
    
    def is_logged_in(self):
        """Check if user is logged in to WhatsApp Web"""
        try:
            # Look for main chat interface elements
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]'))
            )
            return True
        except TimeoutException:
            return False
    
    def get_qr_code(self):
        """Get QR code for login"""
        try:
            # Try different QR code selectors
            qr_selectors = [
                '[data-testid="qr-code"]',
                'canvas[aria-label*="qr"]',
                '.qr-code',
                'canvas'
            ]
            
            qr_element = None
            for selector in qr_selectors:
                try:
                    qr_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"Found QR code with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not qr_element:
                self.logger.warning("QR code element not found with any selector")
                return None
            
            # Get QR code image
            qr_image = qr_element.screenshot_as_png
            qr_base64 = base64.b64encode(qr_image).decode('utf-8')
            
            self.qr_code_data = qr_base64
            return qr_base64
            
        except Exception as e:
            self.logger.error(f"Error getting QR code: {e}")
            return None
    
    def wait_for_login(self):
        """Wait for user to scan QR code and login"""
        try:
            # Wait up to 120 seconds for login
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]'))
            )
            
            self.is_connected = True
            self.logger.info("Successfully logged in to WhatsApp Web")
            
            # Save session info
            self.save_session()
            
            return {
                'success': True,
                'status': 'connected',
                'message': 'Conectado com sucesso ao WhatsApp Web!'
            }
            
        except TimeoutException:
            return {
                'success': False,
                'status': 'timeout',
                'message': 'Tempo limite para fazer login. Tente novamente.'
            }
    
    def save_session(self):
        """Save session data"""
        try:
            session_data = {
                'connected': True,
                'timestamp': datetime.utcnow().isoformat(),
                'user_agent': self.driver.execute_script("return navigator.userAgent;")
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
                
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    def load_session(self):
        """Load saved session data"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Failed to load session: {e}")
            return None
    
    def check_connection(self):
        """Check current connection status"""
        try:
            if not self.driver:
                return {
                    'status': 'disconnected',
                    'message': 'Navegador não iniciado'
                }
            
            # Check if still on WhatsApp Web and logged in
            current_url = self.driver.current_url
            if 'web.whatsapp.com' not in current_url:
                self.is_connected = False
                return {
                    'status': 'disconnected',
                    'message': 'Não está no WhatsApp Web'
                }
            
            if self.is_logged_in():
                self.is_connected = True
                
                # Try to get phone number from profile
                phone_number = self.get_phone_number()
                profile_name = self.get_profile_name()
                
                return {
                    'status': 'connected',
                    'phone_number': phone_number,
                    'profile_name': profile_name,
                    'last_seen': datetime.utcnow().isoformat()
                }
            else:
                self.is_connected = False
                return {
                    'status': 'disconnected',
                    'message': 'Não está logado no WhatsApp Web'
                }
                
        except Exception as e:
            self.logger.error(f"Error checking connection: {e}")
            self.is_connected = False
            return {
                'status': 'error',
                'message': f'Erro ao verificar conexão: {str(e)}'
            }
    
    def get_phone_number(self):
        """Get phone number from profile"""
        try:
            # Click on profile area
            profile_button = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="menu"]')
            profile_button.click()
            time.sleep(1)
            
            # Click on profile option
            profile_option = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="menu-profile"]')
            profile_option.click()
            time.sleep(2)
            
            # Get phone number
            phone_element = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="phone-number"]')
            phone_number = phone_element.text
            
            # Close profile
            close_button = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="drawer-left-close"]')
            close_button.click()
            
            return phone_number
            
        except Exception as e:
            self.logger.error(f"Error getting phone number: {e}")
            return None
    
    def get_profile_name(self):
        """Get profile name"""
        try:
            name_element = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="default-user"] span[title]')
            return name_element.get_attribute('title')
        except Exception as e:
            self.logger.error(f"Error getting profile name: {e}")
            return None
    
    def send_message(self, phone, message):
        """Send a message to a specific phone number"""
        try:
            if not self.is_connected:
                return {
                    'success': False,
                    'error': 'WhatsApp não está conectado'
                }
            
            # Format phone number for WhatsApp Web URL
            clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            # Navigate to chat
            chat_url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            self.driver.get(chat_url)
            time.sleep(3)
            
            # Wait for message input to appear
            message_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="message-composer"]'))
            )
            
            # Type message
            message_input.clear()
            message_input.send_keys(message)
            
            # Send message
            send_button = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="send"]')
            send_button.click()
            
            # Wait for message to be sent
            time.sleep(2)
            
            self.logger.info(f"Message sent to {phone}")
            return {
                'success': True,
                'message_id': f"msg_{int(time.time())}",
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except TimeoutException:
            error_msg = f"Timeout ao enviar mensagem para {phone}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Erro ao enviar mensagem para {phone}: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def start_campaign(self, campaign):
        """Start a message campaign"""
        try:
            if not self.is_connected:
                # Try to reconnect
                connection_result = self.connect_to_whatsapp()
                if not connection_result.get('success') or connection_result.get('status') != 'connected':
                    return {
                        'success': False,
                        'message': 'WhatsApp não está conectado'
                    }
            
            # Update campaign status
            campaign.status = 'running'
            campaign.started_at = datetime.utcnow()
            db.session.commit()
            
            # Get template content
            template = campaign.template
            
            # Process each contact in the campaign
            campaign_contacts = CampaignContact.query.filter_by(campaign_id=campaign.id).all()
            
            sent_count = 0
            failed_count = 0
            
            for campaign_contact in campaign_contacts:
                contact = campaign_contact.contact
                
                # Personalize message
                message = self.personalize_message(template.content, contact)
                
                # Send message
                result = self.send_message(contact.phone, message)
                
                if result['success']:
                    campaign_contact.status = 'sent'
                    campaign_contact.sent_at = datetime.utcnow()
                    sent_count += 1
                else:
                    campaign_contact.status = 'failed'
                    campaign_contact.error_message = result.get('error', 'Erro desconhecido')
                    failed_count += 1
                
                db.session.commit()
                
                # Delay between messages to avoid being blocked
                time.sleep(5)  # 5 seconds between messages
            
            # Update campaign final status
            campaign.status = 'completed'
            campaign.completed_at = datetime.utcnow()
            campaign.sent_count = sent_count
            campaign.failed_count = failed_count
            db.session.commit()
            
            # Log campaign completion
            self.log_activity('campaign_completed', 
                            f'Campanha {campaign.name} finalizada: {sent_count} enviadas, {failed_count} falharam')
            
            return {
                'success': True,
                'message': f'Campanha concluída: {sent_count} mensagens enviadas, {failed_count} falharam'
            }
            
        except Exception as e:
            # Update campaign status to failed
            campaign.status = 'failed'
            db.session.commit()
            
            error_msg = f"Erro ao executar campanha: {str(e)}"
            self.logger.error(error_msg)
            self.log_activity('campaign_failed', 
                            f'Campanha {campaign.name} falhou: {str(e)}', 'error')
            
            return {
                'success': False,
                'message': error_msg
            }
    
    def personalize_message(self, template_content, contact):
        """Replace template variables with contact data"""
        message = template_content
        
        # Replace common variables
        replacements = {
            '{{nome}}': contact.name,
            '{{telefone}}': contact.phone,
            '{{email}}': contact.email or '',
            '{{empresa}}': contact.company or '',
        }
        
        for variable, value in replacements.items():
            message = message.replace(variable, value)
        
        return message
    
    def log_activity(self, action, details, status='success'):
        """Log activity to database"""
        try:
            log = ActivityLog(
                action=action,
                details=details,
                status=status
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Failed to log activity: {e}")
    
    def close(self):
        """Close the browser and cleanup"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.is_connected = False
            self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
    
    def __del__(self):
        """Destructor to ensure browser is closed"""
        self.close()