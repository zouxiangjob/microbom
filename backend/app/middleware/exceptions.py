from typing import Any, Optional, Generic, TypeVar
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

# 定义泛型，支持 IDE 完美推导 Data 内部的强类型结构
T = TypeVar("T")


# ==============================================================================
# 1. 统一企业级标准响应 Schema (对齐前端习惯)
# ==============================================================================
class UnifiedResponse(BaseModel, Generic[T]):
    """统一全局响应骨架"""
    code: int = Field(200, description="业务状态码：200代表成功，其余代表各类业务异常")
    message: str = Field("success", description="提示信息，成功为 'success'，失败为具体的错误原因")
    data: Optional[T] = Field(None, description="核心业务返回负载，无返回时为 null")


# ==============================================================================
# 2. 自定义业务级异常基类 (用于手动抛出的受控业务错误)
# ==============================================================================
class BusinessException(Exception):
    """
    业务逻辑层异常，专门用于处理不属于系统崩溃、而是业务不允许的场景。
    例如：BOM 结构查出环路、超出最大递归深度等。
    """

    def __init__(self, message: str, code: int = 400, status_code: int = 200):
        self.message = message
        self.code = code
        self.status_code = status_code  # 支持外层 HTTP 状态码与内层业务状态码分离


# ==============================================================================
# 3. 核心：全局异常拦截注册器 (Exception Handlers)
# ==============================================================================
def setup_exception_handlers(app: FastAPI):
    """
    将全局所有的崩溃、校验失败、受控报错统一收拢至此，榨干一万行堆栈，只给前端吐干净的 JSON。
    """

    # --- 拦截 1: 手动抛出的受控业务异常 ---
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        return JSONResponse(
            status_code=exc.status_code,
            content=UnifiedResponse(code=exc.code, message=exc.message, data=None).model_dump()
        )

    # --- 拦截 2: FastAPI / Starlette 自带的通用 HTTPException (如 raise HTTPException(404)) ---
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=UnifiedResponse(code=exc.status_code, message=exc.detail, data=None).model_dump()
        )

    # --- 拦截 3: Pydantic 字段校验失败（前端传参格式错误、UUID不合法、表单缺失等） ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # 精准提取 Pydantic 的错误定位，将其转化为人类可读的提示语
        error_messages = []
        for err in exc.errors():
            # loc 代表字段层级，如 ('body', 'payload', 'source_id')
            location = "->".join(str(x) for x in err["loc"] if x != "body")
            raw_msg = err["msg"]
            error_messages.append(f"字段 [{location}] 校验失败: {raw_msg}")

        friendly_message = " | ".join(error_messages) if error_messages else "请求体参数格式不合法"

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,  # 保持标准的 422 协议
            content=UnifiedResponse(
                code=422,
                message=friendly_message,
                data=None
            ).model_dump()
        )

    # --- 拦截 4: 终极防御！未知的系统致命崩溃（如数据库断连、代码空指针等 500 严重错误） ---
    @app.exception_handler(Exception)
    async def global_unknown_exception_handler(request: Request, exc: Exception):
        # TODO: 生产环境下此处应触发 logger.error(f"致命灾难堆栈: {traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=UnifiedResponse(
                code=500,
                message=f"后端服务器发生未知异动，请联系架构师或查看日志。原因: {str(exc)}",
                data=None
            ).model_dump()
        )
