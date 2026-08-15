#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 个人网站一键搭建 · 交互式初始化器

在用户目录（或指定目录）初始化一个网站项目：
  python init_project.py my-site            # 交互式问答 → my-site/config.json
  python init_project.py my-site --type research --title "XX研报库"
  python init_project.py my-site --demo     # 生成演示 config（默认 home）

生成 config.json 后，直接用 build_site.py + deploy.py 即可。
"""
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

BASE_URL_PLACEHOLDER = "https://YOUR-SITE.researches.cn"

SITE_TYPES = {
    "home": "个人主页（名片 + 研究方向 + 最新研报 + 联系方式）",
    "research": "研报库（研报列表 + 搜索筛选 + 下载链接）",
    "dashboard": "数据看板（KPI 卡片 + 图表 + 表格）",
    "notes": "研究笔记（文章列表 + 标签 + 搜索）",
    "resume": "简历 / 求职页（经历时间线 + 技能 + 项目）",
}

DEFAULT_SECTIONS = {
    "home": [
        {"type": "stats", "title": "研究概览",
         "items": [{"label": "深度研报", "value": "0"}, {"label": "跟踪主体", "value": "0"}, {"label": "数据看板", "value": "0"}]},
        {"type": "grid", "title": "研究领域",
         "items": [{"title": "研究领域一", "desc": "在这里描述你的一个研究方向。", "tags": ["标签"]}]},
        {"type": "reports", "title": "最新研报",
         "items": [{"title": "示例研报标题", "desc": "示例摘要", "date": date.today().isoformat(), "url": "research.html"}]},
        {"type": "contact", "title": "联系我",
         "items": [{"k": "Email", "v": "you@example.com", "url": "mailto:you@example.com"}]},
    ],
    "research": [],
    "dashboard": [],
    "notes": [],
    "resume": [],
}


def ask(question, default=None):
    suffix = " [%s]" % default if default else ""
    ans = input("  ? %s%s: " % (question, suffix)).strip()
    if not ans and default:
        return default
    return ans


def make_config(stype, title, logo, desc, name, use_defaults):
    site = {
        "type": stype,
        "title": title,
        "logo": logo,
        "desc": desc,
        "nav": _default_nav(stype),
        "theme": {"primary": "#051C2C", "accent": "#C0392B"},
        "site_url": BASE_URL_PLACEHOLDER,
        "footer_left": "© %s %s" % (date.today().year, logo),
        "footer_right": "数据来源：自有研究",
        "last_updated": date.today().isoformat(),
    }
    cfg = {"site": site}
    cfg["hero"] = {
        "title": title,
        "subtitle": desc,
        "meta": "",
        "cta": [{"label": "了解我的研究", "url": "research.html"}],
    }
    if stype in ("home", "resume"):
        cfg["sections"] = DEFAULT_SECTIONS[stype]
    if stype == "research":
        cfg["reports"] = [
            {"title": "示例研报标题", "type": "策略", "date": date.today().isoformat(),
             "desc": "在这里写研报的一句话摘要。", "url": "#"},
        ]
    if stype == "dashboard":
        cfg["stats"] = [{"label": "指标一", "value": "0"}, {"label": "指标二", "value": "0"}]
        cfg["sections"] = [
            {"type": "chart", "id": "chart1", "title": "数据图表",
             "option": {
                 "tooltip": {"trigger": "axis"},
                 "grid": {"left": 40, "right": 20, "top": 30, "bottom": 30},
                 "xAxis": {"type": "category", "data": ["1月", "2月", "3月"]},
                 "yAxis": {"type": "value"},
                 "series": [{"type": "line", "data": [10, 20, 15], "name": "系列1"}],
             }},
        ]
    if stype == "notes":
        cfg["notes"] = [
            {"title": "第一篇笔记", "date": date.today().isoformat(), "desc": "示例笔记。", "tags": ["示例"], "url": "#"},
        ]
    if stype == "resume":
        cfg["experience"] = [
            {"when": "2020 - 至今", "what": "职位", "where": "机构", "detail": "工作职责描述。"},
        ]
        cfg["skills"] = [{"title": "技能一", "desc": "技能描述"}]
        cfg["experience_title"] = "工作经历"
        cfg["skills_title"] = "专业能力"
    if use_defaults:
        cfg["site"]["site_url"] = "https://%s.researches.cn" % name
    return cfg


def _default_nav(stype):
    if stype == "research":
        return [{"label": "首页", "url": "index.html"}, {"label": "研报库", "url": "index.html"}]
    if stype == "dashboard":
        return [{"label": "首页", "url": "index.html"}, {"label": "看板", "url": "index.html"}]
    if stype == "notes":
        return [{"label": "首页", "url": "index.html"}, {"label": "笔记", "url": "index.html"}]
    if stype == "resume":
        return [{"label": "首页", "url": "index.html"}]
    return [{"label": "首页", "url": "index.html"}, {"label": "研报库", "url": "research.html"}, {"label": "数据看板", "url": "dashboard.html"}, {"label": "研究笔记", "url": "notes.html"}]


def interactive(name):
    print()
    print("个人网站一键搭建 · 初始化 %s/" % name)
    print("=" * 52)
    print("站点类型：")
    for k, v in SITE_TYPES.items():
        print("  %-10s %s" % (k, v))
    stype = ask("选择站点类型", "home").lower()
    if stype not in SITE_TYPES:
        stype = "home"
    title = ask("站点标题（显示在页头）", "我的研究主页")
    logo = ask("Logo 文字（页头简称）", title[:4] if len(title) > 4 else title)
    desc = ask("一句话介绍（SEO + 副标题）", "买方固收研究员的个人主页")
    use_defaults = ask("先按模板生成默认内容，之后再让 AI 填充？(y/n)", "y").lower() == "y"
    print()
    cfg = make_config(stype, title, logo, desc, name, use_defaults)
    return cfg


def main():
    ap = argparse.ArgumentParser(description="个人网站一键搭建 · 初始化")
    ap.add_argument("dir", help="项目目录名（会创建为 <cwd>/<dir>）")
    ap.add_argument("--type", choices=list(SITE_TYPES), help="站点类型（跳过问答）")
    ap.add_argument("--title", help="站点标题（跳过问答）")
    ap.add_argument("--demo", action="store_true", help="直接生成演示配置")
    args = ap.parse_args()

    name = args.dir.strip("/\\")
    target = Path(os.getcwd()) / name
    target.mkdir(parents=True, exist_ok=True)

    if args.demo:
        cfg = make_config(args.type or "home", args.title or "我的研究主页", args.title or "研究主页",
                          "买方固收研究员的个人主页", name, use_defaults=True)
    elif args.type:
        cfg = make_config(args.type, args.title or "我的研究主页", args.title or "研究主页",
                          "买方固收研究员的个人主页", name, use_defaults=True)
    else:
        cfg = interactive(name)

    out = target / "config.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print()
    print("✅ 已生成 %s" % out)
    print()
    print("下一步：")
    print("  1. 编辑 %s 填充你的真实内容（可直接让 AI 帮你填）" % out.name)
    print("  2. 生成站点:  python scripts/build_site.py --config %s --out %s" % (out, target / "dist"))
    print("  3. 部署上线:  python scripts/deploy.py --site-dir %s --name %s" % (target / "dist", name))


if __name__ == "__main__":
    main()
