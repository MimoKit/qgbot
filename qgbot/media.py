"""素材上传：把本地图片变成平台可引用的 `qqbot-media://` 链接。

**为什么需要它**：markdown 消息里的图片必须是公网 URL，让开放平台自己去拉。但插件生成的
图片（渲染的卡片、表情包）只存在于本地磁盘，没有公网地址。旧办法是找个第三方图床传上去，
现在开放平台自己提供了图库，传上去就能用 `qqbot-media://` 引用，不依赖外部服务。

上传流程是**三步预签名**，不是一次 multipart：

1. `POST /v2/media-images/prepare` — 声明文件名、大小、MIME、MD5、SHA1，
   拿回 `upload_id` 和 COS 预签名地址
2. `PUT <presigned_url>` — 把原始字节传上去，`Content-Type` 必须和声明的一致，
   否则 COS 返回 403
3. `POST /v2/media-images/complete` — 带上 `upload_id` 和 ETag 里的 MD5 收尾，
   拿回最终的 `qqbot-media://image/v1/<token>`

**设计取舍：本模块不发 HTTP。** SDK 只负责算签名、组装请求、解析响应，实际的网络调用由
调用方注入一个 `transport`。这样：

- SDK 不绑定 httpx / aiohttp / requests 中的任何一个
- 测试不需要起 mock server
- 调用方能复用自己框架的连接池、代理、重试策略

    result = await upload_image(
        data=png_bytes,
        file_name="card.png",
        transport=my_transport,   # 自己实现三个方法
    )
    text = md.image(result.url, 400, 300)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

# 支持的图片格式与对应的 MIME。扩展名必须和 MIME 一致，平台会校验。
SUPPORTED_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# 单张图片上限 10 MB
MAX_IMAGE_BYTES = 10 * 1024 * 1024
# 每个机器人最多存 100 张，满了要先删
MAX_IMAGES_PER_BOT = 100
# 上传任务的存活时间：4 小时，超时未完成要重新 prepare
UPLOAD_TASK_TTL_SECONDS = 4 * 3600
# 图片的滑动有效期：90 天未被引用就过期，每次引用会重置
IMAGE_TTL_SECONDS = 90 * 24 * 3600

# prepare 接口路径
PATH_PREPARE = "/v2/media-images/prepare"
PATH_COMPLETE = "/v2/media-images/complete"
PATH_LIST = "/v2/media-images"
PATH_DELETE = "/v2/media-images/{image_id}/delete"

# 错误码 → 可读原因
ERROR_CODES: dict[int, str] = {
    40035001: "不支持的图片格式",
    40035002: "超过大小限制",
    40035003: "上传任务不存在、已过期、不属于该机器人，或 MD5 不匹配",
    40035007: "图片数量已达上限（100 张），请先删除",
    40035008: "图片不存在",
    40035009: "图片已过期或已删除",
    40035010: "链接无效，或属于其他机器人",
}


class Transport(Protocol):
    """调用方需实现的网络层。

    三个方法都要能 await。返回值约定：

    - `post_json(path, body)` → `(status_code, response_json)`
    - `put_bytes(url, data, content_type)` → `(status_code, headers)`，
      headers 需要能取到 `ETag` 或 `etag`（大小写不敏感由实现方处理）
    - `delete(path)` → `(status_code, response_json)`
    """

    async def post_json(self, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]: ...

    async def put_bytes(
        self, url: str, data: bytes, content_type: str,
    ) -> tuple[int, dict[str, str]]: ...

    async def delete(self, path: str) -> tuple[int, dict[str, Any]]: ...


class MediaError(Exception):
    """上传失败。`code` 是平台错误码，`message` 是可直接展示的中文原因。"""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass
class MediaImage:
    """上传成功后拿到的图片信息。"""

    image_id: str
    url: str
    ttl: int = IMAGE_TTL_SECONDS
    preview_url: str = ""

    def to_markdown(self, width: int, height: int, alt: str = "text") -> str:
        """直接转成 markdown 图片语法，省得调用方再拼一次。"""
        return f"![{alt} #{int(width)}px #{int(height)}px]({self.url})"

    def to_markdown_auto(self, alt: str = "text") -> str:
        """不带尺寸的引用：平台按原图大小显示。"""
        return f"![{alt}]({self.url})"


def _digest(data: bytes) -> tuple[str, str]:
    """算 MD5 和 SHA1。MD5 用于完整性校验，SHA1 用于幂等。"""
    return hashlib.md5(data).hexdigest(), hashlib.sha1(data).hexdigest()


def resolve_content_type(file_name: str) -> str:
    """从扩展名推 MIME，不支持的格式直接抛错。

    平台的校验是硬性的：扩展名和 Content-Type 对不上会拒收，所以这里不猜。
    """
    lowered = file_name.lower()
    for ext, mime in SUPPORTED_TYPES.items():
        if lowered.endswith(ext):
            return mime
    raise ValueError(
        f"不支持的图片格式：{file_name}，仅支持 {', '.join(SUPPORTED_TYPES)}"
    )


def check_size(data: bytes) -> None:
    """超出 10 MB 平台会拒收，提前拦下来省一次请求。"""
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"图片 {len(data) / 1024 / 1024:.1f} MB 超过上限 "
            f"{MAX_IMAGE_BYTES / 1024 / 1024:.0f} MB"
        )
    if not data:
        raise ValueError("图片内容为空")


def build_prepare_body(data: bytes, file_name: str) -> dict[str, Any]:
    """组装 prepare 请求体。"""
    check_size(data)
    md5, sha1 = _digest(data)
    return {
        "file_name": file_name,
        "file_size": len(data),
        "content_type": resolve_content_type(file_name),
        "md5": md5,
        "sha1": sha1,
    }


def _raise_for(status: int, body: dict[str, Any]) -> None:
    """把平台的错误响应转成 MediaError。"""
    if 200 <= status < 300:
        return
    code = int(body.get("code") or status)
    message = ERROR_CODES.get(code) or str(body.get("message") or f"HTTP {status}")
    raise MediaError(code, message)


async def upload_image(
    *,
    data: bytes,
    file_name: str,
    transport: Transport,
) -> MediaImage:
    """完整的上传流程：prepare → PUT → complete。

    `file_name` 必须带扩展名（png/jpg/jpeg/gif/webp），平台据此推断 MIME。

    失败时抛 `MediaError`（平台拒绝）或 `ValueError`（本地校验不过）。
    """
    body = build_prepare_body(data, file_name)

    status, prepared = await transport.post_json(PATH_PREPARE, body)
    _raise_for(status, prepared)

    upload_id = str(prepared.get("upload_id") or "")
    presigned_url = str(prepared.get("presigned_url") or "")
    if not upload_id or not presigned_url:
        raise MediaError(-1, "prepare 响应缺少 upload_id 或 presigned_url")

    # PUT 的 Content-Type 必须与 prepare 时声明的一致，否则 COS 直接 403
    put_status, headers = await transport.put_bytes(
        presigned_url, data, body["content_type"],
    )
    if not 200 <= put_status < 300:
        raise MediaError(put_status, f"上传到对象存储失败（HTTP {put_status}）")

    # ETag 里是带引号的 MD5，去掉引号才能和 prepare 时声明的一致
    etag = ""
    for key, value in headers.items():
        if key.lower() == "etag":
            etag = str(value).strip('"')
            break
    if not etag:
        raise MediaError(-1, "对象存储未返回 ETag，无法校验完整性")

    complete_status, completed = await transport.post_json(
        PATH_COMPLETE, {"upload_id": upload_id, "md5": etag},
    )
    _raise_for(complete_status, completed)

    url = str(completed.get("url") or "")
    if not url:
        raise MediaError(-1, "complete 响应缺少 url")

    return MediaImage(
        image_id=str(completed.get("image_id") or ""),
        url=url,
        ttl=int(completed.get("ttl") or IMAGE_TTL_SECONDS),
        preview_url=str(completed.get("preview_url") or ""),
    )


async def delete_image(*, image_id: str, transport: Transport) -> bool:
    """删除一张图，释放配额。已发送的消息不受影响。"""
    path = PATH_DELETE.format(image_id=image_id)
    status, body = await transport.delete(path)
    _raise_for(status, body)
    return True


def parse_list_response(body: dict[str, Any]) -> tuple[list[MediaImage], str]:
    """解析列表响应，返回 `(图片列表, 下一页游标)`。"""
    images = [
        MediaImage(
            image_id=str(item.get("image_id") or ""),
            url=str(item.get("url") or ""),
            preview_url=str(item.get("preview_url") or ""),
        )
        for item in body.get("images") or []
    ]
    return images, str(body.get("next_cursor") or "")


__all__ = [
    "ERROR_CODES",
    "IMAGE_TTL_SECONDS",
    "MAX_IMAGES_PER_BOT",
    "MAX_IMAGE_BYTES",
    "PATH_COMPLETE",
    "PATH_DELETE",
    "PATH_LIST",
    "PATH_PREPARE",
    "SUPPORTED_TYPES",
    "UPLOAD_TASK_TTL_SECONDS",
    "MediaError",
    "MediaImage",
    "Transport",
    "build_prepare_body",
    "check_size",
    "delete_image",
    "parse_list_response",
    "resolve_content_type",
    "upload_image",
]
