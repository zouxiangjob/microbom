<template>
  <!-- :key 强制在路由参数变化（如 /attribute/A → /attribute/B）时重建组件，
       否则详情页里 `route.params.id` 是顶层常量，组件复用后不会重新拉数据 -->
  <router-view :key="$route.fullPath" />
</template>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  /* 不在全局禁用滚动：首页由自身容器裁剪，详情页内容超出视口需要滚动 */
}
</style>
