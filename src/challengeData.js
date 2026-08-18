export const chapters = [
  ['系统设计和规格定义', '明确芯片目标、系统架构、接口规格和关键约束。'],
  ['逻辑设计', '把规格转化为 RTL 模块、数据通路和控制逻辑。'],
  ['功能验证', '构建测试平台、覆盖率目标和回归验证流程。'],
  ['物理设计', '完成布局布线、时钟树、功耗和面积优化。'],
  ['时序分析和电气验证', '检查时序收敛、电压降、串扰和可靠性问题。'],
  ['DRC/LVS', '验证版图设计规则，并确认版图与原理图一致。'],
  ['制造准备与测试', '生成流片交付物，规划 DFT、ATE 和量产测试。'],
  ['芯片制造与封装', '理解晶圆制造、封装选择、良率和失效分析。'],
].map(([title, description], index) => ({
  id: index + 1,
  title,
  description,
  levels: buildLevels(index + 1, title),
}))

function buildLevels(chapterId, chapterTitle){
  return Array.from({ length: 8 }, (_, index) => {
    const levelNumber = index + 1
    const isExperiment = levelNumber === 8 && [6, 7, 8].includes(chapterId)
    
    // 实验关卡的标题和描述
    const experimentTitles = {
      6: '🧪 DRC/LVS 实验',
      7: '🧪 制造准备与测试实验',
      8: '🧪 芯片制造与封装实验'
    }
    const experimentDescriptions = {
      6: '完成 DRC 三小关和 LVS 网表比对实验',
      7: '完成数据完整性检查和扫描链设计实验',
      8: '完成制造流程排队和封装匹配实验'
    }

    return {
      id: chapterId * 100 + levelNumber,
      chapter_id: chapterId,
      title: isExperiment ? experimentTitles[chapterId] : `第${levelNumber}关`,
      description: isExperiment ? experimentDescriptions[chapterId] : '',
      status: 'unlocked',
      pass_criteria: isExperiment ? '完成所有实验子关卡并通关。' : '完成本关任务并提交结果。',
      is_experiment: isExperiment,  // 新增标记字段
    }
  })
}

export function getChapter(id){
  return chapters.find(chapter => String(chapter.id) === String(id))
}

export function getLevel(id){
  for(const chapter of chapters){
    const level = chapter.levels.find(item => String(item.id) === String(id))
    if(level) return { ...level, chapterTitle: chapter.title }
  }
  return null
}