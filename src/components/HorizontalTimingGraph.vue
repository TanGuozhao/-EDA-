<template>
  <section class="timing-panel horizontal-panel">
    <div class="panel-heading">
      <div>
        <span class="panel-kicker">02 / Horizontal Timing Graph</span>
        <h3>横向时序图</h3>
      </div>
      <span class="panel-status">由 DAG 生成</span>
    </div>
    <p class="panel-copy">节点从左到右按拓扑层排列，连线使用正交折线。点击方块可查看该节点的时序计算结果。</p>

    <div class="horizontal-stage">
      <svg
        class="horizontal-svg"
        :viewBox="`0 0 ${layout.width} ${layout.height}`"
        role="img"
        aria-label="横向时序图"
      >
        <defs>
          <marker id="horizontal-arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
            <polygon points="0 0, 10 5, 0 10" fill="#242b36" />
          </marker>
          <marker id="horizontal-arrow-active" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
            <polygon points="0 0, 10 5, 0 10" fill="#2f6fed" />
          </marker>
          <filter id="horizontal-shadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="2" dy="3" stdDeviation="2" flood-color="#172033" flood-opacity=".18" />
          </filter>
        </defs>

        <g v-for="edge in layout.edges" :key="`h-${edge.from}-${edge.to}`">
          <path
            :d="edge.path"
            class="horizontal-edge"
            :class="{ active: isIncomingEdge(edge) || isSelectedPathEdge(edge) }"
            :marker-end="edgeMarker(edge)"
          />
          <circle
            v-if="edge.junction"
            :cx="edge.junction.x"
            :cy="edge.junction.y"
            r="6"
            class="horizontal-junction"
            :class="{ active: isIncomingEdge(edge) || isSelectedPathEdge(edge) }"
          />
        </g>

        <g v-for="wire in layout.input_wires" :key="`in-${wire.to}`">
          <path
            :d="wire.path"
            class="horizontal-edge"
            :class="{ active: isIncomingInputWire(wire) || isSelectedPathEdge(wire) }"
            :marker-end="edgeMarker(wire)"
          />
        </g>
        <g v-for="wire in layout.output_wires" :key="`out-${wire.from}`">
          <path :d="wire.path" class="horizontal-edge" :class="{ active: isSelectedPathEdge(wire) }" :marker-end="edgeMarker(wire)" />
        </g>

        <g
          v-for="node in layout.nodes"
          :key="`h-node-${node.id}`"
          class="horizontal-node"
          :class="{ active: selectedNode === node.id, path: selectedPath.includes(node.id) }"
          :transform="`translate(${node.x}, ${node.y})`"
          role="button"
          tabindex="0"
          @click="$emit('select-node', node.id)"
          @pointerdown.stop
          @keyup.enter="$emit('select-node', node.id)"
        >
          <text class="horizontal-label" x="0" y="-30">{{ node.id }}</text>
          <rect v-if="selectedNode === node.id" class="horizontal-selection-ring" x="-27" y="-27" width="54" height="54" rx="4" />
          <rect x="-22" y="-22" width="44" height="44" rx="2" />
          <text class="horizontal-delay" x="0" y="8">{{ node.delay }}</text>
        </g>
      </svg>
    </div>
  </section>
</template>

<script>
export default {
  name: 'HorizontalTimingGraph',
  props: {
    layout: { type: Object, required: true },
    selectedNode: { type: String, required: true },
    selectedPath: { type: Array, default: () => [] },
  },
  emits: ['select-node'],
  setup(props) {
    function isIncomingEdge(edge) {
      return edge.to === props.selectedNode
    }

    function isIncomingInputWire(wire) {
      return wire.to === props.selectedNode
    }

    function isSelectedPathEdge(edge) {
      return props.selectedPath.some((nodeId, index) => nodeId === edge.from && props.selectedPath[index + 1] === edge.to)
    }

    function edgeMarker(edge) {
      if (isIncomingEdge(edge) || isSelectedPathEdge(edge)) return 'url(#horizontal-arrow-active)'
      return 'url(#horizontal-arrow)'
    }

    return { edgeMarker, isIncomingEdge, isIncomingInputWire, isSelectedPathEdge }
  },
}
</script>
