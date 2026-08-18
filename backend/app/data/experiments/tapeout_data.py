# Checklist items for data integrity
CHECKLIST = [
    {"id": "gds", "name": "GDSII file", "desc": "Final layout GDSII file"},
    {"id": "lef", "name": "LEF file", "desc": "LEF for standard cells"},
    {"id": "lib", "name": "Liberty file", "desc": "Timing and power info"},
    {"id": "dmr", "name": "Design rule report", "desc": "DRC report"},
    {"id": "sdf", "name": "SDF", "desc": "Timing back-annotation file"},
]

# simple reference & extracted netlists for LVS exercises
REF_NETLIST = [
    {"id": 1, "type": "device", "content": {"name": "M1", "kind": "PMOS", "W": 2.0, "L": 0.18}},
    {"id": 2, "type": "device", "content": {"name": "M2", "kind": "NMOS", "W": 1.0, "L": 0.18}},
    {"id": 3, "type": "connect", "content": {"net": "NET1", "from": "M1", "to": "M2"}},
]

# extracted has 2-3 deliberate differences
EXTRACTED_NETLIST = [
    {"id": 1, "type": "device", "content": {"name": "M1", "kind": "PMOS", "W": 1.5, "L": 0.18}},  # W mismatch
    {"id": 2, "type": "device", "content": {"name": "M2", "kind": "NMOS", "W": 1.0, "L": 0.18}},
    # missing connection line id 3 -> will be treated as discrepancy
]
# ========== 扫描链数据 ==========

# Level 1：寄存器列表（6个寄存器，带网格坐标）
SCAN_L1_REGS = [
    {"id": "reg1", "x": 0.0, "y": 0.0},
    {"id": "reg2", "x": 1.0, "y": 0.0},
    {"id": "reg3", "x": 2.0, "y": 0.0},
    {"id": "reg4", "x": 3.0, "y": 0.0},
    {"id": "reg5", "x": 4.0, "y": 0.0},
    {"id": "reg6", "x": 5.0, "y": 0.0},
]

# Level 1 最大连线长度限制
SCAN_MAX_LINK_LEN_L1 = 2.0

# Level 2：寄存器列表（8个寄存器）
SCAN_L2_REGS = [
    {"id": "reg1", "x": 0.0, "y": 0.0, "delay": 1.0},
    {"id": "reg2", "x": 1.0, "y": 0.5, "delay": 1.2},
    {"id": "reg3", "x": 2.0, "y": 0.0, "delay": 0.8},
    {"id": "reg4", "x": 3.0, "y": 0.5, "delay": 1.1},
    {"id": "reg5", "x": 4.0, "y": 0.0, "delay": 0.9},
    {"id": "reg6", "x": 5.0, "y": 0.5, "delay": 1.3},
    {"id": "reg7", "x": 6.0, "y": 0.0, "delay": 1.0},
    {"id": "reg8", "x": 7.0, "y": 0.5, "delay": 1.2},
]

# Level 2 权重
SCAN_L2_LENGTH_WEIGHT = 1.0
SCAN_L2_TIMING_WEIGHT = 0.5
SCAN_L2_OPTIMAL_COST = 20.0  # 最优成本阈值

# Level 3：寄存器列表（4个寄存器 + 故障响应）
SCAN_L3_REGS = [
    {"id": "reg1", "x": 0.0, "y": 0.0},
    {"id": "reg2", "x": 1.0, "y": 0.0},
    {"id": "reg3", "x": 2.0, "y": 0.0},
    {"id": "reg4", "x": 3.0, "y": 0.0},
]

# Level 3：真实故障位置
SCAN_L3_TRUE_FAULTS = ["reg2", "reg4"]

# Level 3：故障响应向量（模拟扫描链输出）
SCAN_L3_RESPONSE = [1, 0, 1, 0, 1, 0, 1, 0]  # 长度 8