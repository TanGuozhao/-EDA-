<template>
  <div>
    <div class="nav-row">
      <router-link to="/chapters" class="btn secondary">返回章节列表</router-link>
      <span class="small-muted">章节详情与关卡列表</span>
    </div>

    <div v-if="loading" class="loading">加载章节中……</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>

    <div v-if="chapter" class="card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px">
        <div>
          <div class="chapter-title">{{ chapter.title }}</div>
          <div class="chapter-desc">{{ chapter.description }}</div>
        </div>
        <div style="text-align:right">
          <div class="small-muted">章节ID：{{ chapter.id }}</div>
          <button class="btn" @click="openAllExperiments">查看本章所有实验入口</button>
        </div>
      </div>

      <hr style="margin:12px 0; border:none; border-top:1px solid rgba(15,23,42,0.04)"/>

      <div>
        <div v-if="!chapter.levels || chapter.levels.length===0" class="empty">本章暂无关卡（或后端未返回 levels 字段）。</div>
        <div v-else>
          <div v-for="lvl in chapter.levels" :key="lvl.id" class="level-row">
            <div class="level-meta">
              <div>
                <div class="level-title">关卡：{{ lvl.title }}</div>
                <div class="small-muted">{{ lvl.description || '— 无描述 —' }}</div>
              </div>
            </div>

            <div style="display:flex; align-items:center; gap:8px">
              <div :class="['badge', lvl.status === 'open' ? 'open' : 'locked']">{{ lvl.status || 'unknown' }}</div>
              <div v-if="isCompleted(lvl.id)" class="small-muted" style="color:green">已完成 ✓</div>
              <router-link :to="{ name:'Level', params:{ id: lvl.id } }" class="btn">查看关卡</router-link>

              <!-- 仅在后端返回 experiment 或 has_experiment 标记时显示实验入口 -->
              <router-link
                v-if="lvl.experiment || lvl.has_experiment"
                :to="{ name:'Experiment', params:{ id: lvl.id } }"
                class="btn secondary"
              >
                实验入口
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchChapter } from '../api'
import { useRoute, useRouter } from 'vue-router'
import { isComplete, subscribe } from '../completion'

export default {
  name: 'Chapter',
  setup(){
    const route = useRoute()
    const router = useRouter()
    const chapter = ref(null)
    const loading = ref(false)
    const error = ref(null)

    async function load(){
      loading.value = true; error.value = null
      try{
        const data = await fetchChapter(route.params.id)
        chapter.value = data
      }catch(e){
        error.value = e.message
      }finally{
        loading.value = false
      }
    }

    function openAllExperiments(){
      if(chapter.value?.levels?.length){
        // 跳到实验入口页并传递可选 query 以便过滤到本章（可选）
        router.push({ name: 'Experiments', query: { chapter: chapter.value.id } })
      }else{
        alert('本章没有可查看的实验关卡')
      }
    }

    const updateOnComplete = (id) => {
      // 触发响应式更新
      if(chapter.value && Array.isArray(chapter.value.levels)){
        const idx = chapter.value.levels.findIndex(x => String(x.id) === String(id))
        if(idx !== -1){
          chapter.value.levels[idx] = Object.assign({}, chapter.value.levels[idx])
        }
      }
    }

    let unsub = null
    onMounted(() => { load(); unsub = subscribe(updateOnComplete) })
    onUnmounted(() => { if(unsub) unsub() })

    return { chapter, loading, error, openAllExperiments, isCompleted: isComplete }
  }
}
</script>