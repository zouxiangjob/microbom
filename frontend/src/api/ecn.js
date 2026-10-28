import api from './index'

// 查询当前变更通知：GET /ecn/notifications
export function fetchEcnNotifications() {
  return api.get('/ecn/notifications')
}

// 确认知晓变更（清空通知）：POST /ecn/ack
export function ackEcn() {
  return api.post('/ecn/ack')
}
