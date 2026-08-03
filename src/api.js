// Production uses the same-origin /api proxy; VITE_API_BASE supports an explicit API host when needed.
import { getSessionKey } from './auth'

const BASE = import.meta.env.VITE_API_BASE ?? ''

async function request(path, options = {}){
  const url = BASE + path
  const sessionKey = getSessionKey()
  const res = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(sessionKey ? { 'X-Session-Key': sessionKey } : {}),
      ...options.headers,
    },
  })
  if(!res.ok){
    const text = await res.text().catch(() => null)
    let detail = text
    try {
      const data = text ? JSON.parse(text) : null
      detail = data?.detail || data?.message || text
    } catch {
      detail = text
    }
    throw new Error(detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

function parseSseEventBlock(block) {
  if (!block.trim()) return null
  let event = 'message'
  const dataLines = []
  for (const rawLine of block.split(/\r?\n/)) {
    const line = rawLine.trimEnd()
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^\s/, ''))
  }
  return { event, data: dataLines.join('\n') }
}

async function readSseResponse(res, { signal, onDelta }) {
  if (!res.body) throw new Error('SSE response body is empty')

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    let index = buffer.indexOf('\n\n')
    while (index !== -1) {
      const block = buffer.slice(0, index)
      buffer = buffer.slice(index + 2)
      const event = parseSseEventBlock(block)
      if (event?.event === 'delta') onDelta(event.data)
      if (event?.event === 'error') throw new Error(event.data || 'Tutor assistant stream failed')
      if (event?.event === 'done') return
      index = buffer.indexOf('\n\n')
    }
  }
}

export async function fetchChapters(){
  // GET /api/chapters/
  return request('/api/chapters/')
}

export async function fetchChapter(id){
  // GET /api/chapters/{id}
  return request(`/api/chapters/${encodeURIComponent(id)}`)
}

export async function fetchLevel(id){
  // GET /api/chapters/levels/{id}
  return request(`/api/chapters/levels/${encodeURIComponent(id)}`)
}

export async function register(payload) {
  return request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function login(payload) {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function fetchMe() {
  return request('/api/auth/me')
}

export async function logout() {
  return request('/api/auth/logout', {
    method: 'POST',
  })
}
export async function fetchExperimentLevels() {
  return request('/api/chapters/experiments/list')
}

export async function fetchTimingGraph() {
  return request('/api/timing-analysis/graph')
}

export async function generateTimingChallenge(payload = {}) {
  return request('/api/timing-analysis/challenges/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function fetchCurrentTimingChallenge() {
  return request('/api/timing-analysis/challenges/current')
}

export async function validateTimingChallenge(challengeId, payload) {
  return request(`/api/timing-analysis/challenges/${encodeURIComponent(challengeId)}/validate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

async function readChatSseResponse(res, { signal, onDelta, onDone }) {
  if (!res.body) throw new Error('SSE response body is empty')

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    let index = buffer.indexOf('\n\n')
    while (index !== -1) {
      const block = buffer.slice(0, index)
      buffer = buffer.slice(index + 2)
      const event = parseSseEventBlock(block)
      if (event?.event === 'delta') onDelta(event.data)
      if (event?.event === 'error') throw new Error(event.data || 'Chat stream failed')
      if (event?.event === 'done') {
        let payload = {}
        try {
          payload = event.data ? JSON.parse(event.data) : {}
        } catch {
          payload = {}
        }
        if (typeof onDone === 'function') onDone(payload)
        return payload
      }
      index = buffer.indexOf('\n\n')
    }
  }
  return {}
}

export async function fetchCurrentHlsChallenge(kind = 'asap') {
  return request(`/api/hls/challenges/current?kind=${encodeURIComponent(kind)}`)
}

export async function submitHlsChallenge(challengeId, payload) {
  return request(`/api/hls/challenges/${encodeURIComponent(challengeId)}/submit`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function askTutor(payload = {}) {
  return request('/api/tutor/ask', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function askTutorStream(payload = {}, { signal, onDelta } = {}) {
  const res = await fetch(BASE + '/api/tutor/ask/stream', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => null)
    throw new Error(`${res.status} ${res.statusText}${text ? ' - ' + text : ''}`)
  }

  await readSseResponse(res, {
    signal,
    onDelta: typeof onDelta === 'function' ? onDelta : () => {},
  })
}

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, ms)
    if (signal) {
      signal.addEventListener('abort', () => {
        window.clearTimeout(timer)
        reject(new DOMException('Aborted', 'AbortError'))
      }, { once: true })
    }
  })
}

function buildPreviewReply(payload = {}) {
  const skillLine = payload.skill_id ? `\n\n本轮已选择 Skill：${payload.skill_id}。` : ''
  const styleLine = payload.reply_style && payload.reply_style !== 'default'
    ? `\n回复风格：${payload.reply_style}。`
    : ''
  return [
    '这是前端预览模式的流式回复。',
    '',
    `你的问题是：${payload.message || '未填写问题'}`,
    '',
    '后端接入后，这里会变成真实的 EDA 智能问答：会话持久化、附件解析、RAG 引用、Skill 注入和 Tool 审计都会从 /api/chat/* 返回。',
    '当前页面已经预留左侧会话列表、中间消息流、底部输入区、附件 chip、停止生成按钮和右侧引用来源。',
    skillLine + styleLine,
  ].join('\n')
}

async function streamPreviewLocally(payload, { signal, onDelta }) {
  const reply = buildPreviewReply(payload)
  const step = 8
  for (let index = 0; index < reply.length; index += step) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    onDelta(reply.slice(index, index + step))
    await sleep(24, signal)
  }
}

export async function streamChatPreview(payload = {}, { signal, onDelta } = {}) {
  const res = await fetch(BASE + '/api/chat/stream', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      ...(getSessionKey() ? { 'X-Session-Key': getSessionKey() } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  }).catch(error => {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    return null
  })

  if (!res || res.status === 404 || res.status === 405) {
    await streamPreviewLocally(payload, {
      signal,
      onDelta: typeof onDelta === 'function' ? onDelta : () => {},
    })
    return
  }

  if (!res.ok) {
    const text = await res.text().catch(() => null)
    throw new Error(text || `${res.status} ${res.statusText}`)
  }

  return readChatSseResponse(res, {
    signal,
    onDelta: typeof onDelta === 'function' ? onDelta : () => {},
  })
}

export async function stopChatStream(requestId) {
  if (!requestId) return { stopped: false }
  return request('/api/chat/stop', {
    method: 'POST',
    body: JSON.stringify({ request_id: requestId }),
  }).catch(() => ({ stopped: false }))
}

export async function fetchChatSessions() {
  return request('/api/chat/sessions')
}

export async function fetchChatMessages(sessionId) {
  return request(`/api/chat/sessions/${encodeURIComponent(sessionId)}/messages`)
}

export async function deleteChatSession(sessionId) {
  return request(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  }).catch(() => null)
}
