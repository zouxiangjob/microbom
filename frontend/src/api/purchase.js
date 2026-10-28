import api from './index'

// BOM 打平汇总：GET /purchase/flatten
export function fetchPurchaseRows() {
  return api.get('/purchase/flatten')
}

// 导出 ERP 采购导入 Excel：POST /purchase/export（返回 blob 并触发浏览器下载）
export async function exportPurchaseExcel() {
  const blob = await api.post('/purchase/export', {}, { responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '采购订单导入表.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
