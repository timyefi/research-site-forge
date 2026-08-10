---
name: "个人网站一键搭建"
description: "为买方研究者/固收分析师一键搭建个人研究网站（个人主页、研报库、数据看板、研究笔记、求职/展示页），并100%自动化部署到国内可访问的免费托管平台（腾讯 EdgeOne Makers / GitHub Pages / Cloudflare Pages / Sealos 对象存储）。套用 fioutput 投行级设计体系，无需懂代码，本地内容一键上线。触发场景：搭建个人网站、个人主页、研报库、研究笔记站、数据看板、简历页、把本地HTML/MD部署上线、获取免费域名、发布个人研究服务。"
---

# 个人网站一键搭建（Site Forge）

> 给买方老师的一键建站 + 免费部署方案。**套用 fioutput 投行级设计体系**，本地生成、100% 自动化部署、国内可访问。

## 触发条件

当用户需要：
- 搭建**个人网站 / 个人主页 / 研报库 / 研究笔记站 / 数据看板 / 简历展示页**
- 把**本地 HTML / MD / 看板内容**一键部署上线
- 获取**免费域名 + 免费托管 + 国内可访问**的方案
- 沉淀个人投研体系、对外提供研究服务
- "个人网站" "个人主页" "研报库" "建站" "免费部署" "上线" "发布网站"

## 核心能力

| 能力 | 说明 |
|------|------|
| **一键建站** | 用户只描述需求（几句话），AI 套用 fioutput 设计体系自动生成完整站点 |
| **5 类站点模板** | 个人主页 / 研报库 / 数据看板 / 研究笔记 / 简历页 |
| **100% 自动化部署** | `deploy.py` 自动检测可用工具链 → 自动部署 → 打印访问链接，无需手动操作 |
| **国内可访问** | 默认走腾讯 EdgeOne Makers（国内快、免费、**三级部署通道：CLI+Token → 登录态 → MCP 免认证**，即使无账号也能一键上线） |
| **设计体系** | 内置 `assets/templates/base.css`（fioutput Navy 风格，可自定义主题色） |

## 三步工作流（全程自动化）

```
用户需求一句话 → ① 生成站点 → ② 本地预览 → ③ 一键部署 → 打印访问链接
                     │              │              │
              build_site.py   open preview.html   deploy.py
```

### 步骤 ① 生成站点（AI 自动执行）

```bash
python scripts/build_site.py --config config.json --out dist/
```

- AI 根据用户需求**自动生成** `config.json`（站点类型、标题、主题色、栏目、内容）
- 也可以让用户先 `python scripts/init_project.py <站点目录>` 初始化，再按提示回答几个问题
- 生成的站点为**自包含静态 HTML**（单文件优先，零外部依赖），套用 fioutput 设计体系

**5 类站点类型**（`--template` 参数）：

| 类型 | 用途 | 典型栏目 |
|------|------|---------|
| `home` | 个人主页/名片 | Hero、研究方向、代表成果、联系方式 |
| `research` | 研报库/研报列表 | 研报筛选搜索、下载链接、分类标签 |
| `dashboard` | 数据看板 | KPI 卡片、ECharts 图表、表格 |
| `notes` | 研究笔记/博客 | 文章列表、标签、搜索、正文阅读 |
| `resume` | 简历/求职页 | 基本信息、经历时间线、技能、项目 |

### 步骤 ② 本地预览（AI 自动执行）

```bash
python -m http.server 8848 --directory dist/
```

- AI 自动打开浏览器预览 `http://localhost:8848/`
- 用户确认满意后进入部署；需要修改则直接让 AI 改 config 再重新 build

### 步骤 ③ 一键部署（100% 自动化）

```bash
python scripts/deploy.py --site-dir dist/ --name <站点名>
```

`deploy.py` **自动检测可用工具链并按优先级选择**，全程无需手动操作：

```
检测顺序（自动跳过不可用的）：
  1. edgeone CLI + API Token 已配置     → EdgeOne ① 正式域名（腾讯官方、国内快、免费）★默认
  2. edgeone CLI 已登录                  → EdgeOne ② 正式域名（同上）
  3. edgeone 任意状态（含无 CLI）         → EdgeOne ③ MCP 免认证分享链接（零门槛兜底，无需账号）
  4. git + GITHUB_TOKEN 已配置          → GitHub Pages（海外用户/备选）
  5. wrangler 已登录                    → Cloudflare Pages（备选）
  6. .env 有 Sealos S3 凭证             → Sealos 对象存储（临时/紧急分享）
  7. 全部不可用                          → 打印清晰的配置引导，提示配置后重跑
```

部署完成后打印：**访问链接 / 管理地址 / 更新方法**。

> **100% 自动化原则**：部署过程不要求用户记住任何命令。**即使没有腾讯云账号**，EdgeOne ③ MCP 免认证通道也能一键上线（分享链接）；配置了 API Token 则自动升级为正式域名。配置 Token 只需一次（每个平台都提供了**图形化控制台几步点击**的获取方式，见 `references/`）。此后每次更新网站都是"改内容 → 重新 build → 重新 deploy"一条命令。

## 目录结构

```
个人网站一键搭建/
├── SKILL.md                     ← 本文件（入口）
├── references/
│   ├── providers.md             ← 托管方案对比表 + 凭证配置（EdgeOne 主推）
│   └── edgeone-setup.md         ← EdgeOne CLI 安装 / 登录 / API Token 获取详细步骤
├── assets/
│   └── templates/
│       ├── base.css             ← fioutput 设计体系（Navy，可改 --c-* 变量换主题）
│       └── {home,research,dashboard,notes,resume}.html  ← 5 类站点模板骨架
└── scripts/
    ├── init_project.py          ← 初始化：问答式生成 config.json
    ├── build_site.py            ← 生成站点：config.json → dist/ 自包含静态站点
    └── deploy.py                ← 全自动部署：检测工具链 → 部署 → 打印链接
```

## 部署平台总览（完整对比见 `references/providers.md`）

| 平台 | 国内访问 | 费用 | 自动化 | 定位 |
|------|---------|------|--------|------|
| **腾讯 EdgeOne Makers** | ⭐ 快且稳 | 免费（40 项目/5GB/500 构建·月） | 三级通道：CLI+token / 登录态 / MCP 免认证 | **默认方案** |
| **EdgeOne MCP 分享链接** | 快且稳 | 免费、**无需账号** | 官方公开 MCP 端点 | 零门槛兑底（受内容策略限制） |
| GitHub Pages | 不稳定 | 免费（100GB/月） | git + token | 备选 / 海外 |
| Cloudflare Pages | 一般 | 免费 | wrangler + token | 备选 |
| Sealos 对象存储 | 快 | 个人资源 | S3 直传 | 临时分享 |

> **为什么默认 EdgeOne**：腾讯官方产品、国内边缘加速访问快、免费版 40 个项目对个人绰绰有余、CLI 支持 `-t <token>` 无交互部署（天然适配 AI 自动化）、平台默认域名无需备案（自定义域名才需备案）。**零门槛入口**：未登录/无 token 时自动走官方 MCP 免认证通道（分享链接），实现 100% 自动化。

## 与 site-deploy / fioutput 的复用关系

| 资源 | 复用方式 |
|------|---------|
| `fioutput/brand/base.css` | 设计体系来源 → 本 skill `assets/templates/base.css` 已提炼为"个人站点版"（保留 Navy 主色 + 语义色 + 图表多色 + 字体层级，新增站点头部/卡片/文章列表等组件） |
| `fioutput/html/SKILL.md` | Report 模式（max-width:1126px 长页面）规则被吸收为 build_site.py 的输出规范 |
| `site-deploy/scripts/quick-publish.js` + `.env` | S3 部署参考（Sealos 路径）→ 复刻为 deploy.py 的 Sealos 后端 |
| `site-deploy/SKILL.md` | 单文件 HTML + OG 标签 + 上传注册流程 → 本 skill 生成时自动注入 OG 标签 |

> **不强依赖**：本 skill 自带模板与脚本，不要求用户电脑上有 fioutput / site-deploy。但**若存在**，优先复刻其设计体系与部署经验（见 `references/providers.md` 中"本地资产检测"）。

## 质量标准（Gate）

1. **可部署**：`dist/` 下所有文件为纯静态、无构建依赖；`index.html` 自包含可离线打开
2. **国内可访问**：默认目标 EdgeOne；若用户明确要求其他平台再切换
3. **100% 自动化**：deploy 全流程无需用户输入命令；凭证缺失时给出图形化获取步骤后重跑即可
4. **fioutput 风格**：页面遵循 base.css 设计体系（Navy 主色、无圆角/渐变/斑马纹、来源标注）
5. **移动端可用**：`@media (max-width: 640px)` 响应式适配
6. **可更新**：改 config.json → 重新 build → 重新 deploy 即完成站点更新（同一站点名覆盖）
7. **微信分享可用**：自动注入 `og:title` / `og:description` / `og:image` / `og:url` 标签
