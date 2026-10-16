#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""renovation_check.py — 装修方案交付前自检

用法:
  python3 renovation_check.py --input 装修方案.md
  cat 方案.md | python3 renovation_check.py --stdin

检查项依据 references/08-失败模式与降级.md：
  FM-08 金额千分位 / FM-03 效果图声明 / FM-05 环保等级 / FM-02 结构安全 /
  报价承诺提示 / 【待核】标注 / 三档差异 / 工序逻辑
"""
import argparse, re, sys


def check(text: str):
    issues, tips = [], []

    # FM-08 金额千分位：出现 5-6 位以上连续数字且非千分位，疑似金额
    raw_amounts = re.findall(r"(?<![\d,.])(\d{5,})(?![\d,])", text)
    raw_amounts = [a for a in raw_amounts if "," not in a]
    if raw_amounts:
        issues.append(f"[FM-08] 疑似未千分位的金额：{'、'.join(sorted(set(raw_amounts))[:6])}（应规范为千分位，如 128,000）")

    # FM-03 效果图声明
    if ("效果图" in text or "渲染图" in text) and not re.search(r"仅(作)?示意|仅示意|示意.{0,6}氛围|不是.{0,6}施工依据|以.{0,6}施工图为准", text):
        issues.append("[FM-03] 含效果图但未见“仅示意/以施工图为准”声明，须补图注")

    # FM-05 环保等级
    if ("板材" in text or "定制" in text) and not re.search(r"E1|E0|ENF|18580", text, re.I):
        issues.append("[FM-05] 涉及板材但未写明环保等级（E1/E0/ENF，依据 GB 18580-2017）")

    # FM-02 结构安全
    if re.search(r"拆(除)?(承重墙|剪力墙|梁|柱)|打通承重", text):
        if not re.search(r"报备|非承重|禁止|不得|核实结构", text):
            issues.append("[FM-02] 疑似涉及承重结构拆改且无安全提示，须拦截并提示报备（建设部令第110号）")

    # 报价承诺
    if re.search(r"(保证|承诺|确定).{0,8}(最低价|不超|一定|绝不加价)", text) and "以合同为准" not in text:
        issues.append("[红线] 出现绝对价格承诺，须改为区间并附“以实际合同为准”")

    # 【待核】
    if re.search(r"【待核", text):
        tips.append("含【待核】项：交付前请确认已高亮标注并说明取值依据")

    # 三档差异
    tiers = sum(1 for t in ["经济型", "舒适型", "轻奢型"] if t in text)
    if 0 < tiers < 3 and "预算" in text:
        tips.append(f"[FM-01] 仅检索到 {tiers} 个档位，若为完整预算应含经济型/舒适型/轻奢型三档")

    # 工序逻辑
    if "水电" in text and "油漆" in text:
        if text.find("油漆") < text.find("水电") and "工序" in text:
            issues.append("[FM-10] 工序疑似倒置（油漆出现在水电之前），请按 05 工序逻辑核对")

    # v2：量价分离特征
    if "预算" in text and ("综合单价" not in text and "工程量" not in text):
        tips.append("[v2] 预算未见「工程量×综合单价」量价分离清单，建议用 budget_calc.py 生成可逐项核价的清单")

    # v2：效果图高清
    if ("效果图" in text or "渲染图" in text) and not re.search(r"放大|4x|4×|高清|upscale|质检", text, re.I):
        tips.append("[v2] 效果图未见高清/放大说明，建议走 upscale_bridge.py 4× 放大 + render_check.py 质检（FM-13）")

    # v2：报价审计
    if ("报价单" in text or "报价" in text) and not re.search(r"审计|quote_audit|核价|缺项|量差", text):
        tips.append("[v2] 涉及报价但未见审计/核价，建议跑 quote_audit.py 查缺项/重复/单价异常/量差（FM-11/12）")

    return issues, tips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="待检查文件路径")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读取")
    args = ap.parse_args()

    if args.stdin:
        text = sys.stdin.read()
        name = "<stdin>"
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
        name = args.input
    else:
        ap.print_help()
        return

    issues, tips = check(text)
    print(f"=== 装修方案自检：{name} ===")
    if issues:
        print(f"\n❌ 需修正（{len(issues)}）：")
        for i in issues:
            print("  - " + i)
    else:
        print("\n✅ 无阻断性问题")
    if tips:
        print(f"\n⚠️ 提示（{len(tips)}）：")
        for t in tips:
            print("  - " + t)
    print(f"\n结论：{'存在需修正项，请处理后交付' if issues else '通过（提示项请人工复核）'}")
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
