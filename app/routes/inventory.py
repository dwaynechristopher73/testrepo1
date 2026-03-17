import os
import uuid

from flask import (Blueprint, current_app, flash, redirect,
                   render_template, request, url_for)

from app.database import get_all_parts, log_upload, update_upload_log
from app.services.excel_parser import parse_excel_file

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


def _allowed_file(filename, allowed=None):
    allowed = allowed or {'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


@inventory_bp.route('/')
def list_parts():
    parts = get_all_parts()
    return render_template('inventory/list.html', parts=parts)


@inventory_bp.route('/upload', methods=['GET'])
def upload_form():
    return render_template('inventory/upload.html')


@inventory_bp.route('/upload', methods=['POST'])
def upload_file():
    f = request.files.get('file')
    if not f or not f.filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('inventory.upload_form'))

    if not _allowed_file(f.filename):
        flash('Only .xlsx files are accepted for inventory upload.', 'danger')
        return redirect(url_for('inventory.upload_form'))

    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(f.filename)}"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
    f.save(save_path)

    upload_id = log_upload(f.filename, 'inventory_excel')

    try:
        count, _ = parse_excel_file(save_path)
        update_upload_log(upload_id, 'complete', row_count=count)
        flash(f'Successfully loaded {count} parts from {f.filename}.', 'success')
    except ValueError as e:
        update_upload_log(upload_id, 'error', error_msg=str(e))
        flash(f'Error parsing file: {e}', 'danger')
    except Exception as e:
        update_upload_log(upload_id, 'error', error_msg=str(e))
        flash(f'Unexpected error: {e}', 'danger')

    return redirect(url_for('inventory.list_parts'))
