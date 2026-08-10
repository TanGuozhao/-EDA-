<template>
  <section>
    <div class="page-heading">
      <div>
        <h2>我的</h2>
        <p>查看当前登录账号和本地会话状态。</p>
      </div>
      <button class="btn secondary" type="button" @click="reload">刷新</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">请求失败: {{ error }}</div>

    <div v-else class="profile-grid">
      <div class="card profile-card">
        <span class="card-index">账号</span>
        <strong>{{ user.userName }}</strong>
        <small>{{ user.account }}</small>
      </div>

      <div class="card profile-card">
        <span class="card-index">状态</span>
        <strong>{{ user.status === 'active' ? '正常' : user.status }}</strong>
        <small>当前会话已通过 X-Session-Key 校验</small>
      </div>

      <div class="card profile-card">
        <span class="card-index">最近登录</span>
        <strong>{{ formatTime(user.lastLoginAt) }}</strong>
        <small>注册后首次进入时可能为空</small>
      </div>
    </div>
  </section>
</template>

<script>
import { onMounted, ref } from 'vue'
import { fetchMe } from '../api'
import { setCurrentUser } from '../auth'

export default {
  name: 'Me',
  setup() {
    const loading = ref(false)
    const error = ref('')
    const user = ref({})

    async function reload() {
      loading.value = true
      error.value = ''
      try {
        const result = await fetchMe()
        user.value = result.user || {}
        setCurrentUser(user.value)
      } catch (err) {
        error.value = err.message || '加载失败'
      } finally {
        loading.value = false
      }
    }

    function formatTime(value) {
      if (!value) return '暂无'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return date.toLocaleString()
    }

    onMounted(reload)
    return { loading, error, user, reload, formatTime }
  },
}
</script>
