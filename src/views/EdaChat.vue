<template>
  <div class="eda-chat-page">
    <aside class="eda-chat-sidebar" aria-label="历史会话">
      <button class="eda-chat-new" type="button" @click="newConversation">
        <span aria-hidden="true">+</span>
        新建对话
      </button>

      <label class="eda-chat-search">
        <span aria-hidden="true">⌕</span>
        <input v-model="historyQuery" type="search" placeholder="搜索历史对话" />
      </label>

      <div class="eda-chat-session-list">
        <button
          v-for="session in filteredSessions"
          :key="session.id"
          type="button"
          class="eda-chat-session"
          :class="{ active: session.id === activeSessionId }"
          @click="activeSessionId = session.id"
        >
          <strong>{{ session.title }}</strong>
          <small>{{ session.updatedAt }}</small>
        </button>
        <div v-if="filteredSessions.length === 0" class="eda-chat-empty-small">
          暂无历史会话
        </div>
      </div>

      <button class="eda-chat-clear" type="button" @click="clearLocalHistory">
        清空本地预览历史
      </button>
    </aside>

    <main class="eda-chat-main">
      <section v-if="activeMessages.length === 0" class="eda-chat-welcome">
        <div class="eda-chat-orbit" aria-hidden="true">
          <span>CI</span>
        </div>
        <h2>芯语智问</h2>
        <p>围绕 EDA 学习、RTL 设计、时序分析、高级综合和工具使用进行问答。</p>
        <div class="eda-chat-suggestions">
          <button
            v-for="item in suggestions"
            :key="item.title"
            type="button"
            @click="inputText = item.prompt"
          >
            <strong>{{ item.title }}</strong>
            <small>{{ item.desc }}</small>
          </button>
        </div>
      </section>

      <section v-else ref="threadRef" class="eda-chat-thread" aria-live="polite">
        <article
          v-for="message in activeMessages"
          :key="message.id"
          class="eda-chat-message"
          :class="`eda-chat-message-${message.role}`"
        >
          <div class="eda-chat-avatar" aria-hidden="true">
            {{ message.role === 'user' ? '我' : '芯' }}
          </div>
          <div class="eda-chat-bubble">
            <p v-for="(line, index) in renderMessageLines(message.content)" :key="index">
              {{ line || ' ' }}
            </p>
            <span v-if="message.pending" class="eda-chat-cursor" aria-hidden="true" />
          </div>
        </article>
      </section>

      <form class="eda-chat-composer-wrap" @submit.prevent="pending ? stopStreaming() : sendMessage()">
        <div v-if="attachments.length" class="eda-chat-attachments">
          <div v-for="attachment in attachments" :key="attachment.id" class="eda-chat-attachment-chip">
            <span>{{ attachment.badge }}</span>
            <div>
              <strong>{{ attachment.name }}</strong>
              <small>{{ attachment.sizeLabel }}</small>
            </div>
            <button type="button" aria-label="移除附件" @click="removeAttachment(attachment.id)">×</button>
          </div>
        </div>

        <textarea
          ref="textareaRef"
          v-model="inputText"
          class="eda-chat-input"
          rows="3"
          placeholder="问我 EDA、芯片设计、时序分析或上传资料后的问题..."
          @keydown.enter.exact.prevent="sendMessage"
        />

        <div class="eda-chat-composer-bar">
          <div class="eda-chat-tools">
            <input
              ref="fileInputRef"
              class="sr-only"
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.webp,.gif,.bmp"
              @change="onFilesSelected"
            />
            <button type="button" class="eda-chat-tool-btn" title="上传附件" @click="fileInputRef?.click()">
              <span aria-hidden="true">附件</span>
            </button>
            <select v-model="replyStyle" class="eda-chat-select" aria-label="回复风格">
              <option value="default">默认</option>
              <option value="explain">讲解</option>
              <option value="steps">步骤</option>
              <option value="review">复盘</option>
            </select>
            <select v-model="selectedSkill" class="eda-chat-select" aria-label="选择 Skill">
              <option value="">通用 EDA</option>
              <option value="openai-docs">openai-docs</option>
              <option value="rtl-debug">RTL 调试</option>
              <option value="hls-schedule">HLS 调度</option>
            </select>
          </div>

          <button class="eda-chat-send" type="submit" :disabled="!pending && !canSend">
            <span v-if="pending" aria-hidden="true">■</span>
            <span v-else aria-hidden="true">➤</span>
          </button>
        </div>

        <p class="eda-chat-hint">
          {{ hintText }}
        </p>
      </form>
    </main>

    <aside class="eda-chat-sources" aria-label="引用来源">
      <div class="eda-chat-source-header">
        <span>RAG SOURCES</span>
        <h3>本轮引用</h3>
      </div>
      <button
        v-for="(source, index) in activeSources"
        :key="source.id"
        type="button"
        class="eda-chat-source-card"
      >
        <small>来源 {{ index + 1 }}</small>
        <strong>{{ source.title }}</strong>
        <p>{{ source.excerpt }}</p>
      </button>
      <div v-if="activeSources.length === 0" class="eda-chat-source-empty">
        后端 RAG 接入后，这里会展示本轮回答引用的文档片段、分数和定位信息。
      </div>
    </aside>
  </div>
</template>

<script>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { deleteChatSession, fetchChatMessages, fetchChatSessions, streamChatPreview, stopChatStream } from '../api'
import { getSessionKey } from '../auth'

const LOCAL_SESSIONS_KEY = 'eda_chat_preview_sessions'

function nowLabel() {
  const date = new Date()
  const pad = value => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function readLocalSessions() {
  try {
    const rows = JSON.parse(localStorage.getItem(LOCAL_SESSIONS_KEY) || '[]')
    return Array.isArray(rows) ? rows : []
  } catch {
    return []
  }
}

function saveLocalSessions(sessions) {
  localStorage.setItem(LOCAL_SESSIONS_KEY, JSON.stringify(sessions))
}

function fileSizeLabel(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)}MB`
  return `${Math.max(1, Math.round(bytes / 1024))}KB`
}

export default {
  name: 'EdaChat',
  setup() {
    const sessions = ref(readLocalSessions())
    const activeSessionId = ref(sessions.value[0]?.id || null)
    const historyQuery = ref('')
    const inputText = ref('')
    const replyStyle = ref('default')
    const selectedSkill = ref('')
    const pending = ref(false)
    const attachments = ref([])
    const fileInputRef = ref(null)
    const textareaRef = ref(null)
    const threadRef = ref(null)
    const requestId = ref('')
    const abortController = ref(null)
    const loadingRemoteMessages = ref(false)

    const suggestions = [
      {
        title: '解释建立时间与保持时间',
        desc: '用时序路径和公式讲清判断方法。',
        prompt: '请用一个简单的触发器路径解释 setup time 和 hold time 的区别。'
      },
      {
        title: 'RTL 代码排错思路',
        desc: '定位锁存器、位宽和时序赋值问题。',
        prompt: 'Verilog 代码综合后出现 latch 推断，我应该按什么顺序排查？'
      },
      {
        title: 'HLS 调度练习',
        desc: '比较 ASAP、ALAP 和 List Scheduling。',
        prompt: '请用一张小 DAG 举例说明 ASAP、ALAP 和 List Scheduling 的区别。'
      },
      {
        title: 'Yosys 工具解释',
        desc: '理解 read_verilog、proc、check、stat。',
        prompt: 'Yosys 中 read_verilog、proc、check、stat 分别在验证 RTL 时做什么？'
      }
    ]

    const activeSession = computed(() => sessions.value.find(item => item.id === activeSessionId.value) || null)
    const activeMessages = computed(() => activeSession.value?.messages || [])
    const activeSources = computed(() => {
      for (let index = activeMessages.value.length - 1; index >= 0; index -= 1) {
        const sources = activeMessages.value[index].sources
        if (Array.isArray(sources) && sources.length) return sources
      }
      return []
    })
    const filteredSessions = computed(() => {
      const query = historyQuery.value.trim().toLowerCase()
      if (!query) return sessions.value
      return sessions.value.filter(session => session.title.toLowerCase().includes(query))
    })
    const canSend = computed(() => Boolean(inputText.value.trim() || attachments.value.length))
    const hintText = computed(() => {
      if (pending.value) return '正在生成回复，点击右侧按钮可停止。'
      if (attachments.value.length) return `已添加 ${attachments.value.length} 个附件。当前为前端预览，后端接入后会上传解析。`
      return 'Enter 发送，Shift+Enter 换行。当前页面已预留 SSE、附件、Skill 和引用区域。'
    })

    function persist() {
      saveLocalSessions(sessions.value)
    }

    function mapRemoteSession(session) {
      return {
        id: session.session_id,
        title: session.title || '新对话',
        updatedAt: session.last_message_at ? new Date(session.last_message_at).toLocaleString() : '--',
        messages: []
      }
    }

    function mapRemoteMessage(message) {
      return {
        id: message.message_id,
        role: message.role,
        content: message.content,
        pending: false,
        sources: (message.rag_sources || []).map((source, index) => ({
          id: source.chunk_id || `${message.message_id}-${index}`,
          title: source.legal_title || source.document_id || `来源 ${index + 1}`,
          excerpt: source.display_text || ''
        }))
      }
    }

    async function loadRemoteSessions() {
      if (!getSessionKey()) return
      try {
        const rows = await fetchChatSessions()
        sessions.value = rows.map(mapRemoteSession)
        activeSessionId.value = sessions.value[0]?.id || null
      } catch {
        sessions.value = readLocalSessions()
        activeSessionId.value = sessions.value[0]?.id || null
      }
    }

    async function loadRemoteMessages(sessionId) {
      if (!getSessionKey() || typeof sessionId !== 'number') return
      const target = sessions.value.find(item => item.id === sessionId)
      if (!target || target.messages.length) return
      loadingRemoteMessages.value = true
      try {
        const rows = await fetchChatMessages(sessionId)
        sessions.value = sessions.value.map(session =>
          session.id === sessionId ? { ...session, messages: rows.map(mapRemoteMessage) } : session
        )
      } finally {
        loadingRemoteMessages.value = false
      }
    }

    function ensureSession(seedText = '新对话') {
      if (activeSession.value) return activeSession.value
      const session = {
        id: `local-${Date.now()}`,
        title: seedText.trim().slice(0, 30) || '新对话',
        updatedAt: nowLabel(),
        messages: []
      }
      sessions.value = [session, ...sessions.value]
      activeSessionId.value = session.id
      persist()
      return session
    }

    function newConversation() {
      activeSessionId.value = null
      inputText.value = ''
      attachments.value = []
      nextTick(() => textareaRef.value?.focus())
    }

    function clearLocalHistory() {
      if (getSessionKey()) {
        const ids = sessions.value.map(item => item.id).filter(id => typeof id === 'number')
        Promise.all(ids.map(id => deleteChatSession(id))).finally(() => {
          sessions.value = []
          activeSessionId.value = null
          persist()
        })
        return
      }
      sessions.value = []
      activeSessionId.value = null
      persist()
    }

    function renderMessageLines(content) {
      return String(content || '').split('\n')
    }

    function scrollThread() {
      nextTick(() => {
        if (threadRef.value) threadRef.value.scrollTop = threadRef.value.scrollHeight
      })
    }

    function updateActiveSession(mutator) {
      sessions.value = sessions.value.map(session => {
        if (session.id !== activeSessionId.value) return session
        return mutator(session)
      })
      persist()
    }

    async function sendMessage() {
      if (pending.value || !canSend.value) return
      const text = inputText.value.trim() || '请结合我上传的附件进行分析。'
      const session = ensureSession(text)
      const idSeed = `${Date.now()}-${Math.random().toString(36).slice(2)}`
      requestId.value = `eda-chat-${idSeed}`

      const attachmentNames = attachments.value.map(item => item.name)
      const displayedText = attachmentNames.length
        ? `${text}\n\n[已附文件：${attachmentNames.join('、')}]`
        : text
      const userMessage = { id: `user-${idSeed}`, role: 'user', content: displayedText }
      const assistantMessage = {
        id: `assistant-${idSeed}`,
        role: 'assistant',
        content: '',
        pending: true,
        sources: []
      }

      activeSessionId.value = session.id
      inputText.value = ''
      pending.value = true

      updateActiveSession(current => ({
        ...current,
        title: current.messages.length ? current.title : text.slice(0, 30),
        updatedAt: nowLabel(),
        messages: [...current.messages, userMessage, assistantMessage]
      }))
      scrollThread()

      abortController.value?.abort()
      const controller = new AbortController()
      abortController.value = controller

      try {
        const payload = {
          session_id: typeof session.id === 'number' ? session.id : null,
          message: text,
          request_id: requestId.value,
          reply_style: replyStyle.value,
          skill_id: selectedSkill.value || null,
          attachment_ids: []
        }
        const chunks = []
        const donePayload = await streamChatPreview(payload, {
          signal: controller.signal,
          onDelta(delta) {
            chunks.push(delta)
            updateActiveSession(current => ({
              ...current,
              messages: current.messages.map(message =>
                message.id === assistantMessage.id
                  ? { ...message, content: message.content + delta }
                  : message
              )
            }))
            scrollThread()
          }
        })
        const finalSessionId = donePayload?.session_id
        updateActiveSession(current => ({
          ...current,
          updatedAt: nowLabel(),
          messages: current.messages.map(message =>
            message.id === assistantMessage.id
              ? {
                  ...message,
                  pending: false,
                  sources: selectedSkill.value
                    ? [
                        {
                          id: `skill-${selectedSkill.value}`,
                          title: `Skill: ${selectedSkill.value}`,
                          excerpt: '前端已把本轮选择的 Skill ID 放入请求载荷，后端接入后会返回真实上下文来源。'
                        }
                      ]
                    : []
                }
              : message
          )
        }))
        if (finalSessionId && session.id !== finalSessionId) {
          sessions.value = sessions.value.map(current =>
            current.id === session.id ? { ...current, id: finalSessionId } : current
          )
          activeSessionId.value = finalSessionId
          persist()
        }
        attachments.value = []
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        updateActiveSession(current => ({
          ...current,
          messages: current.messages.map(message =>
            message.id === assistantMessage.id
              ? { ...message, pending: false, content: error?.message || '请求失败，请稍后重试。' }
              : message
          )
        }))
      } finally {
        if (abortController.value === controller) abortController.value = null
        pending.value = false
        requestId.value = ''
      }
    }

    async function stopStreaming() {
      const id = requestId.value
      abortController.value?.abort()
      abortController.value = null
      pending.value = false
      if (id) await stopChatStream(id).catch(() => undefined)
      updateActiveSession(current => ({
        ...current,
        messages: current.messages.map(message =>
          message.pending ? { ...message, pending: false, content: message.content || '已停止生成。' } : message
        )
      }))
    }

    function onFilesSelected(event) {
      const files = Array.from(event.target.files || [])
      const existing = new Set(attachments.value.map(item => `${item.name}-${item.size}`))
      const next = []
      for (const file of files) {
        const key = `${file.name}-${file.size}`
        if (existing.has(key)) continue
        const ext = file.name.includes('.') ? file.name.split('.').pop().toUpperCase() : 'FILE'
        next.push({
          id: `${key}-${Math.random().toString(36).slice(2)}`,
          name: file.name,
          size: file.size,
          badge: ext,
          sizeLabel: fileSizeLabel(file.size)
        })
      }
      attachments.value = [...attachments.value, ...next].slice(0, 6)
      event.target.value = ''
    }

    function removeAttachment(id) {
      attachments.value = attachments.value.filter(item => item.id !== id)
    }

    onMounted(loadRemoteSessions)
    watch(activeSessionId, value => {
      loadRemoteMessages(value)
    })

    return {
      activeMessages,
      activeSessionId,
      activeSources,
      attachments,
      canSend,
      fileInputRef,
      filteredSessions,
      historyQuery,
      hintText,
      inputText,
      pending,
      replyStyle,
      selectedSkill,
      suggestions,
      textareaRef,
      threadRef,
      clearLocalHistory,
      newConversation,
      onFilesSelected,
      removeAttachment,
      renderMessageLines,
      sendMessage,
      stopStreaming,
    }
  }
}
</script>
