import csv
import io

from flask import (Blueprint, current_app, make_response,
                   redirect, render_template, request, url_for)

from app.database import get_checkouts

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    return redirect(url_for('dashboard.history'))


@dashboard_bp.route('/dashboard')
def history():
    filters = {
        'date_from':   request.args.get('date_from', ''),
        'date_to':     request.args.get('date_to', ''),
        'employee':    request.args.get('employee', ''),
        'department':  request.args.get('department', ''),
        'part_number': request.args.get('part_number', ''),
    }
    active_filters = {k: v for k, v in filters.items() if v}
    rows = get_checkouts(active_filters)
    departments = current_app.config['KNOWN_DEPARTMENTS']
    employees = current_app.config['KNOWN_EMPLOYEES']

    return render_template(
        'dashboard/history.html',
        rows=rows,
        filters=filters,
        departments=departments,
        employees=employees,
    )


@dashboard_bp.route('/dashboard/export')
def export_csv():
    filters = {
        'date_from':   request.args.get('date_from', ''),
        'date_to':     request.args.get('date_to', ''),
        'employee':    request.args.get('employee', ''),
        'department':  request.args.get('department', ''),
        'part_number': request.args.get('part_number', ''),
    }
    active_filters = {k: v for k, v in filters.items() if v}
    rows = get_checkouts(active_filters)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'id', 'checkout_date', 'employee_name', 'department',
        'part_number', 'description', 'quantity', 'notes',
        'source_file', 'confirmed_by', 'created_at',
    ])
    for r in rows:
        writer.writerow([
            r['id'], r['checkout_date'], r['employee_name'], r['department'],
            r['part_number'], r['description'], r['quantity'], r['notes'] or '',
            r['source_file'] or '', r['confirmed_by'] or '', r['created_at'],
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=checkouts.csv'
    return response
