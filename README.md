Postnatal Stories Platform
A community platform where parents share recovery stories, enhanced by AI and reviewed by moderators for safety.
What You're Building
Users submit their postnatal experiences through forms. AI transforms these into readable stories. Moderators review everything before publication. Other parents can then find and read stories similar to their experiences.
Prerequisites
Install these first:

Python 3.8+ - Download here
MongoDB - Local install or MongoDB Atlas (cloud)
OpenAI API Key - Get one here
Mailtrap Account - Sign up here for email testing

Quick Setup
1. Get the Code
bashgit clone <your-repo-url>
cd postnatal-stories
2. Install Backend
bashcd backend
pip install -r requirements.txt
3. Configure Environment
Create .env file:
.env# 
Database - local MongoDB or Atlas connection string
MONGODB_URI=mongodb://localhost:27017/postnatal_stories

# Security - generate random 32+ character string
JWT_SECRET_KEY=your-super-secure-random-string-here

# AI Story Generation
OPENAI_API_KEY=sk-your-openai-key-here

# Mailtrap Email Testing
SMTP_SERVER=smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USERNAME=your-mailtrap-username
SMTP_PASSWORD=your-mailtrap-password
EMAIL_FROM=noreply@postnatalstories.com

# Frontend URL
ALLOWED_ORIGINS=https://yourdomain.com

# Environment
ENVIRONMENT=development
4. Get Mailtrap Credentials

Sign up at mailtrap.io
Create an inbox with API/SMTP
Copy SMTP settings to your .env file

5. Start the Backend
cd backend
python main.py
Backend runs on: http://localhost:8000
6. Start the Frontend
cd frontend
python -m http.server 3000
Frontend runs on: http://localhost:3000
First Time Setup
Create Account and in the mongodb change the role from "user" to "admin" inside the "users" section of the database

Test Everything

Visit http://localhost:3000 - should load without errors
Visit http://localhost:8000/health - should show database connected
Submit test story as regular user
Review story as admin in moderation panel
Test password reset (email appears in Mailtrap)

How It Works
User Journey:

User registers account and submits story form
AI processes experience into readable story
System flags potential crisis content
Admin reviews and approves/rejects in moderation panel
Approved stories appear in community section

Key Features:

JWT authentication with 1-week tokens
Crisis detection with immediate resource display
Story search using MongoDB text indexes
Email notifications via Mailtrap
Risk assessment for submitted content

Database Setup Options
Local MongoDB:
bash# Install and start MongoDB service
# Database will be created automatically
MongoDB Atlas (Cloud):

Create cluster at mongodb.com/cloud/atlas
Get connection string
Update MONGODB_URI in .env

Configuration Details
Security Settings:

JWT tokens expire after 1 week
Passwords require 8+ characters with letters and numbers
All inputs are sanitized
Rate limiting prevents abuse

Story Processing:

OpenAI transforms experiences into stories
Crisis keywords trigger support resources
All content reviewed before publication

Troubleshooting
Backend won't start:

Check .env file has all required variables
Verify MongoDB is running
Test database connection

Frontend errors:

Check browser console for JavaScript errors
Verify API_BASE_URL matches backend port
Ensure backend is running

Stories not generating:

Check OpenAI API key and credits
View backend logs for AI service errors

Emails not working:

Verify Mailtrap credentials
Check Mailtrap inbox for test emails
Test SMTP settings in Mailtrap dashboard

Production Deployment
Before going live:

Set ENVIRONMENT=production
Use strong JWT secret (32+ random characters)
Set up production database
Configure real email service (replace Mailtrap)
Update ALLOWED_ORIGINS for your domain
Set up SSL certificates and proper web server

File Structure
backend/
  ├── main.py              # Application entry point
  ├── config.py            # Environment configuration
  ├── database/            # Database models and connection
  ├── routers/             # API endpoints
  └── services/            # AI and email services

frontend/
  ├── index.html           # Main page
  ├── css/styles.css       # Styling
  └── js/                  # Frontend functionality
API Documentation
Development mode provides automatic docs:

Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

Important Notes
This platform provides peer support, not medical advice. Always include crisis resources and appropriate disclaimers. The moderation system helps ensure content safety, but human oversight remains essential for sensitive mental health content.