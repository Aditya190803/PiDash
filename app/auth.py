import json
import os
from typing import Dict, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, request, session, current_app, render_template, redirect, url_for, flash

auth_bp = Blueprint('auth', __name__)

USERS_FILE_ENV = 'USERS_FILE'
DEFAULT_USERS_FILE = 'users.json'


def _users_file_path(app_path: Optional[str] = None) -> str:
    return os.getenv(USERS_FILE_ENV, DEFAULT_USERS_FILE)


def load_users() -> Dict[str, Dict]:
    path = _users_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_users(users: Dict[str, Dict]):
    path = _users_file_path()
    with open(path, 'w') as fh:
        json.dump(users, fh)


def create_user(username: str, password: str, role: str = 'admin') -> None:
    users = load_users()
    users[username] = {
        'password_hash': generate_password_hash(password),
        'role': role
    }
    save_users(users)


def verify_user(username: str, password: str) -> bool:
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    return check_password_hash(user.get('password_hash', ''), password)


def get_user_role(username: str) -> Optional[str]:
    users = load_users()
    user = users.get(username)
    if not user:
        return None
    return user.get('role')


# Role enforcement decorator
from functools import wraps
from flask import abort, session


def require_role(role: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = session.get('user')
            if not user:
                abort(401)
            if get_user_role(user) != role:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if verify_user(username, password):
            session.clear()
            session['user'] = username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('auth.login'))
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))
