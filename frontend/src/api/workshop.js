import api from './index'

// 车间看图：GET /workshop/drawings?code=
export function fetchDrawings(code) {
  return api.get('/workshop/drawings', { params: { code } })
}
