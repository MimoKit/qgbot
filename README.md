<div align="center">

# qgbot

_把 QQ 官方机器人那套 Markdown 语法和键盘 JSON，变成可组合的 Python 调用_

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-%E2%89%A53.10-3776ab)](https://www.python.org/)
[![Docs](https://img.shields.io/badge/文档-中文-8f5db7)](https://docs.example.com/)

写插件时不用再手拼 `<qqbot-cmd-input>` 和按钮 JSON —— 一句 `md.image(url, 400, 300)` 就够。

</div>

## 为什么需要它

QQ 官方机器人的 markdown 跟标准 markdown 不是一回事。图片尺寸得写在 alt 文本里（`![x #200px #300px](url)`）、分隔线是 `***` 不是 `---`、下划线是 `__` 不是 `<u>`、连续换行会被合并所以要多空一行得插零宽空格、@ 用户的标签从 `<@id>` 换成了 `<qqbot-at-user id="" />`。这些细节散在文档各处，每个插件都要重复踩一遍。

按钮是另一层麻烦：平台要一段嵌套 JSON，`action.type` 区分链接 / 回调 / 指令 / 订阅，`permission.type` 区分所有人 / 管理员 / 指定用户 / 指定身份组，手写容易把 `type` 和 `style` 搞混。

图片还有第三层：markdown 里的图必须是公网 URL，平台自己去拉；插件渲染出来的卡片只存在本地磁盘。官方图库的上传是**三步预签名流程**——声明元信息拿预签名地址、PUT 原始字节、回传 ETag 里的 MD5 收尾——不是一次 multipart 提交。

qgbot 把这三块分别封成 `md`、`keyboard`、`media`，再加一个 `message` 负责组装发送用的 payload。

## 特性

- **零依赖** —— 纯标准库实现，不引入任何运行时包，`pip install` 不拉任何东西
- **不绑框架** —— 没有 NoneBot / 自研框架的 import，任何 Python 环境都能直接用
- **不碰网络** —— 素材上传只算签名、组请求、解响应，HTTP 由调用方注入，复用你自己的连接池与重试策略
- **语法对齐平台** —— 分隔线、下划线、图片尺寸、零宽空格、@ 标签这些与标准 md 不同的地方全部按官方语法生成
- **限制可见** —— 标题只支持两级、键盘最多 5 行、图片 10 MB、图库 100 张，都以常量形式暴露
- **结构可测** —— 89 个用例覆盖每一处语法与上传流程，不需要起 mock server

## 模块一览

| 模块 | 覆盖内容 |
| --- | --- |
| `qgbot.md` | 标题、六种文字样式、行内链接与自动链接、带尺寸图片、两种列表（含二级缩进）、引用块、分隔线、多空行、正文内联指令按钮、@ 用户与 @ 全体、频道子频道跳转与系统表情 |
| `qgbot.keyboard` | 链接 / 回调 / 指令三类按钮，权限限定，按行切分，字号设置 |
| `qgbot.media` | 图库上传三步流程，含签名计算、错误码映射、列表解析与删除 |
| `qgbot.message` | markdown 正文与键盘合成发送 body，带 `msg_id` / `msg_seq` 被动回复字段 |

```python
from qgbot import md, command, make_keyboard, Message

content = md.render(
    md.title("今日运势"),
    md.image("https://example.com/card.png", 400, 300),
    md.mention("user_openid"),
    md.quote("宜：出门走走"),
)

payload = Message(
    content,
    keyboard=make_keyboard(command("再抽一次", "今日运势")),
).to_payload(msg_id="收到的那条消息id")
```

## 边界

**不做网络请求。** 素材上传只算 MD5 / SHA1、组装请求体、解析响应，实际 HTTP 由调用方注入的 `Transport` 完成。这样 SDK 不绑定 httpx / aiohttp / requests 中的任何一个，测试也不必起 mock server。

**不管鉴权。** AccessToken 的获取与刷新属于调用方，SDK 产出的 payload 里不含凭据。

**不做语法校验。** 平台限制以常量与注释暴露，但 SDK 不主动改写用户内容。两处例外：标题层级会被夹到合法范围（传 3 得到 2），键盘超过 5 行会被截断（平台本身就不渲染，抛错反而让整条消息发不出去）。

**不解析已有 markdown。** 只有构造，没有反向解析。

## 环境要求

- Python `>= 3.10`

## 开源协议

[MIT](LICENSE)
