# Postnatal Stories

A platform for parents to share recovery stories and find support through their postnatal journey.

## Quick Setup

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### Installation

1. **Clone and navigate**
git clone https://github.com/GuillemynRune/Industry_Project.git
cd Industry_Project


2. **Configure environment**
cp .env.example .env

Edit `.env` and add your:
- `MONGODB_URI` (MongoDB Atlas connection string)
- `JWT_SECRET_KEY` (32+ character random string)
- `OPENAI_API_KEY` (your OpenAI API key)
- Email settings (SMTP credentials)

3. **Run application**
docker-compose up -d


### Access
- **Application**: http://localhost:8080
- **API Documentation**: http://localhost:8080/api/docs (development only)

### Management

# Stop application
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up --build