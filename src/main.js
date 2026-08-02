import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'

import App from './App.vue'
import Chapter from './views/Chapter.vue'
import Experiment from './views/Experiment.vue'
import Experiments from './views/Experiments.vue'
import Home from './views/Home.vue'
import Landing from './views/Landing.vue'
import Level from './views/Level.vue'
import Login from './views/Login.vue'
import Me from './views/Me.vue'
import Records from './views/Records.vue'
import Register from './views/Register.vue'
import ToolVerify from './views/ToolVerify.vue'
import TimingAnalysis from './views/TimingAnalysis.vue'
import BlankTimingAnalysis from './views/BlankTimingAnalysis.vue'
import CircuitVerseDemo from './views/CircuitVerseDemo.vue'
import SchedulingDemo from './views/SchedulingDemo.vue'
import './assets/styles.css'
import { isAuthenticated } from './auth'

const routes = [
  { path: '/', component: Landing, name: 'Landing' },
  { path: '/login', component: Login, name: 'Login' },
  { path: '/register', component: Register, name: 'Register' },
  { path: '/me', component: Me, name: 'Me', meta: { requiresAuth: true } },
  { path: '/chapters', component: Home, name: 'Chapters' },
  { path: '/chapter/:id', component: Chapter, name: 'Chapter', props: true },
  { path: '/level/:id', component: Level, name: 'Level', props: true },
  { path: '/experiment/:id', component: Experiment, name: 'Experiment', props: true },
  { path: '/experiments', component: Experiments, name: 'Experiments' },
  { path: '/tools', component: ToolVerify, name: 'ToolVerify' },
  { path: '/records', component: Records, name: 'Records' },
  { path: '/timing-analysis', component: TimingAnalysis, name: 'TimingAnalysisPrototype' },
  { path: '/circuitverse-demo', component: CircuitVerseDemo, name: 'CircuitVerseDemo' },
  { path: '/scheduling-demo', component: SchedulingDemo, name: 'SchedulingDemo' },
  { path: '/chapter/5/timing-analysis', component: BlankTimingAnalysis, name: 'ChapterTimingAnalysis' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    return {
      name: 'Login',
      query: { redirect: to.fullPath },
    }
  }
  if ((to.name === 'Login' || to.name === 'Register') && isAuthenticated()) {
    return { name: 'Me' }
  }
  return true
})

createApp(App).use(router).mount('#app')
