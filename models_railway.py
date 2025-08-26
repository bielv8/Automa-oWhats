from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    company = db.Column(db.String(100))
    tags = db.Column(db.Text)  # JSON string for tags
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Contact {self.name}>'

class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    variables = db.Column(db.Text)  # JSON string for variable definitions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MessageTemplate {self.name}>'

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('message_template.id'), nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, scheduled, running, completed, failed
    total_contacts = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    scheduled_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    template = db.relationship('MessageTemplate', backref=db.backref('campaigns', lazy=True))

    def __repr__(self):
        return f'<Campaign {self.name}>'

class CampaignContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

    campaign = db.relationship('Campaign', backref=db.backref('campaign_contacts', lazy=True))
    contact = db.relationship('Contact', backref=db.backref('campaign_contacts', lazy=True))

class WhatsAppConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='disconnected')  # connected, disconnected, connecting
    last_check = db.Column(db.DateTime, default=datetime.utcnow)
    phone_number = db.Column(db.String(20))
    profile_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='success')  # success, error, warning