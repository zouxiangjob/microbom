"""
采购 Excel 导出单元测试。
"""
from app.services.purchase import build_purchase_excel


def test_build_excel_returns_xlsx_bytes():
    rows = [
        {"code": "WD-001", "name": "蜗轮减速机", "spec": "WD-80", "qty": 3, "unit": "台"},
        {"code": "ZL-001", "name": "轴承座", "spec": "", "qty": 5, "unit": "个"},
    ]
    content = build_purchase_excel(rows)
    assert isinstance(content, bytes)
    assert len(content) > 0
    # xlsx 是 zip 容器，魔数为 PK\x03\x04
    assert content[:4] == b"PK\x03\x04"


def test_build_excel_empty_rows():
    content = build_purchase_excel([])
    assert isinstance(content, bytes)
    assert len(content) > 0
    assert content[:4] == b"PK\x03\x04"
