"""qgbot —— QQ 官方机器人 Markdown 消息构造 SDK。

只做一件事：把 QQ 官方机器人那套 markdown 语法、键盘 JSON 和素材上传流程包装成可组合的
Python API，让插件不用手拼字符串字面量。

设计边界：
- **不碰网络**。素材上传只算签名、组请求、解响应，实际 HTTP 由调用方注入的 transport 完成。
- **不依赖框架**。纯标准库，任何框架（NoneBot / 自研 / 裸 requests）都能直接 import。
- **不做语法校验**。平台限制（标题层级、按钮数量等）通过常量暴露，由调用方自己控制，
  SDK 不擅自截断或改写用户的内容。

    from qgbot import md

    text = md.render(
        md.title("今日运势", level=1),
        md.quote("宜：出门走走"),
        md.image("https://example.com/a.png", width=200, height=200),
        md.mention("user_openid"),
    )
"""

from . import md
from .keyboard import (
    MAX_ROWS,
    STYLE_BLUE,
    STYLE_GREY,
    Button,
    Keyboard,
    callback,
    command,
    link,
    make_keyboard,
)
from .media import MediaError, MediaImage, Transport, delete_image, upload_image
from .message import Message, markdown_payload, markdown_with_keyboard

__version__ = "0.1.0"

__all__ = [
    "MAX_ROWS",
    "STYLE_BLUE",
    "STYLE_GREY",
    "Button",
    "Keyboard",
    "MediaError",
    "MediaImage",
    "Message",
    "Transport",
    "callback",
    "command",
    "delete_image",
    "link",
    "make_keyboard",
    "markdown_payload",
    "markdown_with_keyboard",
    "md",
    "upload_image",
    "__version__",
]
