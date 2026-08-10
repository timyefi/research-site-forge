# EdgeOne Makers CLI 安装与配置

EdgeOne Makers（原 EdgeOne Pages / Tencent Cloud Pages）是腾讯云基于 EdgeOne 全球边缘加速的**前端开发与部署平台**，支持纯静态站点直接上传。国内访问快、免费额度充裕。

## 1. 安装 CLI（一次性，需 Node.js）

```bash
npm install -g edgeone
edgeone --version        # 验证安装
```

> 如无 Node.js，可在控制台直接拖拽上传 ZIP（纯静态目录压缩即可），但不满足 100% 自动化。建议安装 Node.js + CLI。

## 2. 三种认证方式（任选其一，均支持无交互部署）

### 方式 A：API Token（推荐，100% 自动化）

1. 打开 EdgeOne Makers 控制台：<https://edgeone.cloud.tencent.com/pages>（国内站）
2. 登录腾讯云账号（新用户可用微信/QQ 一键注册，免费）
3. 控制台 → **项目** → 任意项目或新建项目 → 切到 **"API Token"** 标签页
4. 点击 **"创建 API Token"** → 填写描述（如 `site-forge-auto`）→ 创建
5. 复制 Token，写入本地凭证文件：

```bash
# 写入 ~/.site-forge/config.json
{
  "edgeone": { "api_token": "<粘贴Token>" },
  "preferred": "edgeone"
}
```

> Token 只需创建一次。之后 `deploy.py` 每次用 `edgeone makers deploy -t <token>` 自动化部署，无需再登录。

### 方式 B：命令行登录（交互式，用于本地调试）

```bash
edgeone login                    # 浏览器弹出统一登录页
edgeone login --site china       # 腾讯云中国站
edgeone login --site global      # 国际站
edgeone whoami                   # 查看当前登录账号
```

> 登录态存在本机 CLI 配置中，`deploy.py` 检测到已登录也会直接使用（无需 token）。

### 方式 C：Git 连接（需仓库）

把代码推到 EdgeOne Makers 关联的 Git 仓库，后端自动构建部署。不适合本 skill 的一键流程，略。

## 3. 部署命令速查

```bash
# 部署 dist 目录到生产环境（创建或覆盖项目 my-site）
edgeone makers deploy ./dist -n my-site

# 用 API Token 自动化部署（CI / AI 使用）
edgeone makers deploy ./dist -n my-site -t <API_TOKEN>

# 部署到预览环境
edgeone makers deploy ./dist -n my-site -e preview -t <API_TOKEN>

# 查看当前登录账号
edgeone whoami

# 机器可读输出（Agent/CI 使用，含访问链接）
edgeone makers deploy ./dist -n my-site -t <API_TOKEN> --json
```

## 4. 三级部署策略（deploy.py 自动选择）

`deploy.py` 按以下优先级自动选择 EdgeOne 部署通道，**全程无需用户输入命令**：

| 优先级 | 通道 | 条件 | 结果 |
|--------|------|------|------|
| ① | **CLI + API Token** | 已配置 `edgeone.api_token` | 自有项目，域名 `https://<project>.edgeone.cool`（默认 3 小时预览限制） |
| ② | **CLI 已登录态** | 本机已 `edgeone login` | 同上 |
| ③ | **MCP 免认证通道** | 无需任何账号（默认兜底） | 分享链接 `https://mcp.edgeone.site/share/xxx`（公开可访问） |

> **100% 自动化结论**：无需腾讯云账号也能一键部署（走 MCP 通道）；配置了 API Token 则升级为自有项目域名。

## 5. 重要：域名访问规则（实测结论）

> **项目域名默认不是永久公开访问的**，这是 EdgeOne Makers 的内容合规机制：

1. **项目域名**（如 `https://siteforge-official.edgeone.cool`）直接访问会返回 **401**（UNAUTHORIZED）
2. **需要带验证参数的预览链接**：`?eo_token=...&eo_time=...`，**3 小时有效**，过期后 401
3. **要永久公开访问** → 控制台项目 → **Domains** → **Add custom domain**（绑定自定义域名，需 **ICP 备案**，支持免费 SSL）
4. 每次新部署都会生成新的预览链接；控制台 **Preview** 按钮可随时获取

**落地建议**：
- 临时分享/内部预览 → 直接用部署返回的预览链接（3 小时内有效）
- 需要长期稳定对外 → 绑定自定义域名（备案一次，永久生效）
- 完全不想要账号/备案 → 用 **MCP 免认证通道**（分享链接永久有效，但受内容策略限制）

## 6. MCP 免认证通道（零门槛部署）

腾讯官方提供 **Streaming MCP Server**：`https://mcp-on-edge.edgeone.site/mcp-server`，提供 `deploy-html` 工具，**无需登录/无账号**即可部署 HTML 并获得公开访问链接。`deploy.py` 已内置该通道（EdgeOne 路径的最终兜底）。

**内容策略限制（实测）**：免费 MCP 端点会对明显金融类内容（如"研究框架/策略"文章）做策略限制并拒绝部署。部署时若遇此类拒绝，`deploy.py` 会提示改用 **CLI + API Token** 路径（`edgeone login` 一次即可）。

## 7. 常见问题

| 问题 | 解决 |
|------|------|
| `edgeone: command not found` | `npm install -g edgeone` 未成功；确认 Node.js ≥ 18 |
| 部署报"未登录" | 检查 `~/.site-forge/config.json` 中 `edgeone.api_token` 是否正确；或先 `edgeone login` 一次 |
| Token 失效 | 控制台 API Token 页重新创建并更新凭证文件 |
| `edgeone login` 自动打开浏览器失败 | 复制 CLI 打印的链接，在**本机浏览器**打开并完成扫码/登录即可（CLI 会轮询本地回调端口完成 token 写入） |
| 部署后访问 401 | 项目域名需带 `?eo_token=...&eo_time=...` 预览链接（3 小时有效）；需长期公开请绑定自定义域名 |
| 需要自定义域名 | 免费版支持绑定域名（需 **ICP 备案**）；绑定后永久公开访问，免费 SSL |
| 免费额度 | 40 个项目、5GB 总存储、500 次构建/月（见腾讯云文档"限制与配额"） |

## 8. 部署后

- `deploy.py` 会打印**访问链接**：
  - CLI+Token 路径 → 预览链接 `https://<project>.edgeone.cool?eo_token=...&eo_time=...`（**3 小时有效**）
  - MCP 路径 → `https://mcp.edgeone.site/share/xxx`（公开、永久有效，受内容策略限制）
- 更新站点 = 重新 `build_site.py` + `deploy.py`（同名项目覆盖）
- 想永久公开 + 自定义域名：控制台项目 → Domains → 绑定 + DNS 解析 + 免费 SSL（需备案）
