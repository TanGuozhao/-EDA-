<template>
  <section class="timing-shell">
    <HorizontalTimingGraph
      v-if="horizontalLayout"
      class="timing-board"
      :layout="horizontalLayout"
      :selected-node="selectedNode"
      :selected-path="selectedPath"
      @select-node="selectNode"
    />
    <div v-else class="timing-board timing-empty-board">
      后端题目生成失败，当前没有可展示的时序图。
    </div>

    <aside class="timing-side">
      <TimingTaskCard title="题目" :eyebrow="questionTypeLabel">
        <template #action>
          <button
            class="timing-new-question"
            type="button"
            :disabled="isGenerating || (questions.length > 0 && questionIndex >= questions.length - 1)"
            @click="nextQuestion"
          >
            {{ isGenerating ? '生成中' : nextQuestionLabel }}
          </button>
        </template>
        <p v-if="question" class="timing-question-copy">{{ question.prompt }}</p>
        <p v-if="question && isCalculationQuestion" class="timing-question-meta">
          填写结点：{{ question.target_node_ids.join('、') }}
        </p>
        <p v-else-if="question?.type === 'shortest_path'" class="timing-question-meta">
          从 {{ question.source_node_id }} 到 {{ question.target_node_id }} 选择总耗时最小的路径。
        </p>
        <p v-else-if="question?.type === 'path_delay'" class="timing-question-meta">
          信号路径：{{ question.path.join(' -> ') }}
        </p>
        <p v-if="generationError" class="timing-generation-error">{{ generationError }}</p>
      </TimingTaskCard>

      <TimingTaskCard title="作答区">
        <div v-if="isGenerating" class="timing-answer-placeholder">正在从后端生成题目。</div>
        <div v-else-if="!question" class="timing-answer-placeholder">题目生成失败，请查看错误信息。</div>
        <NodeBlankList
          v-else-if="isCalculationQuestion"
          v-model="answers"
          :target-node-ids="question.target_node_ids"
        />
        <div v-else-if="question.type === 'path_delay'" class="path-delay-answer">
          <div class="signal-path-strip">
            <span v-for="(nodeId, index) in question.path" :key="`${nodeId}-${index}`">{{ nodeId }}</span>
          </div>
          <label class="path-delay-input">
            总耗时（纳秒）
            <input v-model="totalDelay" type="number" step="any" inputmode="decimal" />
          </label>
        </div>
        <div v-else class="path-answer-area">
          <PathNodeMap
            :layout="pathMapLayout"
            :source-node-id="question.source_node_id"
            :target-node-id="question.target_node_id"
            :selected-path="selectedPath"
            :current-node-id="selectedNode"
          />
          <p class="path-answer-text">{{ selectedPath.join(' -> ') }}</p>
        </div>
      </TimingTaskCard>

      <TimingTaskCard title="提交">
        <div class="timing-submit-row">
          <button
            class="timing-answer-submit"
            type="button"
            :disabled="!challengeId || isSubmitting || isGenerating"
            @click="submitAnswer"
          >
            {{ isSubmitting ? '提交中' : '提交答案' }}
          </button>
          <p class="timing-submit-status" :class="submission.type">{{ submission.message }}</p>
        </div>
      </TimingTaskCard>
    </aside>
  </section>
</template>

<script>
import { computed, onMounted, ref } from 'vue'
import { fetchCurrentTimingChallenge, validateTimingChallenge } from '../api'
import HorizontalTimingGraph from '../components/HorizontalTimingGraph.vue'
import NodeBlankList from '../components/NodeBlankList.vue'
import PathNodeMap from '../components/PathNodeMap.vue'
import TimingTaskCard from '../components/TimingTaskCard.vue'

const calculationTypes = new Set(['arrival_time', 'required_time', 'slack'])
const questionLabels = {
  arrival_time: '到达时间',
  required_time: '要求时间',
  slack: '裕量',
  shortest_path: '最短路径',
  path_delay: '路径总耗时',
}

export default {
  name: 'BlankTimingAnalysis',
  components: { HorizontalTimingGraph, NodeBlankList, PathNodeMap, TimingTaskCard },
  setup() {
    const horizontalLayout = ref(null)
    const pathMapLayout = ref(null)
    const question = ref(null)
    const questions = ref([])
    const questionIndex = ref(0)
    const challengeId = ref('')
    const selectedNode = ref('')
    const selectedPath = ref([])
    const answers = ref({})
    const totalDelay = ref('')
    const isGenerating = ref(false)
    const isSubmitting = ref(false)
    const generationError = ref('')
    const submission = ref({ type: 'idle', message: '生成题目后开始作答。' })
    const isCalculationQuestion = computed(() => question.value && calculationTypes.has(question.value.type))
    const questionTypeLabel = computed(() => question.value ? questionLabels[question.value.type] : '后端生成')
    const nextQuestionLabel = computed(() => {
      if (!questions.value.length) return '重新生成'
      return questionIndex.value < questions.value.length - 1 ? '下一题' : '已完成'
    })

    onMounted(loadChallenge)

    async function loadChallenge() {
      isGenerating.value = true
      generationError.value = ''
      horizontalLayout.value = null
      pathMapLayout.value = null
      question.value = null
      questions.value = []
      challengeId.value = ''
      submission.value = { type: 'idle', message: '正在从后端生成新题。' }
      try {
        const challenge = await fetchCurrentTimingChallenge()
        horizontalLayout.value = challenge.dag.horizontal_layout
        pathMapLayout.value = challenge.dag.path_map_layout
        questions.value = challenge.questions
        challengeId.value = challenge.challenge_id
        activateQuestion(0)
        submission.value = { type: 'idle', message: '请完成作答后提交。' }
      } catch (error) {
        generationError.value = `题目生成失败：${error.message}`
        submission.value = { type: 'error', message: '当前题目不可提交。' }
      } finally {
        isGenerating.value = false
      }
    }

    function activateQuestion(index) {
      questionIndex.value = index
      question.value = questions.value[index] ?? null
      answers.value = {}
      totalDelay.value = ''
      selectedNode.value = ''
      selectedPath.value = question.value?.type === 'shortest_path' ? [question.value.source_node_id] : []
      submission.value = { type: 'idle', message: '请完成作答后提交。' }
    }

    function nextQuestion() {
      if (!questions.value.length) {
        loadChallenge()
        return
      }
      if (questionIndex.value < questions.value.length - 1) {
        activateQuestion(questionIndex.value + 1)
      }
    }

    function selectNode(nodeId) {
      selectedNode.value = nodeId
      if (question.value?.type !== 'shortest_path') return

      selectedPath.value = nodeId === question.value.source_node_id
        ? [question.value.source_node_id]
        : [...selectedPath.value, nodeId]
      submission.value = { type: 'idle', message: '已记录路径选择，请提交后端验证。' }
    }

    function buildPayload() {
      if (!question.value) throw new Error('当前没有可提交的题目。')
      if (isCalculationQuestion.value) {
        return { answers: answers.value }
      }
      if (question.value.type === 'path_delay') {
        return { total_delay: totalDelay.value }
      }
      return { path: selectedPath.value }
    }

    async function submitAnswer() {
      try {
        const payload = buildPayload()
        isSubmitting.value = true
        submission.value = { type: 'idle', message: '正在提交后端验证。' }
        const result = await validateTimingChallenge(challengeId.value, { question_id: question.value.id, ...payload })
        submission.value = result.correct
          ? { type: 'success', message: '答案正确。' }
          : { type: 'error', message: '答案不正确，请检查后重试。' }
      } catch (error) {
        submission.value = { type: 'error', message: error.message }
      } finally {
        isSubmitting.value = false
      }
    }

    return {
      answers,
      challengeId,
      generationError,
      horizontalLayout,
      isCalculationQuestion,
      isGenerating,
      isSubmitting,
      loadChallenge,
      question,
      questionIndex,
      questionTypeLabel,
      pathMapLayout,
      nextQuestion,
      nextQuestionLabel,
      questions,
      selectedNode,
      selectedPath,
      selectNode,
      submission,
      submitAnswer,
      totalDelay,
    }
  },
}
</script>
