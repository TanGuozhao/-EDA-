<template>
  <Teleport to="body">
    <aside
      v-if="bubbleOpen"
      class="tutor-bubble"
      :class="{ 'is-pending': pending }"
      :style="bubbleStyle"
      aria-live="polite"
    >
      <div class="tutor-bubble-head">
        <div class="tutor-bubble-title">
          <span class="tutor-bubble-icon">i</span>
          <span>{{ pending ? '助教生成中' : '助教答疑' }}</span>
        </div>
        <button class="tutor-bubble-close" type="button" title="关闭" @click="closeBubble">x</button>
      </div>
      <div class="tutor-bubble-body" :class="{ 'is-error': !!error }">
        {{ bubbleText }}
      </div>
    </aside>

    <section
      v-if="panelOpen"
      class="tutor-panel"
      :style="panelStyle"
      role="dialog"
      aria-label="EDA 助教答疑面板"
    >
      <header class="tutor-panel-head">
        <div>
          <div class="tutor-panel-title">EDA 助教答疑</div>
          <div class="tutor-panel-subtitle">
            {{ pending ? '正在结合当前页面语境回答' : '可解释选中内容，也可手动提问' }}
          </div>
        </div>
        <div class="tutor-panel-head-actions">
          <button v-if="pending" class="tutor-panel-btn" type="button" @click="stopCurrentRequest">停止</button>
          <button class="tutor-panel-btn" type="button" @click="panelOpen = false">收起</button>
        </div>
      </header>

      <div class="tutor-panel-body">
        <textarea
          v-model="question"
          class="tutor-input"
          rows="5"
          placeholder="输入问题，或选中页面文字后点击“读取选中”。"
        />

        <div class="tutor-panel-actions">
          <button class="tutor-soft-btn" type="button" :disabled="pending" @click="readSelectionIntoInput">读取选中</button>
          <button class="tutor-soft-btn" type="button" :disabled="pending" @click="explainSelection">解释选中</button>
          <button class="tutor-primary-btn" type="button" :disabled="!canAsk" @click="askCurrentQuestion">提问</button>
        </div>

        <div v-if="contextHint" class="tutor-context-hint">{{ contextHint }}</div>
        <div class="tutor-result" :class="{ 'is-error': !!error }">
          {{ resultText }}
        </div>
      </div>
    </section>

    <section
      ref="shellRef"
      class="tutor-orb"
      :class="{
        'is-open': menuOpen,
        'is-dragging': dragging,
        'has-result': hasResult,
        'is-pending': pending
      }"
      :style="orbStyle"
      aria-label="EDA 助教悬浮球"
    >
      <div class="tutor-orb-actions" aria-hidden="true">
        <button class="tutor-orb-action is-accent" type="button" title="解释选中" :disabled="pending" @click="explainSelection">释</button>
        <button class="tutor-orb-action" type="button" title="打开面板" @click="openPanel">问</button>
        <button class="tutor-orb-action" type="button" title="读取选中" :disabled="pending" @click="readSelectionIntoInput">取</button>
        <button class="tutor-orb-action is-danger" type="button" :title="pending ? '停止生成' : '清空内容'" @click="pending ? stopCurrentRequest() : clearContent()">
          {{ pending ? '停' : '清' }}
        </button>
      </div>

      <button
        ref="ballRef"
        class="tutor-orb-ball"
        type="button"
        title="展开 EDA 助教"
        :aria-expanded="menuOpen"
        @pointerdown="onBallPointerDown"
      >
        <span class="tutor-orb-glow" aria-hidden="true"></span>
        <span class="tutor-orb-content" aria-hidden="true">
          <span class="tutor-orb-core">i</span>
          <span class="tutor-orb-label">助教</span>
        </span>
        <span v-if="pending" class="tutor-orb-badge is-pending"></span>
        <span v-else-if="hasResult" class="tutor-orb-badge is-ready"></span>
      </button>
    </section>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { askTutorStream } from '../api'

const ORB_SIZE = 76
const VIEWPORT_MARGIN = 16
const STORAGE_KEY = 'eda-tutor-orb-position-v1'

const route = useRoute()
const shellRef = ref(null)
const ballRef = ref(null)
const menuOpen = ref(false)
const panelOpen = ref(false)
const bubbleOpen = ref(false)
const dragging = ref(false)
const pending = ref(false)
const question = ref('')
const answer = ref('')
const error = ref('')
const contextHint = ref('')
const position = ref(readStoredPosition())
const dragSession = ref(null)
const abortController = ref(null)

const orbStyle = computed(() => ({
  left: `${position.value.x}px`,
  top: `${position.value.y}px`,
}))

const panelStyle = computed(() => {
  const viewport = getViewport()
  const width = Math.min(420, viewport.width - 34)
  const height = Math.min(560, viewport.height - 54)
  const left = clamp(position.value.x - width - 18, VIEWPORT_MARGIN, viewport.width - width - VIEWPORT_MARGIN)
  const top = clamp(position.value.y + ORB_SIZE / 2 - height / 2, VIEWPORT_MARGIN, viewport.height - height - VIEWPORT_MARGIN)
  return { left: `${left}px`, top: `${top}px` }
})

const bubbleStyle = computed(() => {
  const viewport = getViewport()
  const width = Math.min(340, viewport.width - 34)
  const left = clamp(position.value.x - width - 12, VIEWPORT_MARGIN, viewport.width - width - VIEWPORT_MARGIN)
  const top = clamp(position.value.y + 6, VIEWPORT_MARGIN, viewport.height - 190)
  return { left: `${left}px`, top: `${top}px` }
})

const hasResult = computed(() => !!answer.value.trim() || !!error.value.trim())
const canAsk = computed(() => !!question.value.trim() && !pending.value)
const resultText = computed(() => {
  if (error.value) return error.value
  if (answer.value) return answer.value
  if (pending.value) return '正在生成回答...'
  return '回答会显示在这里。'
})
const bubbleText = computed(() => {
  if (error.value) return error.value
  if (answer.value) return answer.value.slice(0, 220)
  if (pending.value) return '正在读取页面语境并生成回答...'
  return '正在等待问题。'
})

onMounted(() => {
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerCancel)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  stopCurrentRequest()
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerCancel)
  window.removeEventListener('resize', onResize)
})

function getViewport() {
  return { width: window.innerWidth, height: window.innerHeight }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), Math.max(min, max))
}

function clampPosition(nextPosition) {
  const viewport = getViewport()
  return {
    x: clamp(nextPosition.x, 0, viewport.width - ORB_SIZE),
    y: clamp(nextPosition.y, VIEWPORT_MARGIN, viewport.height - ORB_SIZE - VIEWPORT_MARGIN),
  }
}

function readStoredPosition() {
  const viewport = typeof window === 'undefined' ? { width: 1280, height: 720 } : getViewport()
  const fallback = {
    x: viewport.width - ORB_SIZE - VIEWPORT_MARGIN,
    y: Math.round(viewport.height * 0.42),
  }
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (!saved || typeof saved.x !== 'number' || typeof saved.y !== 'number') return fallback
    return {
      x: clamp(saved.x, 0, viewport.width - ORB_SIZE),
      y: clamp(saved.y, VIEWPORT_MARGIN, viewport.height - ORB_SIZE - VIEWPORT_MARGIN),
    }
  } catch {
    return fallback
  }
}

function savePosition() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(position.value))
}

function getSelectionText() {
  return String(window.getSelection?.().toString() || '').trim()
}

function getPageText() {
  const candidates = [
    document.querySelector('main'),
    document.querySelector('[role="main"]'),
    document.querySelector('article'),
    document.querySelector('#app'),
  ]
  const element = candidates.find((item) => item?.textContent?.trim())
  return String(element?.innerText || document.body?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 3600)
}

function buildContext() {
  const selectedText = getSelectionText()
  return {
    page_title: document.title || 'EDA 学习平台',
    route_path: route.fullPath,
    selected_text: selectedText,
    page_text: getPageText(),
    learning_stage: route.name ? String(route.name) : '',
    task_text: selectedText ? `用户选中了：${selectedText}` : '',
  }
}

function openPanel() {
  panelOpen.value = true
  bubbleOpen.value = false
  menuOpen.value = false
}

function closeBubble() {
  if (pending.value) stopCurrentRequest()
  bubbleOpen.value = false
}

function readSelectionIntoInput() {
  openPanel()
  const selected = getSelectionText()
  if (!selected) {
    error.value = '当前没有检测到选中文字。'
    return
  }
  error.value = ''
  question.value = `请解释这段内容：${selected}`
}

function explainSelection() {
  const selected = getSelectionText()
  if (!selected) {
    openPanel()
    error.value = '请先在页面中选中一段文字，再点击解释选中。'
    return
  }
  question.value = `请解释这段内容：${selected}`
  askCurrentQuestion()
}

function clearContent() {
  stopCurrentRequest()
  question.value = ''
  answer.value = ''
  error.value = ''
  contextHint.value = ''
  bubbleOpen.value = false
  menuOpen.value = false
}

function stopCurrentRequest() {
  abortController.value?.abort()
  abortController.value = null
  pending.value = false
}

async function askCurrentQuestion() {
  const cleanQuestion = question.value.trim()
  if (!cleanQuestion || pending.value) return

  const context = buildContext()
  abortController.value?.abort()
  abortController.value = new AbortController()
  pending.value = true
  answer.value = ''
  error.value = ''
  contextHint.value = `语境：${context.page_title}${context.route_path ? ` | ${context.route_path}` : ''}`
  bubbleOpen.value = true
  menuOpen.value = false

  try {
    await askTutorStream(
      {
        question: cleanQuestion,
        context,
        max_tokens: 700,
        temperature: 0.2,
      },
      {
        signal: abortController.value.signal,
        onDelta: (delta) => {
          if (delta) answer.value += delta
        },
      }
    )
  } catch (caughtError) {
    if (caughtError?.name === 'AbortError') return
    error.value = caughtError instanceof Error ? caughtError.message : String(caughtError)
  } finally {
    pending.value = false
    abortController.value = null
  }
}

function onBallPointerDown(event) {
  if (!event.isPrimary || event.button !== 0) return
  dragSession.value = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    startPosition: { ...position.value },
    moved: false,
  }
  ballRef.value?.setPointerCapture(event.pointerId)
  event.preventDefault()
}

function onPointerMove(event) {
  const session = dragSession.value
  if (!session || session.pointerId !== event.pointerId) return

  const dx = event.clientX - session.startX
  const dy = event.clientY - session.startY
  if (!session.moved && Math.hypot(dx, dy) >= 4) {
    session.moved = true
    dragging.value = true
    menuOpen.value = false
  }
  if (!session.moved) return

  position.value = clampPosition({
    x: session.startPosition.x + dx,
    y: session.startPosition.y + dy,
  })
}

function onPointerUp(event) {
  const session = dragSession.value
  if (!session || session.pointerId !== event.pointerId) return

  ballRef.value?.releasePointerCapture(event.pointerId)
  dragSession.value = null
  dragging.value = false

  if (!session.moved) {
    menuOpen.value = !menuOpen.value
    return
  }
  position.value = clampPosition(position.value)
  savePosition()
}

function onPointerCancel(event) {
  if (dragSession.value?.pointerId !== event.pointerId) return
  dragSession.value = null
  dragging.value = false
}

function onResize() {
  position.value = clampPosition(position.value)
  savePosition()
}
</script>

<style scoped>
.tutor-orb {
  position: fixed;
  z-index: 80;
  width: 76px;
  height: 76px;
  touch-action: none;
  filter: drop-shadow(0 22px 30px rgba(47, 111, 237, 0.24));
}

.tutor-orb-ball {
  position: relative;
  display: grid;
  width: 76px;
  height: 76px;
  place-items: center;
  overflow: hidden;
  border: 0;
  border-radius: 50%;
  background:
    radial-gradient(circle at 34% 25%, rgba(255, 255, 255, 0.95) 0 10%, rgba(162, 205, 255, 0.95) 11% 26%, transparent 27%),
    radial-gradient(circle at 62% 74%, rgba(28, 72, 174, 0.96) 0 24%, transparent 25%),
    linear-gradient(145deg, #7dd2ff 0%, #2f6fed 48%, #163d96 100%);
  color: #fff;
  cursor: grab;
  box-shadow:
    inset 0 8px 18px rgba(255, 255, 255, 0.46),
    inset 0 -14px 24px rgba(17, 49, 120, 0.48),
    0 18px 42px rgba(47, 111, 237, 0.42);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.tutor-orb-ball:hover {
  transform: translateY(-2px) scale(1.02);
}

.tutor-orb-ball:active {
  cursor: grabbing;
}

.tutor-orb-glow {
  position: absolute;
  inset: -10px;
  border-radius: 50%;
  background: conic-gradient(from 200deg, rgba(117, 210, 255, 0), rgba(117, 210, 255, 0.78), rgba(47, 111, 237, 0), rgba(255, 255, 255, 0.42));
  opacity: 0.56;
  animation: tutor-orb-spin 6s linear infinite;
}

.tutor-orb-content {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  gap: 2px;
}

.tutor-orb-core {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.65);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.42);
  font-size: 19px;
  font-weight: 900;
  line-height: 1;
}

.tutor-orb-label {
  font-size: 13px;
  font-weight: 900;
  line-height: 1;
  text-shadow: 0 1px 8px rgba(10, 31, 77, 0.45);
}

.tutor-orb-badge {
  position: absolute;
  top: 7px;
  right: 7px;
  z-index: 2;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 0 0 5px rgba(40, 209, 124, 0.18);
}

.tutor-orb-badge.is-pending {
  background: #28d17c;
  animation: tutor-badge-pulse 1.25s ease-in-out infinite;
}

.tutor-orb-badge.is-ready {
  background: #7dd2ff;
}

.tutor-orb-actions {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.tutor-orb-action {
  position: absolute;
  top: 17px;
  left: 17px;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(238, 245, 255, 0.92));
  color: #2f6fed;
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.8),
    0 14px 30px rgba(23, 32, 51, 0.2);
  font: 900 15px/1 "Microsoft YaHei", Arial, sans-serif;
  opacity: 0;
  pointer-events: auto;
  transform: translate(0, 0) scale(0.7);
  transition: transform 0.22s cubic-bezier(0.2, 0.85, 0.25, 1), opacity 0.18s ease, background 0.18s ease;
}

.tutor-orb-action:hover:not(:disabled) {
  background: #2f6fed;
  color: #fff;
}

.tutor-orb-action:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.tutor-orb-action.is-accent {
  color: #fff;
  background: linear-gradient(145deg, #3f8cff, #1f57cf);
}

.tutor-orb-action.is-danger {
  color: #b42318;
}

.tutor-orb.is-open .tutor-orb-action {
  opacity: 1;
}

.tutor-orb.is-open .tutor-orb-action:nth-child(1) {
  transform: translate(-92px, -38px) scale(1);
}

.tutor-orb.is-open .tutor-orb-action:nth-child(2) {
  transform: translate(-112px, 18px) scale(1);
}

.tutor-orb.is-open .tutor-orb-action:nth-child(3) {
  transform: translate(-78px, 72px) scale(1);
}

.tutor-orb.is-open .tutor-orb-action:nth-child(4) {
  transform: translate(-20px, 96px) scale(1);
}

.tutor-panel,
.tutor-bubble {
  position: fixed;
  z-index: 79;
  border: 1px solid rgba(191, 207, 232, 0.84);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 22px 60px rgba(23, 32, 51, 0.22);
  backdrop-filter: blur(16px);
}

.tutor-panel {
  display: flex;
  width: min(420px, calc(100vw - 34px));
  max-height: min(560px, calc(100vh - 54px));
  flex-direction: column;
  overflow: hidden;
  animation: tutor-panel-in 0.32s cubic-bezier(0.2, 0.85, 0.25, 1);
}

.tutor-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(217, 226, 239, 0.9);
  padding: 14px 16px;
}

.tutor-panel-title {
  color: #172033;
  font-size: 16px;
  font-weight: 900;
}

.tutor-panel-subtitle {
  margin-top: 2px;
  color: #667085;
  font-size: 12px;
  line-height: 1.4;
}

.tutor-panel-head-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}

.tutor-panel-btn,
.tutor-soft-btn,
.tutor-primary-btn {
  min-height: 34px;
  border-radius: 6px;
  padding: 7px 12px;
  font: 800 13px/1.2 "Microsoft YaHei", Arial, sans-serif;
  cursor: pointer;
}

.tutor-panel-btn,
.tutor-soft-btn {
  border: 1px solid #d9e2ef;
  background: #fff;
  color: #172033;
}

.tutor-primary-btn {
  border: 0;
  background: #2f6fed;
  color: #fff;
}

.tutor-soft-btn:disabled,
.tutor-primary-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.tutor-panel-body {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
  padding: 14px 16px 16px;
}

.tutor-input {
  width: 100%;
  min-height: 96px;
  resize: vertical;
  border: 1px solid #d9e2ef;
  border-radius: 6px;
  padding: 10px 11px;
  color: #172033;
  font: 14px/1.65 "Microsoft YaHei", Arial, sans-serif;
}

.tutor-input:focus {
  border-color: #2f6fed;
  outline: 2px solid rgba(47, 111, 237, 0.18);
}

.tutor-panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tutor-context-hint {
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.tutor-result {
  min-height: 130px;
  border: 1px solid #d9e2ef;
  border-radius: 6px;
  background: #f9fbff;
  padding: 12px;
  color: #172033;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.tutor-result.is-error,
.tutor-bubble-body.is-error {
  color: #b42318;
}

.tutor-bubble {
  width: min(340px, calc(100vw - 34px));
  padding: 14px 16px;
  animation: tutor-panel-in 0.28s cubic-bezier(0.2, 0.85, 0.25, 1);
}

.tutor-bubble::after {
  position: absolute;
  right: -8px;
  bottom: 28px;
  width: 16px;
  height: 16px;
  border-top: 1px solid rgba(191, 207, 232, 0.84);
  border-right: 1px solid rgba(191, 207, 232, 0.84);
  background: rgba(255, 255, 255, 0.94);
  content: "";
  transform: rotate(45deg);
}

.tutor-bubble-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.tutor-bubble-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #172033;
  font-size: 14px;
  font-weight: 900;
}

.tutor-bubble-icon {
  display: grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 50%;
  background: #eef4ff;
  color: #2f6fed;
  font-size: 12px;
  font-weight: 900;
}

.tutor-bubble-close {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid #d9e2ef;
  border-radius: 50%;
  background: #fff;
  color: #667085;
  cursor: pointer;
  font-weight: 900;
}

.tutor-bubble-body {
  color: #344054;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
}

@keyframes tutor-orb-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes tutor-badge-pulse {
  0%,
  100% {
    transform: scale(0.9);
  }
  50% {
    transform: scale(1.08);
  }
}

@keyframes tutor-panel-in {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 680px) {
  .tutor-panel,
  .tutor-bubble {
    left: 17px !important;
    right: 17px;
    width: auto;
  }
}
</style>
