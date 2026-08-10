<template>
  <div>
    <div class="nav-row">
      <router-link to="/chapters" class="btn secondary">返回八章闯关</router-link>
      <span class="small-muted">工具验证入口（最小演示）</span>
    </div>

    <div class="card">
      <div class="chapter-title">工具验证</div>
      <div class="chapter-desc">用于验证外部工具、环境或 API 是否可访问（你可以在这里扩展成真实的验证表单）。</div>

      <div style="margin-top:12px; display:flex; gap:8px;">
        <button class="btn" @click="pingBackend">检测后端连通性</button>
        <button class="btn secondary" @click="fakeToolCheck">模拟工具验证</button>
      </div>

      <div style="margin-top:12px" class="small-muted">结果：{{ result }}</div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { fetchChapters } from '../api'

export default {
  name: 'ToolVerify',
  setup(){
    const result = ref('— 未检测 —')

    async function pingBackend(){
      result.value = '检测中...'
      try{
        await fetchChapters()
        result.value = '后端 /api/chapters/ 可访问'
      }catch(e){
        result.value = '后端不可用: ' + e.message
      }
    }
    function fakeToolCheck(){
      result.value = '模拟工具验证通过（演示）'
    }

    return { result, pingBackend, fakeToolCheck }
  }
}
</script>