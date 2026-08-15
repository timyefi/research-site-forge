# 托管方案对比与凭证配置

## 方案总览

| 方案 | 国内访问 | 免费额度 | 备案 | 自动化难度 | 定位 |
|------|---------|---------|------|-----------|------|
| **SiteForge 平台（*.researches.cn）** | ⭐ 快且稳（Sealos 国内节点） | 作者自托管、**0 成本** | 免 | 一个 POST 请求、**无需任何账号** | **默认方案** |
| **腾讯 EdgeOne Makers** | ⭐ 快且稳 | 40 项目 / 5GB 总存储 / 500 构建次·月（免备案域名） | 默认域名免备案 | CLI+Token / 登录态 / MCP 免认证三级通道 | 备选 |
| **EdgeOne MCP 分享链接** | 快且稳 | 免费、**无需账号** | 免 | 官方公开 MCP 端点一条命令 | 零门槛兜底（受内容策略限制） |
| GitHub Pages | 不稳定（github.io 常被限速） | 1 站点 1GB / 100GB 带宽/月 | 免 | git + Token | 备选 / 海外 |
| Cloudflare Pages | 一般（大陆节点限速） | 无限带宽 / 500 构建次/月 | 免 | wrangler + Token | 备选 |
| Sealos 对象存储 | 快 | 个人资源（非免费产品） | 免 | S3 直传 | 内部/临时分享（私有桶） |

> **结论**：默认推荐 **SiteForge 平台（`*.researches.cn` 二级域名）**。由作者托管在 Sealos 上，S3 私有桶存储 + 平台网关代理，**免费、免备案、无需任何账号**，`deploy.py` 一个 POST 即完成上线。EdgeOne 作为国内优质备选；其余平台按用户偏好切换。

## 凭证配置（一次性）

所有平台凭证统一存放在 **`~/.site-forge/config.json`**（跨项目复用），结构如下：

```json
{
  "researches": {
    "api_endpoint": "https://api.researches.cn",
    "admin_token": "……"   // 可选：删除站点时用（对应平台 SF_ADMIN_SECRET）
  },
  "edgeone":  { "api_token": "……" },
  "github":   { "token": "ghp_……", "user": "your-github-username" },
  "cloudflare": { "api_token": "……", "account_id": "……" },
  "sealos":   {
    "endpoint": "https://objectstorageapi.bja.sealos.run",
    "access_key": "……",
    "secret_key": "……",
    "bucket": "……",
    "public_base_url": "……"
  },
  "preferred": "researches"
}
```

> 安全提示：`config.json` 放在用户目录（非项目目录），避免误提交。部署脚本只读取本文件，不写入项目。

### SiteForge 平台（推荐）

- 访问地址：`https://api.researches.cn`
- 部署**无需注册账号、无需 Token**；只要能访问 `api.researches.cn` 即可
- 写入（一次即可，AI 或用户手工完成）：
  `~/.site-forge/config.json` 的 `researches.api_endpoint` 与 `preferred: "researches"`
  ```json
  {
    "researches": { "api_endpoint": "https://api.researches.cn" },
    "preferred": "researches"
  }
  ```
- 部署方式：`python scripts/deploy.py --site-dir dist/ --name <站点名>` → 自动 POST 到平台 → 打印 `https://<站点名>.researches.cn/`
- 站点更新：同名重新 deploy 即覆盖（新内容立即生效）
- **删除站点**（破坏性操作，需要管理员令牌）：
  - 平台管理员在应用环境变量配置 `SF_ADMIN_SECRET=<随机串>`
  - 本地在 `researches.admin_token` 配置同一令牌（或环境变量 `SF_ADMIN_TOKEN`）
  - 执行：`python scripts/deploy.py --delete --name <站点名> --provider researches`
  - 或：`curl -X DELETE -H "X-SiteForge-Token: <令牌>" https://api.researches.cn/v1/sites/<站点名>`

### EdgeOne（主推备选）

- 注册/登录：腾讯云 EdgeOne Makers 控制台（国内站：`edgeone.cloud.tencent.com/pages`）
- 获取 API Token：控制台 → 项目 → **API Token** 标签页 → 创建 Token → 复制
- 写入：`~/.site-forge/config.json` 的 `edgeone.api_token`
- 无需在命令行登录；`deploy.py` 用 `edgeone makers deploy -t <token>` 完成自动化
- **零门槛（无账号）**：`deploy.py` 会自动降级到官方 MCP 免认证通道（`mcp-on-edge.edgeone.site`），部署为分享链接形式
- **注意**：MCP 免费端点对明显金融内容有策略限制，若被拒请配置 API Token 走正式通道

### GitHub

- 创建 Token：GitHub → Settings → Developer settings → Personal access tokens → 勾选 `repo` + `workflow` 权限
- 写入：`github.token` + `github.user`
- 部署：创建 `<user>.github.io` 或 `gh-pages` 分支 → push 即上线

### Cloudflare

- 创建 Token：Cloudflare Dashboard → My Profile → API Tokens → Create Token（权限：`Cloudflare Pages: Edit`）
- 写入：`cloudflare.api_token` + `account_id`

### Sealos（内部/临时分享）

- 在 Sealos 桌面创建私有存储桶 → 获取 AccessKey/SecretKey/Bucket 名
- 写入 `sealos.*`；`public_base_url` 填 `https://<你的桶访问域名>` 或 path-style 网关
- 注意：私有桶内容不能对外直连访问，仅供**平台内部**（`*.researches.cn`）或临时直传使用

## 本地资产检测（自动）

`deploy.py` 启动时检测以下本地环境并自动调整：

| 检测项 | 影响 |
|--------|------|
| `researches.api_endpoint` 可访问（默认 `https://api.researches.cn`） | → SiteForge 平台（`*.researches.cn` 二级域名）**默认** |
| `edgeone` CLI 可用 + token 已配置 | → EdgeOne ① CLI+Token（正式域名） |
| `edgeone` CLI 可用 + 已登录 | → EdgeOne ② 登录态（正式域名） |
| 无 CLI / 未登录 / 无 token | → EdgeOne ③ MCP 免认证（分享链接） |
| `git` 可用 + `GITHUB_TOKEN` 已配置 | → 可走 GitHub Pages |
| `wrangler` 可用 + 已登录 | → 可走 Cloudflare |
| `.env` 存在（含 S3 凭证） | → 可走 Sealos（复用 site-deploy 的 `.env` 格式） |
| `fioutput/` 存在 | → 模板设计体系自动对齐（读取其 `brand/base.css` 语义变量） |

## 更新站点

- SiteForge / EdgeOne / Cloudflare / Sealos：重新 build + 重新 deploy 即可**覆盖更新**（同名项目/前缀覆盖）
- GitHub Pages：`git push` 覆盖同分支
- 无需用户执行任何手动操作
