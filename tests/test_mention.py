"""@ 提及与频道内联元素。"""
from __future__ import annotations

import pytest

from qgbot import md


class TestMention:
    def test_at_user_uses_new_tag(self) -> None:
        """平台已废弃 `<@id>`，要用新标签。"""
        assert md.mention("abc123") == '<qqbot-at-user id="abc123" />'

    def test_at_everyone(self) -> None:
        assert md.mention_everyone() == "<qqbot-at-everyone />"

    def test_empty_id_rejected(self) -> None:
        """空 id 会生成无效标签，平台整条拒收。"""
        with pytest.raises(ValueError):
            md.mention("")

    def test_whitespace_id_trimmed(self) -> None:
        assert md.mention("  abc  ") == '<qqbot-at-user id="abc" />'


class TestChannelElements:
    def test_channel_link(self) -> None:
        assert md.channel("123456") == "<#123456>"

    def test_emoji(self) -> None:
        assert md.emoji("123") == "<emoji:123>"


class TestStrategy:
    def test_mention_in_render(self) -> None:
        out = md.render(md.title("测试"), md.mention("u1"), "正文")
        assert '<qqbot-at-user id="u1" />' in out
        assert out.count("\n") == 2
