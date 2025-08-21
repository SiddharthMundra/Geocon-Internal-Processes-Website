from datetime import datetime
from models.database import load_json, save_json
from config import Config

def send_email(to_email, subject, body):
    """Send email notification with logging"""
    email_log = load_json(Config.DATABASES['email_log'])
    if not isinstance(email_log, list):
        email_log = []
    
    # Log email
    email_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'to': to_email,
        'subject': subject,
        'status': 'sent',
        'mode': 'development'
    }
    
    # Development mode - print to terminal
    print(f"\n{'='*50}")
    print(f"EMAIL NOTIFICATION")
    print(f"{'='*50}")
    print(f"TO: {to_email}")
    print(f"SUBJECT: {subject}")
    print(f"{'='*50}")
    print(f"BODY:\n{body}")
    print(f"{'='*50}\n")
    
    email_log.append(email_entry)
    
    # Keep only last 1000 emails
    if len(email_log) > 1000:
        email_log = email_log[-1000:]
    
    save_json(Config.DATABASES['email_log'], email_log)
    return True