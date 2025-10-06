# Chef Agent

A FastAPI-based web service for chef management and operations.

## Project Structure

```
chef-agent/
├── main.py              # FastAPI application entry point
├── pyproject.toml       # Poetry project configuration and dependencies
├── poetry.lock          # Locked dependency versions
├── Dockerfile           # Docker container configuration
├── LICENSE              # Project license
└── README.md            # This file
```

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Health Check Endpoint**: Monitor service status
- **Docker Support**: Containerized deployment
- **Poetry Dependency Management**: Reliable dependency management

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/`      | Welcome message |
| GET    | `/health`| Health check status |

## Prerequisites

- Python 3.13+
- Poetry (for dependency management)
- Docker (optional, for containerized deployment)

## Installation

### Using Poetry (Recommended)

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Clone and navigate to the project**:
   ```bash
   git clone <repository-url>
   cd chef-agent
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Run the application**:
   ```bash
   poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Using pip (Alternative)

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install fastapi uvicorn[standard]
   ```

3. **Run the application**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Docker Deployment

### Build and Run with Docker

1. **Build the Docker image**:
   ```bash
   docker build -t chef-agent .
   ```

2. **Run the container**:
   ```bash
   docker run -d --name chef-agent-container -p 8000:8000 chef-agent
   ```

3. **Stop and remove the container**:
   ```bash
   docker stop chef-agent-container
   docker rm chef-agent-container
   ```

## Usage

Once the application is running, you can access:

- **API Base URL**: `http://localhost:8000`
- **Interactive API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

### Example API Calls

**Health Check**:
```bash
curl http://localhost:8000/health
```
Response:
```json
{
  "status": "ok",
  "system": "Server is running!"
}
```

**Root Endpoint**:
```bash
curl http://localhost:8000/
```
Response:
```json
{
  "Hello": "from FastAPI"
}
```

## Development

### Project Dependencies

The project uses the following main dependencies:

- **FastAPI** (>=0.118.0,<0.119.0): Web framework for building APIs
- **Uvicorn** (>=0.37.0,<0.38.0): ASGI server for running FastAPI applications

### Development Commands

```bash
# Install dependencies
poetry install

# Run with auto-reload for development
poetry run uvicorn main:app --reload

# Run tests (when implemented)
poetry run pytest

# Format code (when configured)
poetry run black .

# Lint code (when configured)
poetry run flake8 .
```

## Configuration

The application runs on:
- **Host**: `0.0.0.0` (all interfaces)
- **Port**: `8000`
- **Auto-reload**: Enabled in development mode

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For questions or issues, please open an issue in the repository or contact the maintainer.
