"""
种子数据脚本：向数据库插入 100 条 PartModel + BOM 关系 + 图纸/文档，用于验证视图层。
运行方式：在 backend/ 目录下执行 python seed_data.py
"""
import random
import uuid

from app.database.session import SyncSessionLocal
from app.models.base import ObjectModel, RelationModel
from app.models.business import (
    PartModel,
    DocumentModel,
    DrawingModel,
    BOMRelation,
    PartDocRelation,
    PartDrawingRelation,
)

PART_CATEGORIES = {
    "WD": {"prefix": "WD", "names": ["蜗轮减速机", "行星减速机", "摆线减速机", "齿轮减速机", "谐波减速机"]},
    "ZL": {"prefix": "ZL", "names": ["轴承座", "法兰盘", "联轴器", "传动轴", "花键轴"]},
    "GJ": {"prefix": "GJ", "names": ["六角螺栓", "内六角螺钉", "紧定螺钉", "弹簧垫圈", "锁紧螺母"]},
    "MF": {"prefix": "MF", "names": ["密封圈", "O型圈", "油封", "防尘盖", "密封垫"]},
    "DQ": {"prefix": "DQ", "names": ["伺服电机", "步进电机", "三相异步电机", "直流电机", "力矩电机"]},
    "CJ": {"prefix": "CJ", "names": ["传感器", "编码器", "限位开关", "接近开关", "光电开关"]},
    "GL": {"prefix": "GL", "names": ["PLC控制器", "变频器", "伺服驱动器", "继电器模块", "IO模块"]},
    "LJ": {"prefix": "LJ", "names": ["铝合金型材", "钢板", "铜管", "尼龙板", "不锈钢棒"]},
    "BZ": {"prefix": "BZ", "names": ["标准件套件A", "标准件套件B", "紧固件组合包", "密封件组合包", "电气件组合包"]},
    "ASM": {"prefix": "ASM", "names": ["主轴总成", "进给系统总成", "润滑系统总成", "冷却系统总成", "电气控制柜总成"]},
}

DESIGNERS = ["张工", "李工", "王工", "赵工", "刘工", "陈工", "杨工", "黄工", "周工", "吴工"]
STATUSES = ["草稿", "待审核", "已发布", "已归档"]
VERSIONS = ["V1.0", "V1.1", "V2.0", "V2.1", "V3.0", "V3.2", "V4.0"]


def seed():
    with SyncSessionLocal() as session:
        print("清空旧数据...")
        session.query(RelationModel).delete()
        session.query(ObjectModel).delete()
        session.commit()

        # ===== 第 1 步：创建 100 个零部件 =====
        print("生成 100 条零部件...")
        parts = []
        counter = 1
        for cat_key, cat_info in PART_CATEGORIES.items():
            prefix = cat_info["prefix"]
            names = cat_info["names"]
            for i in range(10):
                part_number = f"{prefix}-{counter:03d}"
                name = f"{names[i % len(names)]}-{counter:02d}"
                part = PartModel(
                    object_type="part",
                    properties={
                        "part_number": part_number,
                        "name": name,
                        "version": random.choice(VERSIONS),
                        "designer": random.choice(DESIGNERS),
                        "status": random.choice(STATUSES),
                        "category": cat_key,
                        "weight": round(random.uniform(0.1, 150.0), 2),
                        "material": random.choice(["45#钢", "铝合金6061", "不锈钢304", "黄铜H62", "尼龙PA66", "铸铁HT200"]),
                    },
                )
                parts.append(part)
                session.add(part)
                counter += 1

        session.flush()
        print(f"  零部件已 flush，共 {len(parts)} 条")

        # ===== 第 2 步：创建图档对象 =====
        print("生成图档数据...")
        drawings = []
        drawing_map = {}
        for part in parts:
            pn = part.properties["part_number"]
            for idx in range(2):
                drawing_type = "3D数模" if idx == 0 else "2D工程图"
                ext = ".glb" if idx == 0 else ".pdf"
                drawing = DrawingModel(
                    object_type="drawing",
                    properties={
                        "name": f"{pn}_{drawing_type}",
                        "version": part.properties.get("version", "V1.0"),
                        "drawing_type": drawing_type,
                        "format": ext,
                    },
                )
                drawings.append(drawing)
                session.add(drawing)
                drawing_map.setdefault(part.id, []).append(drawing)

        session.flush()
        print(f"  图档已 flush，共 {len(drawings)} 条")

        # ===== 第 3 步：创建文档对象 =====
        print("生成文档数据...")
        documents = []
        doc_map = {}
        doc_tags = ["工艺规程", "技术要求", "检验标准", "装配指导", "材质证明"]
        selected_parts = random.sample(parts, 40)
        for part in selected_parts:
            pn = part.properties["part_number"]
            tag = random.choice(doc_tags)
            doc = DocumentModel(
                object_type="document",
                properties={
                    "name": f"{pn}_{tag}",
                    "doc_version": part.properties.get("version", "V1.0"),
                    "tag": tag,
                },
            )
            documents.append(doc)
            session.add(doc)
            doc_map.setdefault(part.id, []).append(doc)

        session.flush()
        print(f"  文档已 flush，共 {len(documents)} 条")

        # ===== 第 4 步：创建 BOM 关系 =====
        print("生成 BOM 父子关系...")
        bom_count = 0
        asm_parts = [p for p in parts if p.properties.get("category") == "ASM"]
        other_parts = [p for p in parts if p.properties.get("category") != "ASM"]
        for asm in asm_parts:
            num_children = random.randint(3, 8)
            children = random.sample(other_parts, min(num_children, len(other_parts)))
            for child in children:
                rel = BOMRelation(
                    relation_type="bom_relation",
                    source_id=asm.id,
                    target_id=child.id,
                    properties={
                        "quantity": random.randint(1, 10),
                        "position": f"位置{random.randint(1, 20):02d}",
                    },
                )
                session.add(rel)
                bom_count += 1

        session.flush()
        print(f"  BOM 关系已 flush，共 {bom_count} 条")

        # ===== 第 5 步：创建图纸关系 =====
        print("生成图纸关系...")
        drawing_rel_count = 0
        for part_id, dwgs in drawing_map.items():
            for idx, dwg in enumerate(dwgs):
                rel = PartDrawingRelation(
                    relation_type="part_drawing_relation",
                    source_id=part_id,
                    target_id=dwg.id,
                    properties={"is_primary": idx == 0},
                )
                session.add(rel)
                drawing_rel_count += 1

        session.flush()
        print(f"  图纸关系已 flush，共 {drawing_rel_count} 条")

        # ===== 第 6 步：创建文档关系 =====
        print("生成文档关系...")
        doc_rel_count = 0
        for part_id, docs in doc_map.items():
            for doc in docs:
                rel = PartDocRelation(
                    relation_type="part_doc_relation",
                    source_id=part_id,
                    target_id=doc.id,
                    properties={},
                )
                session.add(rel)
                doc_rel_count += 1

        session.flush()
        print(f"  文档关系已 flush，共 {doc_rel_count} 条")

        # ===== 提交 =====
        session.commit()

        print("\n种子数据插入完成！统计：")
        print(f"   零部件 (PartModel):        {session.query(PartModel).count()}")
        print(f"   图档 (DrawingModel):       {session.query(DrawingModel).count()}")
        print(f"   文档 (DocumentModel):      {session.query(DocumentModel).count()}")
        print(f"   BOM 关系 (BOMRelation):    {session.query(BOMRelation).count()}")
        print(f"   图纸关系 (PartDrawing):    {session.query(PartDrawingRelation).count()}")
        print(f"   文档关系 (PartDoc):        {session.query(PartDocRelation).count()}")


if __name__ == "__main__":
    seed()