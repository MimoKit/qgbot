"""键盘与按钮：结构与平台限制。"""
from __future__ import annotations

from qgbot import (
    MAX_ROWS,
    STYLE_BLUE,
    Button,
    Keyboard,
    callback,
    command,
    link,
)
from qgbot import make_keyboard as kb
from qgbot.keyboard import PERM_ADMIN, PERM_USER, for_admins, for_users, rows_of


class TestButtonTypes:
    def test_link_button(self) -> None:
        btn = link("官网", "https://qq.com")
        d = btn.to_dict(0)
        assert d["action"]["type"] == 0
        assert d["action"]["data"] == "https://qq.com"
        assert d["render_data"]["label"] == "官网"

    def test_callback_button(self) -> None:
        btn = callback("点我", "my_callback")
        d = btn.to_dict(1)
        assert d["action"]["type"] == 1
        assert d["action"]["data"] == "my_callback"

    def test_command_button_enters_by_default(self) -> None:
        """点一下就发送，不该还要用户再按一次回车。"""
        btn = command("今日老婆", "今日老婆")
        d = btn.to_dict(0)
        assert d["action"]["type"] == 2
        assert d["action"]["enter"] is True

    def test_command_without_enter(self) -> None:
        btn = command("填字", "菜单", enter=False)
        assert btn.to_dict(0)["action"].get("enter") is not True

    def test_reply_flag(self) -> None:
        btn = command("回", "cmd", reply=True)
        assert btn.to_dict(0)["action"]["reply"] is True

    def test_visited_label_defaults_to_label(self) -> None:
        """点了之后显示的文字不传就用原文字，避免出现空白按钮。"""
        d = link("按钮", "https://x").to_dict(0)
        assert d["render_data"]["visited_label"] == "按钮"

    def test_style(self) -> None:
        assert link("a", "u").to_dict(0)["render_data"]["style"] == STYLE_BLUE


class TestButtonId:
    def test_auto_id_from_index(self) -> None:
        """平台要求按钮 id 在一条消息内唯一，没指定时用序号。"""
        assert link("a", "u").to_dict(0)["id"] == "0"
        assert link("b", "u").to_dict(3)["id"] == "3"

    def test_explicit_id_wins(self) -> None:
        btn = link("a", "u")
        btn.button_id = "custom"
        assert btn.to_dict(9)["id"] == "custom"


class TestPermissions:
    def test_default_everyone(self) -> None:
        assert link("a", "u").to_dict(0)["action"]["permission"] == {"type": 2}

    def test_for_users(self) -> None:
        btn = for_users(link("a", "u"), ["1", "2"])
        assert btn.to_dict(0)["action"]["permission"] == {
            "type": PERM_USER, "specify_user_ids": ["1", "2"],
        }

    def test_for_admins(self) -> None:
        btn = for_admins(link("a", "u"))
        assert btn.to_dict(0)["action"]["permission"] == {"type": PERM_ADMIN}


class TestKeyboard:
    def test_structure(self) -> None:
        k = kb(command("A", "a"), command("B", "b"), command("C", "c"), per_row=2)
        d = k.to_dict()
        assert len(d["content"]["rows"]) == 2
        assert len(d["content"]["rows"][0]["buttons"]) == 2
        assert len(d["content"]["rows"][1]["buttons"]) == 1

    def test_button_ids_are_sequential_across_rows(self) -> None:
        k = kb(*[command(str(i), str(i)) for i in range(5)], per_row=2)
        ids = [
            b["id"]
            for row in k.to_dict()["content"]["rows"]
            for b in row["buttons"]
        ]
        assert ids == ["0", "1", "2", "3", "4"]

    def test_truncates_beyond_max_rows(self) -> None:
        """平台只渲染前 5 行，多出来的直接丢，不抛错。"""
        rows = [[command(f"b{i}", f"c{i}")] for i in range(MAX_ROWS + 3)]
        k = Keyboard(rows=rows)
        assert len(k.to_dict()["content"]["rows"]) == MAX_ROWS

    def test_empty_keyboard_is_falsy(self) -> None:
        """空键盘要能被调用方判成 False，否则会发一个空 keyboard 字段。"""
        assert not Keyboard()
        assert not kb()

    def test_non_empty_is_truthy(self) -> None:
        assert kb(command("a", "a"))

    def test_font_size(self) -> None:
        k = kb(command("a", "a"), font_size="large")
        assert k.to_dict()["content"]["style"]["font_size"] == "large"

    def test_add_row_chaining(self) -> None:
        k = Keyboard()
        k.add_row(command("a", "a")).add_row(command("b", "b"))
        assert len(k.to_dict()["content"]["rows"]) == 2


class TestRowsOf:
    def test_splits(self) -> None:
        btns = [link(str(i), "u") for i in range(7)]
        rows = rows_of(btns, per_row=3)
        assert [len(r) for r in rows] == [3, 3, 1]

    def test_per_row_clamped(self) -> None:
        """每行超过平台上限会被夹到上限值。"""
        btns = [link(str(i), "u") for i in range(10)]
        rows = rows_of(btns, per_row=99)
        assert all(len(r) <= 5 for r in rows)


class TestButtonDataclass:
    def test_direct_construction(self) -> None:
        btn = Button(label="x", action_type=2, data="cmd")
        assert btn.to_dict(0)["render_data"]["label"] == "x"

    def test_click_limit(self) -> None:
        btn = command("a", "a")
        btn.click_limit = 3
        assert btn.to_dict(0)["action"]["click_limit"] == 3

    def test_unsupport_tips(self) -> None:
        btn = command("a", "a")
        btn.unsupport_tips = "请升级 QQ"
        assert btn.to_dict(0)["action"]["unsupport_tips"] == "请升级 QQ"
