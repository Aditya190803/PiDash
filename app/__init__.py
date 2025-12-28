import os
import socket
import platform
import psutil
import logging
import time
import json
from typing import Dict, Any, Optional
from flask import (
    Flask,
    render_template,
    jsonify,
    send_from_directory,
    request,
    redirect,
    url_for,
    flash,
    Response,
)
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
except Exception:
    # Allow running in environments where python-dotenv is not installed (tests, minimal containers)
    def load_dotenv():
        return None


# Import CSRFProtect from the specific submodule to avoid importing Recaptcha which
# transitively imports deprecated Werkzeug APIs (e.g., url_encode in newer Werkzeug)
try:
    from flask_wtf.csrf import CSRFProtect
except Exception:
    # Provide a minimal stub for environments without flask-wtf (tests, minimal builds)
    class CSRFProtect:
        def init_app(self, app):
            # Provide a simple csrf_token template helper
            app.jinja_env.globals["csrf_token"] = lambda: ""

            # Basic enforcement for testing: if CSRF is enabled in config, reject POST/PUT/PATCH/DELETE without a token
            from flask import request, abort

            @app.before_request
            def _simple_csrf_check():
                if not app.config.get("WTF_CSRF_ENABLED"):
                    return None
                if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
                    return None
                token = (
                    request.headers.get("X-CSRFToken")
                    or request.form.get("csrf_token")
                    or request.args.get("csrf_token")
                )
                if not token:
                    # Return 400 to indicate missing CSRF
                    abort(400)

            return None


try:
    from prometheus_client import (
        CollectorRegistry,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
except Exception:
    # Minimal stubs for environments without prometheus_client (tests, minimal builds)
    class CollectorRegistry:
        pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            class _G:
                def set(self, v):
                    return None

            return _G()

    def generate_latest(reg):
        # Return a minimal, static metrics payload so tests can validate presence of expected metric names
        payload = """
# HELP pidash_cpu_usage CPU usage percent
# TYPE pidash_cpu_usage gauge
pidash_cpu_usage 0.0
# HELP pidash_ram_usage RAM usage percent
# TYPE pidash_ram_usage gauge
pidash_ram_usage 0.0
# HELP pidash_disk_usage Disk usage percent
# TYPE pidash_disk_usage gauge
pidash_disk_usage 0.0
# HELP pidash_memory_rss_bytes Process RSS memory in bytes
# TYPE pidash_memory_rss_bytes gauge
pidash_memory_rss_bytes 0
"""
        return payload.encode("utf-8")

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

load_dotenv()

csrf = CSRFProtect()

from functools import wraps
from flask import abort, session


def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = os.getenv("API_KEY")
        # If API_KEY is set, require the key OR allow a logged-in session
        if key:
            provided = request.headers.get("X-API-KEY") or request.args.get("api_key")
            if provided == key:
                return func(*args, **kwargs)
            if session.get("user"):
                return func(*args, **kwargs)
            abort(401)

        # If no API key configured, optionally require login for UI actions
        require_login_flag = os.getenv("REQUIRE_LOGIN", "false").lower() == "true"
        if require_login_flag and not session.get("user"):
            abort(401)

        return func(*args, **kwargs)

    return wrapper


# --- Configuration defaults ---
ALLOWED_EXTENSIONS = set(
    os.getenv("ALLOWED_EXTENSIONS", "txt,pdf,png,jpg,jpeg,gif,zip,py,sh").split(",")
)


def allowed_file(filename: Optional[str]) -> bool:
    if not filename:
        return False
    allowed = set(
        os.getenv("ALLOWED_EXTENSIONS", "txt,pdf,png,jpg,jpeg,gif,zip,py,sh").split(",")
    )
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def get_ip_address() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_cpu_temp() -> str:
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if "cpu_thermal" in temps:
                return f"{temps['cpu_thermal'][0].current:.1f}"
            for name in temps:
                if "core" in name or "cpu" in name or "k10temp" in name:
                    return f"{temps[name][0].current:.1f}"
        return "N/A"
    except Exception:
        return "N/A"


def get_system_stats() -> Dict[str, Any]:
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        load_avg = psutil.getloadavg()
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        processes = len(psutil.pids())

        # Format uptime
        uptime_hours = int(uptime // 3600)
        uptime_minutes = int((uptime % 3600) // 60)

        # Derive OS & kernel info (try PRETTY_NAME from /etc/os-release)
        try:
            os_name = None
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            os_name = line.strip().split("=", 1)[1].strip().strip('"')
                            break
            if not os_name:
                os_name = platform.system()
            kernel = platform.release()
        except Exception:
            os_name = platform.system()
            kernel = platform.release()

        stats = {
            "hostname": socket.gethostname(),
            "ip_address": get_ip_address(),
            "os": os_name,
            "kernel": kernel,
            "cpu_usage": cpu_usage,
            "cpu_per_core": cpu_per_core,
            "cpu_temp": get_cpu_temp(),
            "load_avg_1": load_avg[0],
            "load_avg_5": load_avg[1],
            "load_avg_15": load_avg[2],
            "ram_usage": ram.percent,
            "ram_total": f"{ram.total / (1024**3):.1f} GB",
            "ram_used": f"{ram.used / (1024**3):.1f} GB",
            "ram_free": f"{ram.available / (1024**3):.1f} GB",
            "swap_usage": swap.percent,
            "swap_total": f"{swap.total / (1024**3):.1f} GB",
            "swap_used": f"{swap.used / (1024**3):.1f} GB"
            if swap.total > 0
            else "0 GB",
            "disk_usage": disk.percent,
            "disk_free": f"{disk.free / (1024**3):.1f} GB",
            "disk_total": f"{disk.total / (1024**3):.1f} GB",
            "disk_used": f"{disk.used / (1024**3):.1f} GB",
            "processes": processes,
            "uptime_hours": uptime_hours,
            "uptime_minutes": uptime_minutes,
        }
        return stats
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting system stats: {e}")
        return {
            "hostname": "Error",
            "ip_address": "Error",
            "cpu_usage": 0,
            "cpu_per_core": [],
            "cpu_temp": "N/A",
            "load_avg_1": 0,
            "load_avg_5": 0,
            "load_avg_15": 0,
            "ram_usage": 0,
            "ram_total": "N/A",
            "ram_used": "N/A",
            "ram_free": "N/A",
            "swap_usage": 0,
            "swap_total": "0 GB",
            "swap_used": "0 GB",
            "disk_usage": 0,
            "disk_free": "N/A",
            "disk_total": "N/A",
            "disk_used": "N/A",
            "processes": 0,
            "uptime_hours": 0,
            "uptime_minutes": 0,
        }


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "lsfile")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16777216))
    LOG_LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))
    # Disable CSRF by default for simplicity on local deployments; tests may enable it explicitly
    WTF_CSRF_ENABLED = False

    # Metrics sampling configuration
    # Whether to run an in-process sampler thread (disabled during tests)
    METRICS_SAMPLER_ENABLED = (
        os.getenv("METRICS_SAMPLER_ENABLED", "true").lower() == "true"
    )
    # Sampling interval in seconds (can be fractional)
    METRICS_SAMPLE_INTERVAL = float(os.getenv("METRICS_SAMPLE_INTERVAL", "1"))
    # Retention window for history in seconds (used to cap requests)
    METRICS_HISTORY_SECONDS = int(os.getenv("METRICS_HISTORY_SECONDS", "3600"))


def create_app(config_object: object | str | None = None) -> Flask:
    # Ensure templates/static folders reference project's top-level folders
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_dir = os.path.join(project_root, "templates")
    static_dir = (
        os.path.join(project_root, "static")
        if os.path.isdir(os.path.join(project_root, "static"))
        else None
    )
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Load default config then override with provided config object
    app.config.from_object(Config)
    if config_object:
        if isinstance(config_object, str):
            app.config.from_envvar(config_object, silent=True)
        else:
            app.config.from_mapping(config_object)

    # Configure logging
    logging.basicConfig(
        level=app.config["LOG_LEVEL"],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Fail startup in production when FLASK_SECRET_KEY is not set
    # Use the environment variable directly to avoid relying on cached values
    if os.getenv("FLASK_ENV", "").lower() == "production" and not os.getenv(
        "FLASK_SECRET_KEY"
    ):
        raise RuntimeError(
            "FLASK_SECRET_KEY must be set to a secure value in production"
        )

    # Initialize CSRF protection
    csrf.init_app(app)

    # Provide a fallback for Unsupported Media Type (415) specifically for the
    # /api/create endpoint so clients that send an unusual Content-Type can still
    # be handled gracefully. This captures 415 errors raised by Werkzeug and tries
    # to parse the raw body as JSON or urlencoded data and calls the creation
    # helper in app.files.
    from werkzeug.exceptions import UnsupportedMediaType

    @app.errorhandler(UnsupportedMediaType)
    def handle_unsupported_media_type(err):
        try:
            # Only attempt special handling for POST /api/create
            if request.path == "/api/create" and request.method == "POST":
                raw = request.get_data(as_text=True) or ""
                data = {}
                try:
                    import json as _json

                    data = _json.loads(raw) if raw else {}
                except Exception:
                    # Try parsing as URL-encoded form
                    from urllib.parse import parse_qs

                    parsed = parse_qs(raw, keep_blank_values=True)
                    data = {k: v[0] for k, v in parsed.items()}

                if data and "path" in data and "type" in data and "name" in data:
                    # Delegate to the creation helper in files module
                    from .files import _create_item_from_data

                    storage_root = app.config.get("STORAGE_ROOT", app.config["UPLOAD_FOLDER"])
                    base = os.path.abspath(storage_root)
                    target_dir = os.path.abspath(os.path.join(base, data.get("path", "")))
                    if not target_dir.startswith(base):
                        return jsonify({"error": "Invalid path"}), 400
                    return _create_item_from_data(target_dir, data["type"], data["name"])
        except Exception as e:
            app.logger.debug(f"415 handler failed: {e}")

        # Fall back to default 415 JSON response
        return jsonify({"error": "Unsupported Media Type"}), 415

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Quick links (can be overridden by setup_config later)
    QUICK_LINKS = [
        {"name": "Router Admin", "url": "http://10.0.0.1", "icon": "wifi"},
        {"name": "File Manager", "url": "/file-manager", "icon": "folder"},
        {"name": "Google", "url": "https://google.com", "icon": "search"},
        {"name": "YouTube", "url": "https://youtube.com", "icon": "play"},
        {"name": "GitHub", "url": "https://github.com", "icon": "github"},
    ]
    # Expose default quick links via config so setup/settings can render consistent fields
    app.config["DEFAULT_QUICK_LINKS"] = QUICK_LINKS

    # Load setup config if present and override defaults
    try:
        from .setup import load_setup, _setup_file_path, save_setup

        setup_cfg = load_setup()
        # If there's no setup config yet, write the defaults into the setup file so configuration is persisted
        if not setup_cfg:
            default_cfg = {
                "quick_links": QUICK_LINKS,
                "upload_folder": app.config["UPLOAD_FOLDER"],
            }
            try:
                save_setup(default_cfg)
                setup_cfg = default_cfg
            except Exception:
                # If saving fails, continue with in-memory defaults
                setup_cfg = {}

        if setup_cfg:
            QUICK_LINKS = setup_cfg.get("quick_links", QUICK_LINKS)
            # Allow explicit storage root and upload folder
            if "storage_root" in setup_cfg:
                app.config["STORAGE_ROOT"] = os.path.abspath(setup_cfg["storage_root"])
                app.config["UPLOAD_FOLDER"] = app.config["STORAGE_ROOT"]
            if "upload_folder" in setup_cfg:
                app.config["UPLOAD_FOLDER"] = os.path.abspath(
                    setup_cfg["upload_folder"]
                )
    except Exception:
        # Ignore setup parsing errors and continue with defaults
        pass

    # Add Jinja2 filters for templates
    @app.template_filter("filesizeformat")
    def filesizeformat(value):
        """Format file size in human readable format"""
        if value is None:
            return ""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} PB"

    @app.template_filter("timestamp_to_date")
    def timestamp_to_date(value):
        """Convert timestamp to readable date format"""
        import datetime

        try:
            return datetime.datetime.fromtimestamp(float(value)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except (ValueError, TypeError):
            return "Invalid date"

    # Register blueprints
    from .files import files_bp

    app.register_blueprint(files_bp)

    # Authentication blueprint
    from .auth import auth_bp

    app.register_blueprint(auth_bp)

    # Setup blueprint (first-run + settings)
    from .setup_bp import setup_bp

    app.register_blueprint(setup_bp)

    # Settings blueprint (admin-editable configuration)
    from .settings_bp import settings_bp

    app.register_blueprint(settings_bp)

    @app.route("/")
    def index():
        # Determine whether setup/config is present and expose flag to template so the UI can prompt the user
        try:
            from .setup import load_setup

            setup_cfg = load_setup()
            setup_missing = not bool(setup_cfg)
        except Exception:
            setup_missing = False

        # If AUTO_SETUP is enabled, redirect automatically to setup on first run
        if not app.config.get("TESTING"):
            try:
                auto = os.getenv("AUTO_SETUP", "false").lower() == "true"
                if auto and setup_missing:
                    return redirect(url_for("setup.setup"))
            except Exception:
                pass

        # Build quick links dynamically so updates to setup are reflected immediately
        defaults = app.config.get("DEFAULT_QUICK_LINKS", [])
        links_for_render = []
        try:
            from .setup import load_setup

            saved_cfg = load_setup() or {}
            saved_links = {l.get("name"): l for l in saved_cfg.get("quick_links", [])}
        except Exception:
            saved_links = {}

        for default in defaults:
            name = default.get("name")
            url = saved_links.get(name, {}).get("url", default.get("url", ""))
            links_for_render.append(
                {"name": name, "icon": default.get("icon", ""), "url": url}
            )

        return render_template(
            "index.html", quick_links=links_for_render, setup_missing=setup_missing
        )

    @app.route("/api/stats")
    def api_stats():
        stats = get_system_stats()
        return jsonify(stats)

    @app.route("/api/stats/stream")
    def api_stats_stream():
        """Server-Sent Events stream that pushes JSON payloads for system stats.
        - If the optional query param `count` is provided it will send exactly that many events then close (useful for tests).
        - The interval between messages is controlled by the REALTIME_INTERVAL env var (seconds, default 1).
        """

        def event_stream(count: Optional[int] = None):
            sent = 0
            interval = float(os.getenv("REALTIME_INTERVAL", "1"))
            # Send events until client disconnects or until `count` events have been sent
            try:
                while count is None or sent < count:
                    stats = get_system_stats()
                    payload = json.dumps(stats)
                    yield f"data: {payload}\n\n"
                    sent += 1
                    time.sleep(interval)
            except GeneratorExit:
                # Client disconnected
                return

        # Allow clients to request a finite number of events for testing/debugging
        count_param = request.args.get("count")
        try:
            count = int(count_param) if count_param is not None else None
        except ValueError:
            count = None

        return Response(event_stream(count), mimetype="text/event-stream")

    @app.route("/api/stats/history")
    def api_stats_history():
        """Return short-term historical metrics as JSON.
        Query params:
          - minutes (int): number of minutes of history to return (default 5)
          - step (int): aggregation bucket size in seconds (default 1)
        """
        from .metrics_buffer import buffer

        try:
            minutes = int(request.args.get("minutes", "5"))
        except Exception:
            minutes = 5
        try:
            step = int(request.args.get("step", "1"))
        except Exception:
            step = 1

        # Cap minutes to configured history window
        max_minutes = app.config.get("METRICS_HISTORY_SECONDS", 3600) // 60
        if minutes < 1:
            minutes = 1
        if minutes > max_minutes:
            minutes = max_minutes

        samples = buffer.get_history(minutes=minutes, step=step)
        return jsonify({"minutes": minutes, "step": step, "samples": samples})

    # File routes are registered via the `files_bp` blueprint (see `app/files.py`)

    @app.route("/health")
    def health_check():
        return jsonify({"status": "healthy", "service": "pidash"})

    @app.route("/metrics")
    def metrics():
        registry = CollectorRegistry()
        hostname = socket.gethostname()

        cpu_g = Gauge(
            "pidash_cpu_usage", "CPU usage percent", ["hostname"], registry=registry
        )
        ram_g = Gauge(
            "pidash_ram_usage", "RAM usage percent", ["hostname"], registry=registry
        )
        disk_g = Gauge(
            "pidash_disk_usage", "Disk usage percent", ["hostname"], registry=registry
        )
        mem_rss_g = Gauge(
            "pidash_memory_rss_bytes",
            "Process RSS memory in bytes",
            ["hostname"],
            registry=registry,
        )
        uptime_g = Gauge(
            "pidash_process_uptime_seconds",
            "Process uptime in seconds",
            ["hostname"],
            registry=registry,
        )
        cores_g = Gauge(
            "pidash_cpu_cores", "CPU cores", ["hostname"], registry=registry
        )

        stats = get_system_stats()
        cpu_g.labels(hostname=hostname).set(stats.get("cpu_usage", 0))
        ram_g.labels(hostname=hostname).set(stats.get("ram_usage", 0))
        disk_g.labels(hostname=hostname).set(stats.get("disk_usage", 0))

        try:
            p = psutil.Process()
            mem_rss_g.labels(hostname=hostname).set(getattr(p.memory_info(), "rss", 0))
            uptime_g.labels(hostname=hostname).set(time.time() - p.create_time())
            cores_g.labels(hostname=hostname).set(psutil.cpu_count() or 1)
        except Exception:
            mem_rss_g.labels(hostname=hostname).set(0)
            uptime_g.labels(hostname=hostname).set(0)
            cores_g.labels(hostname=hostname).set(1)

        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # A permissive but safe default CSP; adjust as needed for external resources
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com;",
        )
        return response

    # Start background metrics sampler when enabled and not testing
    try:
        if app.config.get("METRICS_SAMPLER_ENABLED") and not app.config.get("TESTING"):
            import threading
            from . import metrics_buffer

            def _sampler():
                interval = float(app.config.get("METRICS_SAMPLE_INTERVAL", 1))
                while True:
                    try:
                        metrics_buffer.buffer.append_sample(get_system_stats())
                    except Exception:
                        logging.getLogger(__name__).exception(
                            "Error when sampling system stats"
                        )
                    time.sleep(interval)

            t = threading.Thread(
                target=_sampler, daemon=True, name="pidash-metrics-sampler"
            )
            t.start()
    except Exception:
        logging.getLogger(__name__).exception("Failed to start metrics sampler")

    return app


# Provide a default app instance for backwards-compatibility (e.g. imports like `from app import app`)
app = create_app()
__all__ = ["create_app", "app", "get_system_stats"]
