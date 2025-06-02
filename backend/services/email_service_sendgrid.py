"""
DEPLOYMENT INSTRUCTIONS FOR SENDGRID:

1. Remove the original "email_service.py" file
2. Rename this file to "email_service.py" 
3. Add to requirements.txt: sendgrid==6.10.0
4. Remove from .env: SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
5. Add to .env:
   EMAIL_PROVIDER=sendgrid
   SENDGRID_API_KEY=your_sendgrid_api_key
   EMAIL_FROM=noreply@yourdomain.com
6. Create SendGrid account at sendgrid.com
7. Get API key from Settings → API Keys
8. Verify sender email in Settings → Sender Authentication

The code automatically uses SendGrid when EMAIL_PROVIDER=sendgrid, 
otherwise falls back to SMTP for development.
"""

import aiosmtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import app_settings
import os
import asyncio
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

class EmailService:
    """Email service supporting multiple providers"""
    
    @staticmethod
    async def send_password_reset_email(email: str, reset_token: str, user_name: str = "there") -> bool:
        """Send password reset email using configured provider"""
        
        email_provider = os.getenv("EMAIL_PROVIDER", "smtp").lower()
        
        if email_provider == "sendgrid":
            return await EmailService._send_with_sendgrid(email, reset_token, user_name)
        else:
            return await EmailService._send_with_smtp(email, reset_token, user_name)
    
    @staticmethod
    async def _send_with_sendgrid(email: str, reset_token: str, user_name: str) -> bool:
        """Send email using SendGrid API"""
        try:
            sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
            if not sendgrid_api_key:
                logger.error("SENDGRID_API_KEY not configured")
                return False
            
            # Construct reset URL
            if app_settings.allowed_origins[0] == "*":
                base_url = "http://127.0.0.1:5500/frontend/index.html"
            else:
                base_url = app_settings.allowed_origins[0].rstrip('/')
            reset_url = f"{base_url}?token={reset_token}"
            
            # Create email content
            subject = "Reset Your Password - Postnatal Stories"
            html_content = EmailService._get_html_template(user_name, reset_url, email)
            text_content = EmailService._get_text_template(user_name, reset_url)
            
            # Create SendGrid mail object
            message = Mail(
                from_email=(app_settings.email_from or "noreply@postnatalstories.com", app_settings.email_from_name),
                to_emails=email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            # Send email
            sg = SendGridAPIClient(api_key=sendgrid_api_key)
            
            # Run in thread pool since SendGrid client is synchronous
            def send_email():
                return sg.send(message)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, send_email)
            
            if response.status_code in [200, 202]:
                logger.info(f"Password reset email sent via SendGrid to {email}")
                return True
            else:
                logger.error(f"SendGrid API error: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid to {email}: {str(e)}")
            return False
    
    @staticmethod
    async def _send_with_smtp(email: str, reset_token: str, user_name: str) -> bool:
        """Send email using SMTP (original implementation)"""
        if not app_settings.smtp_username or not app_settings.smtp_password:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            # Construct reset URL
            if app_settings.allowed_origins[0] == "*":
                base_url = "http://127.0.0.1:5500/frontend/index.html"
            else:
                base_url = app_settings.allowed_origins[0].rstrip('/')
            reset_url = f"{base_url}?token={reset_token}"
            
            # Create email content
            subject = "Reset Your Password - Postnatal Stories"
            html_content = EmailService._get_html_template(user_name, reset_url, email)
            text_content = EmailService._get_text_template(user_name, reset_url)
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{app_settings.email_from_name} <{app_settings.email_from or app_settings.smtp_username}>"
            message["To"] = email
            
            # Add text and HTML parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=app_settings.smtp_server,
                port=app_settings.smtp_port,
                start_tls=True,
                username=app_settings.smtp_username,
                password=app_settings.smtp_password,
            )
            
            logger.info(f"Password reset email sent via SMTP to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email via SMTP to {email}: {str(e)}")
            return False
    
    @staticmethod
    def _get_html_template(user_name: str, reset_url: str, email: str) -> str:
        """Get HTML email template"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #2c3e50;
                    background: linear-gradient(135deg, #d4f1f9 0%, #fce8ea 100%);
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 30px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 2rem;
                    font-weight: bold;
                    background: linear-gradient(45deg, #6bb6d6, #e891a3);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin-bottom: 10px;
                }}
                .reset-btn {{
                    display: inline-block;
                    padding: 16px 40px;
                    background: linear-gradient(45deg, #a8d8ea, #6bb6d6);
                    color: white;
                    text-decoration: none;
                    border-radius: 30px;
                    font-weight: 600;
                    font-size: 1.1rem;
                    margin: 20px 0;
                    box-shadow: 0 4px 15px rgba(107, 182, 214, 0.3);
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #5d6d7e;
                    font-size: 0.9rem;
                }}
                .warning {{
                    background: rgba(220, 53, 69, 0.1);
                    border: 1px solid rgba(220, 53, 69, 0.3);
                    border-radius: 15px;
                    padding: 15px;
                    margin: 20px 0;
                    color: #721c24;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">Postnatal Stories</div>
                    <h1>Password Reset Request</h1>
                </div>
                
                <p>Hi {user_name},</p>
                
                <p>We received a request to reset your password for your Postnatal Stories account. If you made this request, click the button below to set a new password:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="reset-btn">Reset My Password</a>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Important:</strong> This link will expire in 1 hour for your security. If you didn't request this password reset, you can safely ignore this email.
                </div>
                
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #6bb6d6;">{reset_url}</p>
                
                <div class="footer">
                    <p>Take care,<br>The Postnatal Stories Team</p>
                    <p style="font-size: 0.8rem; margin-top: 20px;">
                        This email was sent to {email}. If you didn't create an account with us, please disregard this email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def _get_text_template(user_name: str, reset_url: str) -> str:
        """Get plain text email template"""
        return f"""
        Postnatal Stories - Password Reset Request
        
        Hi {user_name},
        
        We received a request to reset your password for your Postnatal Stories account.
        
        To reset your password, visit this link:
        {reset_url}
        
        This link will expire in 1 hour for your security.
        
        If you didn't request this password reset, you can safely ignore this email.
        
        Take care,
        The Postnatal Stories Team
        """