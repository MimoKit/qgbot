"""QQ 官方机器人的按钮 / 键盘构造。

平台结构（发给 `keyboard` 字段）：

    {
      "content": {
        "rows": [
          {"buttons": [ {...}, {...} ]},
          {"buttons": [ {...} ]}
        ]
      }
    }

单个按钮：

    {
      "id": "1",
      "render_data": {"label": "显示文字", "visited_label": "点过之后", "style": 1},
      "action": {"type": 2, "data": "指令", "permission": {"type": 2}}
    }

`action.type` 的取值：
- 0 链接跳转，`data` 是 URL
- 1 回调，点后平台推送 `INTERACTION_CREATE` 事件，`data` 是回调值
- 2 指令，点后填入输入框（配 `enter: true` 则直接发送）
- 4 订阅（`subscribe_data`）

`permission.type` 的取值：
- 0 指定用户，配 `specify_user_ids`
- 1 仅管理员
- 2 所有人
- 3 指定身份组，配 `specify_role_ids`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 按钮样式：0 灰色线框，1 蓝色线框
STYLE_GREY = 0
STYLE_BLUE = 1

# 平台限制：键盘最多 5 行
MAX_ROWS = 5
# 每行最多 5 个按钮（平台未明确写死，但超过这个数会挤在一起，实际上按 3 个最舒服）
MAX_BUTTONS_PER_ROW = 5

# action.type
ACTION_URL = 0
ACTION_CALLBACK = 1
ACTION_COMMAND = 2
ACTION_SUBSCRIBE = 4

# permission.type
PERM_USER = 0
PERM_ADMIN = 1
PERM_EVERYONE = 2
PERM_ROLE = 3


@dataclass
class Button:
    """一个按钮。

    用工厂函数 `link()` / `callback()` / `command()` 构造，比直接拼 dict 安全。
    """

    label: str
    action_type: int
    data: str = ""
    visited_label: str = ""
    style: int = STYLE_BLUE
    enter: bool = False
    reply: bool = False
    permission: dict[str, Any] = field(default_factory=lambda: {"type": PERM_EVERYONE})
    click_limit: int | None = None
    unsupport_tips: str = ""
    subscribe_data: dict[str, Any] | None = None
    button_id: str = ""

    def to_dict(self, index: int = 0) -> dict[str, Any]:
        """转成平台要求的按钮结构。

        `index` 用于在未显式指定 id 时生成一个稳定标识——平台要求按钮 id 在同一条消息
        内唯一，重名会导致后一个覆盖前一个的点击状态。
        """
        render_data: dict[str, Any] = {
            "label": self.label,
            "visited_label": self.visited_label or self.label,
            "style": self.style,
        }
        action: dict[str, Any] = {
            "type": self.action_type,
            "data": self.data,
            "permission": self.permission,
        }
        if self.enter:
            action["enter"] = True
        if self.reply:
            action["reply"] = True
        if self.click_limit is not None:
            action["click_limit"] = int(self.click_limit)
        if self.unsupport_tips:
            action["unsupport_tips"] = self.unsupport_tips
        if self.subscribe_data is not None:
            action["subscribe_data"] = self.subscribe_data

        return {
            "id": self.button_id or str(index),
            "render_data": render_data,
            "action": action,
        }


@dataclass
class Keyboard:
    """键盘：若干行，每行若干按钮。"""

    rows: list[list[Button]] = field(default_factory=list)
    font_size: str = ""  # "small" / "medium" / "large"

    def add_row(self, *buttons: Button) -> Keyboard:
        """追加一行。链式调用。"""
        if buttons:
            self.rows.append(list(buttons))
        return self

    def to_dict(self) -> dict[str, Any]:
        """转成平台要求的 keyboard 结构。

        超过 `MAX_ROWS` 的行会被丢弃——平台只认前 5 行，多出来的不会渲染。
        这里截断而不是抛错：调用方可能批量生成按钮，硬失败会让整条消息发不出去。
        """
        counter = 0
        rows = []
        for row in self.rows[:MAX_ROWS]:
            buttons = []
            for btn in row[:MAX_BUTTONS_PER_ROW]:
                buttons.append(btn.to_dict(counter))
                counter += 1
            if buttons:
                rows.append({"buttons": buttons})

        content: dict[str, Any] = {"rows": rows}
        if self.font_size:
            content["style"] = {"font_size": self.font_size}
        return {"content": content}

    def __bool__(self) -> bool:
        """空键盘转成 False，方便调用方判断要不要带 keyboard 字段。"""
        return any(row for row in self.rows)


def link(label: str, url: str, *, visited_label: str = "", style: int = STYLE_BLUE) -> Button:
    """跳转按钮：点击打开链接或客户端能识别的 scheme。"""
    return Button(
        label=label, action_type=ACTION_URL, data=url,
        visited_label=visited_label, style=style,
    )


def callback(
    label: str, value: str, *, visited_label: str = "", style: int = STYLE_BLUE,
) -> Button:
    """回调按钮：点击后平台推送 `INTERACTION_CREATE` 事件，`value` 原样带回来。"""
    return Button(
        label=label, action_type=ACTION_CALLBACK, data=value,
        visited_label=visited_label, style=style,
    )


def command(
    label: str,
    command_text: str,
    *,
    visited_label: str = "",
    style: int = STYLE_BLUE,
    enter: bool = True,
    reply: bool = False,
) -> Button:
    """指令按钮：点击后把指令填入输入框；`enter=True` 时直接发送。

    `enter` 默认 True——用户的预期是"点一下就执行"，还要再按一次发送键会很烦。
    `reply=True` 会让指令以"回复当前消息"的形式发出。
    """
    return Button(
        label=label, action_type=ACTION_COMMAND, data=command_text,
        visited_label=visited_label, style=style, enter=enter, reply=reply,
    )


def for_users(button: Button, user_ids: list[str]) -> Button:
    """把按钮限定为只有指定用户可点。"""
    button.permission = {"type": PERM_USER, "specify_user_ids": [str(u) for u in user_ids]}
    return button


def for_admins(button: Button) -> Button:
    """把按钮限定为仅管理员可点。"""
    button.permission = {"type": PERM_ADMIN}
    return button


def for_roles(button: Button, role_ids: list[str]) -> Button:
    """把按钮限定为只有指定身份组可点（仅频道场景有效）。"""
    button.permission = {"type": PERM_ROLE, "specify_role_ids": [str(r) for r in role_ids]}
    return button


def rows_of(buttons: list[Button], per_row: int = 3) -> list[list[Button]]:
    """把一串按钮按每行 `per_row` 个切分成行。"""
    per_row = max(1, min(MAX_BUTTONS_PER_ROW, int(per_row)))
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def make_keyboard(*buttons: Button, per_row: int = 3, font_size: str = "") -> Keyboard:
    """一次性构造键盘：按 `per_row` 自动分行。"""
    return Keyboard(rows=rows_of(list(buttons), per_row), font_size=font_size)


__all__ = [
    "ACTION_CALLBACK",
    "ACTION_COMMAND",
    "ACTION_SUBSCRIBE",
    "ACTION_URL",
    "MAX_BUTTONS_PER_ROW",
    "MAX_ROWS",
    "PERM_ADMIN",
    "PERM_EVERYONE",
    "PERM_ROLE",
    "PERM_USER",
    "STYLE_BLUE",
    "STYLE_GREY",
    "Button",
    "Keyboard",
    "callback",
    "command",
    "for_admins",
    "for_roles",
    "for_users",
    "make_keyboard",
    "link",
    "rows_of",
]
