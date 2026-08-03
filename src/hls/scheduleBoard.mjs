const MIN_CYCLE_COUNT = 3
const MAX_CYCLE_HEIGHT = 92
const MIN_CYCLE_HEIGHT = 54
const MAX_NODE_HEIGHT = 58
const MIN_NODE_HEIGHT = 38
const MAX_NODE_WIDTH = 100
const MIN_NODE_WIDTH = 76
const TRAY_HEIGHT = 190
const SLOT_X = [120, 270, 420, 570]

export function createScheduleBoardLayout(cycleCount) {
  const normalizedCycleCount = Math.max(MIN_CYCLE_COUNT, cycleCount)
  const cycleHeight = Math.max(
    MIN_CYCLE_HEIGHT,
    Math.min(MAX_CYCLE_HEIGHT, Math.floor(390 / normalizedCycleCount)),
  )
  const nodeHeight = Math.max(MIN_NODE_HEIGHT, Math.min(MAX_NODE_HEIGHT, Math.round(cycleHeight * 0.67)))
  const nodeWidth = Math.max(MIN_NODE_WIDTH, Math.min(MAX_NODE_WIDTH, Math.round(nodeHeight * 1.72)))
  const laneOffset = TRAY_HEIGHT + Math.round(cycleHeight / 2)

  return {
    cycleCount: normalizedCycleCount,
    cycleHeight,
    nodeHeight,
    nodeWidth,
    laneOffset,
    slotX: SLOT_X,
    stageHeight: TRAY_HEIGHT + (normalizedCycleCount * cycleHeight) + 12,
  }
}

export function cycleLabels(layout) {
  return Array.from({ length: layout.cycleCount }, (_, cycle) => cycle)
}

export function laneY(layout, cycle) {
  return (cycle * layout.cycleHeight) + layout.laneOffset
}

export function scheduledPosition(layout, cycle, slot) {
  const normalizedCycle = clampCycle(cycle, layout)
  const normalizedSlot = clampSlot(slot)
  return {
    x: layout.slotX[normalizedSlot],
    y: laneY(layout, normalizedCycle) - (layout.nodeHeight / 2),
  }
}

export function createInitialScheduleNodes(dag, layout) {
  return dag.nodes.map((node) => {
    const isStart = node.id === dag.start_node
    const data = {
      label: node.id,
      operationType: node.operation_type || 'generic',
      scheduled: isStart,
      cycle: isStart ? 0 : null,
      slot: isStart ? 0 : null,
      nodeWidth: layout.nodeWidth,
      nodeHeight: layout.nodeHeight,
      nodePadding: layout.nodeHeight < 46 ? 3 : 6,
      titleFontSize: layout.nodeHeight < 46 ? 12 : 15,
      subtitleFontSize: layout.nodeHeight < 46 ? 8 : 10,
    }
    return createFlowNode(node.id, dag, layout, data, !isStart)
  })
}

export function reflowScheduleNodes(nodes, dag, layout) {
  return nodes.map((node) => createFlowNode(node.id, dag, layout, node.data, node.id !== dag.start_node))
}

export function snapNodeToBoard(node, dag, layout, pointer) {
  if (node.id === dag.start_node) {
    return node
  }
  if (!pointer || typeof pointer.x !== 'number' || typeof pointer.y !== 'number') {
    throw new Error('A valid board-relative pointer position is required')
  }
  const data = pointer.y < TRAY_HEIGHT
    ? { ...node.data, scheduled: false, cycle: null, slot: null }
    : {
      ...node.data,
      scheduled: true,
      cycle: clampCycle(Math.round((pointer.y - layout.laneOffset) / layout.cycleHeight), layout),
      slot: nearestSlot(pointer.x - (layout.nodeWidth / 2), layout),
    }
  return createFlowNode(node.id, dag, layout, data, true)
}

export function scheduleSubmission(nodes, dag) {
  const assignments = {}
  for (const node of nodes) {
    if (!node.data.scheduled || node.id === dag.start_node) continue
    assignments[node.id] = {
      cycle: node.data.cycle,
      resource_slot: node.data.slot,
    }
  }
  return assignments
}

export function cycleLimit(dag, deadlineCycles) {
  return deadlineCycles ? deadlineCycles + 2 : dag.nodes.length + 1
}

function createFlowNode(nodeId, dag, layout, data, draggable) {
  const scheduled = data.scheduled
  const position = scheduled
    ? scheduledPosition(layout, data.cycle, data.slot)
    : trayPosition(dag, nodeId)
  return {
    id: nodeId,
    type: 'hls',
    position,
    width: layout.nodeWidth,
    height: layout.nodeHeight,
    style: {
      width: `${layout.nodeWidth}px`,
      height: `${layout.nodeHeight}px`,
    },
    extent: [[0, 0], [
      layout.slotX.at(-1) + layout.nodeWidth,
      scheduledPosition(layout, layout.cycleCount - 1, 0).y + layout.nodeHeight,
    ]],
    draggable,
    selectable: false,
    connectable: false,
    data: {
      ...data,
      nodeWidth: layout.nodeWidth,
      nodeHeight: layout.nodeHeight,
      nodePadding: layout.nodeHeight < 46 ? 3 : 6,
      titleFontSize: layout.nodeHeight < 46 ? 12 : 15,
      subtitleFontSize: layout.nodeHeight < 46 ? 8 : 10,
    },
  }
}

function trayPosition(dag, nodeId) {
  const nodeIds = dag.nodes.map((node) => node.id).filter((id) => id !== dag.start_node)
  const index = nodeIds.indexOf(nodeId)
  if (index < 0) throw new Error(`Unknown schedulable node: ${nodeId}`)
  return {
    x: SLOT_X[index % SLOT_X.length],
    y: 46 + (Math.floor(index / SLOT_X.length) * 68),
  }
}

function clampCycle(cycle, layout) {
  return Math.min(layout.cycleCount - 1, Math.max(0, cycle))
}

function clampSlot(slot) {
  return Math.min(SLOT_X.length - 1, Math.max(0, slot))
}

function nearestSlot(x, layout) {
  return layout.slotX.reduce(
    (bestSlot, slotX, index) => Math.abs(slotX - x) < Math.abs(layout.slotX[bestSlot] - x) ? index : bestSlot,
    0,
  )
}
