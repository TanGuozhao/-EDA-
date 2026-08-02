<template>
  <CircuitVerseWorkspace @editor-opened="markEditorOpened" @submit="captureSubmission" />
</template>

<script>
import CircuitVerseWorkspace from '../components/CircuitVerseWorkspace.vue'

export default {
  name: 'CircuitVerseDemo',
  components: { CircuitVerseWorkspace },
  setup() {
    function markEditorOpened() {
      // The formal level can use this event for telemetry without coupling to CircuitVerse UI.
    }

    function captureSubmission() {
      // The formal level will forward this raw payload to its backend validation endpoint.
    }

    return { captureSubmission, markEditorOpened }
  },
}
</script>
