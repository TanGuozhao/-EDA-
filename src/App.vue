<template>
  <div class="app" :class="{ 'standalone-prototype': isStandalonePrototype }">
    <header class="header">
      <h1>芯语智问 - EDA 闯关平台</h1>
      <nav>
        <router-link to="/chapters">一芯向前冲</router-link>
        <router-link to="/timing-analysis">时序分析体验</router-link>
        <router-link v-if="currentUser" to="/me">{{ currentUser.userName || currentUser.account }}</router-link>
        <router-link v-else to="/login">登录</router-link>
        <button v-if="currentUser" class="nav-button" type="button" @click="signOut">退出</button>
      </nav>
    </header>

    <main class="main">
      <router-view />
    </main>

    <TutorFloater v-if="showTutor" />
  </div>
</template>

<script>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TutorFloater from './components/TutorFloater.vue'
import { logout } from './api'
import { clearAuthSession, getCurrentUser } from './auth'

export default {
  name: 'App',
  components: {
    TutorFloater,
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const currentUser = ref(getCurrentUser())
    const isStandalonePrototype = computed(() => route.name === 'TimingAnalysisPrototype')
    const showTutor = computed(() => !['CircuitVerseDemo', 'SchedulingDemo'].includes(route.name))

    function syncUser() {
      currentUser.value = getCurrentUser()
    }

    async function signOut() {
      try {
        await logout()
      } catch {
        // Local logout should still clear stale sessions.
      }
      clearAuthSession()
      router.push('/login')
    }

    onMounted(() => window.addEventListener('auth:changed', syncUser))
    onUnmounted(() => window.removeEventListener('auth:changed', syncUser))

    return { isStandalonePrototype, currentUser, showTutor, signOut }
  },
}
</script>
