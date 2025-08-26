#!/usr/bin/env python3
"""
Railway-specific application entry point
This file ensures proper Railway deployment without development-only code
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

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
        import json
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

# Initialize the app with the extension
db.init_app(app)

# Create tables and import routes within app context
with app.app_context():
    # Import models to ensure tables are created
    from models import Contact, MessageTemplate, Campaign, CampaignContact, WhatsAppConnection, ActivityLog
    db.create_all()
    
    # Import routes after app initialization
    from routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=False)