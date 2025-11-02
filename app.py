import socket
import psutil
import os
from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

# --- Configuration ---
UPLOAD_FOLDER = 'lsfile'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'py', 'sh'}

# You can add or remove links here.
# The 'icon' key should correspond to a name from the Lucide icon library (https://lucide.dev/icons/)
QUICK_LINKS = [
    {
        "name": "Router Admin",
        "url": "http://10.0.0.1",
        "icon": "router"
    },
    {
        "name": "File Share",
        "url": "/files", # Updated URL to point to the new file sharing page
        "icon": "folder-archive"
    },
    {
        "name": "Google",
        "url": "https://google.com",
        "icon": "search"
    },
    {
        "name": "YouTube",
        "url": "https://youtube.com",
        "icon": "youtube"
    },
    {
        "name": "GitHub",
        "url": "https://github.com",
        "icon": "github"
    },
]


# --- Flask App Initialization ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# A secret key is needed for flashing messages
app.config['SECRET_KEY'] = 'supersecretkey'

# Create the upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_ip_address():
    """Helper function to get the primary IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_cpu_temp():
    """Helper function to get CPU temperature. Handles different OS environments."""
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps:
                return f"{temps['cpu_thermal'][0].current:.1f}"
            for name in temps:
                if "core" in name or "cpu" in name or "k10temp" in name:
                    return f"{temps[name][0].current:.1f}"
        return "N/A"
    except Exception:
        return "N/A"

def get_system_stats():
    """Gathers all system stats into a dictionary."""
    cpu_usage = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    stats = {
        "hostname": socket.gethostname(),
        "ip_address": get_ip_address(),
        "cpu_usage": cpu_usage,
        "cpu_temp": get_cpu_temp(),
        "ram_usage": ram.percent,
        "ram_total": f"{ram.total / (1024**3):.1f} GB",
        "disk_usage": disk.percent,
        "disk_free": f"{disk.free / (1024**3):.1f} GB",
        "disk_total": f"{disk.total / (1024**3):.1f} GB",
    }
    return stats

@app.route('/')
def index():
    """Renders the main homepage template."""
    return render_template('index.html', quick_links=QUICK_LINKS)

@app.route('/api/stats')
def api_stats():
    """Provides system stats as a JSON API endpoint."""
    stats = get_system_stats()
    return jsonify(stats)

# --- File Sharing Routes ---

@app.route('/files', methods=['GET', 'POST'])
def manage_files():
    """Handles file listing and uploading."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in request.', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading.', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash(f'File "{filename}" uploaded successfully!', 'success')
            return redirect(url_for('manage_files'))
        else:
            flash('File type not allowed.', 'error')
            return redirect(request.url)

    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('files.html', files=files)

@app.route('/download/<filename>')
def download_file(filename):
    """Serves files for download."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- New File Deletion Route ---
@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    """Handles file deletion."""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f'File "{filename}" has been deleted.', 'success')
        else:
            flash(f'Error: File "{filename}" not found.', 'error')
    except Exception as e:
        flash(f'An error occurred while deleting the file: {e}', 'error')
    
    return redirect(url_for('manage_files'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

