<template>
  <section class="scheduling-shell">
    <section class="scheduling-board" aria-label="DAG 调度画布">
      <header class="scheduling-board-header">
        <div>
          <span class="scheduling-kicker">DAG Scheduling</span>
          <h2>调度画布</h2>
        </div>
        <button class="restore-graph-button" type="button" @click="restoreOriginalGraph">还原原图</button>
      </header>

      <div class="flow-stage">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :snap-to-grid="true"
          :snap-grid="[20, 78]"
          :default-viewport="{ x: 0, y: 0, zoom: 1 }"
          :min-zoom="0.45"
          :max-zoom="1.7"
          :delete-key-code="['Backspace', 'Delete']"
          @connect="connectNodes"
          @node-drag-stop="emitGraphChanged"
          @edges-change="emitGraphChanged"
          @viewport-change="updateViewport"
        >
          <Background :gap="[20, 78]" color="#eef3f7" pattern-color="#eef3f7" />
          <Controls :show-interactive="false" />

          <template #node-schedule="nodeProps">
            <Handle type="target" :position="Position.Top" class="schedule-handle" />
            <div class="schedule-node" :class="`operation-${nodeProps.data.operationType || 'arithmetic'}`">
              {{ nodeProps.data.label }}
            </div>
            <Handle type="source" :position="Position.Bottom" class="schedule-handle" />
          </template>
        </VueFlow>

        <div class="cycle-lanes" :style="cycleLayerStyle" aria-hidden="true">
          <div v-for="cycle in cycleLabels" :key="cycle" class="cycle-lane" :style="{ top: `${24 + cycle * 78}px` }">
            <span>Cycle {{ cycle }}</span>
            <i></i>
          </div>
        </div>
      </div>
    </section>

    <aside class="scheduling-side">
      <section class="scheduling-card algorithm-card">
        <div class="scheduling-card-header">
          <h3>算法</h3>
          <span>调度策略</span>
        </div>
        <div class="algorithm-options" role="radiogroup" aria-label="调度算法">
          <button
            v-for="algorithm in algorithms"
            :key="algorithm.id"
            class="algorithm-option"
            :class="{ active: selectedAlgorithm === algorithm.id }"
            type="button"
            role="radio"
            :aria-checked="selectedAlgorithm === algorithm.id"
            @click="selectedAlgorithm = algorithm.id"
          >
            {{ algorithm.label }}
          </button>
        </div>
      </section>

      <section class="scheduling-card constraint-card">
        <div class="scheduling-card-header">
          <h3>约束</h3>
          <span>后端任务参数</span>
        </div>
        <div class="constraint-fields">
          <label>
            总周期上限
            <input v-model="constraints.maxCycles" type="number" min="1" inputmode="numeric">
          </label>
          <label>
            可用运算资源
            <input v-model="constraints.resources" type="text" placeholder="由任务定义">
          </label>
          <label>
            时钟周期
            <input v-model="constraints.clockPeriod" type="text" placeholder="由任务定义">
          </label>
        </div>
      </section>

      <section class="scheduling-card submit-card">
        <button class="submit-schedule-button" type="button" @click="submitSchedule">提交调度</button>
        <p class="submission-status" :class="submissionStatus.type">{{ submissionStatus.message }}</p>
      </section>
    </aside>
  </section>
</template>

<script>
import { computed, ref, watch } from 'vue'
import { addEdge, Handle, MarkerType, Position, VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

function cloneGraph(graph) {
  return {
    nodes: graph.nodes.map((node) => ({
      ...node,
      position: { ...node.position },
      data: { ...node.data },
    })),
    edges: graph.edges.map((edge) => ({ ...edge })),
  }
}

export default {
  name: 'SchedulingDagEditor',
  components: { Background, Controls, Handle, VueFlow },
  props: {
    originalGraph: {
      type: Object,
      required: true,
    },
    algorithms: {
      type: Array,
      required: true,
    },
    initialAlgorithm: {
      type: String,
      default: 'asap',
    },
  },
  emits: ['graph-changed', 'submit'],
  setup(props, { emit }) {
    const initial = cloneGraph(props.originalGraph)
    const nodes = ref(initial.nodes)
    const edges = ref(initial.edges.map(withArrowMarker))
    const selectedAlgorithm = ref(props.initialAlgorithm)
    const constraints = ref({ maxCycles: '', resources: '', clockPeriod: '' })
    const submissionStatus = ref({ type: 'idle', message: '等待提交' })
    const viewport = ref({ x: 0, y: 0, zoom: 1 })
    const cycleLabels = computed(() => Array.from({ length: 7 }, (_, index) => index))
    const cycleLayerStyle = computed(() => ({
      transform: `translate(${viewport.value.x}px, ${viewport.value.y}px) scale(${viewport.value.zoom})`,
    }))

    function withArrowMarker(edge) {
      return {
        ...edge,
        markerEnd: edge.markerEnd || MarkerType.ArrowClosed,
      }
    }

    function graphPayload() {
      return {
        algorithm: selectedAlgorithm.value,
        constraints: { ...constraints.value },
        graph: {
          nodes: nodes.value.map((node) => ({
            id: node.id,
            position: { ...node.position },
            data: { ...node.data },
          })),
          edges: edges.value.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
          })),
        },
      }
    }

    function emitGraphChanged() {
      emit('graph-changed', graphPayload())
    }

    function updateViewport(nextViewport) {
      viewport.value = { ...nextViewport }
    }

    function connectNodes(connection) {
      edges.value = addEdge(
        {
          ...connection,
          id: `${connection.source}-${connection.target}-${Date.now()}`,
          markerEnd: MarkerType.ArrowClosed,
        },
        edges.value,
      )
      emitGraphChanged()
    }

    function restoreOriginalGraph() {
      const original = cloneGraph(props.originalGraph)
      nodes.value = original.nodes
      edges.value = original.edges.map(withArrowMarker)
      submissionStatus.value = { type: 'idle', message: '已还原原图' }
      emitGraphChanged()
    }

    function submitSchedule() {
      const payload = graphPayload()
      submissionStatus.value = { type: 'pending', message: '调度数据已准备' }
      emit('submit', payload)
    }

    watch(selectedAlgorithm, emitGraphChanged)
    watch(constraints, emitGraphChanged, { deep: true })

    return {
      Background,
      Controls,
      Handle,
      Position,
      VueFlow,
      connectNodes,
      constraints,
      cycleLayerStyle,
      cycleLabels,
      edges,
      emitGraphChanged,
      nodes,
      restoreOriginalGraph,
      selectedAlgorithm,
      submissionStatus,
      submitSchedule,
      updateViewport,
    }
  },
}
</script>

<style scoped>
.scheduling-shell{width:min(100%,1440px);height:100%;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:24px}.scheduling-board{min-width:0;min-height:0;display:flex;flex-direction:column;padding:16px;border:1px solid #dce5ef;border-radius:8px;background:#fff;box-shadow:0 5px 16px rgba(23,32,51,.05)}
.scheduling-board-header{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex:0 0 auto;padding-bottom:14px;border-bottom:1px solid #e5ebf2}.scheduling-kicker{display:block;color:#18726a;font-size:11px;font-weight:900;letter-spacing:.1em}.scheduling-board-header h2{margin:5px 0 0;font-size:20px}.restore-graph-button{min-height:32px;border:1px solid #cbd7e5;border-radius:5px;padding:5px 9px;background:#fff;color:#2f6fed;font:800 12px inherit;cursor:pointer}.restore-graph-button:hover{border-color:#2f6fed;background:#eef4ff}
.flow-stage{position:relative;min-height:560px;flex:1 1 auto;margin-top:14px;overflow:hidden;border:1px solid #dce6ee;border-radius:6px;background:#f9fbfc}.flow-stage :deep(.vue-flow){position:relative;z-index:1;background:transparent}.cycle-lanes{pointer-events:none;position:absolute;inset:0;z-index:0}.cycle-lane{position:absolute;right:18px;left:0;height:1px}.cycle-lane span{position:absolute;top:-9px;left:10px;width:62px;color:#68758a;font-size:10px;font-weight:800;text-align:left}.cycle-lane i{position:absolute;top:0;right:0;left:78px;border-top:1px dashed #b9c8d5}.cycle-lane:first-child span{color:#18726a}
.schedule-node{box-sizing:border-box;width:70px;min-height:48px;border:2px solid #18726a;border-radius:6px;padding:12px 7px;background:#fff;color:#172033;font-size:13px;font-weight:900;line-height:20px;text-align:center;box-shadow:0 4px 8px rgba(23,32,51,.09)}.operation-terminal{border-color:#2f6fed;background:#eef4ff;color:#245ccc}.operation-arithmetic{border-color:#167f78;background:#ecf8f5}.operation-control{border-color:#bf8500;background:#fff8de}.operation-storage{border-color:#31945d;background:#eff9f1}.operation-mux{border-color:#c56721;background:#fff3e9}.schedule-handle{width:9px;height:9px;border:2px solid #18726a;background:#fff}.vue-flow__node.selected .schedule-node{border-color:#2f6fed;box-shadow:0 0 0 3px rgba(47,111,237,.15)}.vue-flow__edge-path{stroke:#405063;stroke-width:2}.vue-flow__edge.selected .vue-flow__edge-path{stroke:#2f6fed;stroke-width:3}
.scheduling-side{min-height:0;display:grid;grid-template-rows:minmax(132px,.72fr) minmax(0,1.28fr) minmax(108px,auto);gap:12px}.scheduling-card{min-height:0;overflow:hidden;padding:16px;border:1px solid #dce5ef;border-radius:8px;background:#fff;box-shadow:0 5px 16px rgba(23,32,51,.05)}.scheduling-card-header{display:flex;align-items:center;justify-content:space-between;gap:10px}.scheduling-card-header h3{margin:0;color:#172033;font-size:15px}.scheduling-card-header span{color:#2f6fed;font-size:11px;font-weight:800}
.algorithm-options{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.algorithm-option{min-height:32px;border:1px solid #cbd7e5;border-radius:5px;padding:5px 9px;background:#fff;color:#68758a;font:800 12px inherit;cursor:pointer}.algorithm-option:hover{border-color:#82b9b2;color:#18726a}.algorithm-option.active{border-color:#18726a;background:#eaf6f4;color:#12655e}
.constraint-fields{display:grid;grid-template-columns:minmax(0,1fr);gap:11px;margin-top:14px}.constraint-fields label{display:grid;min-width:0;gap:6px;color:#344054;font-size:12px;font-weight:800}.constraint-fields input{width:100%;min-height:36px;border:1px solid #cbd7e5;border-radius:5px;padding:7px 9px;background:#fff;color:#172033;font:600 13px inherit}.constraint-fields input:focus{outline:2px solid #c9d9ff;border-color:#2f6fed}
.submit-card{display:flex;align-items:center;gap:10px}.submit-schedule-button{min-height:38px;flex:0 0 auto;border:0;border-radius:6px;padding:8px 14px;background:#2f6fed;color:#fff;font:800 13px inherit;cursor:pointer}.submit-schedule-button:hover{background:#245ccc}.submission-status{margin:0;color:#68758a;font-size:12px;line-height:1.45}.submission-status.pending{color:#315b97}
@media (max-width:980px){.scheduling-shell{height:auto;grid-template-columns:1fr}.scheduling-board{min-height:500px}.scheduling-side{grid-template-rows:150px minmax(240px,auto) 108px}}
</style>
