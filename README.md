# Business Permit System

A Django-based web application for managing business permit applications, renewals, amendments, and closures. The system features OCR capabilities, NLP validation, and fraud detection to streamline the permit application process.

## Features

### For Applicants
- User registration and authentication
- Business permit application management
  - New permit applications
  - Permit renewals
  - Amendments
  - Business closures
- Document upload with OCR auto-fill
- Real-time application status tracking
- Email and SMS notifications
- Profile management

### For Administrators
- Comprehensive dashboard
- Application review system
- Document verification with fraud detection
- Automated notifications
- Analytics and reporting
- User management

## Tech Stack

- Python 3.8+
- Django 4.x
- SQLite/PostgreSQL
- HTML/CSS/JavaScript (No frontend framework)
- Django Template Engine

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- Email server configuration (for notifications)
- SMS gateway configuration (optional)

## Installation

1. Clone the repository:
```bash
git clone -b <latest branch> https://github.com/Shorton04/Thesis-nila-jai
cd business_permit_system
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create .env file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. superuser:
```bash
username : Admin
password : Admin123
```

7. Run the development server:
```bash
python manage.py runserver
```

## Project Structure

```
business_permit_system/
├── manage.py
├── permit_system/          # Project configuration
├── accounts/              # User management
├── applications/          # Permit applications
├── documents/            # Document management
├── notifications/        # Notification system
├── static/              # Static files
├── templates/           # Global templates
├── media/              # User uploads
└── tests/              # Test files
```

## Key Components

### Applications Module
- Handles different types of permit applications
- Step-by-step form submission
- Application tracking
- Status updates

### Documents Module
- Document upload and management
- OCR processing
- Fraud detection
- NLP validation

### Notifications Module
- Email notifications
- SMS notifications
- In-app notifications
- Custom templates

## Security Features

- Document tampering detection
- Secure file uploads
- User authentication and authorization
- Form validation
- CSRF protection
- XSS prevention

## Development Guidelines

### Template Structure
- Base templates in `templates/`
- App-specific templates in respective app directories
- Component templates in `templates/components/`

### Static Files
- CSS files in `static/css/`
- JavaScript files in `static/js/`
- Images in `static/images/`

### Adding New Features
1. Create necessary models in appropriate app
2. Add views and forms
3. Create templates
4. Update URLs
5. Add tests
6. Document changes

## Testing

Run tests with:
```bash
pytest
```

## Deployment

1. Update `.env` with production settings
2. Configure your web server (e.g., Nginx)
3. Set up WSGI server (e.g., Gunicorn)
4. Configure static file serving
5. Set up SSL certificate
6. Configure email server
7. Set up database (sqlite3)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

01.2025

## Support

For support, email rmarcdexter@gmail.com
