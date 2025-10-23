# Chef Agent - AI-Powered Meal Planning

A sophisticated AI agent that helps you plan meals, manage shopping lists, and make dietary decisions. Built with FastAPI, LangGraph, and modern security practices.

## Quick Start

### Prerequisites
- Python 3.13+
- Poetry
- Docker (optional)

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd chef-agent
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Setup database:**
   ```bash
   make migrate    # Apply database migrations
   make seed       # Load sample recipes
   ```

4. **Run the application:**
   ```bash
   make dev        # Development mode with auto-reload
   # or
   make run        # Production mode
   ```

5. **Access the API:**
   - API: http://localhost:8070
   - Docs: http://localhost:8070/docs
   - Health: http://localhost:8070/health

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or run individual container
docker build -t chef-agent .
docker run -e GROQ_API_KEY=your_key -p 8070:8070 chef-agent
```

## Architecture

### Clean Architecture (DDD)
```
chef-agent/
├── domain/           # Business logic (entities, repositories)
├── adapters/         # External dependencies (DB, LLM, MCP)
├── use_cases/        # Application services
├── agent/            # AI agent implementation
├── api/              # Web API layer
└── scripts/          # Utilities and migrations
```

### Key Components
- **LangGraph Agent**: Planner → Tools → Responder workflow
- **MCP Server**: Recipe finder and shopping list manager
- **SQLite Database**: With migration system
- **Security**: Rate limiting, CSRF, CSP, input validation
- **Multi-language**: English, German, French support

## Security Features

- **Rate Limiting**: 10 requests/minute per IP
- **Security Headers**: CSP, HSTS, X-Frame-Options
- **Input Validation**: Pydantic models
- **Log Scrubbing**: Sensitive data protection
- **Non-root Container**: Docker security best practices

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/db/status` | Database status |
| GET | `/docs` | Interactive API documentation |

## Testing

```bash
# Run all tests
make test

# Run specific test file
poetry run pytest tests/test_domain_entities.py -v

# Run with coverage
poetry run pytest --cov=. tests/
```

## Development Commands

```bash
make install      # Install dependencies
make migrate      # Run database migrations
make seed         # Load sample data
make test         # Run tests
make lint         # Run linters
make format       # Format code
make clean        # Clean temporary files
make dev          # Start development server
make run          # Start production server
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional (with defaults)
MODEL_NAME=llama-3.1-8b-instant
API_PORT=8070
RATE_LIMIT_PER_MINUTE=10
DEFAULT_LANGUAGE=en
```

## Performance

- **Response Time**: < 100ms for health checks
- **Rate Limit**: 10 requests/minute per IP
- **Database**: SQLite with proper indexing
- **Memory**: ~50MB base usage

## Security Checklist

- [x] Rate limiting implemented
- [x] Security headers (CSP, HSTS, etc.)
- [x] Input validation with Pydantic
- [x] Log scrubbing for sensitive data
- [x] Non-root Docker container
- [x] CORS properly configured
- [x] SQL injection prevention

## Production Deployment

### Docker Compose
```yaml
services:
  app:
    build: .
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    ports:
      - "8070:8070"
    volumes:
      - sqlite_data:/app/data
```

### Environment Setup
1. Set `GROQ_API_KEY` environment variable
2. Configure production database if needed
3. Set up reverse proxy (nginx/traefik)
4. Enable HTTPS/TLS

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For questions or issues, please open an issue in the repository.
