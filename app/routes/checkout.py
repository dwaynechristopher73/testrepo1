import os
import re
import uuid

from flask import (Blueprint, current_app, flash, redirect,
                   render_template, request, url_for)

from app.database import (delete_pending_rows, get_all_parts, get_pending_rows,
                           get_upload_log_entry, insert_checkouts_bulk,
                           log_upload, save_pending_rows, update_upload_log)
from app.services.fuzzy_matcher import build_match_candidates
from app.services.ocr_service import process_upload

checkout_bp = Blueprint('checkout', __name__, url_prefix='/checkout')

ALLOWED = {'pdf', 'png', 'jpg', 'jpeg'}


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


@checkout_bp.route('/upload', methods=['GET'])
def upload_form():
    return render_template('checkout/upload.html')


@checkout_bp.route('/upload', methods=['POST'])
def upload_file():
    f = request.files.get('file')
    if not f or not f.filename:
        flash('No file selected.', 'danger')
        return redirect(url_for('checkout.upload_form'))

    if not _allowed(f.filename):
        flash('Accepted formats: PDF, PNG, JPG, JPEG.', 'danger')
        return redirect(url_for('checkout.upload_form'))

    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(f.filename)}"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
    f.save(save_path)

    upload_id = log_upload(f.filename, 'checkout_scan')

    try:
        ocr_results = process_upload(save_path)
        parts_list = get_all_parts()
        candidates = build_match_candidates(ocr_results, parts_list)
        save_pending_rows(upload_id, candidates)
        update_upload_log(upload_id, 'review_pending', row_count=len(candidates))
    except Exception as e:
        update_upload_log(upload_id, 'error', error_msg=str(e))
        flash(f'Error processing file: {e}', 'danger')
        return redirect(url_for('checkout.upload_form'))

    return redirect(url_for('checkout.review', upload_id=upload_id))


@checkout_bp.route('/review/<int:upload_id>', methods=['GET'])
def review(upload_id):
    entry = get_upload_log_entry(upload_id)
    if not entry:
        flash('Upload not found.', 'danger')
        return redirect(url_for('checkout.upload_form'))

    rows = get_pending_rows(upload_id)
    parts = get_all_parts()
    employees = current_app.config['KNOWN_EMPLOYEES']
    departments = current_app.config['KNOWN_DEPARTMENTS']

    return render_template(
        'checkout/review.html',
        rows=rows,
        parts=parts,
        employees=employees,
        departments=departments,
        entry=entry,
        upload_id=upload_id,
    )


@checkout_bp.route('/review/<int:upload_id>', methods=['POST'])
def confirm_review(upload_id):
    entry = get_upload_log_entry(upload_id)
    if not entry:
        flash('Upload not found.', 'danger')
        return redirect(url_for('checkout.upload_form'))

    pending_rows = get_pending_rows(upload_id)
    parts_map = {p['part_number']: p for p in get_all_parts()}

    confirmed_by = request.form.get('confirmed_by', '').strip() or 'unknown'
    checkout_rows = []

    for row in pending_rows:
        pid = str(row['pending_id'])
        skip = request.form.get(f'skip_{pid}')
        if skip:
            continue

        checkout_date = request.form.get(f'date_{pid}', '').strip()
        employee_name = request.form.get(f'employee_{pid}', '').strip()
        department = request.form.get(f'department_{pid}', '').strip()
        part_number = request.form.get(f'part_number_{pid}', '').strip()
        quantity_str = request.form.get(f'quantity_{pid}', '').strip()
        notes = request.form.get(f'notes_{pid}', '').strip()

        if not checkout_date or not employee_name or not department or not part_number:
            continue

        try:
            quantity = float(re.sub(r'[^\d.]', '', quantity_str)) if quantity_str else 0
        except ValueError:
            quantity = 0

        part = parts_map.get(part_number)
        checkout_rows.append({
            'checkout_date': checkout_date,
            'employee_name': employee_name,
            'department': department,
            'part_id': part['id'] if part else None,
            'part_number': part_number,
            'description': part['description'] if part else part_number,
            'quantity': quantity,
            'notes': notes or None,
            'source_file': entry['filename'],
            'confirmed_by': confirmed_by,
        })

    if checkout_rows:
        insert_checkouts_bulk(checkout_rows)

    delete_pending_rows(upload_id)
    update_upload_log(upload_id, 'complete', row_count=len(checkout_rows))

    flash(f'Saved {len(checkout_rows)} checkout record(s).', 'success')
    return redirect(url_for('dashboard.history'))


@checkout_bp.route('/success')
def success():
    return render_template('checkout/success.html')
