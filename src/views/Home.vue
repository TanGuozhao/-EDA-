<template>
  <div>
    <div class="page-heading">
      <h2>一芯向前冲</h2>
      <button class="btn secondary" @click="reload">刷新</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>

    <div v-if="!loading && !error" class="challenge-grid">
      <router-link to="/" class="challenge-card back-card">
        <span class="card-index">返回</span>
        <strong>回到首页</strong>
        <small>返回平台入口</small>
      </router-link>

      <router-link
        v-for="(ch, index) in chapters"
        :key="ch.id"
        :to="{ name: 'Chapter', params: { id: ch.id } }"
        class="challenge-card"
      >
        <span class="card-index">第 {{ index + 1 }} 章</span>
        <strong>{{ ch.title }}</strong>
        <small>{{ ch.description }}</small>
        <em>{{ ch.levels?.length || 0 }} 个关卡</em>
      </router-link>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { chapters as challengeChapters } from '../challengeData'

export default {
  name: 'Home',
  setup(){
    const chapters = ref([])
    const loading = ref(false)
    const error = ref(null)

    async function load(){
      loading.value = true
      error.value = null
      try{
        chapters.value = challengeChapters
      }catch(e){
        error.value = e.message
      }finally{
        loading.value = false
      }
    }

    onMounted(load)
    return { chapters, loading, error, reload: load }
  }
}
</script>
