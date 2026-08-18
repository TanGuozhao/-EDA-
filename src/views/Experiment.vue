<template>
  <div>
    <div class="nav-row">
      <router-link to="/chapters" class="btn secondary">返回章节列表</router-link>
      <router-link v-if="level?.chapter_id" :to="{ name:'Chapter', params:{ id: level.chapter_id } }" class="btn secondary">返回章节</router-link>
      <router-link v-if="level" :to="{ name:'Level', params:{ id: level.id } }" class="btn secondary">返回关卡</router-link>
    </div>

    <div v-if="loading" class="loading">加载实验中……</div>
    <div v-if="error" class="error">请求失败: {{ error }}</div>

    <div v-if="level" class="card">
      <div class="level-title">{{ level.title }}</div>
      <p class="small-muted">{{ level.description }}</p>

      <!-- ====== 实验信息 ====== -->
      <div v-if="level.experiment" style="margin-top:16px;">
        <h3>🧪 {{ level.experiment.name }}</h3>
        <p><strong>目标：</strong>{{ level.experiment.goal }}</p>
        <p><strong>输入材料：</strong>{{ level.experiment.input_materials }}</p>
        <p><strong>工具要求：</strong>{{ level.experiment.tools_required }}</p>
        <p><strong>预期输出：</strong>{{ level.experiment.expected_output }}</p>
        <p><strong>通过标准：</strong>{{ level.experiment.pass_criteria || level.pass_criteria || '无' }}</p>

        <div style="margin-top:16px; display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn" @click="startExperiment">开始实验</button>
          <button class="btn secondary" @click="showTips">查看提示</button>
          <button class="btn" v-if="!completed" @click="markComplete" style="background:#2e7d32;">标记为已完成</button>
          <span v-else style="color:#2e7d32; font-weight:600;">✅ 已完成</span>
        </div>
      </div>

      <div v-else class="empty">未找到实验信息</div>

      <!-- ====== 实验操作区（根据实验类型动态显示） ====== -->
      <div v-if="level && level.experiment" style="margin-top:20px; border-top:1px solid #e9edf4; padding-top:16px;">
        <h4>📋 实验操作区</h4>
        <p class="small-text">根据实验类型选择操作：</p>

        <!-- DRC -->
        <div v-if="level.experiment.name && level.experiment.name.includes('DRC')">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <button class="btn secondary" @click="drcAction('rule1')">匹配规则 1</button>
            <button class="btn secondary" @click="drcAction('rule2')">匹配规则 2</button>
            <button class="btn secondary" @click="drcAction('rule3')">匹配规则 3</button>
            <button class="btn" @click="drcSubmit">提交 DRC 结果</button>
          </div>
        </div>

        <!-- LVS -->
        <div v-if="level.experiment.name && level.experiment.name.includes('LVS')">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <button class="btn secondary" @click="lvsAction('compare')">对比网表</button>
            <button class="btn secondary" @click="lvsAction('modify')">修改版图</button>
            <button class="btn" @click="lvsSubmit">重新提取并比对</button>
          </div>
        </div>

        <!-- 扫描链 -->
        <div v-if="level.experiment.name && level.experiment.name.includes('扫描链')">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <button class="btn secondary" @click="scanAction('level1')">连成链</button>
            <button class="btn secondary" @click="scanAction('level2')">优化链</button>
            <button class="btn secondary" @click="scanAction('level3')">故障诊断</button>
            <button class="btn" @click="scanSubmit">提交扫描链结果</button>
          </div>
        </div>

        <!-- 制造流程 -->
        <div v-if="level.experiment.name && (level.experiment.name.includes('制造') || level.experiment.name.includes('流程'))">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <button class="btn secondary" @click="flowAction('sort')">排序步骤</button>
            <button class="btn" @click="flowSubmit">提交排序</button>
          </div>
        </div>

        <!-- 封装匹配 -->
        <div v-if="level.experiment.name && level.experiment.name.includes('封装')">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <button class="btn secondary" @click="pkgAction('chip_a')">芯片 A</button>
            <button class="btn secondary" @click="pkgAction('chip_b')">芯片 B</button>
            <button class="btn secondary" @click="pkgAction('chip_c')">芯片 C</button>
            <button class="btn" @click="pkgSubmit">提交封装匹配</button>
          </div>
        </div>

        <!-- 数据完整性检查 -->
        <div v-if="level.experiment.name && level.experiment.name.includes('数据完整性')">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
            <button class="btn secondary" @click="checklistAction('gds')">GDSII</button>
            <button class="btn secondary" @click="checklistAction('lef')">LEF</button>
            <button class="btn secondary" @click="checklistAction('lib')">Liberty</button>
            <button class="btn secondary" @click="checklistAction('dmr')">DRC Report</button>
            <button class="btn secondary" @click="checklistAction('sdf')">SDF</button>
            <button class="btn" @click="checklistSubmit">提交检查结果</button>
          </div>
        </div>

        <!-- 通用提交 -->
        <div style="margin-top:12px;">
          <button class="btn" @click="submitExperiment">📤 提交实验</button>
        </div>

        <!-- 结果展示 -->
        <div v-if="result" :class="['result-box', result.passed ? 'success' : 'error']" style="margin-top:12px;">
          <pre>{{ JSON.stringify(result, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <div v-if="!loading && !level" class="empty">实验不存在</div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchLevel } from '../api'
import { useRoute } from 'vue-router'
import { isComplete, setComplete, subscribe } from '../completion'

export default {
  name: 'Experiment',
  setup(){
    const route = useRoute()
    const level = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const completed = ref(false)
    const result = ref(null)

    async function load(){
      loading.value = true; error.value = null; result.value = null
      try{
        const data = await fetchLevel(route.params.id)
        level.value = data
        completed.value = isComplete(data.id)
      }catch(e){
        error.value = e.message
      }finally{
        loading.value = false
      }
    }

    function startExperiment(){
      alert('开始实验！请根据实验要求完成操作。')
    }

    function showTips(){
      const tips = {
        'DRC': '阅读规则列表，判断每个违规位置对应的规则。',
        'LVS': '对比两份网表，找出不一致的地方并修改版图。',
        '扫描链': '按正确顺序连接寄存器，优化链成本，诊断故障。',
        '制造流程': '将制造步骤按正确顺序排列。',
        '封装匹配': '根据芯片引脚数、功耗和应用场景匹配封装。',
        '数据完整性': '检查数据包，标记异常项。'
      }
      const name = level.value?.experiment?.name || ''
      let tip = '请仔细阅读实验目标和通过标准。'
      for (const [key, value] of Object.entries(tips)) {
        if (name.includes(key)) tip = value
      }
      alert('💡 提示：' + tip)
    }

    function markComplete(){
      if(level.value && level.value.id){
        const ok = setComplete(level.value.id)
        if(ok){
          completed.value = true
          alert('✅ 已标记为完成！')
        }else{
          alert('❌ 标记失败，请检查本地存储设置。')
        }
      }
    }

    // 各实验的模拟操作
    function drcAction(rule){ alert(`DRC: 已选择规则 ${rule}`) }
    function drcSubmit(){ 
      result.value = { passed: true, message: 'DRC 检查通过！所有违规已匹配。' }
    }

    function lvsAction(action){ alert(`LVS: 执行 ${action}`) }
    function lvsSubmit(){ 
      result.value = { passed: true, message: 'LVS 通过！网表完全一致。' }
    }

    function scanAction(level){ alert(`扫描链: 进入 ${level}`) }
    function scanSubmit(){ 
      result.value = { passed: true, message: '扫描链优化完成！成本最优。' }
    }

    function flowAction(action){ alert(`制造流程: ${action}`) }
    function flowSubmit(){ 
      result.value = { passed: true, message: '制造流程排序正确！' }
    }

    function pkgAction(chip){ alert(`封装匹配: 选择 ${chip}`) }
    function pkgSubmit(){ 
      result.value = { passed: true, message: '封装匹配全部正确！' }
    }

    function checklistAction(item){ alert(`数据完整性: 标记 ${item}`) }
    function checklistSubmit(){ 
      result.value = { passed: true, message: '数据完整性检查通过！所有项已标记。' }
    }

    async function submitExperiment(){
      alert('📤 提交实验数据到后端...')
      // 这里可以调用具体的提交接口
    }

    const onCompleteEvent = (id) => {
      if(level.value && String(level.value.id) === String(id)){
        completed.value = true
      }
    }

    let unsub = null
    onMounted(() => { load(); unsub = subscribe(onCompleteEvent) })
    onUnmounted(() => { if(unsub) unsub() })

    return { 
      level, loading, error, completed, result,
      startExperiment, showTips, markComplete,
      drcAction, drcSubmit,
      lvsAction, lvsSubmit,
      scanAction, scanSubmit,
      flowAction, flowSubmit,
      pkgAction, pkgSubmit,
      checklistAction, checklistSubmit,
      submitExperiment
    }
  }
}
</script>