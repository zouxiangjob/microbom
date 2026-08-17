import api from './index'

// 文件类型与后端 FILE_TYPE_MAPPER 对齐：attachment / drawing / document
export const FILE_TYPES = {
  ATTACHMENT: 'attachment',
  DRAWING: 'drawing',
  DOCUMENT: 'document'
}

// 上传：POST /files/{file_type}/upload（multipart：file + object_id）
export function uploadFile(fileType, objectId, file) {
  const form = new FormData()
  form.append('file', file)
  form.append('object_id', objectId)
  return api.post(`/files/${fileType}/upload`, form)
}

// 下载/预览地址：GET /files/download/{object_id}?inline=
export function fileUrl(objectId, inline = true) {
  return `${api.defaults.baseURL}files/download/${objectId}?inline=${inline}`
}

// 文件元数据：GET /files/{object_id}（无文件时后端返回 404）
export function getFileMeta(objectId) {
  return api.get(`/files/${objectId}`)
}
