"""markdown 构造器：语法正确性与边界。"""
from __future__ import annotations

import pytest

from qgbot import md


class TestTitle:
    def test_level_1(self) -> None:
        assert md.title("今日运势") == "# 今日运势"

    def test_level_2(self) -> None:
        assert md.title("详情", level=2) == "## 详情"

    def test_level_clamped_to_max(self) -> None:
        """平台只支持两级标题，传 3 要夹到 2 而不是原样输出。"""
        assert md.title("x", level=3) == "## x"

    def test_level_clamped_to_min(self) -> None:
        assert md.title("x", level=0) == "# x"
        assert md.title("x", level=-5) == "# x"


class TestStyles:
    def test_bold(self) -> None:
        assert md.bold("粗") == "**粗**"

    def test_italic(self) -> None:
        assert md.italic("斜") == "_斜_"

    def test_bold_italic(self) -> None:
        assert md.bold_italic("粗斜") == "***粗斜***"

    def test_underline_uses_double_underscore(self) -> None:
        """平台的下划线语法是 `__`，不是 html 的 <u>。"""
        assert md.underline("下划线") == "__下划线__"

    def test_strike(self) -> None:
        assert md.strike("删") == "~~删~~"


class TestLinks:
    def test_inline_link(self) -> None:
        assert md.link("腾讯", "https://qq.com") == "[腾讯](https://qq.com)"

    def test_autolink(self) -> None:
        assert md.autolink("https://qq.com") == "<https://qq.com>"


class TestImage:
    def test_size_in_alt(self) -> None:
        """尺寸必须写在 alt 里，这是平台的语法。"""
        out = md.image("https://x/a.png", 200, 300)
        assert out == "![text #200px #300px](https://x/a.png)"

    def test_custom_alt(self) -> None:
        out = md.image("https://x/a.png", 10, 20, alt="封面")
        assert out == "![封面 #10px #20px](https://x/a.png)"

    @pytest.mark.parametrize("w,h", [(0, 100), (100, 0), (-1, 100), (100, -1)])
    def test_rejects_non_positive_size(self, w: int, h: int) -> None:
        """不给尺寸会按原图铺满，撑爆消息；这里宁可抛错也不默默放行。"""
        with pytest.raises(ValueError):
            md.image("https://x/a.png", w, h)

    def test_media_scheme(self) -> None:
        out = md.media("abc123")
        assert out == "![text](qqbot-media://abc123)"

    def test_media_with_size(self) -> None:
        out = md.media("abc123", 100, 200)
        assert out == "![text #100px #200px](qqbot-media://abc123)"


class TestLists:
    def test_ordered(self) -> None:
        assert md.ordered(["一", "二"]) == "1. 一\n2. 二"

    def test_unordered(self) -> None:
        assert md.unordered(["一", "二"]) == "- 一\n- 二"

    def test_nested_uses_four_spaces(self) -> None:
        """平台的二级缩进是 4 空格。"""
        assert md.ordered(["子项"], level=2) == "    1. 子项"
        assert md.unordered(["子项"], level=2) == "    - 子项"


class TestQuote:
    def test_single_line(self) -> None:
        assert md.quote("引用") == "> 引用"

    def test_multi_line_each_prefixed(self) -> None:
        assert md.quote("第一行\n第二行") == "> 第一行\n> 第二行"


class TestDivider:
    def test_uses_triple_star(self) -> None:
        """平台的分隔线是 `***`。"""
        assert md.divider() == "***"


class TestBlank:
    def test_contains_zero_width_space(self) -> None:
        """连续 `\\n` 会被平台合并，必须插零宽空格。"""
        out = md.blank()
        assert md.ZERO_WIDTH_SPACE in out

    def test_multiple(self) -> None:
        out = md.blank(2)
        assert out.count(md.ZERO_WIDTH_SPACE) == 2


class TestCmdButtons:
    def test_cmd_input_basic(self) -> None:
        out = md.cmd_input("今日老婆")
        assert 'text="%E4%BB%8A%E6%97%A5%E8%80%81%E5%A9%86"' in out
        assert 'reference="false"' in out

    def test_cmd_input_custom_show(self) -> None:
        out = md.cmd_input("菜单", show="功能菜单")
        assert "show=" in out
        # 中文被 urlencode
        assert "%E5%8A%9F%E8%83%BD%E8%8F%9C%E5%8D%95" in out

    def test_cmd_input_reference(self) -> None:
        out = md.cmd_input("a", reference=True)
        assert 'reference="true"' in out

    def test_special_chars_are_encoded(self) -> None:
        """不编码的话平台解析属性时会截断。"""
        out = md.cmd_input('a"b&c')
        assert '"' not in out.split('text="')[1].split('" ')[0]
        assert "&amp;" not in out  # quote() 用 %26 而不是实体

    def test_cmd_enter(self) -> None:
        out = md.cmd_enter("确认")
        assert out.startswith("<qqbot-cmd-enter")
        assert "确认" not in out  # 已编码


class TestRender:
    def test_joins_with_newline(self) -> None:
        assert md.render(md.title("A"), "正文") == "# A\n正文"

    def test_skips_empty(self) -> None:
        assert md.render(md.title("A"), "", "正文") == "# A\n正文"

    def test_real_world_card(self) -> None:
        """组合出真实卡片，确认每段都在。"""
        out = md.render(
            md.title("今日运势"),
            md.blank(),
            md.quote("宜：出门走走"),
            md.divider(),
            md.image("https://x/a.png", 200, 200),
            md.cmd_input("换一个", show="再抽一次"),
        )
        assert "# 今日运势" in out
        assert "> 宜：出门走走" in out
        assert "***" in out
        assert "![text #200px #200px]" in out
        assert "<qqbot-cmd-input" in out
