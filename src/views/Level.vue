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
    return { level }
  }
}
</script>
