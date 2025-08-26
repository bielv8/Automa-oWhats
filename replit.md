# WhatsApp Automation System

## Overview

This is a Flask-based WhatsApp automation system designed for managing contacts, message templates, and automated messaging campaigns. The application provides a web interface for businesses to manage their WhatsApp communications, including contact management, template creation, campaign scheduling, and activity monitoring. The system simulates WhatsApp Web integration for development purposes and can be extended to work with actual WhatsApp automation libraries.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework
- **Flask**: Chosen as the main web framework for its simplicity and flexibility
- **SQLAlchemy**: Used as the ORM for database operations with a declarative base model
- **Flask-SQLAlchemy**: Integration layer between Flask and SQLAlchemy for easier database management
- **Jinja2 Templates**: Server-side rendering for the web interface with Bootstrap styling

### Database Design
- **SQLite**: Default database for development (configurable via DATABASE_URL environment variable)
- **Connection Pooling**: Configured with pool recycling and pre-ping for production reliability
- **Model Structure**: 
  - Contact management with tags and company information
  - Message templates with variable support
  - Campaign management with status tracking
  - Activity logging for audit trails
  - WhatsApp connection status tracking

### Frontend Architecture
- **Bootstrap 5**: Dark theme UI framework for responsive design
- **Font Awesome**: Icon library for consistent visual elements
- **DataTables**: Enhanced table functionality for data management
- **jQuery**: Client-side scripting for dynamic interactions
- **Progressive Enhancement**: Core functionality works without JavaScript

### WhatsApp Integration Layer
- **Service Pattern**: WhatsAppService class abstracts messaging functionality
- **Simulation Mode**: Development-friendly mock implementation for testing
- **Extensible Design**: Ready for integration with actual WhatsApp automation libraries
- **Status Monitoring**: Real-time connection status checking and reporting

### Application Structure
- **Modular Design**: Separate files for models, routes, and services
- **Configuration Management**: Environment-based configuration for different deployment stages
- **Error Handling**: Comprehensive logging and error management
- **Security**: Session management with configurable secret keys

### Data Management
- **CSV Import**: Bulk contact import functionality
- **Template Variables**: Dynamic message personalization system
- **Campaign Scheduling**: Time-based message delivery system
- **Activity Tracking**: Comprehensive audit log for all system actions

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web application framework
- **Flask-SQLAlchemy**: Database ORM integration
- **Werkzeug**: WSGI utilities and middleware

### Frontend Libraries (CDN)
- **Bootstrap 5**: UI framework with dark theme
- **Font Awesome 6**: Icon library
- **DataTables**: Table enhancement library
- **jQuery**: JavaScript utility library

### Database
- **SQLite**: Default database (development)
- **PostgreSQL**: Recommended for production (configurable via DATABASE_URL)

### Development Tools
- **Python Logging**: Built-in logging for debugging and monitoring
- **ProxyFix**: Werkzeug middleware for reverse proxy deployment

### Future Integration Possibilities
- **WhatsApp Business API**: For official WhatsApp integration
- **Selenium/Puppeteer**: For WhatsApp Web automation
- **Redis**: For session management and caching
- **Celery**: For background task processing
- **Email Services**: For notification and backup communication