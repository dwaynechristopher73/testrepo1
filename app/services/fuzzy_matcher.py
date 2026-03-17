from rapidfuzz import fuzz, process
from flask import current_app


def match_employee(raw_text, known_employees=None, threshold=None):
    if known_employees is None:
        known_employees = current_app.config['KNOWN_EMPLOYEES']
    if threshold is None:
        threshold = current_app.config['FUZZY_EMPLOYEE_THRESHOLD']

    if not raw_text or not raw_text.strip():
        return None, 0

    result = process.extractOne(
        raw_text.strip(),
        known_employees,
        scorer=fuzz.token_sort_ratio,
    )
    if result is None:
        return None, 0
    match, score, _ = result
    if score >= threshold:
        return match, score
    return None, score


def match_department(raw_text, known_departments=None, threshold=None):
    if known_departments is None:
        known_departments = current_app.config['KNOWN_DEPARTMENTS']
    if threshold is None:
        threshold = current_app.config['FUZZY_DEPARTMENT_THRESHOLD']

    if not raw_text or not raw_text.strip():
        return None, 0

    result = process.extractOne(
        raw_text.strip(),
        known_departments,
        scorer=fuzz.ratio,
    )
    if result is None:
        return None, 0
    match, score, _ = result
    if score >= threshold:
        return match, score
    return None, score


def match_part(raw_text, parts_list, threshold=None):
    if threshold is None:
        threshold = current_app.config['FUZZY_PART_THRESHOLD']

    if not raw_text or not raw_text.strip() or not parts_list:
        return None, 0

    combined = [f"{p['part_number']} {p['description']}" for p in parts_list]

    result = process.extractOne(
        raw_text.strip(),
        combined,
        scorer=fuzz.token_set_ratio,
    )
    if result is None:
        return None, 0
    _, score, idx = result
    if score >= threshold:
        return parts_list[idx], score
    return None, score


def build_match_candidates(ocr_results, parts_list):
    candidates = []
    for item in ocr_results:
        employee, emp_score = match_employee(item.get('employee_raw', ''))
        department, dept_score = match_department(item.get('department_raw', ''))
        part, part_score = match_part(item.get('part_raw', ''), parts_list)

        needs_review = (
            employee is None
            or department is None
            or part is None
            or not item.get('quantity_raw')
        )

        candidates.append({
            'date_raw': item.get('date_raw', ''),
            'employee_raw': item.get('employee_raw', ''),
            'department_raw': item.get('department_raw', ''),
            'part_raw': item.get('part_raw', ''),
            'quantity_raw': item.get('quantity_raw', ''),
            'line_text': item.get('line_text', ''),
            'employee': employee,
            'emp_score': emp_score,
            'department': department,
            'dept_score': dept_score,
            'part': part,
            'part_score': part_score,
            'needs_review': needs_review,
        })

    return candidates
