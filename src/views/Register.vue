<template>
  <section class="auth-page">
    <div class="page-heading">
      <div>
        <h2>注册</h2>
        <p>创建一个本地学习账号，后续用于保存个人进度。</p>
      </div>
    </div>

    <form class="auth-card" @submit.prevent="submit">
      <label>
        <span>账号</span>
        <input v-model.trim="form.account" autocomplete="username" placeholder="至少 3 位" />
      </label>

      <label>
        <span>昵称</span>
        <input v-model.trim="form.user_name" autocomplete="name" placeholder="可选" />
      </label>

      <label>
        <span>密码</span>
        <input v-model="form.password" autocomplete="new-password" type="password" placeholder="至少 8 位" />
      </label>

      <label>
        <span>确认密码</span>
        <input v-model="confirmPassword" autocomplete="new-password" type="password" placeholder="再次输入密码" />
      </label>

      <p v-if="error" class="auth-error">{{ error }}</p>

      <div class="auth-actions">
        <button class="btn" type="submit" :disabled="submitting">
          {{ submitting ? '注册中...' : '注册并登录' }}
        </button>
        <router-link class="btn secondary" to="/login">已有账号</router-link>
      </div>
    </form>
  </section>
</template>

<script>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../api'
import { saveAuthSession } from '../auth'

export default {
  name: 'Register',
  setup() {
    const router = useRouter()
    const submitting = ref(false)
    const error = ref('')
    const confirmPassword = ref('')
    const form = reactive({
      account: '',
      user_name: '',
      password: '',
    })

    async function submit() {
      error.value = ''
      if (form.account.length < 3) {
        error.value = '账号至少 3 位'
        return
      }
      if (form.password.length < 8) {
        error.value = '密码至少 8 位'
        return
      }
      if (form.password !== confirmPassword.value) {
        error.value = '两次输入的密码不一致'
        return
      }

      submitting.value = true
      try {
        const result = await register({
          account: form.account,
          password: form.password,
          user_name: form.user_name || form.account,
        })
        saveAuthSession({ sessionKey: result.sessionKey, user: result.user })
        router.replace('/me')
      } catch (err) {
        error.value = err.message || '注册失败'
      } finally {
        submitting.value = false
      }
    }

    return { form, confirmPassword, submitting, error, submit }
  },
}
</script>
