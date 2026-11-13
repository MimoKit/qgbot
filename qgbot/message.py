"""把 markdown 正文与键盘组装成可直接发送的 payload。

QQ 官方机器人发消息的 body 长这样（群聊 / 单聊）：

    {
      "msg_type": 2,
      "markdown": {"content": "# 标题\\n正文"},
      "keyboard": {"content": {"rows": [...]}},
      "msg_id": "..."          # 被动回复必填，主动消息用 msg_seq
    }

`msg_type=2` 是 markdown。`msg_id` 是被动回复必须带上的那条消息的 id——不带就无法回复，
只能走主动消息（有频次限制）。本模块只管组结构，消息 id 与频次由调用方处理。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .keyboard import Keyboard

# 消息类型：2 = markdown
MSG_TYPE_MARKDOWN = 2


@dataclass
class Message:
    """一条待发送的 markdown 消息。

        msg = Message("今日运势", keyboard=keyboard(cmd, link_btn))
        payload = msg.to_payload(msg_id="xxx")

    `content` 用 `md.render()` 拼好再传进来，本类不解析 markdown。
    """

    content: str
    keyboard: Keyboard | None = None
    # 平台限制：一条消息最多能带的按钮数，超过部分平台会整条拒收。
    # 这里不主动截断（Keyboard 已限制 5 行），只是把限制暴露出来供调用方自查。

    def to_payload(self, *, msg_id: str = "", msg_seq: int | None = None) -> dict[str, Any]:
        """转成发送用的 body。

        `msg_id` 是被动回复要回复的那条消息 id；`msg_seq` 用于同一条 msg_id 下连发多条
        （此时必须递增，否则平台按重复消息丢弃）。
        """
        payload: dict[str, Any] = {
            "msg_type": MSG_TYPE_MARKDOWN,
            "markdown": {"content": self.content},
        }
        if self.keyboard:
            payload["keyboard"] = self.keyboard.to_dict()
        if msg_id:
            payload["msg_id"] = str(msg_id)
        if msg_seq is not None:
            payload["msg_seq"] = int(msg_seq)
        return payload


def markdown_payload(content: str) -> dict[str, Any]:
    """只要正文、不要键盘时的快捷构造。"""
    return {"msg_type": MSG_TYPE_MARKDOWN, "markdown": {"content": content}}


def markdown_with_keyboard(content: str, keyboard: Keyboard) -> dict[str, Any]:
    """正文 + 键盘。`keyboard` 为空（所有行都空）时不带该字段。"""
    return Message(content, keyboard=keyboard if keyboard else None).to_payload()


__all__ = [
    "MSG_TYPE_MARKDOWN",
    "Message",
    "markdown_payload",
    "markdown_with_keyboard",
]
