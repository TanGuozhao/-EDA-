<template>
  <div class="path-node-map">
    <div class="path-node-map-meta">
      <span>起点 <strong>{{ sourceNodeId }}</strong></span>
      <span>终点 <strong>{{ targetNodeId }}</strong></span>
    </div>
    <div class="path-node-map-scroll">
      <svg
        class="path-node-map-svg"
        :width="layout.width"
        :height="layout.height"
        :viewBox="`0 0 ${layout.width} ${layout.height}`"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Path selection map"
      >
      <g v-for="edge in layout.edges" :key="`${edge.from}-${edge.to}`">
        <path :d="edge.path" class="path-map-edge" :class="{ active: isPathEdge(edge) }" />
      </g>
      <g
        v-for="node in layout.nodes"
        :key="node.id"
        class="path-map-node"
        :class="{ active: selectedPath.includes(node.id), current: currentNodeId === node.id, terminal: isTerminal(node.id) }"
        :transform="`translate(${node.x}, ${node.y})`"
      >
        <rect x="-20" y="-14" width="40" height="28" rx="4" />
        <text x="0" y="5">{{ node.id }}</text>
      </g>
      </svg>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PathNodeMap',
  props: {
    layout: { type: Object, required: true },
    sourceNodeId: { type: String, required: true },
    targetNodeId: { type: String, required: true },
    selectedPath: { type: Array, default: () => [] },
    currentNodeId: { type: String, default: '' },
  },
  setup(props) {
    function isPathEdge(edge) {
      return props.selectedPath.some((nodeId, index) => nodeId === edge.from && props.selectedPath[index + 1] === edge.to)
    }

    function isTerminal(nodeId) {
      return nodeId === props.sourceNodeId || nodeId === props.targetNodeId
    }

    return { isPathEdge, isTerminal }
  },
}
</script>
