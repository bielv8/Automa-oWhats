import os
import time
import logging
import random
import base64
import qrcode
from io import BytesIO
from datetime import datetime
from app import db
from models import Campaign, CampaignContact, ActivityLog

class WhatsAppMockService:
    """
    Mock WhatsApp Web service for demonstration
    This simulates the real WhatsApp Web integration with realistic QR code generation
    """
    
    def __init__(self):
        self.is_connected = False
        self.qr_code_data = None
        self.logger = logging.getLogger(__name__)
        self.session_data = None
        
    def connect_to_whatsapp(self):
        """Simulate WhatsApp Web connection with QR code"""
        try:
            # Generate a realistic QR code
            qr_data = self.generate_qr_code()
            self.qr_code_data = qr_data
            
            return {
                'success': True,
                'status': 'qr_code',
                'qr_code': qr_data,
                'message': 'Escaneie o código QR com seu WhatsApp'
            }
            
        except Exception as e:
            self.logger.error(f"Error generating QR code: {e}")
            return {
                'success': False,
                'message': f'Erro ao gerar QR Code: {str(e)}'
            }
    
    def generate_qr_code(self):
        """Generate a realistic QR code for WhatsApp Web"""
        try:
            # Create QR code with WhatsApp Web-like data
            whatsapp_data = f"1@{random.randint(1000000000, 9999999999)},{random.randint(10000, 99999)},{int(time.time())}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(whatsapp_data)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return img_str
            
        except Exception as e:
            self.logger.error(f"Error generating QR code: {e}")
            return None
    
    def check_connection(self):
        """Check connection status with realistic simulation"""
        try:
            # Simulate random connection after QR code
            if self.qr_code_data and not self.is_connected:
                # 20% chance of connecting each check (simulates user scanning QR)
                if random.random() < 0.2:
                    self.is_connected = True
                    self.session_data = {
                        'phone_number': '+55 11 99999-9999',
                        'profile_name': 'Usuario Demo',
                        'connected_at': datetime.utcnow().isoformat()
                    }
                    
                    # Log connection
                    self.log_activity('whatsapp_connected', 'WhatsApp Web conectado via QR Code')
                    
                    return {
                        'status': 'connected',
                        'phone_number': self.session_data['phone_number'],
                        'profile_name': self.session_data['profile_name'],
                        'last_seen': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'status': 'connecting',
                        'message': 'Aguardando escaneamento do QR Code'
                    }
            
            # If already connected
            if self.is_connected and self.session_data:
                # 95% chance of staying connected
                if random.random() < 0.95:
                    return {
                        'status': 'connected',
                        'phone_number': self.session_data['phone_number'],
                        'profile_name': self.session_data['profile_name'],
                        'last_seen': datetime.utcnow().isoformat()
                    }
                else:
                    # Simulate disconnection
                    self.is_connected = False
                    self.session_data = None
                    return {
                        'status': 'disconnected',
                        'message': 'Conexão perdida'
                    }
            
            # Default state
            return {
                'status': 'disconnected',
                'message': 'WhatsApp Web não está conectado'
            }
            
        except Exception as e:
            self.logger.error(f"Error checking connection: {e}")
            return {
                'status': 'error',
                'message': f'Erro ao verificar conexão: {str(e)}'
            }
    
    def send_message(self, phone, message):
        """Simulate sending a message"""
        try:
            if not self.is_connected:
                return {
                    'success': False,
                    'error': 'WhatsApp não está conectado'
                }
            
            # Simulate network delay
            time.sleep(random.uniform(0.5, 2.0))
            
            # 90% success rate
            if random.random() < 0.9:
                return {
                    'success': True,
                    'message_id': f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                errors = [
                    'Número não encontrado',
                    'Falha na conexão',
                    'Mensagem muito longa',
                    'Rate limit atingido'
                ]
                return {
                    'success': False,
                    'error': random.choice(errors)
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
                    'message': 'WhatsApp não está conectado'
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
                message = message.replace('{{telefone}}', contact.phone)
                message = message.replace('{{email}}', contact.email or '')
                message = message.replace('{{empresa}}', contact.company or '')
                
                # Send message
                result = self.send_message(contact.phone, message)
                
                if result['success']:
                    campaign_contact.status = 'sent'
                    campaign_contact.sent_at = datetime.utcnow()
                    sent_count += 1
                    self.logger.info(f"Message sent to {contact.phone}")
                else:
                    campaign_contact.status = 'failed'
                    campaign_contact.error_message = result.get('error', 'Erro desconhecido')
                    failed_count += 1
                    self.logger.error(f"Failed to send message to {contact.phone}: {result.get('error')}")
                
                db.session.commit()
                
                # Delay between messages
                time.sleep(random.uniform(1, 3))
            
            # Update campaign
            campaign.status = 'completed'
            campaign.completed_at = datetime.utcnow()
            campaign.sent_count = sent_count
            campaign.failed_count = failed_count
            db.session.commit()
            
            # Log completion
            self.log_activity('campaign_completed', 
                            f'Campanha {campaign.name} finalizada: {sent_count} enviadas, {failed_count} falharam')
            
            return {
                'success': True,
                'message': f'Campanha concluída: {sent_count} mensagens enviadas, {failed_count} falharam'
            }
            
        except Exception as e:
            campaign.status = 'failed'
            db.session.commit()
            
            error_msg = f'Erro na campanha: {str(e)}'
            self.logger.error(error_msg)
            self.log_activity('campaign_failed', f'Campanha {campaign.name} falhou: {str(e)}', 'error')
            
            return {
                'success': False,
                'message': error_msg
            }
    
    def close(self):
        """Disconnect from WhatsApp Web"""
        try:
            self.is_connected = False
            self.session_data = None
            self.qr_code_data = None
            self.log_activity('whatsapp_disconnected', 'WhatsApp Web desconectado')
            self.logger.info("WhatsApp disconnected")
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")
    
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