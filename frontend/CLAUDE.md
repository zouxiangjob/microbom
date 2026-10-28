# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Vue 3 + Vite frontend for a BOM / PDM management system (product structure, parts, technical documents, CAD drawings). It talks to the backend through a real API layer (`src/api/*`); components fetch live data rather than render hardcoded mock data. The backend is a separate FastAPI app in `../backend/` (see its own `CLAUDE.md`), served at `http://127.0.0.1:8000`.

## Architecture

- **Entry** — `src/main.js` registers vue-router and Element Plus globally (`app.use(ElementPlus)`) and imports the global theme `src/styles/theme.css`.
- **Routing** — `src/router/index.js` maps one route per page. `/` is the home/list page (`Index.vue`); the rest are "detail" pages, each carrying an `:id` param (the node UUID, from the backend's `objects.id`).
- **Detail pages** share one layout via `src/components/DetailLayout.vue`. It renders the page title, a back button, and a horizontal tab bar whose tabs are defined by the single source of truth `src/constants/detailTabs.js` (`DETAIL_TABS`). Each tab maps to a route, and `DetailLayout` navigates on tab change — reading `route.params.id` and appending it to the tab path so the node context survives tab switches. The 6 tabs are: 基本属性 / BOM / 图档 / 技术文档 / 版本历史 / 被引用.
  - To add or remove a detail tab, edit `DETAIL_TABS` in `src/constants/detailTabs.js`, update the route in `src/router/index.js`, and create/delete the component in `src/components/`.
- **Detail page components** (`Attribute.vue`, `Bom.vue`, `RelatedObjects.vue`, `VersionHistory.vue`, `WhereUsed.vue`) each wrap their page-specific markup in `<DetailLayout title="..." active-tab="...">` and contain no shared header/tab code. 图档 and 技术文档 share one component `RelatedObjects.vue`, switched by a `kind` prop (`drawing` | `document`); 版本历史 = `VersionHistory.vue`, 被引用 = `WhereUsed.vue`. The tab→route mapping lives in `src/constants/detailTabs.js`, with routes registered in `src/router/index.js`.
- **Non-part object pages** — technical documents and drawings have their own detail pages under `/object/:objectType/...` (`objectType` = `document` | `drawing`), built from `ObjectBasic.vue` / `ObjectParts.vue` / `VersionHistory.vue` / `WhereUsed.vue` (the last two are reused from the part detail pages). They share `DetailLayout` but use the smaller tab set `OBJECT_DETAIL_TABS` (基本属性 / 零部件 / 版本历史 / 被引用), passing `path-prefix="/object/{objectType}"` so the node context survives tab switches.
- **Home page** — `src/components/Index.vue`: left navigation menu + resource tree + data table. The left menu is click-driven; the `activeMenu` ref determines what the right pane renders (via the `showResourceList` computed).
- **Category attribute management** — `src/components/CategoryAttributes.vue` (route `/category/:id/attributes`) manages per-category attribute definitions (`attr_key` / `attr_label` / `value_type` / `required` / `options` / `unit` / `sort_order`). Reached from the category-tree header in `Index.vue` when a category is selected. The part detail page `Attribute.vue` renders a part's category attributes dynamically from these definitions via `getPartAttributeSchema`.

## Key conventions

- **API 接入层已就绪，组件已真实拉取数据。** `src/api/index.js` 是 axios 实例，`baseURL` 默认走相对路径 `/api/v1/`（可用 `VITE_API_BASE` 环境变量覆盖，见 `.env.example`），带响应归一化拦截器：成功直接返回 `data`，失败转成带 `message` 的 `Error`（组件 catch 后 `ElMessage(error.message)`）。
  - `src/api/nodes.js` — 节点 CRUD（`listNodes` / `getNode` / `createNode` / `updateNode` / `deleteNode`），`NODE_TYPES` = part/document/drawing/attachment/category。
  - `src/api/relations.js` — 关系与树穿透：`getNodeTree`（正向）、`getReverseTree`（反向 Where-Used）、`createRelation` / `deleteRelation`。
  - `src/api/files.js` — 文件上传/预览/下载/元数据（`uploadFile` / `fileUrl` / `getFileMeta`），文档与图档的物理文件走这里。
  - `src/api/category-attributes.js` — 分类属性定义 CRUD + 零件属性清单聚合（`listCategoryAttributes` / `getPartAttributeSchema` / `createCategoryAttribute` / `updateCategoryAttribute` / `deleteCategoryAttribute`）。
  - `src/api/mapping.js` — 前后端字段映射契约与统一工具（`nodeToRow` / `documentToRow` / `drawingToRow` / `nodeTitle` / `nodeDisplayName` / `nodeLabel` / `statusTagType`）。
  - `src/utils/tree.js` — 把后端平铺树转成 el-tree 嵌套结构（`flatToTree` / `flatToReverseTree`）。注意：当前 `Bom.vue` / `WhereUsed.vue` 等仍各自手写了树构建逻辑，尚未复用这里的工具。
- **关系类型有两套字符串，别混用。** `relations.js` 的 `RELATION_TYPES` 是 URL 段（如 `BOM: 'bom'`），用于请求路径；而数据里 `edge.relation_type` 是下划线全名（`bom_relation` / `part_drawing_relation` / `part_doc_relation`），用于过滤与展示。DRAWING、DOCUMENT 两种恰好 URL 段 == 数据名，唯独 BOM 不一致（`'bom'` vs `'bom_relation'`），`Bom.vue` 里硬编码了 `'bom_relation'`。
- **Vite proxy 已配置** — `vite.config.js` 把 `/api` 代理到 `http://127.0.0.1:8000`（`changeOrigin: true`），开发环境前端 `baseURL` 走相对路径即可；生产构建用 `VITE_API_BASE` 指向后端完整地址。
- **Element Plus** is registered globally (no on-demand import); icons are imported explicitly from `@element-plus/icons-vue` in each component that uses them.
- **Styling** — `src/styles/theme.css` is the single source of truth for design tokens: a "drafting table / refined blueprint" theme — warm paper (`--paper`), ink-blue text (`--ink-*`), one cyan accent (`--blue`), hairline rules (`--line`). Bahnschrift (DIN) for headers, Segoe UI for body, monospace (`--font-data`) for codes/versions. Element Plus primary is remapped to the cyan accent.
