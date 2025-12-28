from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from .setup import load_setup, save_setup, ensure_upload_folder
from .auth import require_role
import os

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings', methods=['GET', 'POST'])
@require_role('admin')
def settings():
    cfg = load_setup()
    if request.method == 'POST':
        upload_folder = request.form.get('upload_folder', '')
        storage_root = request.form.get('storage_root', '')

        # Build quick_links preserving default names/icons and using posted URLs
        defaults = current_app.config.get('DEFAULT_QUICK_LINKS', [])
        final_links = []
        for i, default in enumerate(defaults):
            key = f'link_{i}_url'
            url = request.form.get(key, '').strip() or default.get('url', '')
            final_links.append({'name': default.get('name'), 'url': url, 'icon': default.get('icon', '')})

        final_cfg = {
            'quick_links': final_links,
        }
        if upload_folder:
            final_cfg['upload_folder'] = os.path.abspath(upload_folder)
            ensure_upload_folder(final_cfg['upload_folder'])
        if storage_root:
            final_cfg['storage_root'] = os.path.abspath(storage_root)
            ensure_upload_folder(final_cfg['storage_root'])

        save_setup(final_cfg)
        flash('Settings saved.', 'success')
        return redirect(url_for('settings.settings'))

    # Build links for rendering
    defaults = current_app.config.get('DEFAULT_QUICK_LINKS', [])
    links_for_render = []
    saved_links = {l.get('name'): l for l in cfg.get('quick_links', [])}
    for default in defaults:
        name = default.get('name')
        url = saved_links.get(name, {}).get('url', default.get('url', ''))
        links_for_render.append({'name': name, 'icon': default.get('icon', ''), 'url': url})

    return render_template('settings.html', quick_links=links_for_render, upload_folder=cfg.get('upload_folder', ''), storage_root=cfg.get('storage_root', ''))