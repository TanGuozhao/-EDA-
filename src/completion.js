// 简单的完成状态管理（localStorage + 事件广播）
// 存储格式：localStorage['completed_levels'] = JSON.stringify(["1","2",...])
export function isComplete(levelId){
  try{
    const s = localStorage.getItem('completed_levels')
    if(!s) return false
    const arr = JSON.parse(s)
    return arr.includes(String(levelId))
  }catch(e){
    return false
  }
}

export function setComplete(levelId){
  try{
    const key = 'completed_levels'
    const s = localStorage.getItem(key)
    const arr = s ? JSON.parse(s) : []
    const idStr = String(levelId)
    if(!arr.includes(idStr)){
      arr.push(idStr)
      localStorage.setItem(key, JSON.stringify(arr))
    }
    // 广播事件，通知页面其他组件更新
    window.dispatchEvent(new CustomEvent('level-complete', { detail: { id: idStr } }))
    return true
  }catch(e){
    console.error('setComplete error', e)
    return false
  }
}

// 取消订阅示例用法：const unsub = subscribe(fn); unsub()
export function subscribe(fn){
  const handler = (e) => { fn(e.detail.id) }
  window.addEventListener('level-complete', handler)
  return () => window.removeEventListener('level-complete', handler)
}