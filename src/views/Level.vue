<template>
  <div>
    <div class="nav-row">
      <router-link to="/chapters" class="btn secondary">返回章节列表</router-link>
      <router-link :to="{ name:'Chapter', params:{ id: parentChapterId } }" v-if="parentChapterId" class="btn secondary">返回章节</router-link>
    </div>

    <div v-if="loading" class="loading">加载关卡中……</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>

    <div v-if="level" class="card">
      <div style="display:flex; justify-content:space-between; gap:12px">
        <div>
          <div class="level-title">{{ level.title }}</div>
          <div class="small-muted">关卡ID: {{ level.id }} · 状态: {{ level.status }}</div>
          <p style="margin-top:8px">{{ level.description }}</p>
        </div>
        <div style="text-align:right">
          <div class="small-muted">通过标准: {{ level.pass_criteria || '无' }}</div>
          <router-link :to="{ name:'Experiment', params:{ id: level.id } }" v-if="level.experiment || level.has_experiment" class="btn">进入实验</router-link>
        </div>
      </div>

      <div style="margin-top:8px">
        <div v-if="isCompleted(level.id)" class="small-muted" style="color:green">您已完成该实验 ✓</div>
      </div>

      <div class="experiment-box">
        <div><strong>实验（预览）</strong></div>
        <div v-if="level.experiment">
          <div><strong>名称：</strong>{{ level.experiment.name }}</div>
          <div><strong>目标：</strong>{{ level.experiment.goal }}</div>
          <div><strong>输入材料：</strong>{{ level.experiment.input_materials }}</div>
          <div><strong>工具：</strong>{{ level.experiment.tools_required }}</div>
          <div><strong>预期输出：</strong>{{ level.experiment.expected_output }}</div>
        </div>
        <div v-else class="small-muted">本关卡未返回实验信息</div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchLevel } from '../api'
import { useRoute } from 'vue-router'
import { isComplete, subscribe } from '../completion'

export default {
  name: 'Level',
  setup(){
    const route = useRoute()
    const level = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const parentChapterId = ref(null)

    async function load(){
      loading.value = true; error.value = null
      try{
        const data = await fetchLevel(route.params.id)
        level.value = data
        parentChapterId.value = data?.chapter_id || null
      }catch(e){
        error.value = e.message
      }finally{
        loading.value = false
      }
    }

    const updateOnComplete = (id) => {
      if(level.value && String(level.value.id) === String(id)){
        level.value = Object.assign({}, level.value)
      }
    }

    let unsub = null
    onMounted(() => { load(); unsub = subscribe(updateOnComplete) })
    onUnmounted(() => { if(unsub) unsub() })

    return { level, loading, error, parentChapterId, isCompleted: isComplete }
  }
}
</script>