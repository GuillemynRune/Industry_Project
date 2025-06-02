import aiosmtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from config import app_settings

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending password reset emails"""
    
    @staticmethod
    async def send_password_reset_email(email: str, reset_token: str, user_name: str = "there") -> bool:
        """Send password reset email to user"""
        if not app_settings.smtp_username or not app_settings.smtp_password:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            # FIXED: Handle wildcard in allowed_origins and match actual frontend path
            frontend_url = os.getenv("FRONTEND_URL")
            if frontend_url:
                reset_url = f"{frontend_url}?token={reset_token}"
            else:
                # Fallback construction
                if app_settings.allowed_origins[0] == "*":
                    base_url = "http://localhost:5500/frontend"
                else:
                    base_url = app_settings.allowed_origins[0].rstrip('/')
                reset_url = f"{base_url}/index.html?token={reset_token}"
            
            # DEBUG: Log the constructed URL
            logger.info(f"Constructed reset URL: {reset_url}")
            
            # Create email content
            subject = "Reset Your Password - Postnatal Stories"
            html_content = f"""
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
            
            text_content = f"""
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
            
            logger.info(f"Password reset email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False