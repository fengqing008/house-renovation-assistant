#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""consistency_check.py — 方案 / 预算 / 效果图 一致性核对

交付前三向交叉核对，防止"方案说奶油风、效果图出工业风""方案 120㎡、预算按 90㎡算"等不一致：

  ① 风格一致性：方案风格 vs 效果图文件/提示词风格
  ② 面积一致性：方案面积 vs 预算面积
  ③ 金额规范：千分位、三档齐全、估算声明
  ④ 效果图齐套：必出空间是否有图 + 是否含"仅示意"声明
  ⑤ 数据溯源：【待核】标注是否说明依据

用法:
  python3 consistency_check.py --plan 方案.md --budget 预算.md --renders renders/
  python3 consistency_check.py --plan 方案.md --renders renders/ --json out.json
退出码：0 全过；1 存在不一致项。
"""
import argparse, glob, json, os, re, sys

STYLES = ["现代简约", "奶油风", "新中式", "日式原木", "侘寂", "工业风", "法式轻奢", "北欧",
          "中古风", "原木极简", "法式田园", "美式复古"]
REQUIRED_ROOMS = ["客厅", "主卧", "厨房"]


def read(path):
    if not path or not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def find_styles(text):
    return [s for s in STYLES if s in text]


def find_area(text):
    m = re.findall(r"(\d+(?:\.\d+)?)\s*(?:㎡|平米|平方米|m2|平)", text)
    return [float(x) for x in m if 30 <= float(x) <= 800]


def main():
    ap = argparse.ArgumentParser(description="方案/预算/效果图一致性核对")
    ap.add_argument("--plan", help="方案 Markdown/pdf 文本")
    ap.add_argument("--budget", help="预算 Markdown/JSON 文本")
    ap.add_argument("--renders", help="效果图目录")
    ap.add_argument("--json", help="报告 JSON 落盘")
    args = ap.parse_args()

    plan, budget = read(args.plan), read(args.budget)
    issues, checks = [], []

    # ① 风格一致
    ps, bs = find_styles(plan), find_styles(budget)
    render_names = []
    if args.renders and os.path.isdir(args.renders):
        render_names = [os.path.basename(p) for p in
                        glob.glob(os.path.join(args.renders, "*")) if os.path.isfile(p)]
    rs = set()
    for n in render_names:
        for s in STYLES:
            if s in n:
                rs.add(s)
    if ps and rs and not (set(ps) & rs):
        issues.append(f"风格不一致：方案={ps}，效果图文件名={sorted(rs)}")
    checks.append(("风格一致（方案×效果图）", "✅" if not (ps and rs) or (set(ps) & rs) else "❌"))

    # ② 面积一致
    pa, ba = find_area(plan), find_area(budget)
    if pa and ba:
        common = set(round(x) for x in pa) & set(round(x) for x in ba)
        checks.append(("面积一致（方案×预算）", "✅" if common else "❌"))
        if not common:
            issues.append(f"面积不一致：方案={sorted(set(pa))}，预算={sorted(set(ba))}")
    else:
        checks.append(("面积一致（方案×预算）", "⚠️ 数据不足"))

    # ③ 金额规范（预算）
    if budget:
        raw = [a for a in re.findall(r"(?<![\d,.])(\d{5,})(?![\d,])", budget) if "," not in a]
        ok_fmt = not raw
        checks.append(("金额千分位", "✅" if ok_fmt else "❌"))
        if raw:
            issues.append(f"预算存在未千分位金额：{'、'.join(sorted(set(raw))[:5])}")
        tiers = sum(1 for t in ["经济型", "舒适型", "轻奢型"] if t in budget)
        checks.append(("三档齐全", "✅" if tiers >= 3 else ("⚠️" if tiers else "—")))
        if tiers and tiers < 3:
            issues.append(f"预算仅 {tiers} 档，应含三档（FM-01）")

    # ④ 效果图齐套与声明
    if render_names:
        missing = [r for r in REQUIRED_ROOMS if not any(r in n for n in render_names)]
        checks.append(("效果图必出空间", "✅" if not missing else "❌"))
        if missing:
            issues.append(f"效果图缺必出空间：{missing}")
        has_decl = ("仅示意" in plan) or ("仅示意" in budget) or any("仅示意" in n for n in render_names)
        checks.append(("效果图仅示意声明", "✅" if has_decl else "❌"))
        if not has_decl:
            issues.append("未见效果图『仅示意』声明（FM-03）")
    else:
        checks.append(("效果图齐套", "— 未提供 renders/"))

    # ⑤ 【待核】依据
    if "【待核" in (plan + budget):
        checks.append(("【待核】标注", "⚠️ 见正文（须说明依据）"))

    print("=== 一致性核对报告 ===")
    print("| 核对项 | 结论 |")
    print("|--------|------|")
    for name, v in checks:
        print(f"| {name} | {v} |")
    if issues:
        print(f"\n❌ 不一致项（{len(issues)}）：")
        for x in issues:
            print("  - " + x)
    else:
        print("\n✅ 未发现不一致项")
    print(f"\n结论：{'存在不一致，处理后交付' if issues else '通过'}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"checks": checks, "issues": issues}, f, ensure_ascii=False, indent=2)
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
