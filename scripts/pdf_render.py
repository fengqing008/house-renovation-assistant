#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""美化 PDF 生成器（pdf_render.py v4）—— 装修方案 Markdown → 精装版 PDF。
v4：对照参考件（衬线正文＋金棕点缀＋页脚书名/页码）重排：
    · 字体 Noto Serif CJK SC（衬线），正文 #3a322b / 标题 #6a4f33 / 强调 #8a5a2a
    · 封面：徽标＋大标题＋副标题＋双色分隔线＋信息行＋日期
    · 页脚：左书名（#bcab97）＋ 中页码「— N —」
    · 修 pandoc 自动标题块（封面不重复大标题）、去 justify
用法：python3 pdf_render.py --md 方案.md --out 方案-美化版.pdf --title T --subtitle S --meta M --feature F --date D --doctitle DT
"""
import argparse, pathlib, subprocess, re
from weasyprint import HTML, CSS


def build(md, out, title, subtitle, meta, feature, date, doctitle):
    base = pathlib.Path(md).parent
    body = "/tmp/_pdfbody.html"
    subprocess.run(["pandoc", str(md), "-t", "html5", "-o", body, "--wrap=none",
                    "--toc", "--toc-depth=2"], check=True)
    inner = open(body, encoding="utf-8").read()
    if "<body" in inner:
        inner = inner.split("<body", 1)[1].lstrip(">")
    for t in ("</body>", "</html>", "<head>", "</head>"):
        inner = inner.replace(t, "")
    inner = re.sub(r'<header id="title-block-header">.*?</header>', '', inner, flags=re.S)
    inner = re.sub(r'<h1 class="title">.*?</h1>', '', inner, flags=re.S)
    inner = re.sub(r'<p class="title">.*?</p>', '', inner, flags=re.S)
    inner = inner.replace("&nbsp;", " ")

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title></head>
<body>
<section class="cover">
  <div class="c-badge">室内设计方案</div>
  <h1 class="c-title">{title}</h1>
  <p class="c-sub">{subtitle}</p>
  <div class="c-rule"><span></span><span></span></div>
  <p class="c-meta">{meta}</p>
  <p class="c-feature">{feature}</p>
  <p class="c-date">{date}</p>
</section>
<div class="content">{inner}</div>
</body></html>"""

    css = CSS(string=f"""
@page {{
  size: A4; margin: 20mm 17mm 16mm 17mm;
  @bottom-left {{ content: "{doctitle}"; font-size: 8pt; color: #bcab97;
                 font-family: "Noto Serif CJK SC","Noto Serif CJK JP",serif; }}
  @bottom-center {{ content: "— " counter(page) " —"; font-size: 9pt; color: #9a8672;
                    font-family: "Noto Serif CJK SC","Noto Serif CJK JP",serif; }}
}}
@page :first {{ @bottom-left{{content:"";}} @bottom-center{{content:"";}} }}
html, body {{ font-size: 10.5pt; }}
body {{ font-family: "Noto Serif CJK SC","Noto Serif CJK JP","WenQuanYi Zen Hei",serif;
       color:#3a322b; line-height:1.76; text-align:left; word-spacing:0; }}
/* ---------- 封面 ---------- */
.cover {{ page-break-after: always; text-align:center; padding-top: 44mm; }}
.c-badge {{ display:inline-block; color:#a9784a; font-size:11pt; letter-spacing:6px;
           border:1px solid #D9C7B0; border-radius:18px; padding:4px 20px; }}
.c-title {{ font-size:29pt; color:#6a4f33; line-height:1.45; margin:13mm 4mm 6mm; font-weight:700; }}
.c-sub  {{ font-size:13pt; color:#7a6a58; margin:3mm 0; }}
.c-rule {{ width:56mm; margin:8mm auto; }}
.c-rule span {{ display:block; height:3px; background:#E0CDB4; margin-bottom:2px; }}
.c-rule span:last-child {{ height:1px; width:38mm; margin:0 auto; background:#C79A6B; }}
.c-meta {{ font-size:11pt; color:#9a8672; margin:2mm 0; }}
.c-feature {{ font-size:10.5pt; color:#8a7a68; margin:2mm 0 0; }}
.c-date {{ font-size:10pt; color:#b09a80; margin-top:16mm; letter-spacing:2px; }}
/* ---------- 目录 ---------- */
#TOC {{ page-break-after: always; }}
#TOC::before {{ content:"目 录"; display:block; font-size:15pt; color:#6a4f33; font-weight:700;
               text-align:center; letter-spacing:8px; margin:6mm 0 7mm; }}
#TOC > ul {{ list-style:none; padding-left:0; margin:0; }}
#TOC > ul > li {{ margin:2.6mm 0; font-size:11pt; color:#6a4f33; font-weight:700; }}
#TOC ul ul {{ list-style:none; padding-left:8mm; margin:1mm 0 2mm; }}
#TOC ul ul li {{ margin:1mm 0; font-size:9.8pt; color:#8a7a66; font-weight:400; }}
#TOC a {{ color:inherit; text-decoration:none; }}
/* ---------- 标题 ---------- */
h1 {{ font-size:15pt; color:#8a6a4a; font-weight:700; margin:8mm 0 3.4mm;
     padding-bottom:2mm; border-bottom:1px solid #EFE3D2; page-break-after:avoid; }}
h2 {{ font-size:12.6pt; color:#8a5a2a; font-weight:700; margin:5.4mm 0 2mm; page-break-after:avoid; }}
h3 {{ font-size:10.8pt; color:#7a5c3c; font-weight:700; margin:3.8mm 0 1.4mm; page-break-after:avoid; }}
p {{ margin:1.5mm 0; }}
strong {{ color:#8a5a2a; }}
/* ---------- 引用 ---------- */
blockquote {{ background:#FBF6EF; border-left:3px solid #D9C7B0; margin:2.8mm 0; padding:2.4mm 4mm;
             color:#6a5a48; font-size:9.8pt; border-radius:0 6px 6px 0; }}
blockquote p {{ margin:0.6mm 0; }}
/* ---------- 表格 ---------- */
table {{ border-collapse:collapse; width:100%; margin:2.8mm 0; font-size:8.6pt; }}
th {{ background:#F1E4D6; color:#6a4f33; font-weight:700; padding:1.9mm 2.2mm; text-align:left;
     border:1px solid #E4DAC9; }}
td {{ padding:1.7mm 2.2mm; border:1px solid #E9DFCF; color:#3a322b; line-height:1.55; }}
tr:nth-child(even) td {{ background:#FBF6EF; }}
/* ---------- 图片 ---------- */
img {{ max-width:78%; display:block; margin:2.8mm auto; border-radius:6px;
      box-shadow:0 2px 8px rgba(120,100,70,.15); }}
figure {{ margin:2mm 0; }}
figcaption {{ text-align:center; font-size:8.8pt; color:#9a8672; margin-top:1mm; }}
hr {{ border:none; border-top:1px dashed #DCCFBB; margin:4.4mm 0; }}
""")
    HTML(string=html, base_url=str(base)).write_pdf(str(out), stylesheets=[css])
    print("美化版 PDF 已生成：", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="装修方案"); ap.add_argument("--subtitle", default="")
    ap.add_argument("--meta", default=""); ap.add_argument("--feature", default="")
    ap.add_argument("--date", default=""); ap.add_argument("--doctitle", default="")
    a = ap.parse_args()
    build(a.md, a.out, a.title, a.subtitle, a.meta, a.feature, a.date, a.doctitle)
