<template>
  <section class="timing-task-card">
    <div class="timing-task-card-header">
      <h3>{{ title }}</h3>
      <slot name="action">
        <span v-if="eyebrow" class="timing-task-card-eyebrow">{{ eyebrow }}</span>
      </slot>
    </div>
    <div class="timing-task-card-body">
      <slot />
    </div>
  </section>
</template>

<script>
export default {
  name: 'TimingTaskCard',
  props: {
    title: { type: String, required: true },
    eyebrow: { type: String, default: '' },
  },
}
</script>
