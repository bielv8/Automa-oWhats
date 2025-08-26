#!/usr/bin/env python3
"""
Main application entry point for Replit and production deployment
"""
import os
from app import app

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    # Check if running in development mode
    debug = os.environ.get("FLASK_ENV") == "development" or os.environ.get("DEBUG", "").lower() in ("true", "1")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=debug)