---
layout: home

hero:
  name: qgbot
  text: QQ 官方机器人的 Markdown 构造 SDK
  tagline: 把平台那套 markdown 语法、键盘 JSON 和图片上传流程，收敛成可组合的 Python 调用。纯标准库，零运行时依赖，不绑定任何 bot 框架。
  actions:
    - theme: brand
      text: 项目概览
      link: /qgbot
    - theme: alt
      text: GitHub
      link: https://github.com/MimoKit/qgbot

features:
  - icon: 🪶
    title: 零依赖
    details: 纯标准库实现，不引入任何运行时包，pip install 不拉任何东西。
  - icon: 🔌
    title: 不绑框架
    details: 没有 NoneBot 或自研框架的 import，任何 Python 环境都能直接用。
  - icon: 🌐
    title: 不碰网络
    details: 素材上传只算签名、组请求、解响应，HTTP 由调用方注入，复用你自己的连接池与重试策略。
  - icon: 📐
    title: 语法对齐平台
    details: 分隔线、下划线、图片尺寸、零宽空格、@ 标签这些与标准 md 不同的地方，全部按官方语法生成。
  - icon: 📏
    title: 限制可见
    details: 标题只支持两级、键盘最多 5 行、图片 10 MB、图库 100 张，都以常量形式暴露。
  - icon: 🧪
    title: 结构可测
    details: 89 个用例覆盖每一处语法与上传流程，不需要起 mock server。
---
