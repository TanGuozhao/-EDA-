<template>
  <section class="auth-page">
    <div class="page-heading">
      <div>
        <h2>登录</h2>
        <p>使用本地账号进入 EDA 闯关平台。</p>
      </div>
    </div>

    <form class="auth-card" @submit.prevent="submit">
      <label>
        <span>账号</span>
        <input v-model.trim="form.account" autocomplete="username" placeholder="请输入账号" />
      </label>

      <label>
        <span>密码</span>
        <input v-model="form.password" autocomplete="current-password" type="password" placeholder="请输入密码" />
      </label>

      <p v-if="error" class="auth-error">{{ error }}</p>

      <div class="auth-actions">
        <button class="btn" type="submit" :disabled="submitting">
          {{ submitting ? '登录中...' : '登录' }}
        </button>
        <router-link class="btn secondary" to="/register">注册账号</router-link>
      </div>
    </form>
  </section>
</template>

<script>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../api'
import { saveAuthSession } from '../auth'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const submitting = ref(false)
    const error = ref('')
    const form = reactive({
      account: '',
      password: '',
    })

    async function submit() {
      error.value = ''
      if (!form.account || !form.password) {
        error.value = '请填写账号和密码'
        return
      }

      submitting.value = true
      try {
        const result = await login(form)
        saveAuthSession({ sessionKey: result.sessionKey, user: result.user })
        router.replace(route.query.redirect || '/me')
      } catch (err) {
        error.value = err.message || '登录失败'
      } finally {
        submitting.value = false
      }
    }

    return { form, submitting, error, submit }
  },
}
</script>
