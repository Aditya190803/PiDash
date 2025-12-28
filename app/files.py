from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    current_app,
    session,
    abort,
    jsonify,
)
from werkzeug.utils import secure_filename
from typing import Optional
import json
from . import allowed_file, require_api_key
from .auth import get_user_role
import os

files_bp = Blueprint("files", __name__)


@files_bp.route("/download/<path:filename>")
@require_api_key
def download_file(filename):
    # If user is logged in, require admin role to download sensitive files under storage root
    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    safe_path = os.path.abspath(os.path.join(storage_root, filename))
    if not safe_path.startswith(os.path.abspath(storage_root)):
        abort(400)

    # If logged in, ensure admin role for downloads (safety decision)
    if session.get("user"):
        if get_user_role(session["user"]) != "admin":
            abort(403)

    directory = os.path.dirname(safe_path) or storage_root
    fname = os.path.basename(safe_path)
    # Force download by sending as attachment
    return send_from_directory(directory, fname, as_attachment=True)


@files_bp.route("/open/<path:filename>")
@require_api_key
def open_file(filename):
    # Serve file inline so browsers can open it in a tab when supported
    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    safe_path = os.path.abspath(os.path.join(storage_root, filename))
    if not safe_path.startswith(os.path.abspath(storage_root)):
        abort(400)

    # If logged in, ensure admin role for opening sensitive files
    if session.get("user"):
        if get_user_role(session["user"]) != "admin":
            abort(403)

    directory = os.path.dirname(safe_path) or storage_root
    fname = os.path.basename(safe_path)
    return send_from_directory(directory, fname, as_attachment=False)


@files_bp.route("/file-manager", methods=["GET", "POST"])
def file_manager():
    # Enhanced file manager route
    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    # Get current path from query parameter or default to root
    current_path = request.args.get("path", "")
    if current_path.startswith("/"):
        current_path = current_path[1:]

    target = os.path.abspath(os.path.join(base, current_path))
    if not target.startswith(base):
        abort(400)

    if os.path.isdir(target):
        entries = []
        for name in sorted(os.listdir(target)):
            path = os.path.join(target, name)
            stat = os.stat(path)
            entries.append(
                {
                    "name": name,
                    "is_dir": os.path.isdir(path),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "path": os.path.relpath(path, base),
                }
            )

        # Build breadcrumb
        relpath = os.path.relpath(target, base)
        if relpath == ".":
            relpath = ""

        return render_template(
            "file_manager.html", entries=entries, current_path=relpath
        )
    else:
        # If it's a file, redirect to download (authorization will apply)
        rel = os.path.relpath(target, base)
        return redirect(url_for("files.download_file", filename=rel))


# API endpoints for enhanced file operations
@files_bp.route("/api/files", methods=["GET"])
@require_api_key
def api_list_files():
    """API endpoint to list files in JSON format for the enhanced file manager"""
    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)
    current_path = request.args.get("path", "")

    if current_path.startswith("/"):
        current_path = current_path[1:]

    target = os.path.abspath(os.path.join(base, current_path))
    if not target.startswith(base):
        return jsonify({"error": "Invalid path"}), 400

    if not os.path.isdir(target):
        return jsonify({"error": "Not a directory"}), 400

    entries = []
    for name in sorted(os.listdir(target)):
        path = os.path.join(target, name)
        stat = os.stat(path)
        entries.append(
            {
                "name": name,
                "is_dir": os.path.isdir(path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "path": os.path.relpath(path, base),
            }
        )

    return jsonify(
        {"entries": entries, "current_path": current_path, "base_path": base}
    )


@files_bp.route("/api/file/<path:filename>", methods=["GET"])
@require_api_key
def api_get_file(filename):
    """API endpoint to get file content and metadata"""
    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    target = os.path.abspath(os.path.join(base, filename))
    if not target.startswith(base):
        return jsonify({"error": "Invalid path"}), 400

    if not os.path.isfile(target):
        return jsonify({"error": "File not found"}), 404

    # Check if user is logged in and has admin role for sensitive files
    if session.get("user"):
        if get_user_role(session["user"]) != "admin":
            abort(403)

    try:
        # Determine file type
        file_ext = os.path.splitext(filename)[1].lower()
        content_type = "text"
        language = "plaintext"

        if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]:
            content_type = "image"
        elif file_ext in [".pdf"]:
            content_type = "pdf"
        elif file_ext in [
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".md",
            ".txt",
            ".sh",
        ]:
            content_type = "code"
            # Determine language for Monaco Editor
            language_map = {
                ".py": "python",
                ".js": "javascript",
                ".html": "html",
                ".css": "css",
                ".json": "json",
                ".xml": "xml",
                ".md": "markdown",
                ".txt": "plaintext",
                ".sh": "shell",
            }
            language = language_map.get(file_ext, "plaintext")
        else:
            content_type = "binary"
            language = "plaintext"

        # Read file content if it's text-based
        content = ""
        if content_type in ["text", "code"]:
            try:
                with open(target, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                content = "Unable to read file content"

        return jsonify(
            {
                "name": os.path.basename(filename),
                "path": filename,
                "size": os.path.getsize(target),
                "mtime": os.path.getmtime(target),
                "type": content_type,
                "language": language if content_type == "code" else "plaintext",
                "content": content,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@files_bp.route("/api/upload", methods=["POST"])
@require_api_key
def api_upload_file():
    """API endpoint for file upload"""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    # Get target directory
    target_dir = request.form.get("path", "")
    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    if target_dir.startswith("/"):
        target_dir = target_dir[1:]

    target_path = os.path.abspath(os.path.join(base, target_dir))
    if not target_path.startswith(base):
        return jsonify({"error": "Invalid target directory"}), 400

    # Ensure target directory exists
    os.makedirs(target_path, exist_ok=True)

    # Save file
    filename = secure_filename(file.filename)
    file_path = os.path.join(target_path, filename)

    try:
        file.save(file_path)
        current_app.logger.info(
            f'File "{filename}" uploaded successfully to {target_dir}'
        )
        return jsonify({"message": f'File "{filename}" uploaded successfully'})
    except Exception as e:
        current_app.logger.error(f"Error uploading file: {e}")
        return jsonify({"error": "Upload failed"}), 500


@files_bp.route("/api/save", methods=["POST"])
@require_api_key
def api_save_file():
    """API endpoint to save file content"""
    data = request.get_json()
    if not data or "path" not in data or "content" not in data:
        return jsonify({"error": "Invalid request"}), 400

    file_path = data["path"]
    content = data["content"]

    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    target = os.path.abspath(os.path.join(base, file_path))
    if not target.startswith(base):
        return jsonify({"error": "Invalid path"}), 400

    # Check if user is logged in and has admin role
    if session.get("user"):
        if get_user_role(session["user"]) != "admin":
            abort(403)

    try:
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        current_app.logger.info(f'File "{file_path}" saved successfully')
        return jsonify({"message": "File saved successfully"})
    except Exception as e:
        current_app.logger.error(f"Error saving file: {e}")
        return jsonify({"error": "Save failed"}), 500


@files_bp.route("/api/delete", methods=["POST"])
@require_api_key
def api_delete_file():
    """API endpoint to delete files or directories.

    If deleting a directory that is not empty, clients may pass `{"recursive": true}`
    in the request JSON to remove it and its contents recursively.
    """
    data = request.get_json()
    if not data or "path" not in data:
        return jsonify({"error": "Invalid request"}), 400

    file_path = data["path"]
    recursive = data.get("recursive", False)

    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    target = os.path.abspath(os.path.join(base, file_path))
    if not target.startswith(base):
        return jsonify({"error": "Invalid path"}), 400

    # Check if user is logged in and has admin role
    if session.get("user"):
        if get_user_role(session["user"]) != "admin":
            abort(403)

    try:
        if os.path.isfile(target):
            os.remove(target)
            current_app.logger.info(f'File "{file_path}" deleted successfully')
            return jsonify({"message": "File deleted successfully"})
        elif os.path.isdir(target):
            # If recursive requested, remove directory tree
            if recursive:
                import shutil

                shutil.rmtree(target)
                current_app.logger.info(f'Directory "{file_path}" recursively deleted')
                return jsonify({"message": "Directory deleted recursively"})
            else:
                try:
                    os.rmdir(target)
                    current_app.logger.info(f'Directory "{file_path}" deleted successfully')
                    return jsonify({"message": "Directory deleted successfully"})
                except OSError:
                    return jsonify({"error": "Directory not empty. Use recursive: true to remove."}), 400
        else:
            return jsonify({"error": "File or directory not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {e}")
        return jsonify({"error": "Delete failed"}), 500


@files_bp.route("/api/rename", methods=["POST"])
@require_api_key
def api_rename_file():
    """API endpoint to rename files"""
    data = request.get_json()
    if not data or "old_path" not in data or "new_path" not in data:
        return jsonify({"error": "Invalid request"}), 400

    old_path = data["old_path"]
    new_path = data["new_path"]

    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    old_target = os.path.abspath(os.path.join(base, old_path))
    new_target = os.path.abspath(os.path.join(base, new_path))

    if not old_target.startswith(base) or not new_target.startswith(base):
        return jsonify({"error": "Invalid path"}), 400

    # Check if user is logged in and has admin role
    if session.get("user"):
        if get_user_role(session["user"]) != "admin":
            abort(403)

    try:
        if os.path.exists(old_target):
            # Ensure destination parent exists
            os.makedirs(os.path.dirname(new_target), exist_ok=True)
            os.rename(old_target, new_target)
            current_app.logger.info(
                f'File "{old_path}" renamed to "{new_path}" successfully'
            )
            return jsonify({"message": "File renamed successfully"})
        else:
            return jsonify({"error": "File or directory not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error renaming file: {e}")
        return jsonify({"error": "Rename failed"}), 500


@files_bp.route("/api/create", methods=["POST"])
@require_api_key
def api_create_item():
    """API endpoint to create new files or directories

    Accepts JSON (application/json) or form-encoded data (multipart/form-data or
    application/x-www-form-urlencoded) for compatibility with different clients.
    """
    # Parse payload robustly: prefer JSON, but fall back to form data
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        # Try common form encodings
        if request.form:
            data = request.form.to_dict()
        else:
            # Last resort: try to parse raw body as JSON or URL-encoded string
            raw = request.get_data(as_text=True) or ""
            if raw:
                try:
                    data = json.loads(raw)
                except Exception:
                    # Try parsing as URL-encoded form data (e.g., text/plain payloads)
                    from urllib.parse import parse_qs

                    parsed = parse_qs(raw, keep_blank_values=True)
                    # Reduce lists to single values
                    data = {k: v[0] for k, v in parsed.items()}
            else:
                data = {}

    # Log parsed payload for troubleshooting unusual content-types
    current_app.logger.debug(f"api_create parsed data: {data!r}")
    if not data or "path" not in data or "type" not in data or "name" not in data:
        return jsonify({"error": "Invalid request"}), 400

    base_path = data["path"]
    item_type = data["type"]  # 'file' or 'folder'
    name = data["name"]

    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    target_dir = os.path.abspath(os.path.join(base, base_path))
    if not target_dir.startswith(base):
        return jsonify({"error": "Invalid path"}), 400

    # Check if user is logged in and has admin role
    if session.get("user"):
        if get_user_role(session["user"]) != "admin":
            abort(403)

    try:
        return _create_item_from_data(target_dir, item_type, name)
    except Exception as e:
        current_app.logger.error(f"Error creating item: {e}")
        return jsonify({"error": "Creation failed"}), 500


# Helper function to centralize creation logic so other handlers (like error handlers)
# can call it directly when parsing of the request body fails at the framework level.
def _create_item_from_data(target_dir: str, item_type: str, name: str):
    """Create a folder or file at target_dir with name.

    Returns a Flask response tuple (response, status_code) or a Flask Response.
    """
    safe_name = secure_filename(name)
    if not safe_name:
        return jsonify({"error": "Invalid name"}), 400
    item_path = os.path.abspath(os.path.join(target_dir, safe_name))
    if not item_path.startswith(target_dir):
        return jsonify({"error": "Invalid path"}), 400

    if item_type == "folder":
        os.makedirs(item_path, exist_ok=True)
        current_app.logger.info(f'Directory "{safe_name}" created successfully')
        return jsonify({"message": f'Directory "{safe_name}" created successfully'})
    elif item_type == "file":
        os.makedirs(os.path.dirname(item_path), exist_ok=True)
        with open(item_path, "w") as f:
            f.write("")
        current_app.logger.info(f'File "{safe_name}" created successfully')
        return jsonify({"message": f'File "{safe_name}" created successfully'})
    else:
        return jsonify({"error": "Invalid item type"}), 400


@files_bp.route("/delete/<path:filename>", methods=["POST"])
@require_api_key
def delete_file(filename: str):
    try:
        storage_root = current_app.config.get(
            "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
        )
        safe_path = os.path.abspath(os.path.join(storage_root, filename))
        if not safe_path.startswith(os.path.abspath(storage_root)):
            flash("Invalid filename.", "error")
            return redirect(url_for("files.file_manager"))

        # Require admin role for deletion
        if session.get("user"):
            if get_user_role(session["user"]) != "admin":
                abort(403)

        if os.path.exists(safe_path):
            os.remove(safe_path)
            current_app.logger.info(f'File "{safe_path}" deleted successfully')
            flash(f'File "{filename}" has been deleted.', "success")
        else:
            current_app.logger.warning(f'File "{safe_path}" not found for deletion')
            flash(f'Error: File "{filename}" not found.', "error")
    except Exception as e:
        current_app.logger.error(f"Error deleting file {filename}: {e}")
        flash(f"An error occurred while deleting the file: {e}", "error")

    return redirect(url_for("files.file_manager"))


# File manager browsing UI
@files_bp.route("/browse/", defaults={"subpath": ""})
@files_bp.route("/browse/<path:subpath>")
def browse(subpath):
    storage_root = current_app.config.get(
        "STORAGE_ROOT", current_app.config["UPLOAD_FOLDER"]
    )
    base = os.path.abspath(storage_root)

    target = os.path.abspath(os.path.join(base, subpath))
    if not target.startswith(base):
        abort(400)

    if os.path.isdir(target):
        entries = []
        for name in sorted(os.listdir(target)):
            path = os.path.join(target, name)
            stat = os.stat(path)
            entries.append(
                {
                    "name": name,
                    "is_dir": os.path.isdir(path),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                }
            )
        # Build breadcrumb
        relpath = os.path.relpath(target, base)
        if relpath == ".":
            relpath = ""
        return render_template(
            "browse.html", entries=entries, current_path=relpath, base_base=base
        )
    else:
        # If it's a file, redirect to download (authorization will apply)
        rel = os.path.relpath(target, base)
        return redirect(url_for("files.download_file", filename=rel))
