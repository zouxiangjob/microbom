<template>
  <div class="common-layout">
    <el-container class="layout-container">
      <el-header class="header">
        <div class="logo">TCL</div>
        <div class="search-wrapper">
          <el-input v-model="topSearch" placeholder="搜索..." class="top-search" />
        </div>
        <div class="header-icons">
          <el-icon><Bell /></el-icon>
          <el-icon><User /></el-icon>
        </div>
      </el-header>

      <el-container>
        <el-aside width="150px" class="main-aside">
          <el-menu default-active="5" class="side-menu" background-color="#001529" text-color="#fff">
            <el-menu-item index="1"><el-icon><HomeFilled /></el-icon><span>首页</span></el-menu-item>
            <el-sub-menu index="2">
              <template #title><el-icon><Management /></el-icon><span>BOM管理</span></template>
            </el-sub-menu>
            <el-sub-menu index="3">
              <template #title><el-icon><OfficeBuilding /></el-icon><span>工厂管理</span></template>
            </el-sub-menu>
            <el-sub-menu index="4">
              <template #title><el-icon><Operation /></el-icon><span>工艺规划</span></template>
            </el-sub-menu>
            <el-sub-menu index="5">
              <template #title><el-icon><Files /></el-icon><span>工艺资源模型</span></template>
              <el-menu-item index="5-1">工序</el-menu-item>
              <el-menu-item index="5-2">工步</el-menu-item>
            </el-sub-menu>
          </el-menu>
        </el-aside>

        <el-aside width="220px" class="tree-aside">
          <div class="tree-header">
            <el-input v-model="filterText" placeholder="查询" :prefix-icon="Search" />
          </div>
          <el-tree
            :data="treeData"
            :props="defaultProps"
            default-expand-all
            highlight-current
            class="resource-tree"
          />
        </el-aside>

        <el-main class="main-content">
          <div class="toolbar">
            <el-button type="primary" :icon="Plus">创建</el-button>
            <el-button :icon="CopyDocument">属性比对</el-button>
            <el-dropdown ml-2>
              <el-button :icon="Download">导入<el-icon class="el-icon--right"><arrow-down /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item>Excel导入</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button :icon="Upload">导出</el-button>
            <el-button type="primary" plain>提交至工作流程</el-button>
          </div>

          <div class="search-form">
            <el-form :inline="true" :model="searchForm">
              <el-form-item label="模糊搜索"><el-input v-model="searchForm.code" /></el-form-item>            
              <el-form-item>
                <el-button type="primary">查询</el-button>
                <el-button>重置</el-button>
              </el-form-item>
            </el-form>
          </div>

          <el-table :data="tableData" border style="width: 100%" class="data-table">
            <el-table-column type="selection" width="40" />
            <el-table-column prop="displayName" label="显示名称" min-width="180" sortable>
              <template #default="scope">
                <el-link type="primary" @click="navigateToAttribute(scope.row)">
                  {{ scope.row.displayName }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="status" label="数据状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === '工作中' ? 'success' : 'warning'">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="version" label="修订版本" width="100" />
            <el-table-column prop="creator" label="创建者" width="120" />
            <el-table-column label="操作" fixed="right" width="180">
              <template #default>
                <el-button link type="primary">编辑</el-button>
                <el-button link type="primary">提交</el-button>
                <el-button link type="primary">分类</el-button>
                <el-dropdown trigger="click">
                  <span class="el-dropdown-link">...</span>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item>另存</el-dropdown-item>
                      <el-dropdown-item>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              layout="total, prev, pager, next, sizes"
              :total="271"
              :page-size="10"
              class="mt-4"
            />
          </div>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, Plus, CopyDocument, Download, Upload, 
  Bell, User, HomeFilled, Management, OfficeBuilding, Operation, Files 
} from '@element-plus/icons-vue'

const router = useRouter()
const topSearch = ref('')
const filterText = ref('')

const searchForm = reactive({
  code: '',
  name: '',
  type: ''
})

// 树形数据
const treeData = [
  {
    label: '辅助材料',
    children: []
  },
  {
    label: '基础材料',
    children: []
  },
  {
    label: '工艺资源库',
    children: [
      {
        label: '技能',
        children: [{ label: '人员技能' }]
      },
      {
        label: '工艺装备'
      },
      {
        label: '设备',
        children: [
          { label: '五轴铣床/加工中心' },
          { label: '车床', children: [{ label: '车床6063' }] }
        ]
      }
    ]
  }
]

const defaultProps = {
  children: 'children',
  label: 'label',
}

// 表格数据
const tableData = ref([
  { displayName: 'ME000000335/A.1;CNC机', name: 'CNC机', status: '工作中', version: 'A.1', creator: 'lixuan1001' },
  { displayName: 'ME000000334/A.1;二氧化碳焊机', name: '二氧化碳焊机', status: '工作中', version: 'A.1', creator: 'lixuan1001' },
  { displayName: 'ME000000333/A.2;工资资源', name: '工资资源', status: '审批中', version: 'A.2', creator: 'lixuan1001' },
  { displayName: 'ME000002981/A.2;530工艺资源测试', name: '530工艺资源测试2', status: '工作中', version: 'A.2', creator: 'UserTest123' },
  { displayName: 'ME000000332/B.1;测试新建-编辑', name: '测试新建-编辑', status: '工作中', version: 'B.1', creator: 'zhanglifan' },
])

// 导航到属性页面
const navigateToAttribute = (row) => {
  router.push('/attribute')
}
</script>

<style scoped>
.common-layout {
  height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.layout-container {
  height: 100%;
}

.header {
  background-color: #409eff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: white;
  padding: 0 20px;
}

.logo {
  font-size: 24px;
  font-weight: bold;
  width: 150px;
}

.search-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
}

.top-search {
  width: 400px;
}

.header-icons .el-icon {
  font-size: 20px;
  margin-left: 20px;
  cursor: pointer;
}

.main-aside {
  background-color: #001529;
}

.side-menu {
  border-right: none;
}

.tree-aside {
  border-right: 1px solid #dcdfe6;
  padding: 10px;
  background-color: #fff;
}

.tree-header {
  margin-bottom: 15px;
}

.main-content {
  background-color: #f0f2f5;
  padding: 15px;
}

.toolbar {
  background: #fff;
  padding: 10px 15px;
  margin-bottom: 10px;
  display: flex;
  gap: 10px;
}

.search-form {
  background: #fff;
  padding: 15px 15px 0;
  margin-bottom: 10px;
}

.data-table {
  margin-top: 10px;
}

.pagination-container {
  background: #fff;
  padding: 10px;
  display: flex;
  justify-content: flex-end;
}

.el-dropdown-link {
  cursor: pointer;
  color: var(--el-color-primary);
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
}
</style>