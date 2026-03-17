"""
Run this script once to generate tests/sample_data/sample_inventory.xlsx
Usage: python tests/create_sample_inventory.py
"""
import os
import openpyxl

rows = [
    ('PN-1001', '3/8 Hex Bolt SS', 'each', 'Bin A-1'),
    ('PN-1002', 'Flat Washer 3/8', 'each', 'Bin A-2'),
    ('PN-1003', 'Lock Nut 3/8', 'each', 'Bin A-3'),
    ('PN-1004', 'Sheet Metal Screw #8', 'box', 'Bin B-1'),
    ('PN-1005', 'PVC Elbow 90deg 1in', 'each', 'Bin C-4'),
    ('PN-1006', 'Wire Loom 3/8 Black', 'ft', 'Shelf D-2'),
    ('PN-1007', 'E-Stop Button Red', 'each', 'Cabinet E-1'),
    ('PN-1008', 'T-Slot Nut M6', 'bag', 'Bin A-10'),
    ('PN-1009', 'Air Cylinder 1in Bore', 'each', 'Shelf F-3'),
    ('PN-1010', 'Proximity Sensor NPN', 'each', 'Cabinet E-2'),
    ('PN-1011', 'Oil Sight Glass', 'each', 'Shelf G-1'),
    ('PN-1012', 'V-Belt A42', 'each', 'Bin H-1'),
    ('PN-1013', 'Bearing 6205-2RS', 'each', 'Bin H-2'),
    ('PN-1014', 'Seal Kit 2in Cylinder', 'each', 'Cabinet I-1'),
    ('PN-1015', 'Thermocouple J-Type', 'each', 'Cabinet E-3'),
    ('PN-1016', 'Contactor 40A 24VDC', 'each', 'Cabinet E-4'),
    ('PN-1017', 'Terminal Block 10pos', 'each', 'Cabinet E-5'),
    ('PN-1018', 'Lubricant Grease 14oz', 'tube', 'Shelf J-1'),
    ('PN-1019', 'Filter Element 10um', 'each', 'Bin K-1'),
    ('PN-1020', 'Pressure Gauge 0-160psi', 'each', 'Shelf F-4'),
]

out_path = os.path.join(os.path.dirname(__file__), 'sample_data', 'sample_inventory.xlsx')
os.makedirs(os.path.dirname(out_path), exist_ok=True)

wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Parts'
ws.append(['part_number', 'description', 'unit', 'location'])
for row in rows:
    ws.append(row)

wb.save(out_path)
print(f"Saved {len(rows)} parts to {out_path}")
