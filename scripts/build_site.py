#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py — 个人网站一键搭建 · 站点生成器
从 config.json 生成自包含静态站点到 dist/（套用 fioutput 设计体系）。

用法:
  python build_site.py --config config.json --out dist/ [--site-url https://...]
  python build_site.py --demo            # 生成演示站点 demo-site/
  python build_site.py --config config.json --out dist/ --article 文章ID   # 仅重建单篇文章

config.json 结构示例（init_project.py 会生成）:
{
  "site": {
    "type": "home|research|dashboard|notes|resume",
    "title": "XX的投资笔记",
    "logo": "XX",
    "desc": "一句话介绍",
    "nav": [ {"label": "首页", "url": "index.html"}, ... ],
    "theme": { "primary": "#051C2C", "accent": "#C0392B" },
    "site_url": "https://xxx.researches.cn",
    "footer_left": "© 2026 XX",
    "footer_right": "数据来源：XX",
    "last_updated": "2026-08-10"
  },
  "hero": { "title": "...", "subtitle": "...", "meta": "...", "cta": [...] },
  "sections": [ { "type": "stats|grid|table|cards|text|reports", ... } ],
  "reports": [ {"title","type","date","desc","url"} ],
  "notes":   [ {"title","date","desc","tags","url"} ],
  "stats":   [ {"label","value"} ],
  "experience": [ {"when","what","where","detail"} ],
  "skills":  [ {"title","desc"} ],
  "articles": { "文章ID": { "title","date","tags","body_md" } }
}
"""
import argparse
import html as _html
import json
import os
import re
import shutil
import sys
from datetime import date

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "templates")
CSS_PATH = os.path.join(TEMPLATE_DIR, "base.css")

TEMPLATES = ["home", "research", "dashboard", "notes", "resume", "article"]


# ─────────────────────────── 工具函数 ───────────────────────────

def esc(s):
    """HTML 转义"""
    if s is None:
        return ""
    return _html.escape(str(s))


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_css(cfg):
    """加载 base.css，并应用用户主题色覆盖"""
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()
    theme = cfg.get("site", {}).get("theme", {}) or {}
    overrides = []
    if theme.get("primary"):
        overrides.append(":root { --c-primary: %s; }" % theme["primary"])
    if theme.get("accent"):
        overrides.append(":root { --c-accent: %s; }" % theme["accent"])
    if theme.get("surface"):
        overrides.append(":root { --c-surface: %s; }" % theme["surface"])
    return css + "\n/* theme overrides */\n" + "\n".join(overrides)


def build_nav_links(cfg, current="index.html"):
    nav = cfg.get("site", {}).get("nav", [])
    out = []
    for item in nav:
        label = esc(item.get("label", ""))
        url = esc(item.get("url", "#"))
        cls = " active" if url == current else ""
        out.append('<a class="%s" href="%s">%s</a>' % (cls.strip(), url, label))
    return "\n      ".join(out)


def render_template(name, cfg, css, **extra):
    path = os.path.join(TEMPLATE_DIR, name + ".html")
    with open(path, "r", encoding="utf-8") as f:
        tpl = f.read()
    site = cfg.get("site", {})
    site_url = site.get("site_url", "") or ""
    replace = {
        "{{SITE_TITLE}}": esc(site.get("title", "我的网站")),
        "{{SITE_DESC}}": esc(site.get("desc", "")),
        "{{SITE_URL}}": esc(site_url),
        "{{LOGO}}": esc(site.get("logo", site.get("title", "My Site"))),
        "{{NAV_LINKS}}": build_nav_links(cfg),
        "{{FOOTER_LEFT}}": esc(site.get("footer_left", "")),
        "{{FOOTER_RIGHT}}": esc(site.get("footer_right", "数据来源：自有研究")),
        "{{LAST_UPDATED}}": esc(site.get("last_updated", date.today().isoformat())),
        "{{CSS}}": css,
    }
    replace.update(extra)
    for k, v in replace.items():
        tpl = tpl.replace(k, str(v))
    return tpl


def render_sections(cfg, css):
    """home/dashboard 的自由区块渲染"""
    sections = cfg.get("sections", [])
    out = []
    for i, sec in enumerate(sections):
        stype = sec.get("type", "text")
        title = esc(sec.get("title", ""))
        alt = ' alt' if sec.get("alt") else ''
        if stype == "stats":
            cards = "".join(
                '<div class="stat-card"><div class="num">%s</div><div class="label">%s</div></div>'
                % (esc(s.get("value", "")), esc(s.get("label", "")))
                for s in sec.get("items", [])
            )
            out.append('<section class="section%s"><div class="wrap"><h2>%s</h2>'
                       '<div class="stats-row">%s</div></div></section>'
                       % (alt, title, cards))
        elif stype == "grid":
            cards = "".join(
                '<div class="card"><h3>%s</h3><div class="desc">%s</div>%s%s</div>'
                % (esc(c.get("title", "")), esc(c.get("desc", "")),
                   _tag_row(c.get("tags", [])),
                   _link_more(c.get("url")))
                for c in sec.get("items", [])
            )
            out.append('<section class="section%s"><div class="wrap"><h2>%s</h2>'
                       '<div class="grid">%s</div></div></section>'
                       % (alt, title, cards))
        elif stype == "table":
            head = "".join("<th>%s</th>" % esc(h) for h in sec.get("headers", []))
            rows = ""
            for r in sec.get("rows", []):
                cells = []
                for cell in r:
                    if isinstance(cell, dict) and cell.get("url"):
                        cells.append('<a href="%s">%s</a>' % (esc(cell["url"]), esc(cell.get("text", ""))))
                    else:
                        cells.append(esc(str(cell)))
                rows += "<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in cells)
            out.append('<section class="section%s"><div class="wrap"><h2>%s</h2>'
                       '<div class="table-wrap"><table><thead><tr>%s</tr></thead>'
                       '<tbody>%s</tbody></table></div></div></section>'
                       % (alt, title, head, rows))
        elif stype == "reports":
            rows = "".join(
                '<li><div><a class="t" href="%s">%s</a>'
                '<div class="desc">%s</div></div><span class="d">%s</span></li>'
                % (esc(r.get("url", "#")), esc(r.get("title", "")),
                   esc(r.get("desc", "")), esc(r.get("date", "")))
                for r in sec.get("items", [])
            )
            out.append('<section class="section%s"><div class="wrap"><h2>%s</h2>'
                       '<ul class="report-list">%s</ul></div></section>'
                       % (alt, title, rows))
        elif stype == "text":
            out.append('<section class="section%s"><div class="wrap prose"><h2>%s</h2>%s</div></section>'
                       % (alt, title, markdown_to_html(sec.get("body", ""))))
        elif stype == "contact":
            items = "".join(
                '<div class="item"><div class="k">%s</div><div class="v">%s</div></div>'
                % (esc(c.get("k", "")), _link_or_text(c.get("v", ""), c.get("url")))
                for c in sec.get("items", [])
            )
            out.append('<section class="section%s"><div class="wrap"><h2>%s</h2>'
                       '<div class="contact">%s</div></div></section>'
                       % (alt, title, items))
    return "\n\n".join(out)


def _tag_row(tags):
    if not tags:
        return ""
    return ('<div class="tag-row">' + "".join('<span class="tag">%s</span>' % esc(t) for t in tags) + "</div>") \
        if tags else ""


def _link_more(url):
    if not url:
        return ""
    return '<a class="more" href="%s">了解更多 →</a>' % esc(url)


def _link_or_text(text, url):
    if url:
        return '<a href="%s">%s</a>' % (esc(url), esc(text))
    return esc(text)


def render_hero(cfg):
    hero = cfg.get("hero", {}) or {}
    cta = ""
    items = hero.get("cta", [])
    if items:
        btns = []
        for i, b in enumerate(items):
            cls = "btn" if i == 0 else "btn btn-outline"
            btns.append('<a class="%s" href="%s">%s</a>' % (cls, esc(b.get("url", "#")), esc(b.get("label", ""))))
        cta = '<div class="cta">%s</div>' % "".join(btns)
    return (esc(hero.get("title", "")), esc(hero.get("subtitle", "")),
            esc(hero.get("meta", "")), cta)


# ─────────────────────────── Markdown 迷你转换 ───────────────────────────

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def _inline(md):
    md = _BOLD_RE.sub(r"<strong>\1</strong>", md)
    md = _ITALIC_RE.sub(r"<em>\1</em>", md)
    md = _INLINE_CODE_RE.sub(r"<code>\1</code>", md)
    md = _LINK_RE.sub(r'<a href="\2">\1</a>', md)
    return md


def markdown_to_html(md):
    if not md:
        return ""
    lines = md.split("\n")
    out = []
    in_list = False
    in_blockquote = False
    for line in lines:
        s = line.rstrip()
        if not s:
            if in_list:
                out.append("</ul>")
                in_list = False
            if in_blockquote:
                out.append("</blockquote>")
                in_blockquote = False
            out.append("")
            continue
        m = _HEADING_RE.match(s)
        if m:
            if in_list:
                out.append("</ul>"); in_list = False
            if in_blockquote:
                out.append("</blockquote>"); in_blockquote = False
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, _inline(m.group(2)), lvl))
            continue
        if s.startswith("- ") or s.startswith("* "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append("<li>%s</li>" % _inline(s[2:]))
            continue
        if s.startswith("> "):
            if not in_blockquote:
                out.append("<blockquote>"); in_blockquote = True
            out.append(_inline(s[2:]))
            continue
        if in_list:
            out.append("</ul>"); in_list = False
        if in_blockquote:
            out.append("</blockquote>"); in_blockquote = False
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                continue  # 分隔行
            out.append("<tr>%s</tr>" % "".join("<td>%s</td>" % _inline(c) for c in cells))
            continue
        # 表格检测：首次出现且下一个非空行是分隔行 → 加 <table>
        if s.startswith("|") and out and out[-1].startswith("|") is False:
            out.append("<table>")
            out.append(s)
            continue
        out.append("<p>%s</p>" % _inline(s))
    if in_list:
        out.append("</ul>")
    if in_blockquote:
        out.append("</blockquote>")
    # 简单把连续的 <tr> 包进 table
    result = "\n".join(out)
    # 若出现过 <table>，把后续连续 <tr> 用 <thead>/<tbody> 包裹
    return result


# ─────────────────────────── 各类型渲染 ───────────────────────────

def render_home(cfg, css):
    hero = cfg.get("hero", {}) or {}
    h_title, h_sub, h_meta, h_cta = render_hero(cfg)
    extra = {
        "{{HERO_TITLE}}": h_title,
        "{{HERO_SUBTITLE}}": h_sub,
        "{{HERO_META}}": h_meta,
        "{{HERO_CTA}}": h_cta,
        "{{SECTIONS}}": render_sections(cfg, css),
    }
    return render_template("home", cfg, css, **extra)


def render_research(cfg, css):
    reports = cfg.get("reports", [])
    rows = "".join(
        '<tr><td><a class="t" href="%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td></tr>'
        % (esc(r.get("url", "#")), esc(r.get("title", "")), esc(r.get("type", "")),
           esc(r.get("date", "")), esc(r.get("desc", "")))
        for r in reports
    )
    extra = {
        "{{REPORT_ROWS}}": rows,
        "{{REPORT_JSON}}": json.dumps(reports, ensure_ascii=False),
    }
    return render_template("research", cfg, css, **extra)


def render_dashboard(cfg, css):
    stats = cfg.get("stats", [])
    stat_cards = "".join(
        '<div class="stat-card"><div class="num">%s</div><div class="label">%s</div></div>'
        % (esc(s.get("value", "")), esc(s.get("label", "")))
        for s in stats
    )
    sections = render_sections(cfg, css)
    # 图表初始化（sections 中 type=chart 由 AI 在 config 中给 chart_html）
    chart_init = ""
    chart_html = ""
    for sec in cfg.get("sections", []):
        if sec.get("type") == "chart":
            cid = sec.get("id", "chart1")
            option = sec.get("option")
            chart_html += '<section class="section"><div class="wrap"><h2>%s</h2>' % esc(sec.get("title", "图表"))
            if sec.get("desc"):
                chart_html += '<p class="lead">%s</p>' % esc(sec["desc"])
            chart_html += '<div id="%s" style="width:100%%;height:400px;"></div></div></section>' % cid
            if isinstance(option, (dict, list)):
                chart_init += (
                    "var _charts = _charts || [];\n"
                    "var ch = echarts.init(document.getElementById('%s'));\n"
                    "ch.setOption(%s);\n"
                    "_charts.push(ch);\n"
                ) % (cid, json.dumps(option, ensure_ascii=False))
            else:
                chart_init += "/* chart %s: option 未提供，由 config 补充 */\n" % cid
    sections = chart_html + sections
    resize_js = (
        "var _charts = [];\n"
        "window.addEventListener('resize', function(){ _charts.forEach(function(c){ c.resize(); }); });\n"
    )
    extra = {
        "{{STAT_CARDS}}": stat_cards,
        "{{SECTIONS}}": sections,
        "{{CHART_INIT}}": "<script>" + chart_init + resize_js + "</script>",
    }
    return render_template("dashboard", cfg, css, **extra)


def render_notes(cfg, css):
    notes = cfg.get("notes", [])
    items = "".join(
        '<li><div><a class="t" href="%s">%s</a>%s<div class="tag-row" style="margin-top:4px">%s</div></div><span class="d">%s</span></li>'
        % (esc(n.get("url", "#")), esc(n.get("title", "")),
           '<div class="desc">%s</div>' % esc(n.get("desc", "")) if n.get("desc") else "",
           _tag_row(n.get("tags", [])), esc(n.get("date", "")))
        for n in notes
    )
    extra = {
        "{{NOTE_ITEMS}}": items,
        "{{NOTES_JSON}}": json.dumps(notes, ensure_ascii=False),
    }
    return render_template("notes", cfg, css, **extra)


def render_resume(cfg, css):
    h_title, h_sub, h_meta, h_cta = render_hero(cfg)
    exp = cfg.get("experience", [])
    timeline = "".join(
        '<div class="item"><div class="when">%s</div><div class="what">%s</div>'
        '<div class="where">%s</div><div class="detail">%s</div></div>'
        % (esc(e.get("when", "")), esc(e.get("what", "")), esc(e.get("where", "")),
           esc(e.get("detail", "")))
        for e in exp
    )
    skills = cfg.get("skills", [])
    skill_cards = "".join(
        '<div class="card"><h3>%s</h3><div class="desc">%s</div></div>'
        % (esc(s.get("title", "")), esc(s.get("desc", "")))
        for s in skills
    )
    # 额外区块（如获奖、论文）用 sections
    extra_sections = render_sections(cfg, css)
    extra = {
        "{{HERO_TITLE}}": h_title,
        "{{HERO_SUBTITLE}}": h_sub,
        "{{HERO_META}}": h_meta,
        "{{HERO_CTA}}": h_cta,
        "{{EXPERIENCE_TITLE}}": cfg.get("experience_title", "工作经历"),
        "{{TIMELINE_ITEMS}}": timeline,
        "{{SKILLS_TITLE}}": cfg.get("skills_title", "专业能力"),
        "{{SKILL_CARDS}}": skill_cards,
        "{{EXTRA_SECTIONS}}": extra_sections,
    }
    return render_template("resume", cfg, css, **extra)


def render_article(cfg, css, article_id):
    articles = cfg.get("articles", {}) or {}
    art = articles.get(article_id)
    if not art:
        sys.exit("article not found: %s" % article_id)
    extra = {
        "{{ARTICLE_TITLE}}": esc(art.get("title", article_id)),
        "{{ARTICLE_META}}": "%s · %s" % (esc(art.get("date", "")), " ".join(esc(t) for t in art.get("tags", []))),
        "{{ARTICLE_BODY}}": markdown_to_html(art.get("body_md", "")),
        "{{ARTICLE_SOURCE}}": cfg.get("site", {}).get("footer_right", "自有研究"),
    }
    return render_template("article", cfg, css, **extra)


# ─────────────────────────── 主流程 ───────────────────────────

RENDERERS = {
    "home": render_home,
    "research": render_research,
    "dashboard": render_dashboard,
    "notes": render_notes,
    "resume": render_resume,
}


def build(cfg, out_dir, only_article=None):
    stype = cfg.get("site", {}).get("type", "home")
    css = load_css(cfg)
    os.makedirs(out_dir, exist_ok=True)

    if only_article:
        # 仅重建单篇文章（不动首页列表）
        html_out = render_article(cfg, css, only_article)
        with open(os.path.join(out_dir, "%s.html" % only_article), "w", encoding="utf-8") as f:
            f.write(html_out)
        print("[build] article %s.html rebuilt" % only_article)
        return

    # 首页/列表页
    renderer = RENDERERS.get(stype, render_home)
    index_html = renderer(cfg, css)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("[build] index.html (%s mode) written" % stype)

    # 文章页
    for aid, art in (cfg.get("articles", {}) or {}).items():
        if not art.get("url"):
            art["url"] = "%s.html" % aid
        html_out = render_article(cfg, css, aid)
        with open(os.path.join(out_dir, "%s.html" % aid), "w", encoding="utf-8") as f:
            f.write(html_out)
        print("[build] %s.html written" % aid)

    # 复制附加资源（静态目录 copy_files）
    copy_files = cfg.get("site", {}).get("copy_files", [])
    for src in copy_files:
        if os.path.isdir(src):
            dst = os.path.join(out_dir, os.path.basename(src.rstrip("/\\")))
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print("[build] copied dir %s -> %s" % (src, dst))
        elif os.path.isfile(src):
            shutil.copy2(src, os.path.join(out_dir, os.path.basename(src)))
            print("[build] copied file %s" % src)

    print("[build] done → %s" % os.path.abspath(out_dir))


DEMO_CONFIG = {
    "site": {
        "type": "home",
        "title": "张三 · 固定收益研究",
        "logo": "张三",
        "desc": "买方固收研究员的个人主页：利率策略、信用研究、数据看板。",
        "nav": [
            {"label": "首页", "url": "index.html"},
            {"label": "研报库", "url": "research.html"},
            {"label": "数据看板", "url": "dashboard.html"},
            {"label": "研究笔记", "url": "notes.html"},
        ],
        "theme": {"primary": "#051C2C", "accent": "#C0392B"},
        "site_url": "https://example.researches.cn",
        "footer_left": "© 2026 张三",
        "footer_right": "数据来源：自有研究",
        "last_updated": "2026-08-10",
    },
    "hero": {
        "title": "用数据说话，以研究立身",
        "subtitle": "十年利率债与信用债研究经验，专注宏观周期判断与信用风险定价。",
        "meta": "固定收益研究 · 利率策略 · 信用分析",
        "cta": [
            {"label": "查看研报库", "url": "research.html"},
            {"label": "数据看板", "url": "dashboard.html"},
        ],
    },
    "sections": [
        {
            "type": "stats",
            "title": "研究概览",
            "items": [
                {"label": "深度研报", "value": "86"},
                {"label": "跟踪主体", "value": "320+"},
                {"label": "年覆盖报告", "value": "24"},
                {"label": "数据看板", "value": "6"},
            ],
        },
        {
            "type": "grid",
            "title": "研究领域",
            "items": [
                {"title": "利率策略", "desc": "基于资金面、机构行为与曲线的利率方向判断框架。", "tags": ["利率", "策略"]},
                {"title": "信用研究", "desc": "城投与产业主体的信用风险定价与利差分析。", "tags": ["信用", "利差"]},
                {"title": "数据工程", "desc": "自建固收数据库与自动化看板，覆盖资金、利差、机构行为。", "tags": ["数据", "自动化"]},
            ],
        },
        {
            "type": "reports",
            "title": "最新研报",
            "items": [
                {"title": "2026年三季度利率策略展望", "desc": "从资金面与供给端看长端利率方向", "date": "2026-07-28", "url": "research.html"},
                {"title": "城投债利差分位数全景", "desc": "区域利差分布与历史分位监测", "date": "2026-07-12", "url": "research.html"},
                {"title": "基金久期行为的市场指示意义", "desc": "聪明钱久期与市场拐点", "date": "2026-06-30", "url": "research.html"},
            ],
        },
        {
            "type": "contact",
            "title": "联系我",
            "items": [
                {"k": "Email", "v": "zhangsan@example.com", "url": "mailto:zhangsan@example.com"},
                {"k": "微信", "v": "zhangsan_research"},
                {"k": "研究笔记", "v": "notes.html", "url": "notes.html"},
            ],
        },
    ],
    "reports": [
        {"title": "2026年三季度利率策略展望", "type": "策略", "date": "2026-07-28",
         "desc": "从资金面与供给端看长端利率方向。", "url": "research.html"},
        {"title": "城投债利差分位数全景", "type": "信用", "date": "2026-07-12",
         "desc": "区域利差分布与历史分位监测。", "url": "research.html"},
        {"title": "基金久期行为的市场指示意义", "type": "策略", "date": "2026-06-30",
         "desc": "聪明钱久期与市场拐点。", "url": "research.html"},
    ],
    "stats": [
        {"label": "深度研报", "value": "86"},
        {"label": "跟踪主体", "value": "320+"},
        {"label": "年覆盖报告", "value": "24"},
        {"label": "数据看板", "value": "6"},
    ],
    "articles": {
        "method": {
            "title": "我的利率研究框架",
            "date": "2026-06-01",
            "tags": ["利率", "方法论"],
            "body_md": (
                "## 研究框架\n\n"
                "- **基本面**：增长、通胀、就业\n"
                "- **资金面**：央行操作、银行间水位\n"
                "- **机构行为**：久期、杠杆、持仓结构\n"
                "- **估值**：曲线形态、利差分位\n\n"
                "> 核心判断来自数据验证，而非主观直觉。\n\n"
                "详情请参考我的**研报库**与**数据看板**。"
            ),
        },
    },
    "experience": [
        {"when": "2022 - 至今", "what": "买方固收研究员", "where": "某资管机构",
         "detail": "负责利率策略与信用研究，管理固收研究框架与数据库。"},
        {"when": "2018 - 2022", "what": "信用分析师", "where": "某券商研究所",
         "detail": "覆盖城投与产业债，撰写深度报告与信用跟踪。"},
    ],
    "skills": [
        {"title": "利率策略", "desc": "资金面—机构行为—曲线三维框架"},
        {"title": "信用分析", "desc": "城投/产业主体信用风险定价"},
        {"title": "数据工程", "desc": "Python + 数据库自动化研究流程"},
    ],
    "notes": [
        {"title": "我的利率研究框架", "date": "2026-06-01", "desc": "从资金面到曲线的方法论。",
         "tags": ["利率", "方法论"], "url": "method.html"},
        {"title": "资金面观测指标体系", "date": "2026-05-20", "desc": "银行间流动性的九大维度。",
         "tags": ["资金面"], "url": "#"},
        {"title": "城投利差怎么看", "date": "2026-04-11", "desc": "区域分位与一级市场情绪。",
         "tags": ["信用", "城投"], "url": "#"},
    ],
}


def build_demo():
    out = "demo-site"
    cfg = DEMO_CONFIG
    build(cfg, out)
    # 生成各类型演示页
    for t in ["research", "dashboard", "notes", "resume"]:
        c = json.loads(json.dumps(cfg))
        c["site"]["type"] = t
        c["site"]["title"] = "%s · 演示" % t
        c["site"]["nav"] = [{"label": "首页", "url": "index.html"}, {"label": t, "url": "index.html"}]
        renderer = RENDERERS[t]
        html_out = renderer(c, load_css(c))
        with open(os.path.join(out, "%s.html" % t), "w", encoding="utf-8") as f:
            f.write(html_out)
        print("[demo] %s.html written" % t)
    print("[demo] done → %s/" % out)


def main():
    ap = argparse.ArgumentParser(description="个人网站一键搭建 · 站点生成器")
    ap.add_argument("--config", default="config.json", help="config.json 路径")
    ap.add_argument("--out", default="dist", help="输出目录")
    ap.add_argument("--demo", action="store_true", help="生成演示站点")
    ap.add_argument("--article", help="仅重建单篇文章（给出文章ID）")
    args = ap.parse_args()

    if args.demo:
        build_demo()
        return
    cfg = load_config(args.config)
    build(cfg, args.out, only_article=args.article)


if __name__ == "__main__":
    main()
