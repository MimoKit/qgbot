"""端到端示例：拼一张带图、带 @、带按钮的卡片，打印出 payload。

不联网，只演示 SDK 的用法。运行：

    python examples/card.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 正文里有零宽空格（平台的空行语法），GBK 控制台打不出来
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qgbot import command, link, make_keyboard, md  # noqa: E402
from qgbot.message import Message  # noqa: E402


def build_fortune_card(user_openid: str, role_name: str, image_url: str) -> Message:
    """一张运势卡片：标题 + 图 + 引用块 + 内联按钮 + 键盘。"""
    content = md.render(
        md.title("今日运势"),
        md.blank(),
        md.image(image_url, width=400, height=300, alt="运势卡片"),
        md.blank(),
        md.mention(user_openid),
        md.bold(f"今日老婆：{role_name}"),
        md.quote("宜：出门走走\n忌：熬夜"),
        md.divider(),
        md.cmd_input("再抽一次", show="换一个"),
    )

    keyboard = make_keyboard(
        command("再抽一次", "今日运势"),
        command("查看列表", "老婆列表"),
        link("官方群", "https://qm.qq.com/q/example"),
        per_row=3,
    )

    return Message(content, keyboard=keyboard)


def main() -> None:
    msg = build_fortune_card(
        user_openid="ABC123DEF456",
        role_name="散华",
        image_url="https://example.com/card.png",
    )
    payload = msg.to_payload(msg_id="msg_id_from_event")

    print("=== markdown 正文 ===")
    print(payload["markdown"]["content"])
    print()
    print("=== 完整 payload ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
