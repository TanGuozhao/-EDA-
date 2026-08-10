const SESSION_KEY = 'auth_session_key'
const USER_KEY = 'auth_user'

function safeParse(value) {
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

export function saveAuthSession({ sessionKey, user }) {
  if (!sessionKey) return
  localStorage.setItem(SESSION_KEY, sessionKey)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  window.dispatchEvent(new CustomEvent('auth:changed'))
}

export function getSessionKey() {
  return localStorage.getItem(SESSION_KEY) || ''
}

export function getCurrentUser() {
  return safeParse(localStorage.getItem(USER_KEY))
}

export function setCurrentUser(user) {
  if (!user) {
    localStorage.removeItem(USER_KEY)
  } else {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }
  window.dispatchEvent(new CustomEvent('auth:changed'))
}

export function clearAuthSession() {
  localStorage.removeItem(SESSION_KEY)
  localStorage.removeItem(USER_KEY)
  window.dispatchEvent(new CustomEvent('auth:changed'))
}

export function isAuthenticated() {
  return Boolean(getSessionKey())
}
