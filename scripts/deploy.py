#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy.py — 个人网站一键搭建 . 100% 自动化部署器

自动检测本地可用工具链并按优先级部署:
  1. edgeone CLI（已登录 或 ~/.site-forge/config.json 有 edgeone.api_token）-> 腾讯 EdgeOne Makers（默认）
  2. git + GITHUB_TOKEN / github token 已配置                              -> GitHub Pages（备选）
  3. wrangler 已登录                                                       -> Cloudflare Pages（备选）
  4. site-deploy/.env 或 ~/.site-forge/config.json 有 Sealos S3 凭证        -> Sealos 对象存储（临时分享）
  5. 全部不可用 -> 打印配置引导（图形化步骤），提示配置后重跑

用法:
  python deploy.py --site-dir dist/ --name my-site [--provider edgeone|github|cloudflare|sealos] [--title "标题"]
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HOME = Path.home()
SFORGE_DIR = HOME / ".site-forge"
CONFIG_PATH = SFORGE_DIR / "config.json"

# 本项目根（scripts/ 的上一级）
SKILL_ROOT = Path(__file__).resolve().parent.parent


# --------------------------- 工具 ---------------------------

def log(msg):
    print("[deploy] %s" % msg)


def warn(msg):
    print("[deploy] [WARN] %s" % msg)


def run(cmd, timeout=180):
    """运行命令，返回 (returncode, stdout)"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return -1, "command not found: %s" % cmd[0]
    except subprocess.TimeoutExpired:
        return -2, "timeout"


def which(cmd):
    return shutil.which(cmd)


def load_config():
    """读取 ~/.site-forge/config.json（凭证全局复用）"""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except Exception as e:
            warn("config.json 解析失败: %s" % e)
    return {}


def ensure_config_exists():
    """确保凭证目录存在"""
    SFORGE_DIR.mkdir(parents=True, exist_ok=True)


def find_sealos_env():
    """从 site-deploy/.env（若存在）读取 Sealos 凭证，兼容复用"""
    env_path = SKILL_ROOT.parent / "site-deploy" / ".env"
    if env_path.exists():
        data = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
        if data.get("S3_ACCESS_KEY") and data.get("S3_BUCKET"):
            # site-deploy 页面 S3 key 前缀为 pages/，访问 URL = SITE_BASE_URL/pages/{name}/
            base = data.get("SITE_BASE_URL", "").rstrip("/")
            public_base = base + "/pages" if base else ""
            return {
                "endpoint": data.get("S3_INTERNAL_ENDPOINT", "https://objectstorageapi.bja.sealos.run"),
                "access_key": data["S3_ACCESS_KEY"],
                "secret_key": data.get("S3_SECRET_KEY", ""),
                "bucket": data["S3_BUCKET"],
                "public_base_url": public_base,
            }
    return None


# --------------------------- EdgeOne Makers ---------------------------

EDGEONE_MCP_URL = "https://mcp-on-edge.edgeone.site/mcp-server"


def detect_edgeone(cfg):
    cli = which("edgeone")
    if not cli:
        # 即使没有 CLI，MCP 免认证通道也可用
        return True, "edgeone (MCP 免认证通道可用)"
    token = (cfg.get("edgeone") or {}).get("api_token")
    if token:
        return True, "edgeone (API token)"
    rc, out = run([cli, "whoami"])
    if rc == 0:
        return True, "edgeone (已登录)"
    return True, "edgeone (MCP 免认证通道可用)"


def _mcp_call(url, method, params, timeout=120):
    """调用 EdgeOne 官方 Streaming MCP 端点（免认证，返回 JSON）"""
    import urllib.error  # noqa
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _mcp_deploy_html(url, html, timeout=120):
    """通过 MCP deploy-html 部署单页 HTML，返回公开 URL（None 失败）"""
    try:
        data = _mcp_call(url, "tools/call",
                         {"name": "deploy-html", "arguments": {"value": html}}, timeout=timeout)
        result = data.get("result") or {}
        content = result.get("content") or []
        for item in content:
            text = item.get("text", "")
            if text.startswith("http"):
                return text.strip()
        # 检查策略限制（金融内容可能被 EdgeOne 免费 MCP 端点拒绝）
        for item in content:
            text = item.get("text", "")
            if "policy restrictions" in text.lower():
                warn("MCP 策略限制: 该页面含金融内容，免费 MCP 端点拒绝部署。请使用 CLI + API Token 路径（edgeone login 后重新部署）")
                return None
        err = data.get("error")
        if err:
            warn("MCP deploy-html 失败: %s" % err)
    except Exception as e:
        warn("MCP deploy-html 失败: %s" % e)
    return None


def deploy_edgeone_mcp(cfg, site_dir, name, title):
    """免认证快速通道：逐页通过官方 MCP 部署，返回入口页 URL。
    适合无腾讯云账号/未登录的零门槛场景（分享链接形式，非自有项目域名）。"""
    log("使用 EdgeOne MCP 免认证通道部署（无需腾讯云账号）...")
    files = []
    for root, _dirs, fnames in os.walk(site_dir):
        for fn in fnames:
            if fn.endswith(".html"):
                files.append(os.path.join(root, fn))
    files.sort(key=lambda p: 0 if os.path.basename(p).lower() == "index.html" else 1)
    if not files:
        warn("未找到 HTML 文件")
        return False, None
    urls = {}
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            html = fh.read()
        rel = os.path.relpath(f, site_dir).replace("\\", "/")
        url = _mcp_deploy_html(EDGEONE_MCP_URL, html)
        if not url:
            warn("页面部署失败: %s" % rel)
            continue
        urls[rel] = url
        log("已部署 %s -> %s" % (rel, url))
    if not urls:
        return False, None
    entry = urls.get("index.html") or next(iter(urls.values()))
    log("EdgeOne MCP 部署完成，共 %d 页" % len(urls))
    return True, entry


def deploy_edgeone(cfg, site_dir, name, title):
    cli = which("edgeone")
    token = (cfg.get("edgeone") or {}).get("api_token")

    # 优先：CLI + API Token（自有项目，正式域名）
    if cli and token:
        cmd = [cli, "makers", "deploy", site_dir, "-n", name, "--json", "-t", token]
        log("执行: edgeone makers deploy %s -n %s --json -t ***" % (site_dir, name))
        rc, out = run(cmd, timeout=300)
        if rc == 0:
            url = _parse_edgeone_url(out)
            if url:
                return True, url
            return True, None
        warn("EdgeOne CLI 部署失败（token 可能无效），尝试 MCP 免认证通道...")
        return deploy_edgeone_mcp(cfg, site_dir, name, title)

    # 已登录态
    if cli:
        rc, _ = run([cli, "whoami"])
        if rc == 0:
            cmd = [cli, "makers", "deploy", site_dir, "-n", name, "--json"]
            log("执行: edgeone makers deploy %s -n %s --json" % (site_dir, name))
            rc, out = run(cmd, timeout=300)
            if rc == 0:
                url = _parse_edgeone_url(out)
                if url:
                    return True, url
                return True, None
            warn("EdgeOne CLI 部署失败，尝试 MCP 免认证通道...")
            return deploy_edgeone_mcp(cfg, site_dir, name, title)

    # 无 CLI 或未认证 -> MCP 免认证通道
    return deploy_edgeone_mcp(cfg, site_dir, name, title)


def _parse_edgeone_url(out):
    """从 edgeone deploy --json 输出解析访问链接"""
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                url = data.get("url") or data.get("previewUrl") or data.get("productionUrl")
                if url:
                    return url
            except Exception:
                continue
    return parse_url_from_output(out)


# --------------------------- GitHub Pages ---------------------------

def detect_github(cfg):
    if not which("git"):
        return False, "git 未安装"
    token = (cfg.get("github") or {}).get("token") or os.environ.get("GITHUB_TOKEN")
    user = (cfg.get("github") or {}).get("user")
    if token and user:
        return True, "github pages"
    return False, "git 可用但缺 github token/user"


def deploy_github(cfg, site_dir, name, title):
    git = which("git")
    token = (cfg.get("github") or {}).get("token") or os.environ.get("GITHUB_TOKEN")
    user = (cfg.get("github") or {}).get("user")
    repo = name if name.endswith(".github.io") or name.startswith(user) else "%s.github.io" % user
    log("GitHub Pages 目标仓库: %s" % repo)

    tmp = site_dir  # 直接在 dist 里操作 git
    rc, _ = run([git, "-C", tmp, "init", "-q"])
    run([git, "-C", tmp, "checkout", "-q", "-b", "gh-pages"])
    run([git, "-C", tmp, "add", "-A"])
    run([git, "-C", tmp, "config", "user.email", "site-forge@local"])
    run([git, "-C", tmp, "config", "user.name", "site-forge"])
    run([git, "-C", tmp, "commit", "-q", "-m", "deploy: %s" % title])
    # 使用 token 推送
    url = "https://%s@github.com/%s/%s.git" % (token, user, repo)
    rc, out = run([git, "-C", tmp, "push", "-q", "-f", url, "gh-pages"])
    if rc != 0:
        warn("GitHub 推送失败:\n%s" % out[-2000:])
        return False, None
    return True, "https://%s.github.io/%s/" % (user, "" if repo.endswith(".github.io") else repo)


# --------------------------- Cloudflare Pages ---------------------------

def detect_cloudflare(cfg):
    wr = which("wrangler")
    if not wr:
        return False, "wrangler 未安装"
    token = (cfg.get("cloudflare") or {}).get("api_token")
    if token:
        return True, "cloudflare (token)"
    return False, "wrangler 未登录且无 token"


def deploy_cloudflare(cfg, site_dir, name, title):
    wr = which("wrangler")
    token = (cfg.get("cloudflare") or {}).get("api_token")
    account_id = (cfg.get("cloudflare") or {}).get("account_id")
    env = os.environ.copy()
    if token:
        env["CLOUDFLARE_API_TOKEN"] = token
    if account_id:
        env["CLOUDFLARE_ACCOUNT_ID"] = account_id
    cmd = [wr, "pages", "deploy", site_dir, "--project-name", name, "--branch", "production"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=240, env=env,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        out = (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        warn("wrangler 执行失败: %s" % e)
        return False, None
    if p.returncode != 0:
        warn("Cloudflare 部署失败:\n%s" % out[-2000:])
        return False, None
    return True, parse_url_from_output(out)


# --------------------------- Sealos 对象存储 ---------------------------

def detect_sealos(cfg):
    if cfg:
        cred = cfg.get("sealos") or {}
        if cred.get("access_key") and cred.get("bucket"):
            return True, "sealos (s3)"
    if find_sealos_env():
        return True, "sealos (site-deploy .env)"
    return False, "无 sealos 凭证"


def s3_put_simple(cred, key, data, content_type):
    """用 AWS SigV4 简单实现（依赖 boto3 则用 boto3，否则用内置实现）"""
    try:
        import boto3  # noqa
        return s3_put_boto3(cred, key, data, content_type)
    except ImportError:
        return s3_put_sigv4(cred, key, data, content_type)


def s3_put_boto3(cred, key, data, content_type):
    import boto3
    from botocore.config import Config
    s3 = boto3.client(
        "s3",
        endpoint_url=cred["endpoint"],
        aws_access_key_id=cred["access_key"],
        aws_secret_access_key=cred["secret_key"],
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}),
    )
    s3.put_object(Bucket=cred["bucket"], Key=key, Body=data, ContentType=content_type)
    return True


def _hmac_sha256(key, msg):
    import hashlib, hmac
    return hmac.new(key, msg, hashlib.sha256).digest()


def s3_put_sigv4(cred, key, data, content_type):
    """极简 SigV4 PUT（无 boto3 时使用），适用 Sealos 兼容 S3 网关"""
    import datetime
    import hashlib
    import hmac
    import urllib.parse

    endpoint = cred["endpoint"].rstrip("/")
    bucket = cred["bucket"]
    host = urllib.parse.urlparse(endpoint).netloc
    region = "us-east-1"
    service = "s3"
    now = datetime.datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(data).hexdigest()

    canonical_uri = "/%s/%s" % (bucket, urllib.parse.quote(key, safe="/"))
    canonical_headers = "content-type:%s\nhost:%s\nx-amz-content-sha256:%s\nx-amz-date:%s\n" % (
        content_type, host, payload_hash, amz_date)
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
    canonical_request = "PUT\n%s\n\n%s\n%s\n%s" % (canonical_uri, canonical_headers, signed_headers, payload_hash)

    scope = "%s/%s/%s/aws4_request" % (date_stamp, region, service)
    string_to_sign = "AWS4-HMAC-SHA256\n%s\n%s\n%s" % (amz_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest())

    k_date = _hmac_sha256(("AWS4" + cred["secret_key"]).encode(), date_stamp.encode())
    k_region = _hmac_sha256(k_date, region.encode())
    k_service = _hmac_sha256(k_region, service.encode())
    k_signing = _hmac_sha256(k_service, "aws4_request".encode())
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    auth = ("AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s"
            % (cred["access_key"], scope, signed_headers, signature))
    url = endpoint + canonical_uri
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", content_type)
    req.add_header("x-amz-content-sha256", payload_hash)
    req.add_header("x-amz-date", amz_date)
    req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status >= 300:
                warn("S3 PUT %s 失败: HTTP %s" % (key, resp.status))
                return False
    except Exception as e:
        warn("S3 PUT %s 失败: %s" % (key, e))
        return False
    return True


def deploy_sealos(cfg, site_dir, name, title):
    cred = (cfg.get("sealos") or {}) if cfg else {}
    if not (cred.get("access_key") and cred.get("bucket")):
        cred = find_sealos_env()
    if not cred:
        warn("无 Sealos 凭证")
        return False, None

    # 站点 key 前缀直接用站点名（公开桶路径式访问 URL = public_base_url + / + name）
    # 兼容 site-deploy .env:public_base_url 已含 /pages，URL = SITE_BASE_URL/pages/{name}/
    prefix = "%s/" % name.strip("/")
    failed = 0
    content_types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
        ".md": "text/markdown; charset=utf-8",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "application/zip",
        ".csv": "text/csv; charset=utf-8",
    }
    for root, dirs, files in os.walk(site_dir):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, site_dir).replace("\\", "/")
            key = prefix + rel
            ext = os.path.splitext(fn)[1].lower()
            ct = content_types.get(ext, "application/octet-stream")
            with open(full, "rb") as f:
                data = f.read()
            if not s3_put_simple(cred, key, data, ct):
                failed += 1
                warn("上传失败: %s" % rel)
    if failed:
        return False, None
    base = cred.get("public_base_url", "")
    if not base:
        warn("未配置 public_base_url，无法打印访问链接;请补充 sealos.public_base_url")
        return True, None
    url = "%s/%s/" % (base.rstrip("/"), name.strip("/"))
    return True, url


# --------------------------- 通用 ---------------------------

def parse_url_from_output(out):
    """从 CLI 输出中提取 https 访问链接"""
    import re
    m = re.search(r"https?://[^\s\"'<>)]+", out)
    if m:
        # 过滤明显的非页面地址
        u = m.group(0).rstrip(".,;")
        if not any(x in u for x in ("oauth", "login", "api.", ".json", "console")):
            return u
    return None


PROVIDERS = ["edgeone", "github", "cloudflare", "sealos"]


def detect_all(cfg):
    det = {
        "edgeone": detect_edgeone(cfg),
        "github": detect_github(cfg),
        "cloudflare": detect_cloudflare(cfg),
        "sealos": detect_sealos(cfg),
    }
    return det


def print_guide(det, cfg):
    print()
    print("=" * 64)
    print("  需要配置一个部署平台后才能上线（一次性，约 3 分钟）")
    print("=" * 64)
    print()
    print("当前检测状态:")
    for k in PROVIDERS:
        ok, msg = det[k]
        print("  %-10s %s  %s" % (k, "OK" if ok else "NO", msg))
    print()
    print("推荐配置（国内访问最快，免费）:腾讯 EdgeOne Makers")
    print("  1) 打开 https://edgeone.cloud.tencent.com/pages ，登录腾讯云账号（微信/QQ 即可）")
    print("  2) 控制台 -> 项目 -> API Token 标签页 -> 创建 API Token")
    print("  3) 复制 Token，执行:")
    print()
    print('     mkdir -p ~/.site-forge && echo \'{ "edgeone": { "api_token": "<你的Token>" }, "preferred": "edgeone" }\' > ~/.site-forge/config.json')
    print()
    print("  4) 重新执行部署命令即可自动上线")
    print()
    print("其他平台配置方法见:references/providers.md")
    print()


def deploy(cfg, site_dir, name, provider=None, title="我的个人网站"):
    det = detect_all(cfg)
    preferred = (cfg.get("preferred") or "edgeone").lower()
    order = PROVIDERS if provider else ([preferred] + [p for p in PROVIDERS if p != preferred])
    if provider:
        order = [provider]
    for p in order:
        if p not in det:
            continue
        ok, msg = det[p]
        if not ok:
            if provider:
                warn("provider=%s 不可用:%s" % (p, msg))
            continue
        log("使用 %s 部署..." % msg)
        if p == "edgeone":
            ok2, url = deploy_edgeone(cfg, site_dir, name, title)
        elif p == "github":
            ok2, url = deploy_github(cfg, site_dir, name, title)
        elif p == "cloudflare":
            ok2, url = deploy_cloudflare(cfg, site_dir, name, title)
        elif p == "sealos":
            ok2, url = deploy_sealos(cfg, site_dir, name, title)
        else:
            continue
        if ok2:
            print()
            print("=" * 64)
            print("  [OK]  部署成功！")
            print()
            print("  URL:  访问链接: %s" % (url or "(请查看上方 CLI 输出)"))
            print("  UPDATE:  更新方法: 修改 config.json -> python scripts/build_site.py --config config.json --out dist/ -> python scripts/deploy.py --site-dir dist/ --name %s" % name)
            print("=" * 64)
            return 0
        else:
            warn("%s 部署失败，尝试下一平台..." % p)
    print_guide(det, cfg)
    return 1


def main():
    ap = argparse.ArgumentParser(description="个人网站一键搭建 . 100% 自动化部署")
    ap.add_argument("--site-dir", default="dist", help="站点输出目录")
    ap.add_argument("--name", required=True, help="站点名（唯一，纯小写字母数字连字符）")
    ap.add_argument("--title", default="我的个人网站", help="站点标题")
    ap.add_argument("--provider", choices=PROVIDERS, help="指定部署平台")
    ap.add_argument("--check", action="store_true", help="仅检测环境可用性")
    args = ap.parse_args()

    ensure_config_exists()
    cfg = load_config()
    det = detect_all(cfg)
    log("环境检测: " + ", ".join("%s=%s" % (k, "OK" if v[0] else "NO") for k, v in det.items()))

    if args.check:
        for k, (ok, msg) in det.items():
            print("%-10s %s  %s" % (k, "OK" if ok else "NO", msg))
        return 0

    sys.exit(deploy(cfg, args.site_dir, args.name, args.provider, args.title))


if __name__ == "__main__":
    main()
