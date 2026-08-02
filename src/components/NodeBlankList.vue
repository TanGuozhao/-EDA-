<template>
  <div class="node-blank-list">
    <label v-for="nodeId in targetNodeIds" :key="nodeId" class="node-blank-row">
      <span>{{ nodeId }}:</span>
      <input
        :value="modelValue[nodeId] ?? ''"
        type="text"
        inputmode="decimal"
        :aria-label="`${nodeId} answer`"
        @input="updateValue(nodeId, $event.target.value)"
      />
    </label>
  </div>
</template>

<script>
export default {
  name: 'NodeBlankList',
  props: {
    targetNodeIds: { type: Array, default: () => [] },
    modelValue: { type: Object, default: () => ({}) },
  },
  emits: ['update:modelValue'],
  methods: {
    updateValue(nodeId, value) {
      this.$emit('update:modelValue', { ...this.modelValue, [nodeId]: value })
    },
  },
}
</script>
