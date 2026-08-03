<template>
  <section class="hls-page">
    <header class="hls-topbar">
      <div>
        <span class="hls-kicker">High-Level Synthesis</span>
        <h2>高级综合第一关</h2>
        <p>把操作 DAG 排进时钟周期，或在 PPA 方案中选出柏拉图最优解。</p>
      </div>
      <div class="hls-tabs" role="tablist" aria-label="HLS 题型">
        <button
          v-for="item in challengeKinds"
          :key="item.id"
          type="button"
          :class="{ active: selectedKind === item.id }"
          @click="loadChallenge(item.id)"
        >
          {{ item.label }}
        </button>
      </div>
    </header>

    <p v-if="loading" class="hls-state">正在加载题目...</p>
    <p v-else-if="error" class="hls-state error">{{ error }}</p>

    <section v-else-if="challenge" class="hls-layout">
      <section class="hls-board">
        <header class="hls-panel-header">
          <div>
            <span class="hls-kicker">{{ challenge.title }}</span>
            <h3>{{ challenge.prompt }}</h3>
          </div>
          <div v-if="isDagChallenge" class="hls-panel-actions">
            <button type="button" class="hls-add-cycle" title="新增周期" :disabled="!canAddCycle" @click="addCycle">+</button>
            <button type="button" class="hls-ghost" @click="resetLayout">重置布局</button>
          </div>
        </header>

        <div
          v-if="isDagChallenge"
          ref="flowStage"
          class="hls-flow-stage"
          :style="{ height: `${laneCanvasHeight}px` }"
          @pointerdown.capture="rememberDraggedNode"
        >
          <VueFlow
            ref="flowInstance"
            v-model:nodes="flowNodes"
            v-model:edges="flowEdges"
            :default-viewport="{ x: 0, y: 0, zoom: 1 }"
            :pan-on-drag="false"
            :zoom-on-scroll="false"
            :zoom-on-pinch="false"
            :zoom-on-double-click="false"
            :auto-pan-on-node-drag="false"
            :fit-view-on-init="false"
          >
            <svg class="hls-lanes" :height="laneCanvasHeight" width="760" aria-hidden="true">
              <text class="hls-tray-title" x="14" y="26">待调度操作</text>
              <line class="hls-tray-divider" x1="14" y1="176" x2="742" y2="176" />
              <g v-for="cycle in cycles" :key="cycle" :transform="`translate(0, ${laneY(cycle)})`">
                <text x="14" y="4">Cycle {{ cycle }}</text>
                <line x1="100" y1="0" x2="742" y2="0" />
              </g>
            </svg>
            <template #node-hls="nodeProps">
              <Handle type="target" :position="Position.Top" class="hls-handle" />
              <div
                class="hls-node"
                :class="[`op-${nodeProps.data.operationType}`, { 'is-unscheduled': !nodeProps.data.scheduled }]"
                :style="{ width: `${nodeProps.data.nodeWidth}px`, height: `${nodeProps.data.nodeHeight}px`, padding: `${nodeProps.data.nodePadding}px` }"
              >
                <strong :style="{ fontSize: `${nodeProps.data.titleFontSize}px` }">{{ nodeProps.data.label }}</strong>
                <span :style="{ fontSize: `${nodeProps.data.subtitleFontSize}px` }">{{ nodeProps.data.operationType }}</span>
              </div>
              <Handle type="source" :position="Position.Bottom" class="hls-handle" />
            </template>
          </VueFlow>

        </div>

        <div v-else class="pareto-grid">
          <label
            v-for="option in challenge.options"
            :key="option.id"
            class="pareto-option"
            :class="{ selected: selectedOptions.includes(option.id) }"
          >
            <input v-model="selectedOptions" type="checkbox" :value="option.id">
            <strong>{{ option.name }}</strong>
            <span>性能 {{ option.performance }}</span>
            <span>功耗 {{ option.power }}</span>
            <span>面积 {{ option.area }}</span>
          </label>
        </div>
      </section>

      <aside class="hls-side">
        <section class="hls-card">
          <h3>约束</h3>
          <dl>
            <template v-if="challenge.deadline_cycles">
              <dt>总周期</dt>
              <dd>{{ challenge.deadline_cycles }}</dd>
            </template>
            <template v-if="challenge.resource_limits">
              <dt>资源</dt>
              <dd>{{ formatResources(challenge.resource_limits) }}</dd>
            </template>
            <template v-if="challenge.hu_resource_count">
              <dt>HU 资源数</dt>
              <dd>{{ challenge.hu_resource_count }}</dd>
            </template>
            <template v-if="challenge.constraints">
              <dt>PPA 约束</dt>
              <dd>{{ formatParetoConstraints(challenge.constraints) }}</dd>
            </template>
          </dl>
        </section>

        <section class="hls-card">
          <h3>提交结果</h3>
          <button type="button" class="hls-submit" :disabled="submitting" @click="submitAnswer">
            {{ submitting ? '判题中...' : '提交' }}
          </button>
          <div v-if="result" class="hls-result" :class="{ success: result.correct }">
            <strong>{{ result.correct ? '正确' : `得分 ${result.score}` }}</strong>
            <p v-if="!result.feedback.length">这份调度满足当前题目的依赖和资源约束。</p>
            <ul v-else>
              <li v-for="(item, index) in result.feedback.slice(0, 8)" :key="index">{{ item.message }}</li>
            </ul>
          </div>
        </section>
      </aside>
    </section>
  </section>
</template>

<script>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Handle, MarkerType, Position, VueFlow } from '@vue-flow/core'
import { fetchCurrentHlsChallenge, submitHlsChallenge } from '../api'
import {
  createInitialScheduleNodes,
  createScheduleBoardLayout,
  cycleLimit,
  cycleLabels,
  laneY as boardLaneY,
  reflowScheduleNodes,
  scheduleSubmission,
  snapNodeToBoard,
} from '../hls/scheduleBoard.mjs'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

export default {
  name: 'HighLevelSynthesis',
  components: { Handle, VueFlow },
  setup() {
    const challengeKinds = [
      { id: 'asap', label: 'ASAP' },
      { id: 'alap', label: 'ALAP' },
      { id: 'list', label: 'List' },
      { id: 'hu', label: 'HU' },
      { id: 'pareto', label: 'Pareto' },
    ]
    const selectedKind = ref('asap')
    const challenge = ref(null)
    const flowNodes = ref([])
    const flowEdges = ref([])
    const selectedOptions = ref([])
    const flowStage = ref(null)
    const flowInstance = ref(null)
    const draggedNodeId = ref(null)
    const visibleCycleCount = ref(3)
    const result = ref(null)
    const loading = ref(false)
    const submitting = ref(false)
    const error = ref('')
    const boardLayout = computed(() => createScheduleBoardLayout(visibleCycleCount.value))
    const cycles = computed(() => cycleLabels(boardLayout.value))
    const laneCanvasHeight = computed(() => boardLayout.value.stageHeight)
    const canAddCycle = computed(() => {
      if (!challenge.value?.dag) return false
      return visibleCycleCount.value < cycleLimit(challenge.value.dag, challenge.value.deadline_cycles)
    })
    const isDagChallenge = computed(() => challenge.value && challenge.value.kind !== 'pareto')

    async function loadChallenge(kind) {
      selectedKind.value = kind
      loading.value = true
      error.value = ''
      result.value = null
      selectedOptions.value = []
      try {
        challenge.value = await fetchCurrentHlsChallenge(kind)
        if (!Number.isInteger(challenge.value.initial_cycle_count) || challenge.value.initial_cycle_count < 3) {
          throw new Error('题目缺少有效的初始周期配置')
        }
        visibleCycleCount.value = challenge.value.initial_cycle_count
        resetLayout()
      } catch (err) {
        error.value = err.message || '加载失败'
      } finally {
        loading.value = false
      }
    }

    function resetLayout() {
      if (!challenge.value?.dag) return
      flowNodes.value = createInitialScheduleNodes(challenge.value.dag, boardLayout.value)
      flowEdges.value = challenge.value.dag.edges.map((edge) => ({
        id: `${edge.from}-${edge.to}`,
        source: edge.from,
        target: edge.to,
        markerEnd: MarkerType.ArrowClosed,
      }))
    }

    function rememberDraggedNode(event) {
      const nodeElement = event.target.closest('.vue-flow__node')
      draggedNodeId.value = nodeElement?.dataset.id || null
    }

    async function snapDraggedNode(event) {
      const nodeId = draggedNodeId.value
      draggedNodeId.value = null
      if (!nodeId || nodeId === challenge.value?.dag?.start_node || !challenge.value?.dag) return
      const pointer = pointerInStage(event)
      if (!pointer) return
      await new Promise((resolve) => requestAnimationFrame(resolve))
      const node = flowNodes.value.find((item) => item.id === nodeId)
      if (!node) return
      const snappedNode = snapNodeToBoard(node, challenge.value.dag, boardLayout.value, pointer)
      const nextNodes = flowNodes.value.map((item) => item.id === nodeId ? snappedNode : item)
      flowNodes.value = nextNodes
      await nextTick()
      flowInstance.value?.setNodes(nextNodes)
    }

    function buildDagSubmission() {
      return {
        assignments: scheduleSubmission(flowNodes.value, challenge.value.dag),
        edges: flowEdges.value.map((edge) => ({ from: edge.source, to: edge.target })),
      }
    }

    function pointerInStage(event) {
      if (!flowStage.value) return null
      const rect = flowStage.value.getBoundingClientRect()
      return {
        x: event.clientX - rect.left + flowStage.value.scrollLeft,
        y: event.clientY - rect.top + flowStage.value.scrollTop,
      }
    }

    function addCycle() {
      if (!canAddCycle.value || !challenge.value?.dag) return
      visibleCycleCount.value += 1
      flowNodes.value = reflowScheduleNodes(flowNodes.value, challenge.value.dag, boardLayout.value)
    }

    function laneY(cycle) {
      return boardLaneY(boardLayout.value, cycle)
    }


    async function submitAnswer() {
      if (!challenge.value) return
      submitting.value = true
      result.value = null
      try {
        const payload = challenge.value.kind === 'pareto'
          ? { selected_option_ids: selectedOptions.value }
          : buildDagSubmission()
        result.value = await submitHlsChallenge(challenge.value.id, payload)
      } catch (err) {
        result.value = { correct: false, score: 0, feedback: [{ message: err.message || '提交失败' }] }
      } finally {
        submitting.value = false
      }
    }

    function formatResources(resources) {
      return Object.entries(resources).map(([name, count]) => `${name}: ${count}`).join(' / ')
    }

    function formatParetoConstraints(constraints) {
      return constraints.map((item) => `${item.metric} ${item.operator} ${item.value}`).join(' / ')
    }

    onMounted(() => {
      window.addEventListener('pointerup', snapDraggedNode, true)
      loadChallenge('asap')
    })

    onBeforeUnmount(() => {
      window.removeEventListener('pointerup', snapDraggedNode, true)
    })

    return {
      Handle,
      Position,
      VueFlow,
      challenge,
      challengeKinds,
      addCycle,
      canAddCycle,
      cycles,
      error,
      flowStage,
      flowInstance,
      flowEdges,
      flowNodes,
      formatParetoConstraints,
      formatResources,
      isDagChallenge,
      laneCanvasHeight,
      laneY,
      loadChallenge,
      loading,
      resetLayout,
      result,
      selectedKind,
      selectedOptions,
      rememberDraggedNode,
      snapDraggedNode,
      submitAnswer,
      submitting,
    }
  },
}
</script>

<style scoped>
.hls-page{width:100%;max-width:1360px;margin:0 auto;color:#172033}.hls-topbar{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin-bottom:18px}.hls-kicker{display:block;color:#1f7a8c;font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}.hls-topbar h2{margin:6px 0 4px;font-size:32px}.hls-topbar p{margin:0;color:#667085;line-height:1.5}.hls-tabs{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;max-width:460px}.hls-tabs button,.hls-ghost{min-height:34px;border:1px solid #cbd7e5;border-radius:6px;padding:6px 10px;background:#fff;color:#1f7a8c;font:800 13px inherit;cursor:pointer}.hls-tabs button.active{border-color:#1f7a8c;background:#e8f3f5;color:#0f4c5c}
.hls-layout{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:18px}.hls-board,.hls-card{border:1px solid #d8e1e8;border-radius:8px;background:#fff;box-shadow:0 8px 20px rgba(19,32,51,.06)}.hls-board{min-height:650px;padding:16px}.hls-panel-header{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;padding-bottom:12px;border-bottom:1px solid #e5ebf2}.hls-panel-header h3{max-width:820px;margin:5px 0 0;font-size:18px;line-height:1.45}.hls-panel-actions{display:flex;align-items:center;gap:8px}.hls-flow-stage{position:relative;margin-top:14px;overflow:auto;border:1px solid #e2e8f0;border-radius:7px;background:#fbfcfe}.hls-flow-stage :deep(.vue-flow){position:relative;min-width:760px;background:transparent}.hls-flow-stage :deep(.vue-flow__pane),.hls-flow-stage :deep(.vue-flow__viewport){background:transparent}.hls-lanes{pointer-events:none;position:absolute;top:0;left:0;overflow:visible;z-index:-1}.hls-lanes text{fill:#667085;font-size:12px;font-weight:900}.hls-lanes line{stroke:#b8c6d5;stroke-dasharray:4 3;stroke-width:1}.hls-lanes .hls-tray-divider{stroke:#d8e1e8;stroke-dasharray:none}.hls-lanes .hls-tray-title{fill:#1f7a8c;font-size:13px}
.hls-node{box-sizing:border-box;border:2px solid #1f7a8c;border-radius:6px;background:#fff;text-align:center;box-shadow:0 5px 10px rgba(19,32,51,.1)}.hls-node strong{display:block;line-height:1.1}.hls-node span{display:block;margin-top:2px;color:#667085;font-weight:800;line-height:1.1}.hls-node.is-unscheduled{border-style:dashed;background:#fff}.op-terminal{border-color:#2f6fed;background:#eef4ff}.op-add{border-color:#1f7a8c;background:#ecf8f5}.op-mul{border-color:#9c5a10;background:#fff6e8}.op-cmp{border-color:#7a4fd1;background:#f3efff}.hls-handle{width:9px;height:9px;border:2px solid #1f7a8c;background:#fff}.hls-add-cycle{width:34px;height:34px;border:1px solid #1f7a8c;border-radius:6px;background:#fff;color:#1f7a8c;font:900 24px/1 inherit;cursor:pointer}.hls-add-cycle:disabled{border-color:#cbd7e5;color:#98a2b3;cursor:not-allowed}
.hls-side{display:grid;grid-template-rows:auto 1fr;gap:14px}.hls-card{padding:16px}.hls-card h3{margin:0 0 12px;font-size:16px}.hls-card dl{display:grid;grid-template-columns:80px minmax(0,1fr);gap:8px;margin:0;color:#172033;font-size:13px}.hls-card dt{color:#667085;font-weight:800}.hls-card dd{margin:0;font-weight:800}.hls-submit{width:100%;min-height:40px;border:0;border-radius:6px;background:#2f6fed;color:#fff;font:900 14px inherit;cursor:pointer}.hls-submit:disabled{opacity:.6;cursor:not-allowed}.hls-result{margin-top:14px;padding:12px;border-radius:7px;background:#fff3f0;color:#b42318;font-size:13px;line-height:1.5}.hls-result.success{background:#eaf8f0;color:#237249}.hls-result strong{display:block;margin-bottom:6px}.hls-result ul{margin:0;padding-left:18px}.hls-result p{margin:0}.hls-state{padding:30px;text-align:center;color:#667085}.hls-state.error{color:#b42318}
.pareto-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:16px}.pareto-option{display:grid;grid-template-columns:auto 1fr repeat(3,72px);align-items:center;gap:10px;min-height:72px;border:1px solid #d8e1e8;border-radius:8px;padding:12px;background:#fbfcfe;cursor:pointer}.pareto-option.selected{border-color:#1f7a8c;background:#e8f3f5}.pareto-option strong{font-size:15px}.pareto-option span{color:#667085;font-size:12px;font-weight:800}
@media (max-width:980px){.hls-topbar{align-items:flex-start;flex-direction:column}.hls-layout{grid-template-columns:1fr}.pareto-grid{grid-template-columns:1fr}.pareto-option{grid-template-columns:auto 1fr}.hls-board{min-height:560px}}
</style>
