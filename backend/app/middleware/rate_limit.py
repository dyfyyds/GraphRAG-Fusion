"""
简单的内存限流中间件
基于客户端 IP 的滑动窗口限流
"""
import time
import asyncio
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API 限流中间件"""

    # 路径限流配置: (窗口秒数, 最大请求数)
    RATE_LIMITS = {
        "/api/auth/login": (60, 10),      # 登录: 10次/分钟
        "/api/auth/register": (300, 5),   # 注册: 5次/5分钟
        "/api/chat": (60, 30),            # 问答: 30次/分钟
        "/api/documents/upload": (60, 200), # 上传: 200次/分钟（前端已有并发控制，大批量上传需要更高限额）
    }
    # 全局限流: 所有 API 60次/分钟
    GLOBAL_LIMIT = (60, 100)

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def _get_client_ip(self, request) -> str:
        """获取客户端 IP（支持反向代理）"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_limit(self, key: str, window: int, max_requests: int) -> bool:
        """检查是否超过限流，返回 True 表示允许"""
        now = time.time()
        cutoff = now - window
        # 清理过期记录
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        if len(self._requests[key]) >= max_requests:
            return False
        self._requests[key].append(now)
        return True

    async def dispatch(self, request, call_next):
        # 只对 API 路径限流
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        async with self._lock:
            # 查找该路径是否配置了专属限额
            matched = next(
                (
                    (pattern, window, max_req)
                    for pattern, (window, max_req) in self.RATE_LIMITS.items()
                    if path.startswith(pattern)
                ),
                None,
            )

            if matched is not None:
                # 有专属配置：仅按专属限额限流。
                # 不再叠加全局限额——否则全局 100 次/分钟会让上传 200 次/分钟
                # 的专属配置永远无法生效，大批量上传超过 100 次后即被全局拦截。
                pattern, window, max_req = matched
                rate_key = f"{pattern}:{client_ip}"
                if not self._check_limit(rate_key, window, max_req):
                    return JSONResponse(
                        {"detail": f"该接口请求过于频繁，请{window}秒后再试"},
                        status_code=429,
                        headers={"Retry-After": str(window)},
                    )
            else:
                # 无专属配置：使用全局默认限额兜底
                global_key = f"global:{client_ip}"
                if not self._check_limit(global_key, *self.GLOBAL_LIMIT):
                    return JSONResponse(
                        {"detail": "请求过于频繁，请稍后再试"},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )

        return await call_next(request)
