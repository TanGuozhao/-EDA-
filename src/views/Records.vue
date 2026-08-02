<template>
  <div>
    <div class="nav-row">
      <router-link to="/chapters" class="btn secondary">返回八章闯关</router-link>
      <span class="small-muted">学习记录（占位），可接后端 /api/records 等接口</span>
    </div>

    <div class="card">
      <div class="chapter-title">学习记录</div>
      <div class="chapter-desc">这里会展示用户的闯关进度、通过情况、分数等（当前为最小示例）。</div>

      <div style="margin-top:12px">
        <div class="small-muted">示例数据：</div>
        <ul>
          <li>张三：第 2 章 · 已通过：1/5</li>
          <li>李四：第 1 章 · 已通过：3/8</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
export default { name: 'Records' }
</script>