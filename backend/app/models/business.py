from base import Base, ObjectModel, RelationModel


# ==============================================================================
# 1. 业务对象定义 (利用 SQLAlchemy 单表继承机制扩展 ObjectModel)
# ==============================================================================

class PartModel(ObjectModel):
    """零部件对象"""
    # 告诉 SQLAlchemy：当 objects 表的 object_type == "part" 时，自动实例化为这个类
    __mapper_args__ = {
        "polymorphic_identity": "part",
    }

    # 快捷业务属性封装（利用 Python 属性代理底层 JSON 字典，开发时极爽）
    @property
    def part_number(self) -> str:
        """零件编码"""
        return self.properties.get("part_number", "")

    @part_number.setter
    def part_number(self, value: str):
        self.properties["part_number"] = value


class DocumentModel(ObjectModel):
    """文档对象 (如：工艺规程、技术要求说明书)"""
    __mapper_args__ = {
        "polymorphic_identity": "document",
    }

    @property
    def doc_version(self) -> str:
        """文档版本"""
        return self.properties.get("doc_version", "A.0")


class DrawingModel(ObjectModel):
    """图档对象 (如：2D图纸、3D数模)"""
    __mapper_args__ = {
        "polymorphic_identity": "drawing",
    }


class AttachmentModel(ObjectModel):
    """附件对象 (附属于文档或图档的源文件、辅助说明等)"""
    __mapper_args__ = {
        "polymorphic_identity": "attachment",
    }


# ==============================================================================
# 2. 业务关系定义 (利用 SQLAlchemy 单表继承机制扩展 RelationModel)
# ==============================================================================

class BOMRelation(RelationModel):
    """BOM关系：零部件 -> 零部件 (父子结构)"""
    __mapper_args__ = {
        "polymorphic_identity": "bom_relation",
    }

    @property
    def quantity(self) -> int:
        """装配数量 (从关系属性 JSON 中读取)"""
        return self.properties.get("quantity", 1)

    @quantity.setter
    def quantity(self, value: int):
        self.properties["quantity"] = value


class PartDocRelation(RelationModel):
    """零部件与文档关系：零部件 -> 文档"""
    __mapper_args__ = {
        "polymorphic_identity": "part_doc_relation",
    }


class PartDrawingRelation(RelationModel):
    """零部件与图档关系：零部件 -> 图档"""
    __mapper_args__ = {
        "polymorphic_identity": "part_drawing_relation",
    }


class DocAttachmentRelation(RelationModel):
    """文档与附件关系：文档 -> 附件"""
    __mapper_args__ = {
        "polymorphic_identity": "doc_attachment_relation",
    }


class DrawingAttachmentRelation(RelationModel):
    """图档与附件关系：图档 -> 附件"""
    __mapper_args__ = {
        "polymorphic_identity": "drawing_attachment_relation",
    }
