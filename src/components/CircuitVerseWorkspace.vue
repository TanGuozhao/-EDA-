<template>
  <section class="timing-shell circuitverse-lab-shell">
    <section class="timing-board circuitverse-board" aria-label="CircuitVerse 实验工作区">
      <div class="circuitverse-board-heading">
        <div>
          <span class="circuitverse-kicker">CircuitVerse</span>
          <h2>实验工作区</h2>
        </div>
        <span class="editor-status" :class="editorState">{{ editorStatus }}</span>
      </div>

      <iframe
        v-if="deliveryMode === 'iframe'"
        :src="editorUrl"
        title="CircuitVerse 实验编辑器"
        class="circuitverse-frame"
        @load="editorState = 'ready'"
      />

      <div v-else class="circuitverse-launch-surface">
        <div class="circuit-grid" aria-hidden="true">
          <span v-for="index in 96" :key="index" />
        </div>
        <div class="launch-content">
          <span class="editor-brand">CIRCUITVERSE</span>
          <button class="circuitverse-open-button" type="button" @click="openEditor">
            打开 CircuitVerse
          </button>
        </div>
      </div>
    </section>

    <aside class="timing-side">
      <TimingTaskCard title="题目" eyebrow="任务接口">
        <slot name="question">
          <p class="circuitverse-question-copy">{{ task.prompt || '暂无题目内容' }}</p>
        </slot>
      </TimingTaskCard>

      <TimingTaskCard title="作答区">
        <slot name="answer" :answers="answers" :fields="resolvedAnswerFields">
          <form class="circuitverse-answer-form" @submit.prevent="submitAnswer">
            <template v-for="field in resolvedAnswerFields" :key="field.id">
              <label v-if="field.type !== 'textarea' && field.type !== 'select'" :for="inputId(field)">
                {{ field.label }}
                <input
                  :id="inputId(field)"
                  v-model="answers[field.id]"
                  :type="field.type || 'text'"
                  :placeholder="field.placeholder || ''"
                  :required="Boolean(field.required)"
                >
              </label>

              <label v-else-if="field.type === 'textarea'" :for="inputId(field)">
                {{ field.label }}
                <textarea
                  :id="inputId(field)"
                  v-model="answers[field.id]"
                  :placeholder="field.placeholder || ''"
                  :required="Boolean(field.required)"
                />
              </label>

              <label v-else :for="inputId(field)">
                {{ field.label }}
                <select :id="inputId(field)" v-model="answers[field.id]" :required="Boolean(field.required)">
                  <option value="" disabled>请选择</option>
                  <option v-for="option in field.options || []" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </label>
            </template>
          </form>
        </slot>
      </TimingTaskCard>

      <TimingTaskCard title="提交">
        <div class="circuitverse-submit-row">
          <button class="circuitverse-submit-button" type="button" @click="submitAnswer">提交作答</button>
          <p class="circuitverse-submit-status" :class="submissionState.type">{{ submissionState.message }}</p>
        </div>
      </TimingTaskCard>
    </aside>
  </section>
</template>

<script>
import { computed, ref, watch } from 'vue'
import TimingTaskCard from './TimingTaskCard.vue'

const defaultAnswerFields = [
  {
    id: 'circuitverse_share_url',
    label: 'CircuitVerse 分享链接',
    type: 'url',
    placeholder: 'https://circuitverse.org/simulator/...',
    required: true,
  },
]

export default {
  name: 'CircuitVerseWorkspace',
  components: { TimingTaskCard },
  props: {
    task: {
      type: Object,
      default: () => ({ id: 'circuitverse-lab', prompt: '' }),
    },
    answerFields: {
      type: Array,
      default: () => defaultAnswerFields,
    },
    editorUrl: {
      type: String,
      default: 'https://circuitverse.org/simulator',
    },
    deliveryMode: {
      type: String,
      default: 'new-window',
      validator: (value) => ['new-window', 'iframe'].includes(value),
    },
  },
  emits: ['editor-opened', 'submit'],
  setup(props, { emit }) {
    const answers = ref({})
    const editorState = ref('idle')
    const submissionState = ref({ type: 'idle', message: '等待提交' })

    const editorStatus = computed(() => {
      if (editorState.value === 'ready') return '编辑器已就绪'
      if (editorState.value === 'opened') return '编辑器已打开'
      if (editorState.value === 'blocked') return '浏览器阻止打开'
      return '等待开始'
    })

    const resolvedAnswerFields = computed(() => props.answerFields.length ? props.answerFields : defaultAnswerFields)

    function resetAnswers() {
      answers.value = Object.fromEntries(resolvedAnswerFields.value.map((field) => [field.id, '']))
    }

    function inputId(field) {
      return `circuitverse-${props.task.id || 'lab'}-${field.id}`
    }

    function openEditor() {
      const editorWindow = window.open(props.editorUrl, `circuitverse-${props.task.id || 'lab'}`)
      if (!editorWindow) {
        editorState.value = 'blocked'
        return
      }
      editorWindow.opener = null
      editorState.value = 'opened'
      emit('editor-opened', { taskId: props.task.id || null })
    }

    function submitAnswer() {
      const payload = {
        taskId: props.task.id || null,
        answers: { ...answers.value },
      }
      submissionState.value = { type: 'pending', message: '作答数据已准备' }
      emit('submit', payload)
    }

    watch(
      () => [props.task.id, props.answerFields],
      () => {
        editorState.value = 'idle'
        submissionState.value = { type: 'idle', message: '等待提交' }
        resetAnswers()
      },
      { immediate: true },
    )

    return {
      answers,
      editorState,
      editorStatus,
      inputId,
      openEditor,
      resolvedAnswerFields,
      submissionState,
      submitAnswer,
    }
  },
}
</script>

<style scoped>
.circuitverse-lab-shell{height:100%}.circuitverse-board{min-width:0;overflow:hidden;padding:16px;border:1px solid #dce5ef;border-radius:8px;background:#fff;box-shadow:0 5px 16px rgba(23,32,51,.05)}
.circuitverse-board-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex:0 0 auto;padding-bottom:14px;border-bottom:1px solid #e5ebf2}.circuitverse-kicker{display:block;color:#18726a;font-size:11px;font-weight:900;letter-spacing:.1em}.circuitverse-board-heading h2{margin:5px 0 0;font-size:20px}
.editor-status{display:inline-flex;align-items:center;min-height:28px;padding:4px 8px;border:1px solid #d7e0ea;border-radius:5px;background:#f8fafc;color:#68758a;font-size:11px;font-weight:800;white-space:nowrap}.editor-status.opened,.editor-status.ready{border-color:#9cd8c5;background:#edf9f5;color:#13795b}.editor-status.blocked{border-color:#efb6a8;background:#fff4f1;color:#b42318}
.circuitverse-launch-surface{position:relative;display:flex;min-height:0;flex:1 1 auto;align-items:center;justify-content:center;margin-top:14px;border:1px solid #dce6ee;border-radius:6px;background:#f7faf9;overflow:hidden}.circuit-grid{position:absolute;inset:0;display:grid;grid-template-columns:repeat(12,1fr);grid-template-rows:repeat(8,1fr);opacity:.75}.circuit-grid span{border-right:1px solid #dce6ee;border-bottom:1px solid #dce6ee}.circuit-grid span:nth-child(12n){border-right:0}.circuit-grid span:nth-last-child(-n+12){border-bottom:0}
.launch-content{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;gap:14px}.editor-brand{color:#18726a;font-size:12px;font-weight:900;letter-spacing:.14em}.circuitverse-open-button,.circuitverse-submit-button{min-height:39px;border:0;border-radius:6px;padding:8px 14px;background:#18726a;color:#fff;font:800 13px inherit;cursor:pointer}.circuitverse-open-button:hover{background:#115d57}.circuitverse-submit-button{background:#2f6fed}.circuitverse-submit-button:hover{background:#245ccc}
.circuitverse-frame{width:100%;min-height:0;flex:1 1 auto;margin-top:14px;border:1px solid #dce6ee;border-radius:6px;background:#fff}
.circuitverse-question-copy{margin:14px 0 0;color:#172033;font-size:14px;line-height:1.65}.circuitverse-answer-form{display:grid;gap:12px;padding-top:14px}.circuitverse-answer-form label{display:grid;gap:6px;color:#344054;font-size:12px;font-weight:800}.circuitverse-answer-form input,.circuitverse-answer-form textarea,.circuitverse-answer-form select{width:100%;min-height:38px;border:1px solid #cbd7e5;border-radius:5px;padding:8px 9px;background:#fff;color:#172033;font:600 13px inherit}.circuitverse-answer-form textarea{min-height:92px;resize:vertical}.circuitverse-answer-form input:focus,.circuitverse-answer-form textarea:focus,.circuitverse-answer-form select:focus{outline:2px solid #c9d9ff;border-color:#2f6fed}
.circuitverse-submit-row{display:flex;height:100%;align-items:center;gap:10px}.circuitverse-submit-status{margin:0;color:#68758a;font-size:12px;line-height:1.45}.circuitverse-submit-status.pending{color:#315b97}
@media (max-width:980px){.circuitverse-lab-shell{height:auto}.circuitverse-board{min-height:460px}}
</style>
