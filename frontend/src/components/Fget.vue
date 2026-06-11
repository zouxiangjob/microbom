<template>
  <div class="referenced-container">

        <!-- 顶部标题栏 -->
    <div class="header-section">
      <h2 class="page-title">ME000000253/B.1;GSK磨床</h2>
    </div>
    <!-- 横向菜单（与其他页面保持一致，切换时会触发路由跳转） -->
    <el-tabs v-model="activeTab" class="custom-tabs">
        <el-tab-pane label="基本属性" name="basic" />
        <el-tab-pane label="BOM" name="bom" />
        <el-tab-pane label="CAD 模型" name="cad" />
        <el-tab-pane label="相关文档" name="docs" />
        <el-tab-pane label="版本历史" name="history" />
        <el-tab-pane label="被引用" name="referenced" />
        <el-tab-pane label="流程" name="workflow" />
      </el-tabs>
    <!-- 图表操作浮层 -->
    <div class="graph-toolbar">
      <el-button-group>
        <el-tooltip content="全屏"><el-button :icon="FullScreen" size="small" /></el-tooltip>
        <el-tooltip content="自适应"><el-button :icon="Aim" size="small" /></el-tooltip>
      </el-button-group>
      <div class="zoom-info">100%</div>
      <el-button-group>
        <el-button :icon="Plus" size="small" />
        <el-button :icon="Minus" size="small" />
        <el-button :icon="RefreshRight" size="small" />
      </el-button-group>
    </div>

    <!-- 图表容器 -->
    <div id="container" class="graph-canvas"></div>
      <!-- 顶部横向工具栏（保持与其他页面一致） -->
      <div class="header-section">
        <h2 class="page-title">ME000000253/B.1;GSK磨床</h2>
      </div>
      <div class="horizontal-toolbar">
        <el-button type="primary">创建</el-button>
        <el-button>属性比对</el-button>
        <el-dropdown>
          <el-button>导入<el-icon class="el-icon--right"><arrow-down /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>Excel导入</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button>导出</el-button>
        <el-button type="primary" plain>提交至工作流程</el-button>
      </div>

  
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { FullScreen, Aim, Plus, Minus, RefreshRight } from '@element-plus/icons-vue'
import LogicFlow from '@logicflow/core'
import '@logicflow/core/lib/style/index.css'

const router = useRouter()
const activeTab = ref('referenced')

watch(activeTab, (newVal) => {
  const routeMap = {
    'basic': '/attribute',
    'bom': '/bom',
    'cad': '/cad',
    'docs': '/doc',
    'history': '/ehistory',
    'referenced': '/fget',
    'workflow': '/gbmnp'
  }
  if (routeMap[newVal]) router.push(routeMap[newVal])
})

onMounted(() => {
  const lf = new LogicFlow({
    container: document.querySelector('#container'),
    grid: false,
    isSilentMode: true, // 只读模式
    edgeTextDraggable: false,
  })

  // 定义图表数据
  const data = {
    nodes: [
      { id: '1', type: 'rect', x: 100, y: 200, text: 'GSK磨床, B.1/ME000000253', properties: { style: { fill: '#409eff', stroke: '#409eff', radius: 20 }}},
      { id: '2', type: 'rect', x: 400, y: 100, text: '批量替换测试A2, A.1/ME000000721' },
      { id: '3', type: 'rect', x: 400, y: 200, text: '批量替换测试A3, A.2/ME000000722' },
      { id: '4', type: 'rect', x: 400, y: 300, text: '批量替换测试A4, A.1/ME000000723' },
      { id: '5', type: 'rect', x: 700, y: 100, text: '批量替换测试A1...' }
    ],
    edges: [
      { sourceNodeId: '1', targetNodeId: '2', text: '工艺与资源的分配关系', type: 'polyline' },
      { sourceNodeId: '1', targetNodeId: '3', text: '工艺与资源的分配关系', type: 'polyline' },
      { sourceNodeId: '1', targetNodeId: '4', text: '工艺与资源的分配关系', type: 'polyline' },
      { sourceNodeId: '2', targetNodeId: '5', text: '工艺工序关系', type: 'polyline' },
      { sourceNodeId: '3', targetNodeId: '5', text: '工艺工序关系', type: 'polyline' }
    ]
  }

  // 自定义节点和连线样式（模拟图中圆角矩形和红色文字连线）
  lf.setTheme({
    rect: {
      fill: '#409eff',
      stroke: '#409eff',
      color: '#fff',
      radius: 15,
    },
    polyline: {
      stroke: '#dcdfe6',
    },
    edgeText: {
      color: '#f56c6c', // 红色文字
      fontSize: 11,
      background: { fill: 'transparent' }
    }
  })

  lf.render(data)
  lf.translateCenter() // 居中显示
})
</script>

<style scoped>
.referenced-container {
  position: relative;
  height: 600px;
  background-color: #fff;
  border: 1px solid #ebeef5;
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

/* 右侧浮动工具栏样式 */
.graph-toolbar {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  background: #fdfdfd;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
  z-index: 10;
}

.zoom-info {
  text-align: center;
  font-size: 12px;
  color: #909399;
  padding: 5px 0;
}

/* 修改 LogicFlow 文本位置及样式 */
:deep(.lf-element-text) {
  pointer-events: none;
}
</style>
