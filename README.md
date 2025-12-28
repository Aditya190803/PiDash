# PiDash
A Simple Dashboard for Raspberry Pi 

[![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions)

**Quick development:** use `requirements.in` + `pip-compile` and `pip-compile requirements.in` to pin dependencies.


## Deploy Instructions

### Docker Build
```bash
docker build -t pidash .
```

### Docker Run
```bash
docker run -d -p 5001:5001 --name pidash --restart unless-stopped pidash
```

### Environment Variables
Copy `.env.example` to `.env` and customize:
- `FLASK_SECRET_KEY`: Secret key for Flask sessions
- `FLASK_DEBUG`: Enable debug mode (false in production)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 5001)
- `MAX_CONTENT_LENGTH`: Maximum file upload size in bytes (default: 16MB)

### Local Development
```bash
# Install and pin dependencies
pip install pip-tools
pip-compile requirements.in
pip install -r requirements.txt

# Copy env and start locally
cp .env.example .env
python app.py
```

**Notes:**
- In production, ensure `FLASK_SECRET_KEY` is set (the app will refuse to start with the default secret when `FLASK_ENV=production`).
- Optionally set `API_KEY` to protect destructive endpoints (`/delete` and `/download`) using the `X-API-KEY` header.
- Configure `ALLOWED_EXTENSIONS` as a comma-separated list in the environment to restrict uploads.

### Docker Compose (Local dev)
To start the app locally with Docker Compose:

```bash
docker-compose up --build -d
```

This will mount `./lsfile` to the container for uploads and expose port 5001.

To stop and remove containers:

```bash
docker-compose down
```

## Features
- System monitoring dashboard
- File sharing with upload/download
- Real-time system stats (CPU, RAM, Disk)
- Docker container support
- Health check endpoint (`/health`)
- Configurable via environment variables
