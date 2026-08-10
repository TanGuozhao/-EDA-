<template>
  <SchedulingDagEditor
    :original-graph="schedulingDemoGraph"
    :algorithms="schedulingAlgorithms"
    initial-algorithm="asap"
    @graph-changed="captureGraph"
    @submit="captureSubmission"
  />
</template>

<script>
import SchedulingDagEditor from '../components/SchedulingDagEditor.vue'
import { schedulingAlgorithms, schedulingDemoGraph } from '../scheduling/demoGraph'

export default {
  name: 'SchedulingDemo',
  components: { SchedulingDagEditor },
  setup() {
    function captureGraph() {
      // Formal pages will send the raw graph state to a backend scheduling service.
    }

    function captureSubmission() {
      // This prototype captures no answer locally and performs no scheduling calculation.
    }

    return { captureGraph, captureSubmission, schedulingAlgorithms, schedulingDemoGraph }
  },
}
</script>
