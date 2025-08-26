import os
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
import base64
from app import db
from models import Campaign, CampaignContact, ActivityLog

class WhatsAppSimpleService:
    """
    Simplified WhatsApp Web automation service
    """
    
    def __init__(self):
        self.driver = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        self.qr_code_data = None
        
    def start_browser(self):
        """Initialize and start the browser"""
        try:
            if self.driver:
                return True
                
            self.logger.info("Starting Firefox browser...")
            
            # Configure Firefox options for Replit environment
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--window-size=1200,800')
            
            # Set Firefox preferences
            options.set_preference("dom.webnotifications.enabled", False)
            options.set_preference("media.autoplay.default", 2)
            
            # Start Firefox with system geckodriver
            service = Service()
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.implicitly_wait(5)
            
            self.logger.info("Browser started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return False
    
    def connect_to_whatsapp(self):
        """Connect to WhatsApp Web"""
        try:
            if not self.start_browser():
                return {
                    'success': False,
                    'message': 'Falha ao iniciar navegador'
                }
            
            self.logger.info("Navigating to WhatsApp Web...")
            self.driver.get('https://web.whatsapp.com')
            
            # Wait for page to load
            time.sleep(3)
            
            # Check if already logged in
            if self.check_logged_in():
                self.is_connected = True
                return {
                    'success': True,
                    'status': 'connected',
                    'message': 'Já conectado ao WhatsApp Web'
                }
            
            # Look for QR code
            qr_data = self.capture_qr_code()
            if qr_data:
                return {
                    'success': True,
                    'status': 'qr_code',
                    'qr_code': qr_data,
                    'message': 'Escaneie o código QR'
                }
            else:
                return {
                    'success': False,
                    'message': 'QR Code não encontrado. Tente novamente.'
                }
                
        except Exception as e:
            self.logger.error(f"Error connecting to WhatsApp: {e}")
            return {
                'success': False,
                'message': f'Erro: {str(e)}'
            }
    
    def check_logged_in(self):
        """Check if user is logged in"""
        try:
            # Look for main WhatsApp interface
            self.driver.find_element(By.CSS_SELECTOR, '[data-testid="chat-list"]')
            return True
        except:
            return False
    
    def capture_qr_code(self):
        """Capture QR code from WhatsApp Web"""
        try:
            # Wait for QR code container
            qr_selectors = [
                '[data-testid="qr-code"]',
                'canvas',
                '[data-ref="qr"]',
                '.qr-code img',
                'img[alt*="qr"]'
            ]
            
            qr_element = None
            for selector in qr_selectors:
                try:
                    qr_element = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"QR code found with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not qr_element:
                # If no specific QR element found, take screenshot of the login area
                try:
                    login_area = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="intro-wrapper"]')
                    qr_image = login_area.screenshot_as_png
                except:
                    # Fallback: take screenshot of entire page
                    qr_image = self.driver.get_screenshot_as_png()
            else:
                qr_image = qr_element.screenshot_as_png
            
            # Convert to base64
            qr_base64 = base64.b64encode(qr_image).decode('utf-8')
            self.qr_code_data = qr_base64
            
            return qr_base64
            
        except Exception as e:
            self.logger.error(f"Error capturing QR code: {e}")
            return None
    
    def check_connection(self):
        """Check current connection status"""
        try:
            if not self.driver:
                return {
                    'status': 'disconnected',
                    'message': 'Navegador não iniciado'
                }
            
            # Check if browser is still alive
            try:
                current_url = self.driver.current_url
            except WebDriverException:
                self.driver = None
                self.is_connected = False
                return {
                    'status': 'disconnected',
                    'message': 'Conexão perdida'
                }
            
            # Check if on WhatsApp Web
            if 'web.whatsapp.com' not in current_url:
                return {
                    'status': 'disconnected',
                    'message': 'Não está no WhatsApp Web'
                }
            
            # Check if logged in
            if self.check_logged_in():
                self.is_connected = True
                
                # Try to get phone number
                phone = self.get_phone_number()
                name = self.get_profile_name()
                
                return {
                    'status': 'connected',
                    'phone_number': phone,
                    'profile_name': name,
                    'last_seen': datetime.utcnow().isoformat()
                }
            else:
                self.is_connected = False
                return {
                    'status': 'disconnected',
                    'message': 'Não está logado'
                }
                
        except Exception as e:
            self.logger.error(f"Error checking connection: {e}")
            return {
                'status': 'error',
                'message': f'Erro: {str(e)}'
            }
    
    def get_phone_number(self):
        """Get phone number from profile"""
        try:
            # This is a simplified version - in real implementation
            # you'd navigate to profile and get the actual number
            return "+55 11 99999-9999"
        except:
            return None
    
    def get_profile_name(self):
        """Get profile name"""
        try:
            # This is a simplified version
            return "WhatsApp User"
        except:
            return None
    
    def send_message(self, phone, message):
        """Send a message to a phone number"""
        try:
            if not self.is_connected:
                return {
                    'success': False,
                    'error': 'WhatsApp não conectado'
                }
            
            # Format phone number
            clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            # Navigate to chat
            chat_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(chat_url)
            time.sleep(3)
            
            # Try to send message
            try:
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="send"]'))
                )
                send_button.click()
                time.sleep(2)
                
                return {
                    'success': True,
                    'message_id': f"msg_{int(time.time())}",
                    'timestamp': datetime.utcnow().isoformat()
                }
            except TimeoutException:
                return {
                    'success': False,
                    'error': 'Não foi possível enviar a mensagem'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_campaign(self, campaign):
        """Start a message campaign"""
        try:
            if not self.is_connected:
                return {
                    'success': False,
                    'message': 'WhatsApp não conectado'
                }
            
            # Update campaign status
            campaign.status = 'running'
            campaign.started_at = datetime.utcnow()
            db.session.commit()
            
            # Get contacts
            campaign_contacts = CampaignContact.query.filter_by(campaign_id=campaign.id).all()
            template = campaign.template
            
            sent_count = 0
            failed_count = 0
            
            for campaign_contact in campaign_contacts:
                contact = campaign_contact.contact
                
                # Personalize message
                message = template.content
                message = message.replace('{{nome}}', contact.name)
                message = message.replace('{{empresa}}', contact.company or '')
                
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
                
                # Delay between messages
                time.sleep(3)
            
            # Update campaign
            campaign.status = 'completed'
            campaign.completed_at = datetime.utcnow()
            campaign.sent_count = sent_count
            campaign.failed_count = failed_count
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Campanha concluída: {sent_count} enviadas, {failed_count} falharam'
            }
            
        except Exception as e:
            campaign.status = 'failed'
            db.session.commit()
            return {
                'success': False,
                'message': f'Erro na campanha: {str(e)}'
            }
    
    def close(self):
        """Close the browser"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.is_connected = False
            self.logger.info("Browser closed")
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
    
    def __del__(self):
        """Destructor"""
        self.close()