<template>
  <div>
    <div class="nav-row">
      <span class="small-muted">请选择入口（示意页，最小改动实现四入口）</span>
    </div>

    <div class="grid chapters-grid">
      <div class="card">
        <div class="chapter-title">八章闯关</div>
        <div class="chapter-desc">从八章入口进入各章关卡与闯关流程（你原来的章节列表页面在此）。</div>
        <div style="margin-top:12px; display:flex; gap:8px;">
          <router-link to="/chapters" class="btn">进入八章闯关</router-link>
        </div>
      </div>

      <div class="card">
        <div class="chapter-title">实验关卡入口</div>
        <div class="chapter-desc">直接查看/搜索/进入实验关卡（按关卡列表或 ID 打开实验）。</div>
        <div style="margin-top:12px; display:flex; gap:8px;">
          <router-link to="/experiments" class="btn">进入实验关卡入口</router-link>
        </div>
      </div>

      <div class="card">
        <div class="chapter-title">工具验证入口</div>
        <div class="chapter-desc">工具验证（演示页）：用于验证外部工具或练习环境是否可用。</div>
        <div style="margin-top:12px; display:flex; gap:8px;">
          <router-link to="/tools" class="btn">工具验证</router-link>
        </div>
      </div>

      <div class="card">
        <div class="chapter-title">学习记录</div>
        <div class="chapter-desc">展示用户学习记录和闯关进度（占位，可接后端接口）。</div>
        <div style="margin-top:12px; display:flex; gap:8px;">
          <router-link to="/records" class="btn">查看学习记录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Landing'
}
</script>