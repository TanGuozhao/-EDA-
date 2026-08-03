import assert from 'node:assert/strict'
import test from 'node:test'

import {
  createInitialScheduleNodes,
  createScheduleBoardLayout,
  reflowScheduleNodes,
  scheduleSubmission,
  snapNodeToBoard,
} from '../scheduleBoard.mjs'

const dag = {
  start_node: 'START',
  end_node: 'END',
  nodes: [
    { id: 'START', operation_type: 'terminal' },
    { id: 'A', operation_type: 'add' },
    { id: 'END', operation_type: 'terminal' },
  ],
}

test('initial board reserves only the requested cycle count', () => {
  const layout = createScheduleBoardLayout(3)
  const expandedLayout = createScheduleBoardLayout(8)
  const nodes = createInitialScheduleNodes(dag, layout)
  const operation = nodes.find((node) => node.id === 'A')

  assert.equal(layout.cycleCount, 3)
  assert.equal(operation.data.scheduled, false)
  assert.ok(expandedLayout.cycleHeight < layout.cycleHeight)
  assert.ok(expandedLayout.nodeHeight < layout.nodeHeight)
  assert.equal(operation.extent[1][0], layout.slotX.at(-1) + layout.nodeWidth)
})

test('drop is clamped to the currently reserved cycle range', () => {
  const layout = createScheduleBoardLayout(3)
  const operation = createInitialScheduleNodes(dag, layout).find((node) => node.id === 'A')
  const dropped = snapNodeToBoard(operation, dag, layout, { x: 320, y: 9999 })

  assert.equal(dropped.data.scheduled, true)
  assert.equal(dropped.data.cycle, 2)
})

test('adding a cycle reflows pixels without changing a submitted cycle', () => {
  const initialLayout = createScheduleBoardLayout(3)
  const operation = createInitialScheduleNodes(dag, initialLayout).find((node) => node.id === 'A')
  const scheduled = snapNodeToBoard(operation, dag, initialLayout, { x: 320, y: initialLayout.laneOffset + initialLayout.cycleHeight })
  const reflowed = reflowScheduleNodes([scheduled], dag, createScheduleBoardLayout(4))[0]

  assert.equal(reflowed.data.cycle, 1)
  assert.deepEqual(scheduleSubmission([reflowed], dag), {
    A: { cycle: 1, resource_slot: 1 },
  })
})
