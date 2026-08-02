export const schedulingDemoDag = {
  nodes: [
    { id: 'START', delay: 0 }, { id: 'A', delay: 1 }, { id: 'B', delay: 1 }, { id: 'C', delay: 1 },
    { id: 'D', delay: 1 }, { id: 'E', delay: 1 }, { id: 'H', delay: 1 }, { id: 'F', delay: 1 },
    { id: 'G', delay: 1 }, { id: 'END', delay: 0 },
  ],
  edges: [
    { from: 'START', to: 'A' }, { from: 'A', to: 'B' }, { from: 'A', to: 'C' },
    { from: 'B', to: 'D' }, { from: 'B', to: 'E' }, { from: 'C', to: 'E' }, { from: 'C', to: 'H' },
    { from: 'D', to: 'F' }, { from: 'E', to: 'F' }, { from: 'H', to: 'G' }, { from: 'F', to: 'G' },
    { from: 'G', to: 'END' },
  ],
  delays: { START: 0, A: 1, B: 1, C: 1, D: 1, E: 1, H: 1, F: 1, G: 1, END: 0 },
  start_node: 'START',
  end_node: 'END',
  node_attributes: {
    START: { operation_type: 'terminal' }, A: { operation_type: 'arithmetic' },
    B: { operation_type: 'arithmetic' }, C: { operation_type: 'control' }, D: { operation_type: 'storage' },
    E: { operation_type: 'arithmetic' }, H: { operation_type: 'mux' }, F: { operation_type: 'arithmetic' },
    G: { operation_type: 'control' }, END: { operation_type: 'terminal' },
  },
  scheduling: {
    cycle_count: 7,
    assignments: {
      START: { cycle: 0, resource_slot: 1 }, A: { cycle: 1, resource_slot: 0 },
      B: { cycle: 2, resource_slot: 1 }, C: { cycle: 2, resource_slot: 2 }, D: { cycle: 3, resource_slot: 0 },
      E: { cycle: 3, resource_slot: 1 }, H: { cycle: 3, resource_slot: 2 }, F: { cycle: 4, resource_slot: 1 },
      G: { cycle: 5, resource_slot: 1 }, END: { cycle: 6, resource_slot: 1 },
    },
  },
}

const SLOT_X = [115, 335, 555]
const CYCLE_Y = 78

export function buildSchedulingFlowGraph(dag) {
  const assignments = dag.scheduling?.assignments || {}
  const attributes = dag.node_attributes || {}
  const fallbackCycle = 0

  return {
    nodes: dag.nodes.map((node, index) => {
      const assignment = assignments[node.id] || { cycle: fallbackCycle, resource_slot: index }
      return {
        id: node.id,
        type: 'schedule',
        position: {
          x: SLOT_X[assignment.resource_slot] ?? SLOT_X[SLOT_X.length - 1],
          y: assignment.cycle * CYCLE_Y,
        },
        data: {
          label: node.id,
          delay: node.delay,
          operationType: attributes[node.id]?.operation_type || 'arithmetic',
        },
      }
    }),
    edges: dag.edges.map((edge) => ({
      id: `${edge.from}-${edge.to}`,
      source: edge.from,
      target: edge.to,
    })),
  }
}

// Kept for existing prototype consumers while the fixture itself is now a canonical DAG.
export const schedulingDemoGraph = buildSchedulingFlowGraph(schedulingDemoDag)

export const schedulingAlgorithms = [
  { id: 'asap', label: 'ASAP' },
  { id: 'alap', label: 'ALAP' },
  { id: 'list', label: 'List Scheduling' },
]
