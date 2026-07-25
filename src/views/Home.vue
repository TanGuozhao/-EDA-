<template>
  <div>
    <div class="nav-row">
      <button class="btn secondary" @click="reload">刷新章节列表</button>
      <span class="small-muted">从这里进入八章闯关，每章可展开查看关卡；每个关卡可打开其实验入口。</span>
    </div>

    <div v-if="loading" class="loading">加载中……</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>
    <div v-if="!loading && !error && chapters?.length === 0" class="empty">没有章节数据</div>

    <div v-if="chapters?.length" class="grid chapters-grid">
      <div class="card" v-for="ch in chapters" :key="ch.id">
        <div class="chapter-title">{{ ch.title }}</div>
        <div class="chapter-desc">{{ ch.description || '— 无章节描述 —' }}</div>

        <div style="margin-top:12px">
          <div class="small-muted" v-if="ch.levels?.length">关卡数量: {{ ch.levels.length }}</div>
          <div class="small-muted" v-else>关卡数量: 未知</div>
        </div>

        <div style="display:flex; gap:8px; margin-top:12px">
          <router-link :to="{ name:'Chapter', params:{ id: ch.id } }" class="btn">查看关卡</router-link>
          <button class="btn secondary" @click="openChapterInNewTab(ch.id)">在新页打开</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { fetchChapters } from '../api'

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
        const data = await fetchChapters()
        // if backend returns nested levels use them; otherwise show stub
        chapters.value = Array.isArray(data) ? data : []
      }catch(e){
        error.value = e.message
      }finally{
        loading.value = false
      }
    }
    onMounted(load)
    return { chapters, loading, error, reload: load, openChapterInNewTab(id){ window.open(`/chapter/${id}`, '_blank') } }
  }
}
</script>