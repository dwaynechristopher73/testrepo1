import os
import tempfile
import pytest
import openpyxl

from app.services.excel_parser import parse_excel_file

SAMPLE_XLSX = os.path.join(os.path.dirname(__file__), 'sample_data', 'sample_inventory.xlsx')


def _make_xlsx(rows, headers=None):
    """Helper: create a temp xlsx file and return its path."""
    headers = headers or ['part_number', 'description', 'unit', 'location']
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    tmp.close()
    return tmp.name


class TestHeaderDetection:
    def test_standard_headers(self, app):
        path = _make_xlsx([('PN-001', 'Test Part', 'each', 'Bin 1')])
        try:
            count, parts = parse_excel_file(path)
            assert count == 1
            assert parts[0]['part_number'] == 'PN-001'
        finally:
            os.unlink(path)

    def test_alternate_headers(self, app):
        path = _make_xlsx(
            [('PN-002', 'Another Part', 'box', '')],
            headers=['part #', 'item description', 'uom', 'bin'],
        )
        try:
            count, parts = parse_excel_file(path)
            assert count == 1
            assert parts[0]['part_number'] == 'PN-002'
            assert parts[0]['description'] == 'Another Part'
        finally:
            os.unlink(path)

    def test_header_not_in_row_1(self, app):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Company: Novalis', None, None, None])
        ws.append(['Report Date: 2026-01-01', None, None, None])
        ws.append(['part_number', 'description', 'unit', 'location'])
        ws.append(['PN-003', 'Third Part', 'each', 'Shelf A'])
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(tmp.name)
        tmp.close()
        try:
            count, parts = parse_excel_file(tmp.name)
            assert count == 1
            assert parts[0]['part_number'] == 'PN-003'
        finally:
            os.unlink(tmp.name)


class TestNormalization:
    def test_part_number_uppercase_strip(self, app):
        path = _make_xlsx([('  pn-lower  ', 'Some Part', '', '')])
        try:
            _, parts = parse_excel_file(path)
            assert parts[0]['part_number'] == 'PN-LOWER'
        finally:
            os.unlink(path)

    def test_description_whitespace_collapse(self, app):
        path = _make_xlsx([('PN-X', '  Extra   Spaces  Here  ', '', '')])
        try:
            _, parts = parse_excel_file(path)
            assert parts[0]['description'] == 'Extra Spaces Here'
        finally:
            os.unlink(path)

    def test_blank_rows_skipped(self, app):
        path = _make_xlsx([
            ('PN-A', 'Part A', 'each', 'Bin 1'),
            (None, None, None, None),
            ('PN-B', 'Part B', 'each', 'Bin 2'),
        ])
        try:
            count, parts = parse_excel_file(path)
            assert count == 2
        finally:
            os.unlink(path)

    def test_unit_none_when_blank(self, app):
        path = _make_xlsx([('PN-Y', 'Part Y', '', '')])
        try:
            _, parts = parse_excel_file(path)
            assert parts[0]['unit'] is None
        finally:
            os.unlink(path)


class TestErrors:
    def test_no_recognizable_headers(self, app):
        path = _make_xlsx([], headers=['col_a', 'col_b', 'col_c'])
        try:
            with pytest.raises(ValueError, match='header'):
                parse_excel_file(path)
        finally:
            os.unlink(path)

    def test_no_data_rows(self, app):
        path = _make_xlsx([])
        try:
            with pytest.raises(ValueError, match='No part rows'):
                parse_excel_file(path)
        finally:
            os.unlink(path)


@pytest.fixture
def app():
    """Minimal Flask app context so database functions work."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from app import create_app
    application = create_app('development')
    with application.app_context():
        yield application
