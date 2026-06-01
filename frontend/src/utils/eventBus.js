// Simple event bus for cross-component communication
// 使用 window 全局对象确保单例
if (!window.__eventBus) {
  window.__eventBus = {}
}
const events = window.__eventBus

export function emit(event, data) {
  console.log('[EventBus] emit:', event, data)
  if (events[event]) {
    events[event].forEach(callback => callback(data))
  }
}

export function on(event, callback) {
  console.log('[EventBus] on:', event)
  if (!events[event]) {
    events[event] = []
  }
  events[event].push(callback)
  // 返回取消订阅函数
  return () => {
    events[event] = events[event].filter(cb => cb !== callback)
  }
}

export function off(event, callback) {
  if (events[event]) {
    events[event] = events[event].filter(cb => cb !== callback)
  }
}
