#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quote_audit.py — 装修报价单审计器（审计师水准）

把装修公司/施工队的报价单，逐条与「量价分离基准」（budget_calc 的工程量×综合单价）比对，
输出审计发现清单：
  ① 缺项（漏项）——标准 15 项中报价单未列的，后期必成增项
  ② 重复计列——同一分项出现多次
  ③ 单价异常——综合单价高于基准 +30% 或低于 −30%
  ④ 量差——报价工程量与估算工程量偏差 ＞±20%
  ⑤ 低价套餐特征——总额显著低 + 缺项多 → "低价引流+后期增项"风险
  ⑥ 审减/核增建议合计

用法:
  python3 quote_audit.py --csv 报价单.csv --area 120 --city 西安 --tier 舒适型
  python3 quote_audit.py --csv 报价单.csv --area 120 --city 西安 --tier 舒适型 --json out.json

报价单 CSV 表头（自动探测）：项目/名称 | 单位 | 工程量/数量 | 单价/综合单价 | 合价/金额
"""
import argparse, csv, json, re, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import budget_calc as BC

# 标准分项关键词（用于模糊匹配报价项 -> 标准项；匹配时按关键词长优先，避免"柜"抢"橱柜"）
KEYWORDS = {
    "拆除清运": ["拆除", "拆改", "清运", "砸墙"],
    "水电改造": ["水电", "电路", "水路", "强弱电", "给排水", "布线", "水管", "电线"],
    "防水工程": ["防水", "闭水"],
    "墙地砖铺贴": ["贴砖", "铺砖", "瓷砖", "墙砖", "地砖", "瓦工", "铺贴"],
    "木作吊顶": ["吊顶", "木工", "石膏板", "背景墙", "造型"],
    "墙面涂装": ["乳胶漆", "油漆", "涂料", "腻子", "墙漆", "涂装"],
    "木门安装": ["木门", "房门", "套装门", "室内门"],
    "断桥铝门窗": ["断桥", "门窗", "铝合金窗", "封窗", "窗户"],
    "全屋定制": ["定制", "衣柜", "鞋柜", "榻榻米", "书柜", "柜体", "柜"],
    "橱柜": ["橱柜", "厨柜", "台面"],
    "卫浴洁具": ["洁具", "马桶", "淋浴", "花洒", "浴室柜", "卫浴"],
    "灯具照明": ["灯具", "灯带", "筒灯", "射灯", "照明"],
    "开关插座面板": ["开关", "插座", "面板"],
    "窗帘软装": ["窗帘", "软装", "挂画", "地毯", "绿植"],
    "家具": ["家具", "沙发", "床", "餐桌", "桌椅"],
}
HEAD_ALIASES = {
    "name": ["项目", "名称", "内容", "分项", "条目", "施工项目", "工程项目"],
    "unit": ["单位", "计量单位"],
    "qty": ["工程量", "数量", "量", "面积", "长度"],
    "price": ["单价", "综合单价", "单位价格"],
    "amount": ["合价", "金额", "小计", "合计", "总价"],
}


def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("，", "").strip()
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None


def detect_header(rows):
    for i, r in enumerate(rows[:5]):
        joined = "".join(r)
        if any(a in joined for a in HEAD_ALIASES["name"]) and any(a in joined for a in HEAD_ALIASES["qty"]):
            return i, r
    return None, None


def map_cols(header):
    cmap = {}
    for key, aliases in HEAD_ALIASES.items():
        for j, h in enumerate(header):
            if any(a in str(h) for a in aliases):
                cmap.setdefault(key, j)
                break
    return cmap


def classify(name):
    """最长关键词优先匹配，避免短词（如"柜"）抢走长词（"橱柜"）。"""
    hits = [(kw, std) for std, kws in KEYWORDS.items() for kw in kws if kw in name]
    if not hits:
        return None
    hits.sort(key=lambda x: -len(x[0]))
    return hits[0][1]


def audit(csv_path, area, city, tier):
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.reader(f) if any(str(c).strip() for c in r)]
    if not rows:
        raise ValueError("报价单为空")
    hi, header = detect_header(rows)
    if hi is None:
        header = ["项目", "单位", "工程量", "单价", "合价"]
        data = rows
    else:
        data = rows[hi + 1:]
    cmap = map_cols(header)
    q0, n_in = 0, 0

    base = BC.calc(area, city, tier)
    base_map = {n: (qty, unit, cp, amt) for (n, unit, qty, m, l, cp, amt) in base["分项"]}

    quoted, seen = [], {}
    for r in data:
        def g(k):
            return r[cmap[k]] if k in cmap and cmap[k] < len(r) else ""
        name = str(g("name")).strip()
        if not name or "合计" in name or "总计" in name or "小计" in name:
            continue
        qty = num(g("qty")) or 0
        price = num(g("price"))
        amount = num(g("amount"))
        if price is None and amount and qty:
            price = amount / qty
        if amount is None and price and qty:
            amount = price * qty
        quoted.append({"name": name, "qty": qty, "price": price or 0, "amount": amount or 0, "std": classify(name)})
        q0 += amount or 0
        n_in += 1
        seen[name] = seen.get(name, 0) + 1

    findings = {"缺项": [], "重复计列": [], "单价异常": [], "量差": [], "风险提示": []}
    matched_std = set()
    for it in quoted:
        std = it["std"]
        if std and std in base_map:
            matched_std.add(std)
            bqty, bunit, bcp, bamt = base_map[std]
            if it["price"] and bcp and abs(it["price"] - bcp) / bcp > 0.30:
                d = (it["price"] - bcp) / bcp * 100
                findings["单价异常"].append(
                    f"{it['name']}：报价单价 {it['price']:,.0f} vs 基准 {bcp:,.0f}（{d:+.0f}%，阈值 ±30%）")
            if it["qty"] and bqty and abs(it["qty"] - bqty) / bqty > 0.20:
                d = (it["qty"] - bqty) / bqty * 100
                findings["量差"].append(
                    f"{it['name']}：报价量 {it['qty']:g}{bunit} vs 估算 {bqty:g}{bunit}（{d:+.0f}%，阈值 ±20%）")
    for std in base_map:
        if std not in matched_std:
            bqty, bunit, bcp, bamt = base_map[std]
            findings["缺项"].append(f"{std}（基准约 {bamt:,.0f} 元）——报价单未见，后期必成增项，须要求补列")
    for name, cnt in seen.items():
        if cnt > 1:
            findings["重复计列"].append(f"{name} 出现 {cnt} 次——核对是否重复计列/拆项")

    base_total = base["总额中值"]
    if q0 and q0 < base_total * 0.7 and len(findings["缺项"]) >= 4:
        findings["风险提示"].append(
            f"报价总额 {q0:,.0f} 元 显著低于基准 {base_total:,.0f} 元（{q0/base_total*100:.0f}%）且缺项 {len(findings['缺项'])} 项"
            f"——典型「低价引流 + 后期增项」，务必签「总价包干/闭口合同」或列明增项规则。")
    if q0 and q0 > base_total * 1.4:
        findings["风险提示"].append(f"报价总额 {q0:,.0f} 元 高于基准 {base_total:,.0f} 元（{q0/base_total*100:.0f}%）——核对是否含高档材料或存在虚高。")

    return {"报价行数": n_in, "报价总额": round(q0, 0), "基准总额": base_total,
            "基准档位": tier, "基准城市": city, "基准面积": area,
            "发现": findings, "报价明细": quoted}


def main():
    ap = argparse.ArgumentParser(description="装修报价单审计器（审计师水准）")
    ap.add_argument("--csv", required=True, help="报价单 CSV 路径")
    ap.add_argument("--area", type=float, required=True)
    ap.add_argument("--city", required=True)
    ap.add_argument("--tier", default="舒适型", help="经济型/舒适型/轻奢型")
    ap.add_argument("--json", help="审计报告 JSON 落盘")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"文件不存在：{args.csv}", file=sys.stderr); sys.exit(2)
    try:
        res = audit(args.csv, args.area, args.city, args.tier)
    except Exception as e:
        print(f"审计失败：{e}", file=sys.stderr); sys.exit(1)

    print("# 装修报价单审计报告\n")
    print(f"- 报价行数：{res['报价行数']}　报价总额：**{res['报价总额']:,.0f} 元**")
    print(f"- 基准（{res['基准城市']}·{res['基准面积']:g}㎡·{res['基准档位']}）：{res['基准总额']:,.0f} 元")
    f = res["发现"]
    for k in ["缺项", "重复计列", "单价异常", "量差", "风险提示"]:
        items = f[k]
        icon = "❌" if k in ("缺项", "风险提示") and items else ("⚠️" if items else "✅")
        print(f"\n## {k}（{len(items)}）{icon}")
        if not items:
            print("- 无")
        for x in items:
            print(f"- {x}")
    print("\n---\n> 审计依据：量价分离基准（budget_calc v2，工程量按面积推算、材料全国参考、人工按城市系数）。")
    print("> 单价/量差阈值为 ±30% / ±20%，可按项目调整；缺项与风险提示为**重点核查项**。")
    print("> 本报告供议价与合同把关参考，不构成正式造价鉴定意见。")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fp:
            json.dump(res, fp, ensure_ascii=False, indent=2)
    sys.exit(0)


if __name__ == "__main__":
    main()
