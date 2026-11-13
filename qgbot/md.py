"""QQ 官方机器人 Markdown 语法构造器。

平台支持的语法（来自官方文档）：
- 标题 `#` ~ `##`
- 粗体 `**`、下划线加粗 `__`、斜体 `_` / `*`、
  粗斜体 `***`、删除线 `~~`
- 链接 `[文字](url)`、自动链接 `<url>`
- 图片 `![描述 #宽px #高px](url)`，尺寸写在 alt 文本里
- 有序 / 无序列表，二级缩进 4 空格
- 引用块 `>`
- 分隔线 `***`
- 多个空行要用零宽空格 `​` 单独成行

**与标准 Markdown 的差异**：图片尺寸必须写在 alt 里，不写就按原图尺寸铺满，长图会把
消息撑得极大。`image()` 因此默认要求显式宽高，避免误用。

**正文里的小指令按钮**（`<qqbot-cmd-input>`）也在这个模块：它本质是嵌在 markdown 字符串里
的标签，不是独立元素。
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import quote as urlquote

# 零宽空格：平台用它表示"再来一个空行"。直接写两个 `\n` 只会被合并成一个。
ZERO_WIDTH_SPACE = "​"

# 标题最高只到二级，更深层级平台不渲染
MAX_TITLE_LEVEL = 2


def text(content: str) -> str:
    """普通文本。原样返回，只做类型归一。"""
    return str(content)


def title(content: str, level: int = 1) -> str:
    """标题。`level` 取 1 或 2，超出范围会被夹到边界值。

    平台只支持两级标题，传 3 不会被渲染成三级，而是直接当正文处理——
    与其让用户困惑，不如夹到合法范围并保持视觉层次。
    """
    level = max(1, min(MAX_TITLE_LEVEL, int(level)))
    return f"{'#' * level} {content}"


def bold(content: str) -> str:
    return f"**{content}**"


def italic(content: str) -> str:
    return f"_{content}_"


def bold_italic(content: str) -> str:
    return f"***{content}***"


def underline(content: str) -> str:
    """下划线加粗（平台语法是 `__`，不是常见的 `<u>`）。"""
    return f"__{content}__"


def strike(content: str) -> str:
    return f"~~{content}~~"


def link(label: str, url: str) -> str:
    """行内链接。"""
    return f"[{label}]({url})"


def autolink(url: str) -> str:
    """自动链接：平台会自己把 URL 变成可点击的链接。"""
    return f"<{url}>"


def image(url: str, width: int, height: int, alt: str = "text") -> str:
    """图片。尺寸必须显式给出。

    QQ 按 alt 里的 `#宽px #高px` 决定显示尺寸；不给就按原图铺满，一张 1080×1920 的图
    会把消息撑满整屏。宽高传 0 或负数时抛错，逼调用方做决定而不是默默出问题。

    图片 URL 必须公网可访问。本地图片要先传到平台素材库，再用 `qqbot-media://` 引用，
    这里不做上传。
    """
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError(f"图片尺寸必须为正数，收到 {width}x{height}")
    return f"![{alt} #{width}px #{height}px]({url})"


def media(media_id: str, width: int = 0, height: int = 0, alt: str = "text") -> str:
    """引用平台上已上传的素材（`qqbot-media://` scheme）。

    `media_id` 是素材上传接口返回的 ID。不传尺寸时按原图显示，需要控制大小就补宽高。
    """
    if width and height:
        return f"![{alt} #{int(width)}px #{int(height)}px](qqbot-media://{media_id})"
    return f"![{alt}](qqbot-media://{media_id})"


def ordered(items: Iterable[str], level: int = 1) -> str:
    """有序列表。`level=2` 时整块缩进 4 空格。"""
    indent = "    " * (int(level) - 1)
    return "\n".join(f"{indent}{i}. {item}" for i, item in enumerate(items, start=1))


def unordered(items: Iterable[str], level: int = 1) -> str:
    """无序列表。`level=2` 时整块缩进 4 空格。"""
    indent = "    " * (int(level) - 1)
    return "\n".join(f"{indent}- {item}" for item in items)


def quote(content: str, lines: int = 1) -> str:
    """引用块。多行内容每行都会加上 `>` 前缀。

    `lines` 参数保留给「空一行再引用」的排版需求：平台要求引用块与上一段正文之间
    有空行，这里不自动加（见 `blank()`），由调用方决定间距。
    """
    body = "\n".join(f"> {line}" for line in str(content).splitlines())
    return body


def divider() -> str:
    """水平分隔线。平台语法是 `***`，不是 `---`。"""
    return "***"


def blank(count: int = 1) -> str:
    """空行。

    平台会把连续 `\n` 合并，真正想要多个空行要在中间插入零宽空格行。
    这里返回的内容需要调用方用 `render()` 拼接，`render` 会自动处理分隔。
    """
    return "\n".join([ZERO_WIDTH_SPACE] * max(1, int(count)))


def cmd_input(command: str, show: str | None = None, reference: bool = False) -> str:
    """正文里的「小指令按钮」，点击等同于在输入框填入并发送该指令。

    `show` 是按钮上显示的文字，不传就显示指令本身。
    `reference=False` 表示点击时不引用当前消息；绝大多数场景都不需要引用。

    参数里的引号、`&` 等会被 URL 编码——不编码的话平台解析标签属性时会截断。
    """
    encoded_command = urlquote(command, safe="")
    encoded_show = urlquote(show or command, safe="")
    ref = "true" if reference else "false"
    return f'<qqbot-cmd-input text="{encoded_command}" show="{encoded_show}" reference="{ref}" />'


def cmd_enter(command: str, show: str | None = None) -> str:
    """正文里的「回车发送」按钮：点击后直接发送，不经过输入框。

    与 `cmd_input` 的区别是少了"填入输入框"这一步，适合确认类操作。

    **群聊与文字子频道不可用**——平台限制，只能在单聊里用。
    """
    encoded_command = urlquote(command, safe="")
    encoded_show = urlquote(show or command, safe="")
    return f'<qqbot-cmd-enter text="{encoded_command}" show="{encoded_show}" />'


def mention(user_id: str) -> str:
    """@ 某个用户。

    `user_id` 的含义随场景变化：
    - 群聊：成员的 `member_openid`
    - 文字子频道：用户的 `user_openid`

    **群聊里 @ 用户只在 markdown 消息中有效**，纯文本消息不支持。

    旧的 `<@id>` 写法平台已标记废弃，这里生成的是新的 `<qqbot-at-user>` 标签。
    """
    uid = str(user_id or "").strip()
    if not uid:
        raise ValueError("mention 需要非空的用户 id")
    return f'<qqbot-at-user id="{uid}" />'


def mention_everyone() -> str:
    """@ 全体成员。

    两个硬限制：
    - 机器人必须是群管理员
    - **每个群每个自然日只能 @ 一次**

    第二条容易踩坑——超出后平台直接拒收整条消息，而不是只忽略这个标签。
    """
    return "<qqbot-at-everyone />"


def channel(channel_id: str) -> str:
    """跳转到子频道（仅频道场景，且必须是当前频道下的子频道）。"""
    return f"<#{channel_id}>"


def emoji(emoji_id: str) -> str:
    """引用系统表情（仅频道场景，且只支持 type=1 的表情）。"""
    return f"<emoji:{emoji_id}>"


def join(*parts: str) -> str:
    """把多段 markdown 用换行拼起来，跳过空段。"""
    return "\n".join(str(p) for p in parts if p)


def render(*parts: str) -> str:
    """把多段内容拼成完整 markdown 正文。

    每个参数之间用单个换行分隔，空字符串和 None 会被跳过。
    需要空行请显式插入 `blank()`。
    """
    return join(*parts)


__all__ = [
    "MAX_TITLE_LEVEL",
    "ZERO_WIDTH_SPACE",
    "autolink",
    "blank",
    "bold",
    "bold_italic",
    "channel",
    "cmd_enter",
    "cmd_input",
    "emoji",
    "divider",
    "image",
    "italic",
    "join",
    "link",
    "media",
    "mention",
    "mention_everyone",
    "ordered",
    "quote",
    "render",
    "strike",
    "text",
    "title",
    "underline",
    "unordered",
]
