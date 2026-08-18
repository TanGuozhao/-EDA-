import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Chapter from '../views/Chapter.vue'
import Level from '../views/Level.vue'
import Experiment from '../views/Experiment.vue'
import Experiments from '../views/Experiments.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/chapters',
    name: 'Chapters',
    component: Home
  },
  {
    path: '/chapter/:id',
    name: 'Chapter',
    component: Chapter
  },
  {
    path: '/level/:id',
    name: 'Level',
    component: Level
  },
  {
    path: '/experiments',
    name: 'Experiments',
    component: Experiments
  },
  {
    path: '/experiment/:id',
    name: 'Experiment',
    component: Level
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router