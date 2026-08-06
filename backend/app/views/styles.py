"""
全局样式常量与 CSS 模板，统一管理所有视图层的视觉风格。
"""

GLOBAL_CSS = '''
    <style>
        /* 1. 全局表格表头：24px 粗体、深蓝字、浅灰蓝背景 */
        .q-table th {
            font-size: 24px !important;
            font-weight: bold !important;
            background-color: #f1f5f9 !important;
            color: #1e3a8a !important;
        }

        /* 2. 全局表格数据单元格：达到最大字号 24px，方便工业屏高清晰度阅读 */
        .q-table td {
            font-size: 20px !important;
            font-weight: 500 !important;
            color: #1f2937 !important;
        }

        /* 3. 全局按钮默认字体 */
        .q-btn__content {
            font-size: 24px !important;
            font-weight: bold;
        }

        /* 4. 输入框/下拉选择框：18px 大字号输入体验 */
        .q-field__native, .q-field__input {
            font-size: 18px !important;
        }
    </style>
'''

# 工宽行高便于业风大字号表格行内样式与样式类（最大字号 24px，2.2 倍触控）
INDUSTRIAL_TABLE_STYLE = 'font-size: 24px; line-height: 2.2; font-weight: 500;'
INDUSTRIAL_TABLE_CLASSES = 'w-full text-xl'

# UI 块标题层级样式常量（严格遵循字号阶梯，最高不超过 24px）
HEADER_LABEL_CLASSES = 'text-3xl font-black text-gray-800'  # 顶栏/资产库标题：24px
SECTION_HEADER_CLASSES = 'text-2xl font-black text-gray-900 mb-2'  # 区块大标题：24px
CARD_TITLE_BOLD_CLASSES = 'text-2xl font-black text-gray-800 mb-0'  # 紧凑卡片标题：20px
CARD_TITLE_CLASSES = 'text-2xl font-bold text-gray-700 border-b pb-2 mb-2'  # 带分隔线卡片标题：20px