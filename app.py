from app import create_app
import os

# Create app instance for compatibility with gunicorn and tests
app = create_app()

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5001"))

    app.logger.info(f"Starting PiDash on {host}:{port}, debug={debug_mode}")
    app.run(debug=debug_mode, host=host, port=port)
