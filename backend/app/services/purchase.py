"""
采购服务：将 BOM 打平汇总结果导出为 ERP 采购导入 Excel。
"""
import io
from typing import Any, Dict, List

import pandas as pd


def build_purchase_excel(rows: List[Dict[str, Any]]) -> bytes:
    """将 BOM 打平行转换为 ERP 采购导入 Excel 的字节流。"""
    df = pd.DataFrame(rows)
    out = pd.DataFrame()
    out["编号"] = df["code"] if "code" in df else []
    out["名称"] = df["name"] if "name" in df else []
    out["规格"] = df["spec"] if "spec" in df else []
    out["采购数量"] = df["qty"] if "qty" in df else []
    out["出入库仓库"] = "主物料仓"
    out["备注说明"] = "MicroBOM 系统自动打平去重导出"

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        out.to_excel(writer, index=False)
    return buf.getvalue()
