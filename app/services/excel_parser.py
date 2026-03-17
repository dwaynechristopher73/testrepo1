import re
import openpyxl

from app.database import upsert_parts

HEADER_VARIANTS = {
    'part_number': {'part_number', 'part #', 'part#', 'part no', 'part no.', 'item #', 'item#', 'item no', 'pn'},
    'description': {'description', 'desc', 'item description', 'name', 'part description', 'item name'},
    'unit':        {'unit', 'uom', 'unit of measure', 'units'},
    'location':    {'location', 'bin', 'loc', 'shelf', 'bin location'},
}


def _normalize_header(cell_value):
    if cell_value is None:
        return ''
    return str(cell_value).strip().lower()


def _find_header_row(sheet):
    for row_idx, row in enumerate(sheet.iter_rows(max_row=15, values_only=True), start=1):
        normalized = [_normalize_header(c) for c in row]
        matched_fields = set()
        for field, variants in HEADER_VARIANTS.items():
            for cell in normalized:
                if cell in variants:
                    matched_fields.add(field)
                    break
        if len(matched_fields) >= 2:
            return row_idx, normalized
    return None, None


def _map_columns(normalized_headers):
    col_map = {}
    for field, variants in HEADER_VARIANTS.items():
        for idx, header in enumerate(normalized_headers):
            if header in variants:
                col_map[field] = idx
                break
    return col_map


def _normalize_part_number(value):
    if value is None:
        return ''
    return re.sub(r'\s+', '', str(value)).upper()


def _normalize_text(value):
    if value is None:
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def parse_excel_file(filepath):
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    sheet = wb.active

    header_row_idx, normalized_headers = _find_header_row(sheet)
    if header_row_idx is None:
        raise ValueError(
            "Could not find a header row in the Excel file. "
            "Expected columns: part_number (or 'part #'), description, and optionally unit, location."
        )

    col_map = _map_columns(normalized_headers)

    if 'part_number' not in col_map and 'description' not in col_map:
        raise ValueError("Excel file must have at least a part_number or description column.")

    parts = []
    for row in sheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
        part_number = _normalize_part_number(row[col_map['part_number']] if 'part_number' in col_map else None)
        description = _normalize_text(row[col_map['description']] if 'description' in col_map else None)
        unit = _normalize_text(row[col_map['unit']] if 'unit' in col_map else None) or None
        location = _normalize_text(row[col_map['location']] if 'location' in col_map else None) or None

        if not part_number and not description:
            continue

        if not part_number:
            part_number = 'UNKNOWN'
        if not description:
            description = part_number

        parts.append({
            'part_number': part_number,
            'description': description,
            'unit': unit,
            'location': location,
        })

    wb.close()

    if not parts:
        raise ValueError("No part rows found in the Excel file after the header row.")

    count = upsert_parts(parts)
    return count, parts
