<template>
  <div>
    <div class="nav-row">
      <router-link to="/chapters" class="btn secondary">返回八章闯关</router-link>
      <span class="small-muted">所有章中可用的实验关卡（平展列表，仅显示有实验的关卡）</span>
    </div>

    <div v-if="loading" class="loading">加载中……</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>

    <div v-if="levels?.length" class="grid" style="grid-template-columns:repeat(auto-fill,minmax(320px,1fr));">
      <div class="card" v-for="lvl in levels" :key="lvl.id">
        <div style="display:flex; justify-content:space-between;">
          <div>
            <div class="level-title">{{ lvl.title }}</div>
            <div class="small-muted">章：{{ lvl.chapter_title || '未知' }}</div>
          </div>
          <div style="text-align:right">
            <div :class="['badge', lvl.status === 'open' ? 'open' : 'locked']">{{ lvl.status || 'unknown' }}</div>
            <div v-if="isCompleted(lvl.id)" class="small-muted" style="margin-top:6px;color:green">已完成 ✓</div>
          </div>
        </div>

        <div style="margin-top:8px" class="small-muted">{{ lvl.description || '— 无描述 —' }}</div>

        <div style="margin-top:12px; display:flex; gap:8px;">
          <router-link :to="{ name:'Experiment', params:{ id: lvl.id } }" class="btn">进入实验</router-link>
          <router-link :to="{ name:'Level', params:{ id: lvl.id } }" class="btn secondary">查看关卡</router-link>
        </div>
      </div>
    </div>

    <div v-if="!loading && !error && (!levels || levels.length===0)" class="empty">暂无实验关卡</div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchExperimentLevels, fetchLevel } from '../api'
import { isComplete, subscribe } from '../completion'

export default {
  name: 'Experiments',
  setup(){
    const levels = ref([])
    const loading = ref(false)
    const error = ref(null)

    // 将章节中的 levels 平展出来（不做 experiment 过滤）
    function flattenLevels(chapters){
      const flat = []
      if(Array.isArray(chapters)){
        chapters.forEach(ch => {
          if(Array.isArray(ch.levels)){
            ch.levels.forEach(l => {
              flat.push(Object.assign({}, l, { chapter_title: ch.title }))
            })
          }
        })
      }
      return flat
    }

    // 如果某些关卡没有 experiment 字段，调用关卡详情接口进行补充判断
    async function enrichLevelsWithDetailIfNeeded(flatLevels){
      // 先看是否已经有 experiment 字段
      const haveExperimentDirectly = flatLevels.some(l => l.experiment || l.has_experiment)
      if(haveExperimentDirectly){
        // 直接返回只包含有 experiment 的关卡
        return flatLevels.filter(l => l.experiment || l.has_experiment)
      }

      // 否则，逐个调用 fetchLevel 获取详情（注意：这会产生多个请求）
      const detailed = []
      // 简单并行：注意如果关卡数量很多，可能需要做限流。这里按最小修改提供简单实现。
      const promises = flatLevels.map(async (l) => {
        try{
          const det = await fetchLevel(l.id)
          // det 可能包含 experiment 字段
          if(det && (det.experiment || det.has_experiment)){
            // 合并章节标题等信息，便于显示
            detailed.push(Object.assign({}, det, { chapter_title: l.chapter_title }))
          }
        }catch(e){
          // 忽略单个关卡获取失败，但记录到控制台以便调试
          console.warn('fetchLevel failed for', l.id, e)
        }
      })
      await Promise.all(promises)
      return detailed
    }

  async function load(){
  loading.value = true; 
  error.value = null;
  try{
    // 直接调用后端新接口，只返回有实验的关卡
    const expLevels = await fetchExperimentLevels();
    levels.value = expLevels || [];
  }catch(e){
    console.error(e);
    error.value = e.message || String(e);
  }finally{
    loading.value = false;
  }
}

    const updateOnComplete = (id) => {
      const idx = levels.value.findIndex(x => String(x.id) === String(id))
      if(idx !== -1){
        levels.value[idx] = Object.assign({}, levels.value[idx])
      }
    }

    let unsub = null
    onMounted(() => { load(); unsub = subscribe(updateOnComplete) })
    onUnmounted(() => { if(unsub) unsub() })

    return { levels, loading, error, isCompleted: isComplete }
  }
}
</script>