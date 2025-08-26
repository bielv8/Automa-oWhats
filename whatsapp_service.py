import random
import time
from datetime import datetime
from app import db
from models import Campaign, CampaignContact, ActivityLog
import logging

class WhatsAppService:
    """
    WhatsApp Web automation service
    This is a simulation layer for development and demonstration purposes
    """
    
    def __init__(self):
        self.is_connected = False
        self.session_data = None
        self.logger = logging.getLogger(__name__)
    
    def check_connection(self):
        """
        Check WhatsApp Web connection status
        In production, this would interface with actual WhatsApp Web automation
        """
        # Simulate connection check
        if random.random() > 0.3:  # 70% chance of being connected
            self.is_connected = True
            return {
                'status': 'connected',
                'phone_number': '+55 11 99999-9999',
                'profile_name': 'Empresa Demo',
                'last_seen': datetime.utcnow().isoformat()
            }
        else:
            self.is_connected = False
            return {
                'status': 'disconnected',
                'message': 'WhatsApp Web não está conectado'
            }
    
    def send_message(self, phone, message):
        """
        Send a message to a specific phone number
        In production, this would send actual WhatsApp messages
        """
        if not self.is_connected:
            return {
                'success': False,
                'error': 'WhatsApp não está conectado'
            }
        
        # Simulate message sending with some delay and random success/failure
        time.sleep(random.uniform(0.5, 2.0))  # Simulate network delay
        
        if random.random() > 0.1:  # 90% success rate
            self.logger.info(f"Message sent to {phone}: {message[:50]}...")
            return {
                'success': True,
                'message_id': f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            error_messages = [
                'Número não encontrado',
                'Falha na conexão',
                'Rate limit atingido',
                'Número bloqueado'
            ]
            error = random.choice(error_messages)
            self.logger.error(f"Failed to send message to {phone}: {error}")
            return {
                'success': False,
                'error': error
            }
    
    def start_campaign(self, campaign):
        """
        Start a message campaign
        In production, this would handle bulk message sending with proper queuing
        """
        try:
            # Check connection first
            connection_status = self.check_connection()
            if connection_status['status'] != 'connected':
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
                
                # Personalize message (replace variables)
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
                
                # Add small delay between messages to avoid being blocked
                time.sleep(random.uniform(1, 3))
            
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
            
            self.logger.error(f"Campaign failed: {e}")
            self.log_activity('campaign_failed', 
                            f'Campanha {campaign.name} falhou: {str(e)}', 'error')
            
            return {
                'success': False,
                'message': f'Erro ao executar campanha: {str(e)}'
            }
    
    def personalize_message(self, template_content, contact):
        """
        Replace template variables with contact data
        """
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
        log = ActivityLog(
            action=action,
            details=details,
            status=status
        )
        db.session.add(log)
        db.session.commit()
