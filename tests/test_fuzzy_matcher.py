import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def app():
    from app import create_app
    application = create_app('development')
    with application.app_context():
        yield application


class TestMatchEmployee:
    def test_exact_match(self, app):
        from app.services.fuzzy_matcher import match_employee
        match, score = match_employee('Dwayne')
        assert match == 'Dwayne'
        assert score == 100

    def test_typo_match(self, app):
        from app.services.fuzzy_matcher import match_employee
        match, score = match_employee('Dwayn3')
        assert match == 'Dwayne'

    def test_partial_first_name(self, app):
        from app.services.fuzzy_matcher import match_employee
        match, score = match_employee('Logan R')
        assert match == 'Logan'

    def test_transposed_letters(self, app):
        from app.services.fuzzy_matcher import match_employee
        match, score = match_employee('Chadd')
        assert match == 'Chad'

    def test_no_match_returns_none(self, app):
        from app.services.fuzzy_matcher import match_employee
        match, score = match_employee('ZZZZZZZZZ')
        assert match is None

    def test_empty_string(self, app):
        from app.services.fuzzy_matcher import match_employee
        match, score = match_employee('')
        assert match is None
        assert score == 0


class TestMatchDepartment:
    def test_exact(self, app):
        from app.services.fuzzy_matcher import match_department
        match, score = match_department('Extrusion')
        assert match == 'Extrusion'

    def test_common_ocr_error(self, app):
        from app.services.fuzzy_matcher import match_department
        match, score = match_department('Extruslon')
        assert match == 'Extrusion'

    def test_lowercase(self, app):
        from app.services.fuzzy_matcher import match_department
        match, score = match_department('finishing')
        assert match == 'Finishing'

    def test_abbreviation_uv(self, app):
        from app.services.fuzzy_matcher import match_department
        match, score = match_department('UV')
        assert match == 'UV'


class TestMatchPart:
    PARTS = [
        {'id': 1, 'part_number': 'PN-1001', 'description': '3/8 Hex Bolt SS'},
        {'id': 2, 'part_number': 'PN-1002', 'description': 'Flat Washer 3/8'},
        {'id': 3, 'part_number': 'PN-1003', 'description': 'Lock Nut 3/8'},
    ]

    def test_exact_part_number(self, app):
        from app.services.fuzzy_matcher import match_part
        match, score = match_part('PN-1001', self.PARTS)
        assert match['part_number'] == 'PN-1001'

    def test_transposed_digit(self, app):
        from app.services.fuzzy_matcher import match_part
        match, score = match_part('PN-1O01 Hex Bolt', self.PARTS)
        assert match is not None
        assert match['part_number'] == 'PN-1001'

    def test_description_only(self, app):
        from app.services.fuzzy_matcher import match_part
        match, score = match_part('Flat Washer', self.PARTS)
        assert match['part_number'] == 'PN-1002'

    def test_empty_parts_list(self, app):
        from app.services.fuzzy_matcher import match_part
        match, score = match_part('PN-1001', [])
        assert match is None

    def test_no_match(self, app):
        from app.services.fuzzy_matcher import match_part
        match, score = match_part('ZZZZZ QQQQQ', self.PARTS, threshold=95)
        assert match is None


class TestBuildMatchCandidates:
    PARTS = [
        {'id': 1, 'part_number': 'PN-1001', 'description': '3/8 Hex Bolt SS'},
    ]

    def test_high_confidence_not_flagged(self, app):
        from app.services.fuzzy_matcher import build_match_candidates
        ocr = [{
            'date_raw': '03/17/2026',
            'employee_raw': 'Dwayne',
            'department_raw': 'Extrusion',
            'part_raw': 'PN-1001 Hex Bolt',
            'quantity_raw': '10',
            'line_text': 'PN-1001 Hex Bolt qty: 10',
        }]
        results = build_match_candidates(ocr, self.PARTS)
        assert len(results) == 1
        assert results[0]['employee'] == 'Dwayne'
        assert results[0]['department'] == 'Extrusion'

    def test_missing_employee_flagged(self, app):
        from app.services.fuzzy_matcher import build_match_candidates
        ocr = [{
            'date_raw': '03/17/2026',
            'employee_raw': '',
            'department_raw': 'UV',
            'part_raw': 'PN-1001',
            'quantity_raw': '5',
            'line_text': '',
        }]
        results = build_match_candidates(ocr, self.PARTS)
        assert results[0]['needs_review'] is True
