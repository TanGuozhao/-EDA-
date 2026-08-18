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

      <div
        v-for="(lvl, index) in chapter.levels"
        :key="lvl.id"
        class="challenge-card"
        :class="{ 'experiment-chapter': [6,7,8].includes(Number(chapter.id)) }"
      >
        <span class="card-index">第 {{ index + 1 }} 关</span>
        <strong>{{ lvl.title }}</strong>
        <small>{{ lvl.description }}</small>
        <em>{{ statusText(lvl.status) }}</em>

        <!-- 六七八章的最后一关（第8关）显示"进入实验"按钮 -->
        <div v-if="[6,7,8].includes(Number(chapter.id)) && index === 7" class="card-actions">
          <router-link
            :to="{ name: 'Experiment', params: { id: lvl.id } }"
            class="btn-experiment"
          >
            🧪 进入实验
          </router-link>
          <router-link
            :to="levelTarget(lvl)"
            class="btn-level"
          >
            查看关卡
          </router-link>
        </div>

        <!-- 其他情况只显示关卡链接 -->
        <router-link
          v-else
          :to="levelTarget(lvl)"
          class="btn-level-only"
        >
          查看关卡 →
        </router-link>
      </div>
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

<style scoped>
.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-heading h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1a2b4a;
  margin-bottom: 4px;
}
.page-heading p {
  color: #6b7a8f;
  font-size: 15px;
}
.loading, .error {
  text-align: center;
  padding: 40px;
  color: #6b7a8f;
}
.error {
  color: #c62828;
}

.challenge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.challenge-card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e9edf4;
  padding: 20px;
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  transition: 0.2s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  position: relative;
}
.challenge-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.08);
}
.challenge-card .card-index {
  font-size: 12px;
  font-weight: 600;
  color: #4a7cf7;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.challenge-card strong {
  font-size: 16px;
  margin: 6px 0 4px;
  color: #1a2b4a;
}
.challenge-card small {
  font-size: 13px;
  color: #6b7a8f;
  flex: 1;
}
.challenge-card em {
  font-style: normal;
  font-size: 12px;
  margin-top: 8px;
  color: #4a7cf7;
  background: #eef3fc;
  padding: 2px 12px;
  border-radius: 12px;
  align-self: flex-start;
}

/* 返回卡片 */
.back-card {
  background: #f8f9fa;
  border-style: dashed;
}
.back-card strong {
  color: #4a7cf7;
}
.back-card small {
  color: #6b7a8f;
}

/* 六七八章实验卡片 */
.experiment-chapter {
  padding-bottom: 16px;
}
.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.btn-experiment {
  display: inline-block;
  padding: 6px 14px;
  background: #4a7cf7;
  color: white;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: 0.2s;
}
.btn-experiment:hover {
  background: #3a6be0;
}
.btn-level {
  display: inline-block;
  padding: 6px 14px;
  background: #e9edf4;
  color: #1a2b4a;
  border-radius: 6px;
  font-size: 13px;
  text-decoration: none;
  transition: 0.2s;
}
.btn-level:hover {
  background: #d5dce6;
}
.btn-level-only {
  display: inline-block;
  margin-top: 10px;
  color: #4a7cf7;
  font-size: 13px;
  text-decoration: none;
  font-weight: 600;
  align-self: flex-start;
}
.btn-level-only:hover {
  text-decoration: underline;
}
</style>