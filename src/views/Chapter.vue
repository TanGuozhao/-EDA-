<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>{{ chapter?.title || '章节关卡' }}</h2>
        <p>{{ chapter?.description }}</p>
      </div>
    </div>

    <div v-if="loading" class="loading">加载章节中...</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>

    <div v-if="chapter" class="challenge-grid">
      <router-link to="/chapters" class="challenge-card back-card">
        <span class="card-index">返回</span>
        <strong>一芯向前冲</strong>
        <small>回到八章总览</small>
      </router-link>

      <router-link
        v-for="(lvl, index) in chapter.levels"
        :key="lvl.id"
        :to="levelTarget(lvl)"
        class="challenge-card"
      >
        <span class="card-index">第 {{ index + 1 }} 关</span>
        <strong>{{ lvl.title }}</strong>
        <small>{{ lvl.description }}</small>
        <em>{{ statusText(lvl.status) }}</em>
      </router-link>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { getChapter } from '../challengeData'
import { useRoute } from 'vue-router'

export default {
  name: 'Chapter',
  setup(){
    const route = useRoute()
    const chapter = ref(null)
    const loading = ref(false)
    const error = ref(null)

    async function load(){
      loading.value = true
      error.value = null
      try{
        chapter.value = getChapter(route.params.id)
        if(!chapter.value) throw new Error('章节不存在')
      }catch(e){
        error.value = e.message
      }finally{
        loading.value = false
      }
    }

    function statusText(status){
      if(status === 'completed') return '已完成'
      if(status === 'locked') return '未解锁'
      return '可挑战'
    }

    function levelTarget(level){
      if(Number(level.chapter_id) === 5 && Number(level.id) === 501){
        return { name: 'ChapterTimingAnalysis' }
      }
      return { name: 'Level', params: { id: level.id } }
    }

    onMounted(load)
    return { chapter, loading, error, statusText, levelTarget }
  }
}
</script>
