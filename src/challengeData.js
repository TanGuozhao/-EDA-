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
    const isTimingAnalysis = chapterId === 5 && levelNumber === 1
    return {
      id: chapterId * 100 + levelNumber,
      chapter_id: chapterId,
      title: isTimingAnalysis ? '时序分析' : `第${levelNumber}关`,
      description: '',
      status: 'unlocked',
      pass_criteria: '完成本关任务并提交结果。',
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
