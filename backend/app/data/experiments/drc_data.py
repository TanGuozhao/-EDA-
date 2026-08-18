# Minimal DRC rule list and example violations for levels
RULES = [
    {"id": 1, "title": "Min width", "desc": "Metal trace width must be >= 0.2um"},
    {"id": 2, "title": "Min spacing", "desc": "Spacing between metals >= 0.2um"},
    {"id": 3, "title": "Via enclosure", "desc": "Via must be enclosed by metal by >= 0.05um"},
]

LEVEL1_VIOLATIONS = [
    {"pos_id": "p1", "rule_id": 1, "desc": "Trace too narrow"},
    {"pos_id": "p2", "rule_id": 2, "desc": "Spacing too small"},
    {"pos_id": "p3", "rule_id": 3, "desc": "Via enclosure too small"},
]

LEVEL2_VIOLATIONS = [
    {"pos_id": "l2_1", "rule_id": 1, "desc": "Narrow metal"},
    {"pos_id": "l2_2", "rule_id": 2, "desc": "Close spacing"},
    {"pos_id": "l2_3", "rule_id": 1, "desc": "Another narrow trace"},
]

LEVEL3_VIOLATIONS = [
    {"pos_id": "l3_1", "rule_id": 2, "desc": "Spacing conflict cluster"},
    {"pos_id": "l3_2", "rule_id": 1, "desc": "Narrow trace adjacent to l3_1"},
]