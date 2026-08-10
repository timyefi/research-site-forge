# 个人研究平台部署 · SiteForge

> 给买方研究者 / 固收分析师的一键建站 + 免费部署方案。**套用 fioutput 投行级设计体系**，本地生成、100% 自动化部署、国内可访问。

## 项目简介

为**买方老师 / 投研研究者**提供"一句话 → 完整个人研究平台"的一站式能力：

- **一键建站**：个人主页 / 研报库 / 数据看板 / 研究笔记 / 简历页，5 类站点模板 + 1 篇文章页模板
- **fioutput 设计体系**：内置 Navy 投行级设计系统（`assets/templates/base.css`，可自定义主题色）
- **100% 自动化部署**：自动检测可用工具链并部署，全程无需手动命令
- **国内可访问**：默认腾讯 EdgeOne（快且免费），三级部署通道 + GitHub Pages / Cloudflare / Sealos 兜底

## 快速开始

```bash
# ① 初始化项目（交互式问答生成 config.json）
python scripts/init_project.py my-site

# ② 生成站点（config.json → dist/ 自包含静态站点）
python scripts/build_site.py --config my-site/config.json --out my-site/dist

# ③ 一键部署（自动检测工具链，部署后打印访问链接）
python scripts/deploy.py --site-dir my-site/dist --name my-site
```

## 部署平台

| 平台 | 国内访问 | 费用 | 自动化 | 定位 |
|------|---------|------|--------|------|
| **腾讯 EdgeOne Makers** | ⭐ 快且稳 | 免费（40 项目/5GB/500 构建·月） | 三级通道：CLI+Token / 登录态 / MCP 免认证 | **默认方案** |
| **EdgeOne MCP 分享链接** | 快且稳 | 免费、**无需账号** | 官方公开 MCP 端点 | 零门槛兜底（受内容策略限制） |
| GitHub Pages | 不稳定 | 免费 | git + token | 备选 / 海外 |
| Cloudflare Pages | 一般 | 免费 | wrangler + token | 备选 |
| Sealos 对象存储 | 快 | 个人资源 | S3 直传 | 临时分享 |

> **EdgeOne 三级通道**：① CLI+API Token（自有项目）→ ② CLI 已登录态 → ③ MCP 免认证（无需账号，分享链接）。即使没有腾讯云账号也能一键上线。

## 目录结构

```
个人研究平台部署/
├── SKILL.md                    ← Skill 入口（触发条件、三步工作流、部署总览）
├── LICENSE                     ← 版权与许可（作者：叶青）
├── references/
│   ├── providers.md            ← 托管方案对比 + 4 平台凭证配置
│   └── edgeone-setup.md        ← EdgeOne CLI 安装 / Token / 三级通道 / 域名访问规则
├── assets/templates/
│   ├── base.css                ← fioutput Navy 设计体系（可自定义主题色）
│   └── home/research/dashboard/notes/resume/article.html  ← 6 类站点模板
└── scripts/
    ├── init_project.py         ← 交互式初始化 → config.json
    ├── build_site.py           ← config.json → 自包含静态站点（含 Markdown 渲染）
    └── deploy.py               ← 100% 自动化部署器（edgeone→github→cloudflare→sealos）
```

## 复用关系

| 资源 | 复用方式 |
|------|---------|
| `fioutput/brand/base.css` | 设计体系来源 → 提炼为"个人站点版" base.css |
| `site-deploy/.env` + 脚本 | S3 部署参考 → 复刻为 deploy.py 的 Sealos 后端 |
| `site-deploy/SKILL.md` | 单文件 HTML + OG 标签 + 上传流程规范 |

## License

Copyright (c) 2026 叶青 (Ye Qing). All rights reserved.

本项目采用**非商业使用许可 + 商业使用需授权**模式：

- ✅ **免费使用**：个人学习、研究、教学、非盈利性个人网站搭建
- ⚠️ **商业使用需取得授权**：任何商业用途（收费服务、企业商业化系统等）须事先获得原作者书面授权

详见 [LICENSE](./LICENSE)。
