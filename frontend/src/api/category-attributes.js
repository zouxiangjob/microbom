import api from './index'

// 查询某分类下的属性定义：GET /category-attributes?category_id=
export function listCategoryAttributes(categoryId) {
  return api.get('/category-attributes', { params: { category_id: categoryId } })
}

// 聚合：零件 → 所属分类的属性定义 + 当前值：GET /category-attributes/part-schema/{partId}
// 返回 { part_id, part_number, category_id, category_name, attributes: [{...def, value, has_value}] }
export function getPartAttributeSchema(partId) {
  return api.get(`/category-attributes/part-schema/${partId}`)
}

// 新增属性定义：POST /category-attributes
export function createCategoryAttribute(payload) {
  return api.post('/category-attributes', payload)
}

// 更新属性定义：PUT /category-attributes/{attrId}
export function updateCategoryAttribute(attrId, payload) {
  return api.put(`/category-attributes/${attrId}`, payload)
}

// 删除属性定义：DELETE /category-attributes/{attrId}
export function deleteCategoryAttribute(attrId) {
  return api.delete(`/category-attributes/${attrId}`)
}
