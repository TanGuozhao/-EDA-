<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>{{ level?.title || '关卡详情' }}</h2>
        <p v-if="level">{{ level.chapterTitle }} / {{ level.description }}</p>
      </div>
    </div>

    <div v-if="!level" class="error">关卡不存在</div>

    <div v-if="level" class="card">
      <router-link :to="{ name:'Chapter', params:{ id: level.chapter_id } }" class="btn secondary">返回章节</router-link>
      <div class="experiment-box">
        <div class="level-title">闯关任务</div>
        <p>{{ level.description }}</p>
        <div class="small-muted">通过标准：{{ level.pass_criteria }}</div>
      </div>

      <!-- ====== 实验入口（第8关） ====== -->
      <div v-if="isExperiment" style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #e9edf4;">
        <h3 style="font-size: 16px; margin-bottom: 8px;">🧪 实验关卡</h3>
        <p style="font-size: 14px; color: #6b7a8f; margin-bottom: 12px;">
          本章包含实验任务，请进入实验环境完成动手操作。
        </p>
        <a :href="experimentUrl" class="btn" style="background: #f5a623; color: white; text-decoration: none;">
          🚀 进入实验
        </a>
        <span style="margin-left: 12px; font-size: 13px; color: #6b7a8f;">
          {{ experimentHint }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { getLevel } from '../challengeData'

export default {
  name: 'Level',
  setup(){
    const route = useRoute()
    const level = computed(() => getLevel(route.params.id))

    const isExperiment = computed(() => {
      if (!level.value) return false
      const id = level.value.id
  // 第6章第8关 = 608，第7章第8关 = 708，第8章第8关 = 808
      return [608, 708, 808].includes(id)
    })

    const experimentUrl = computed(() => {
      if (!level.value) return '#'
      const map = {
        6: '/chapter6.html',
        7: '/chapter7.html',
        8: '/chapter8.html'
      }
      return map[level.value.chapter_id] || '#'
    })

    const experimentHint = computed(() => {
      const map = {
        6: 'DRC 三小关 + LVS',
        7: '数据完整性检查 + 扫描链三小关',
        8: '制造流程排队 + 封装匹配'
      }
      return map[level.value?.chapter_id] || ''
    })

    return { level, isExperiment, experimentUrl, experimentHint }
  }
}
</script>