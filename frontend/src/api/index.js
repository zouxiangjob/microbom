import axios from 'axios'

// 后端 FastAPI 统一挂载在 /api/v1 前缀下（见 backend/app/api/v1/__init__.py）
// baseURL 默认走相对路径，由 Vite dev server 的 proxy 转发到后端（见 vite.config.js），
// 生产环境可用 VITE_API_BASE 环境变量覆盖（如 http://127.0.0.1:8000/api/v1/）。
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1/',
  timeout: 10000
})

// 响应归一化：
// - 成功：后端直接返回裸数据（对象/数组），这里透传 response.data
// - 失败：后端统一返回 { code, message, data }（见 backend/app/middleware/exceptions.py），
//   这里统一转成带 message 的 Error，组件 catch 后可直接 ElMessage(error.message)
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const body = error.response?.data
    const message =
      (body && (body.message || body.detail)) ||
      error.message ||
      '请求失败'
    return Promise.reject(new Error(message))
  }
)

export default api
