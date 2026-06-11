from pydantic import BaseModel
from datetime import datetime

class FileOut(BaseModel):
    id: int
    original_name: str
    file_size: int
    mime_type: int
    # 🔥 直接暴露 file_url 给前端，前端拿到后可以直接放入 <img src="..."> 中
    file_url: str 
    created_at: datetime

    # 允许 Pydantic 读取 SQLAlchemy ORM 模型
    model_config = {"from_attributes": True}
