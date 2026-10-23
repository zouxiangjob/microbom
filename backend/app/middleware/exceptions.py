import logging
from typing import Any, Optional, Generic, TypeVar
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.exceptions")

# 定义泛型，支持 IDE 对 Data 内部结构的类型推导
T = TypeVar("T")


# ==============================================================================
# 1. 统一响应 Schema
# ==============================================================================
class UnifiedResponse(BaseModel, Generic[T]):
    """统一全局响应骨架。"""
    code: int = Field(200, description="业务状态码：200 代表成功，其余代表各类业务异常")
    message: str = Field("success", description="提示信息，成功为 'success'，失败为具体错误原因")
    data: Optional[T] = Field(None, description="业务返回负载，无返回时为 null")


# ==============================================================================
# 2. 业务级异常基类
# ==============================================================================
class BusinessException(Exception):
    """业务逻辑层异常，用于手动抛出的受控业务错误（非系统崩溃）。

    例如：BOM 结构出现环路、超出最大递归深度等。
    """

    def __init__(self, message: str, code: int = 400, status_code: int = 200):
        self.message = message
        self.code = code
        self.status_code = status_code  # 支持外层 HTTP 状态码与内层业务状态码分离


# ==============================================================================
# 3. 全局异常拦截注册器
# ==============================================================================
def setup_exception_handlers(app: FastAPI):
    """将全局的崩溃、校验失败、受控报错统一收拢，向前端返回干净的 JSON。"""

    # --- 拦截 1：手动抛出的受控业务异常 ---
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        return JSONResponse(
            status_code=exc.status_code,
            content=UnifiedResponse(code=exc.code, message=exc.message, data=None).model_dump()
        )

    # --- 拦截 2：FastAPI / Starlette 自带的 HTTPException ---
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=UnifiedResponse(code=exc.status_code, message=exc.detail, data=None).model_dump()
        )

    # --- 拦截 3：Pydantic 字段校验失败（传参格式错误、UUID 非法、表单缺失等）---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_messages = []
        for err in exc.errors():
            # loc 代表字段层级，如 ('body', 'payload', 'source_id')
            location = "->".join(str(x) for x in err["loc"] if x != "body")
            raw_msg = err["msg"]
            error_messages.append(f"字段 [{location}] 校验失败: {raw_msg}")

        friendly_message = " | ".join(error_messages) if error_messages else "请求体参数格式不合法"

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=UnifiedResponse(code=422, message=friendly_message, data=None).model_dump()
        )

    # --- 拦截 4：未知的系统级异常（如数据库断连、空指针等 500 错误）---
    @app.exception_handler(Exception)
    async def global_unknown_exception_handler(request: Request, exc: Exception):
        logger.exception("未捕获异常: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=UnifiedResponse(
                code=500,
                message=f"后端服务器发生未知异常，请联系管理员。原因: {str(exc)}",
                data=None
            ).model_dump()
        )
