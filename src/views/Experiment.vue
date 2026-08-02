<template>
  <div>
    <div class="nav-row">
      <router-link to="/chapters" class="btn secondary">返回章节列表</router-link>
      <router-link v-if="level?.chapter_id" :to="{ name:'Chapter', params:{ id: level.chapter_id } }" class="btn secondary">返回章节</router-link>
      <router-link v-if="level" :to="{ name:'Level', params:{ id: level.id } }" class="btn secondary">返回关卡</router-link>
    </div>

    <div v-if="loading" class="loading">加载实验中……</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>

    <div v-if="level" class="card">
      <div class="level-title">{{ level.title }} — 实验详情</div>
      <p class="small-muted">{{ level.description }}</p>

      <div v-if="level.experiment" style="margin-top:10px">
        <h3>{{ level.experiment.name }}</h3>
        <p><strong>目标：</strong>{{ level.experiment.goal }}</p>
        <p><strong>输入材料：</strong>{{ level.experiment.input_materials }}</p>
        <p><strong>工具要求：</strong>{{ level.experiment.tools_required }}</p>
        <p><strong>预期输出：</strong>{{ level.experiment.expected_output }}</p>
        <p><strong>通过标准：</strong>{{ level.experiment.pass_criteria || level.pass_criteria || '无' }}</p>

        <div style="margin-top:14px; display:flex; gap:8px">
          <button class="btn" @click="startExperiment">开始实验（模拟）</button>
          <button class="btn secondary" @click="showTips">查看做题提示</button>
          <button class="btn" v-if="!completed" @click="markComplete" style="background:green">标记为已完成</button>
          <div v-else class="small-muted" style="color:green; align-self:center">已标记为已完成 ✓</div>
        </div>
      </div>

      <div v-else class="empty">未找到实验信息</div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchLevel } from '../api'
import { useRoute } from 'vue-router'
import { isComplete, setComplete, subscribe } from '../completion'

export default {
  name: 'Experiment',
  setup(){
    const route = useRoute()
    const level = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const completed = ref(false)

    async function load(){
      loading.value = true; error.value = null
      try{
        const data = await fetchLevel(route.params.id)
        level.value = data
        completed.value = isComplete(data.id)
      }catch(e){
        error.value = e.message
      }finally{
        loading.value = false
      }
    }

    function startExperiment(){
      alert('开始实验（演示）：可以在这里打开实验环境或提交答案接口。')
    }
    function showTips(){
      alert('提示：阅读“输入材料”和“预期输出”，确保使用工具按要求生成结果并满足通过标准。')
    }

    function markComplete(){
      if(level.value && level.value.id){
        const ok = setComplete(level.value.id)
        if(ok){
          completed.value = true
          alert('已标记为完成。')
        }else{
          alert('标记失败，请检查本地存储设置。')
        }
      }
    }

    const onCompleteEvent = (id) => {
      if(level.value && String(level.value.id) === String(id)){
        completed.value = true
      }
    }

    let unsub = null
    onMounted(() => { load(); unsub = subscribe(onCompleteEvent) })
    onUnmounted(() => { if(unsub) unsub() })

    return { level, loading, error, startExperiment, showTips, markComplete, completed }
  }
}
</script>