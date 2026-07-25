const BASE = 'http://127.0.0.1:8000'

async function request(path){
  const url = BASE + path
  const res = await fetch(url, {credentials: 'same-origin'})
  if(!res.ok){
    const text = await res.text().catch(()=>null)
    throw new Error(`${res.status} ${res.statusText} ${text ? ' - ' + text : ''}`)
  }
  return res.json()
}

export async function fetchChapters(){
  // GET /api/chapters/
  return request('/api/chapters/')
}

export async function fetchChapter(id){
  // GET /api/chapters/{id}
  return request(`/api/chapters/${encodeURIComponent(id)}`)
}

export async function fetchLevel(id){
  // GET /api/chapters/levels/{id}
  return request(`/api/chapters/levels/${encodeURIComponent(id)}`)
}
export async function fetchExperimentLevels() {
  return request('/api/chapters/experiments/list')
}