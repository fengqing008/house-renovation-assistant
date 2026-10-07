#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""budget_calc.py — 装修费用预算测算（v2 · 量价分离「结算式」模型）

核心升级（v1 单方×系数×固定占比 → v2 量价分离）：
  - 工程量估算：按建筑面积推算各分部分项工程量（地面/墙面/顶面/点位/柜体/门窗…）
  - 综合单价拆分：每项 = 材料单价 + 人工单价，三档差异体现在**材料档次与单价**，非只改系数
  - 地区校准：**材料价不乘系数，人工费乘城市系数**（符合实际：材料全国接近，人工地区差 2–3 倍）
  - 输出「结算式」清单：序号 | 分部分项 | 工程量 | 单位 | 材料单价 | 人工单价 | 综合单价 | 合价
    → 可逐项核价、可与装修公司报价单逐条对照（配合 quote_audit.py）

口径见 references/04-预算测算口径.md、references/16-报价审计要点.md。
金额千分位输出，标注为估算区间。

用法:
  python3 budget_calc.py --area 120 --city 西安 --tier 舒适型
  python3 budget_calc.py --area 120 --city 西安 --tier all --json
"""
import argparse, json

CITY_LEVEL = {"一线": 2.0, "新一线": 1.45, "二线": 1.1, "三四线": 0.8}
CITY_MAP = {
    "北京": "一线", "上海": "一线", "广州": "一线", "深圳": "一线",
    "成都": "新一线", "重庆": "新一线", "杭州": "新一线", "武汉": "新一线", "苏州": "新一线",
    "西安": "新一线", "南京": "新一线", "长沙": "新一线", "郑州": "新一线", "天津": "新一线",
    "合肥": "新一线", "青岛": "新一线", "东莞": "新一线", "宁波": "新一线", "佛山": "新一线",
    "沈阳": "二线", "昆明": "二线", "无锡": "二线", "厦门": "二线", "福州": "二线", "济南": "二线",
    "大连": "二线", "哈尔滨": "二线", "长春": "二线", "石家庄": "二线", "南昌": "二线", "贵阳": "二线",
    "南宁": "二线", "太原": "二线", "兰州": "二线", "乌鲁木齐": "二线", "海口": "二线", "珠海": "二线",
    "惠州": "二线", "中山": "二线", "温州": "二线", "绍兴": "二线", "嘉兴": "二线", "常州": "二线",
    "南通": "二线", "徐州": "二线", "泉州": "二线", "烟台": "二线", "潍坊": "二线", "唐山": "二线",
    "洛阳": "二线", "襄阳": "二线", "宜昌": "二线", "金华": "二线", "台州": "二线", "廊坊": "二线",
    "保定": "二线", "汕头": "二线", "湛江": "二线", "漳州": "二线", "荆州": "二线", "黄石": "二线",
    "恩施": "三四线", "利川": "三四线", "临潼": "三四线", "仙桃": "三四线", "天门": "三四线",
    "潜江": "三四线", "漳浦": "三四线", "汉川": "三四线", "应城": "三四线", "安陆": "三四线",
    "咸宁": "三四线", "十堰": "三四线", "荆门": "三四线", "孝感": "三四线", "黄冈": "三四线",
    "随州": "三四线", "鄂州": "三四线", "云梦": "三四线", "大悟": "三四线", "远安": "三四线",
}

# 分部分项：(名称, 单位, 工程量key, 经济(材料,人工), 舒适(材料,人工), 轻奢(材料,人工))
# 单价为全国参考（元/单位）；材料不乘城市系数、人工乘。单方结果（舒适型·新一线）约 2,200–2,900 元/㎡（含家具软装）。
ITEMS = [
    ("拆除清运", "㎡", "ground", (30, 25), (45, 40), (65, 60)),
    ("水电改造", "点位", "points", (110, 70), (150, 95), (220, 140)),
    ("防水工程", "㎡", "wet", (35, 25), (50, 40), (75, 55)),
    ("墙地砖铺贴", "㎡", "tile", (80, 70), (150, 80), (280, 110)),
    ("木作吊顶", "㎡", "ceiling", (65, 45), (100, 65), (170, 100)),
    ("墙面涂装", "㎡", "wall", (20, 16), (36, 26), (62, 44)),
    ("木门安装", "樘", "doors", (650, 450), (1200, 700), (2400, 1000)),
    ("断桥铝门窗", "㎡", "window", (300, 160), (480, 250), (880, 400)),
    ("全屋定制", "㎡", "custom", (400, 220), (650, 320), (1200, 560)),
    ("橱柜", "延米", "cabinet", (800, 500), (1500, 850), (2800, 1400)),
    ("卫浴洁具", "间", "bath", (1500, 1000), (3200, 1800), (7000, 3500)),
    ("灯具照明", "㎡", "ground", (25, 18), (50, 35), (100, 60)),
    ("开关插座面板", "点位", "points", (15, 10), (25, 16), (45, 28)),
    ("窗帘软装", "㎡", "ground", (50, 35), (100, 65), (200, 120)),
    ("家具", "㎡", "ground", (120, 80), (200, 130), (420, 260)),
]
SEP = {"经济型": 3, "舒适型": 4, "轻奢型": 5}
MGMT = {"经济型": 0.06, "舒适型": 0.09, "轻奢型": 0.12}
TIER_ALIAS = {"经济": "经济型", "舒适": "舒适型", "轻奢": "轻奢型"}


def quantities(area: float) -> dict:
    """工程量估算口径（套内率 0.85；全屋定制按 0.35 投影系数）"""
    g = area * 0.85
    return {
        "ground": round(g, 1),
        "wall": round(g * 2.6, 1),
        "ceiling": round(area * 0.5, 1),
        "tile": round(g + area * 0.45, 1),
        "wet": round(area * 0.12, 1),
        "points": round(area * 0.8),
        "doors": max(3, round(area / 22)),
        "window": round(area * 0.12, 1),
        "custom": round(area * 0.35, 1),
        "cabinet": 4,
        "bath": max(1, round(area / 60)),
    }


def resolve_city(city: str) -> float:
    city = city.strip()
    if city in CITY_LEVEL:
        return CITY_LEVEL[city]
    if city in CITY_MAP:
        return CITY_LEVEL[CITY_MAP[city]]
    return 1.0


def calc(area: float, city: str, tier: str) -> dict:
    coef = resolve_city(city)
    idx = SEP[tier]
    q = quantities(area)
    rows, mat_total, lab_total = [], 0.0, 0.0
    for name, unit, key, *prices in ITEMS:
        m, l = prices[idx - 3]
        qty = q[key]
        mat, lab = m * qty, l * qty * coef
        rows.append((name, unit, qty, m, round(l * coef, 1), round(m + l * coef, 1), round(mat + lab, 0)))
        mat_total += mat
        lab_total += lab
    subtotal = mat_total + lab_total
    mgmt = subtotal * MGMT[tier]
    total = subtotal + mgmt
    lo, hi = total * 0.9, total * 1.15
    return {
        "面积": area, "城市": city, "档位": tier, "人工系数": coef,
        "工程量": q, "分项": rows,
        "材料费": round(mat_total, 0), "人工费": round(lab_total, 0),
        "直接费": round(subtotal, 0), "管理费税金": round(mgmt, 0),
        "总额中值": round(total, 0), "总额区间": (round(lo, 0), round(hi, 0)),
        "单方造价中值": round(total / area, 0), "单方区间": (round(lo / area, 0), round(hi / area, 0)),
        "未识别城市": city.strip() not in CITY_MAP and city.strip() not in CITY_LEVEL,
    }


def fmt(x):
    return f"{x:,.0f}"


def render(r: dict) -> str:
    L = [f"### {r['档位']}（{r['城市']} · {r['面积']:g}㎡ · 人工系数 {r['人工系数']}）"]
    L.append(f"- 单方造价：{fmt(r['单方区间'][0])}–{fmt(r['单方区间'][1])} 元/㎡（中值 {fmt(r['单方造价中值'])}）")
    L.append(f"- 总额区间：**{fmt(r['总额区间'][0])}–{fmt(r['总额区间'][1])} 元**（中值 {fmt(r['总额中值'])} 元）")
    L.append(f"- 费用构成：材料费 {fmt(r['材料费'])} ＋ 人工费 {fmt(r['人工费'])} ＝ 直接费 {fmt(r['直接费'])}；管理费及税金 {fmt(r['管理费税金'])}")
    L.append("")
    L.append("| 序号 | 分部分项 | 工程量 | 单位 | 材料单价 | 人工单价 | 综合单价 | 合价(元) |")
    L.append("|-----:|----------|-------:|:----:|--------:|--------:|--------:|--------:|")
    for i, (n, u, qty, m, l, cp, amt) in enumerate(r["分项"], 1):
        L.append(f"| {i} | {n} | {qty} | {u} | {fmt(m)} | {fmt(l)} | {fmt(cp)} | {fmt(amt)} |")
    L.append(f"| — | **合计（直接费）** | — | — | — | — | — | **{fmt(r['直接费'])}** |")
    if r["未识别城市"]:
        L.append("")
        L.append(f"> ⚠️ 城市「{r['城市']}」未识别，按新一线人工基准估算，落地须按当地当季信息价校准【待核】。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="装修预算测算（量价分离 v2）")
    ap.add_argument("--area", type=float, required=True)
    ap.add_argument("--city", required=True)
    ap.add_argument("--tier", default="all", help="经济型/舒适型/轻奢型/all")
    ap.add_argument("--json", action="store_true", help="输出 JSON（供报价审计/一致性核对）")
    args = ap.parse_args()

    t = TIER_ALIAS.get(args.tier.strip(), args.tier.strip())
    tiers = list(SEP.keys()) if t == "all" else [t]
    if t != "all" and t not in SEP:
        print(f"未知档位：{args.tier}"); return

    if args.json:
        print(json.dumps({tt: calc(args.area, args.city, tt) for tt in tiers}, ensure_ascii=False, indent=2))
        return

    print(f"# 装修费用预算估算（量价分离 · {args.city} · {args.area:g}㎡）\n")
    for tt in tiers:
        print(render(calc(args.area, args.city, tt)))
        print()
    print("---")
    print("> 本预算为**估算区间**，非报价承诺；最终以实际合同与当地当季信息价为准。")
    print("> 量价分离：工程量按建筑面积推算（口径见 references/04 第一节），材料价全国参考、人工费按城市系数校准，可逐项核价。")
    print("> 易超支项：水电改造（预留 10%–20%）、全屋定制、主材升级；建议另预留总额 5%–10% 不可预见费。")
    print("> 审计用途：将本清单与装修公司报价单逐条对照 → 运行 `quote_audit.py` 查缺项/重复/单价异常/量差。")


if __name__ == "__main__":
    main()
