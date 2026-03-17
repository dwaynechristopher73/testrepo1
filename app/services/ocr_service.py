import re
import io
import json
import os

from flask import current_app

MOCK_OCR_FIXTURE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'tests', 'sample_data', 'sample_ocr_response.json'
)

DATE_PATTERN = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b')
QUANTITY_PATTERN = re.compile(r'\b(\d+(?:\.\d+)?)\b')


def process_upload(filepath):
    if current_app.config.get('USE_MOCK_OCR'):
        return _mock_ocr(filepath)
    return _real_ocr(filepath)


def _real_ocr(filepath):
    from google.cloud import vision
    import pdf2image
    from PIL import Image

    ext = os.path.splitext(filepath)[1].lower()
    images = []

    if ext == '.pdf':
        images = pdf2image.convert_from_path(filepath, dpi=300)
    else:
        images.append(Image.open(filepath))

    client = vision.ImageAnnotatorClient()
    all_lines = []

    for img in images:
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        content = buf.getvalue()

        gv_image = vision.Image(content=content)
        response = client.document_text_detection(image=gv_image)

        if response.error.message:
            raise RuntimeError(f"Vision API error: {response.error.message}")

        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    text = ' '.join(
                        ''.join(s.text for s in word.symbols)
                        for word in paragraph.words
                    )
                    if text.strip():
                        all_lines.append(text.strip())

    return extract_checkout_data(all_lines)


def _mock_ocr(filepath):
    fixture_path = MOCK_OCR_FIXTURE
    if os.path.exists(fixture_path):
        with open(fixture_path) as f:
            data = json.load(f)
        return extract_checkout_data(data.get('lines', []))

    mock_lines = [
        '03/17/2026',
        'Employee: Dwayne',
        'Dept: Extrusion',
        'PN-1001 Hex Bolt SS 3/8  qty: 10',
        'PN-1002 Flat Washer  qty: 20',
        'PN-1003 Lock Nut  qty: 5',
    ]
    return extract_checkout_data(mock_lines)


def extract_checkout_data(text_lines):
    date_found = None
    employee_raw = None
    department_raw = None
    part_rows = []

    for line in text_lines:
        stripped = line.strip()
        if not stripped:
            continue

        if date_found is None:
            m = DATE_PATTERN.search(stripped)
            if m:
                date_found = m.group(1)
                continue

        lower = stripped.lower()

        if employee_raw is None and ('employee' in lower or 'emp' in lower or 'name' in lower):
            parts = re.split(r'[:=\-]', stripped, maxsplit=1)
            if len(parts) == 2:
                employee_raw = parts[1].strip()
            continue

        if department_raw is None and ('dept' in lower or 'department' in lower):
            parts = re.split(r'[:=\-]', stripped, maxsplit=1)
            if len(parts) == 2:
                department_raw = parts[1].strip()
            continue

        qty_match = QUANTITY_PATTERN.findall(stripped)
        if qty_match:
            qty = qty_match[-1]
            part_text = re.sub(r'(?i)(qty|quantity)\s*:?\s*\d+[\.\d]*', '', stripped).strip()
            part_text = re.sub(r'\s+', ' ', part_text)
            part_rows.append({
                'date_raw': date_found or '',
                'employee_raw': employee_raw or '',
                'department_raw': department_raw or '',
                'part_raw': part_text,
                'quantity_raw': qty,
                'line_text': stripped,
            })

    if not part_rows and (date_found or employee_raw):
        part_rows.append({
            'date_raw': date_found or '',
            'employee_raw': employee_raw or '',
            'department_raw': department_raw or '',
            'part_raw': '',
            'quantity_raw': '',
            'line_text': ' | '.join(text_lines[:5]),
        })

    return part_rows
