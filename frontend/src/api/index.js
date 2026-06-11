import axios from 'axios'

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/', // 后端 API 地址
  timeout: 10000
})

export default api
