# Manufacturing steps in order (id used for checking)
MANUFACTURING_STEPS = [
    {"id": "oxidation", "title": "Oxidation"},
    {"id": "photolith", "title": "Photolithography"},
    {"id": "etch", "title": "Etch"},
    {"id": "deposition", "title": "Deposition"},
    {"id": "metallization", "title": "Metallization"},
    {"id": "cmp", "title": "CMP"},
    {"id": "wafer_test", "title": "Wafer Test"},
    {"id": "dicing", "title": "Dicing/Cutting"},
]

# Packaging options and chips for matching
PACKAGES = [
    {"id": "DIP", "name": "DIP", "pin_count_range": [6, 40]},
    {"id": "QFP", "name": "QFP", "pin_count_range": [32, 256]},
    {"id": "BGA", "name": "BGA", "pin_count_range": [64, 1024]},
]

CHIPS = [
    {"id": "chip_a", "pins": 28, "power_mW": 100, "app": "microcontroller", "best_match": "QFP"},
    {"id": "chip_b", "pins": 16, "power_mW": 10, "app": "sensor", "best_match": "DIP"},
    {"id": "chip_c", "pins": 256, "power_mW": 500, "app": "high-speed-processor", "best_match": "BGA"},
]