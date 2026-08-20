# 贡献指南

欢迎给 huawo-website-skill 贡献!

---

## 你可以贡献什么

### 🎨 新风格模板

最有价值的贡献。每个新风格就是一个新的 HTML 模板,放到 `assets/`。

**要求**:
- 纯 HTML + CSS 单文件,无依赖
- 占位符用 `[xxx]` 格式(跟现有模板一致)
- 图片位置用 `[IMG: 描述]` 占位
- 包含手机端适配(`@media (max-width: 768px)`)
- 设计语言克制,不炫技

**已有的风格**:
- 水墨安静风(中国水墨、书法、印章)
- 极简现代风(黑白灰、留白、无衬线)
- 温暖手作风(米色、手写感、纸张质感)

**欢迎的方向**(举例,不限):
- 赛博朋克风
- 复古打字机风
- 杂志编辑风
- 极简手账风
- 日式和风

### 🌍 翻译

把 `README.md` 和 `SKILL.md` 翻译成其他语言:
- `README.en.md`(英文)
- `README.ja.md`(日文)
- `README.ko.md`(韩文)

### 🐛 Bug 修复

- 模板里的 CSS 问题
- 占位符替换 bug
- 质量检查脚本的误报/漏报

### 📖 文档改进

- 教程文案优化
- 新增部署平台的说明
- FAQ 补充

---

## 怎么贡献

### 标准流程(PR)

1. **Fork** 这个仓库
2. **Clone** 你 fork 的仓库到本地
3. **新建分支**:`git checkout -b feature/your-feature`
4. **做改动**
5. **测试**(见下方测试要求)
6. **Commit**:`git commit -m "feat: 加一个新风格 XX 风"`
7. **Push**:`git push origin feature/your-feature`
8. **发起 PR**:在 GitHub 上发起 Pull Request,说明你做了什么

### Commit 信息规范

用 [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: 新增 XX 风格模板`
- `fix: 修复极简风手机端崩溃`
- `docs: 补充部署指南的 Vercel 部分`
- `refactor: 重构质量检查脚本`
- `chore: 更新依赖`

---

## 测试要求

### 新风格模板必须通过

1. **占位符检查**:跑 `python scripts/check-quality.py 新模板.html --template assets/02-极简现代风.html`,对照 CSS 结构
2. **视觉检查**:
   - 桌面端(1440px)布局正常
   - 手机端(375px)不崩
   - 中文字号 ≥ 16px
3. **占位符替换测试**:让 AI 按新模板走一遍完整流程,看能不能正常替换、交付

### 文档改动

- 检查 markdown 渲染正常(GitHub 上看一遍)
- 内部链接有效

---

## 设计原则(贡献者必读)

如果你贡献新风格或改动现有风格,必须遵守:

### ✅ 必须做

- **克制不炫技**:个人介绍站,内容比形式重要
- **纯 HTML/CSS**:不要引入 React/Vue/任何框架
- **中文优先**:模板默认中文,占位符用中文描述
- **响应式**:必须有手机端适配
- **无障碍**:颜色对比够,字号合理

### ❌ 不要做

- ❌ 加复杂动效(Framer Motion、GSAP、WebGL 等)
- ❌ 加外部依赖(React、Vue、jQuery 等)
- ❌ 用 Google Fonts 作为主字体(国内慢,可以作为可选增强)
- ❌ 混风格(比如把水墨元素加到极简站里)
- ❌ 替换所有内容用占位符,但保留某个具体名字(会让用户困惑)

---

## 代码风格

### HTML/CSS

- 用 2 空格缩进
- CSS 颜色用变量(`:root` 里定义)
- 类名用语义化(`.hero`、`.nav`、`.work-card`),不用 `.div1`、`.style-2`
- 中文注释用 `/* 中文注释 */`

### Python(脚本)

- Python 3.7+
- 用 `pathlib` 不用 `os.path`
- 函数加 type hints
- 复杂逻辑加注释

---

## 有问题?

- **bug 报告**:开 [Issue](../../issues),说明复现步骤
- **新风格想法**:开 Issue 讨论再动手
- **使用问题**:看 [教程](https://tcnprzcql6xt.feishu.cn/docx/VifCdjesVoJUONxI0XocFWlbnyg) 或开 Issue

---

## 感谢

每个贡献者都会在 release notes 里被感谢。

一起把这个 skill 做成中文圈最好的个人网站工具 💪
