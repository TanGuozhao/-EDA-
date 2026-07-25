<template>
  <div class="app">
    <header class="header">
      <h1>芯语智问 — EDA 闯关平台</h1>
      <nav>
        <router-link to="/">首页（八章闯关）</router-link>
      </nav>
    </header>

    <main class="main">
      <router-view />
    </main>

    <footer class="footer">
      <small>后端接口: http://127.0.0.1:8000 — /api/chapters/</small>
    </footer>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>