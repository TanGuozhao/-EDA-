import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'         // 原来的章节列表（保留文件名 Home.vue）
import Chapter from './views/Chapter.vue'
import Level from './views/Level.vue'
import Experiment from './views/Experiment.vue'
import Landing from './views/Landing.vue'   // 新增
import Experiments from './views/Experiments.vue' // 新增
import ToolVerify from './views/ToolVerify.vue'   // 新增
import Records from './views/Records.vue'         // 新增
import './assets/styles.css'

const routes = [
  { path: '/', component: Landing, name: 'Landing' },    // 入口页（四入口）
  { path: '/chapters', component: Home, name: 'Chapters' }, // 八章闯关页（原 Home.vue）
  { path: '/chapter/:id', component: Chapter, name: 'Chapter', props: true },
  { path: '/level/:id', component: Level, name: 'Level', props: true },
  { path: '/experiment/:id', component: Experiment, name: 'Experiment', props: true },
  { path: '/experiments', component: Experiments, name: 'Experiments' }, // 实验关卡入口页
  { path: '/tools', component: ToolVerify, name: 'ToolVerify' }, // 工具验证入口
  { path: '/records', component: Records, name: 'Records' } // 学习记录入口
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

createApp(App).use(router).mount('#app')