#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""layout_check.py — 空间尺寸与规范红线校核器（专家级 S3 校验）

依据 references/10-人体工学尺度库 与 GB 50096-2011《住宅设计规范》，
输入房间净尺寸，逐项校核人体工学与规范红线，输出 ✅达标 / ⚠接近下限 / ❌不达标 清单与建议。

用法:
  python3 layout_check.py --room 主卧 --width 3.3 --depth 4.2 --bed 1.8
  python3 layout_check.py --room 厨房 --width 1.8 --depth 3.2 --layout L
  python3 layout_check.py --room 卫生间 --width 1.6 --depth 2.4
  python3 layout_check.py --room 客厅 --width 3.9 --depth 5.4 --height 2.8
  python3 layout_check.py --list
  python3 layout_check.py --json '{"room":"主卧","width":3.3,"depth":4.2,"bed":1.8}'

参数说明:
  --width  房间净宽(m)   --depth 房间净深(m)   --height 净高(m，可选)
  --bed    床宽(m，卧室用，默认 1.8)   --layout 厨房布局(一字/L/U，默认 L)
"""
import argparse, json, sys

# ---- 判据来源：references/10-人体工学尺度库 + GB 50096-2011 ----
MIN = {
    "主通道": 1.00, "次通道": 0.90, "床侧通道": 0.60, "床侧通道理想": 0.70,
    "沙发茶几": 0.30, "沙发茶几理想": 0.45, "餐椅后通道": 0.75, "衣柜前": 0.60,
    "厨房单排": 0.90, "厨房双排": 1.20, "卫浴干区过道": 0.70, "淋浴区": 0.90,
    "马桶前": 0.45, "浴室柜前": 0.60, "净高": 2.40, "操作台净长": 2.10,
}
ROOMS = ["客厅", "餐厅", "主卧", "次卧", "儿童房", "厨房", "卫生间", "阳台", "玄关", "书房"]


def _verdict(actual, need):
    if actual is None:
        return "—", "未提供该尺寸"
    if actual >= need:
        return "✅", "达标"
    if actual >= need * 0.95:
        return "⚠️", f"接近下限（差 {need-actual:.2f}m）"
    return "❌", f"不达标（差 {need-actual:.2f}m）"


def check(room, w, d, h=None, bed=1.8, layout="L"):
    rows = []  # (项目, 判据, 实测, 结论, 建议)

    def add(name, need, actual, unit="m", advice=""):
        icon, note = _verdict(actual, need)
        rows.append((name, f"≥{need}{unit}", "—" if actual is None else f"{actual:.2f}{unit}", icon + note, advice))

    # —— 通用 ——
    if h is not None:
        add("室内净高", MIN["净高"], h, "m", "GB 50096-2011；＜2.40m 不合规")

    if room in ("客厅", "餐厅"):
        add("主要通道净宽", MIN["主通道"], d, "m", "沙发/餐桌到对侧 ≥1.00m")
        add("沙发与茶几间距", MIN["沙发茶几"], 0.40 if d >= 4.0 else 0.35, "m", "经验值 0.30–0.45m")
        add("餐椅后通道", MIN["餐椅后通道"], max(w - 3.0, 0) if w > 3 else None, "m", "拉椅落座需 ≥0.75m")
    elif room in ("主卧", "次卧", "儿童房"):
        side = (w - bed) / 2
        ls = w - bed  # 床靠一侧时另一侧通道
        add(f"床侧通道(居中)", MIN["床侧通道"], side, "m",
            f"按床宽 {bed}m 居中推算；理想 ≥0.70m")
        add(f"床侧通道(靠墙)", MIN["床侧通道"], ls, "m", "床靠一侧墙时单侧通道")
        add("衣柜前操作", MIN["衣柜前"], min(d - bed - 0.05, 1.0) if d > bed else None, "m", "平开/推拉门前空间")
    elif room == "厨房":
        if layout in ("U", "双排", "二字"):
            aisle = d - 1.20
            add("双排操作间距", MIN["厨房双排"], aisle, "m", "两排台面(各0.6m)之间净距")
        else:
            aisle = d - 0.60
            add("单排操作通道", MIN["厨房单排"], aisle, "m", "台面深 0.6m 后剩余通道")
        add("操作台净长", MIN["操作台净长"], w, "m", "单排台面净长")
    elif room == "卫生间":
        add("淋浴区宽度", MIN["淋浴区"], w if w <= 1.5 else 1.0, "m", "≥0.90×0.90m")
        add("干区过道", MIN["卫浴干区过道"], max(d - 1.2, 0), "m", "洗漱区前过道")
        add("马桶前空间", MIN["马桶前"], max(w - 0.60, 0), "m", "马桶前方活动空间")
    elif room == "阳台":
        add("通行/操作净宽", MIN["次通道"], d, "m", "洗衣机位宽 ≥0.60m")
    elif room == "玄关":
        add("通行净宽", MIN["次通道"], d, "m", "鞋柜(0.35m)后剩余通道")
    elif room == "书房":
        add("通道净宽", MIN["次通道"], d, "m", "书桌/书架前空间")
    else:
        add("主要通道净宽", MIN["主通道"], d, "m", "通用判据")
    return rows


def render(room, w, d, h, rows):
    out = [f"# 空间尺寸校核：{room}（净宽 {w:.2f}m × 净深 {d:.2f}m" + (f" × 净高 {h:.2f}m" if h else "") + "）", ""]
    out.append("| 校核项 | 判据 | 实测 | 结论 | 说明 |")
    out.append("|--------|------|------|------|------|")
    for name, need, actual, verdict, advice in rows:
        out.append(f"| {name} | {need} | {actual} | {verdict} | {advice} |")
    bad = [r for r in rows if r[3].startswith("❌")]
    warn = [r for r in rows if r[3].startswith("⚠")]
    out.append("")
    if bad:
        out.append(f"**结论：❌ {len(bad)} 项不达标，须调整布局或尺寸后再定稿。**")
    elif warn:
        out.append(f"**结论：⚠️ {len(warn)} 项接近下限，建议优化。**")
    else:
        out.append("**结论：✅ 全部达标。**")
    out.append("")
    out.append("> 判据来源：references/10-人体工学尺度库、GB 50096-2011。")
    out.append("> 尺寸为按典型布置推算，实际须以实测与家具尺寸复核；未实测项标【待核】。")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="装修空间尺寸与规范校核（专家版）")
    ap.add_argument("--room", help="房间名：" + "/".join(ROOMS))
    ap.add_argument("--width", type=float, help="净宽 m")
    ap.add_argument("--depth", type=float, help="净深 m")
    ap.add_argument("--height", type=float, default=None, help="净高 m")
    ap.add_argument("--bed", type=float, default=1.8, help="床宽 m（卧室）")
    ap.add_argument("--layout", default="L", help="厨房布局：一字/L/U")
    ap.add_argument("--json", help="直接传入 JSON")
    ap.add_argument("--list", action="store_true", help="列出支持房间与判据")
    args = ap.parse_args()

    if args.list:
        print("支持房间：" + "、".join(ROOMS))
        print("\n判据速览（详见 references/10）：")
        for k, v in MIN.items():
            print(f"  {k}: ≥{v}m")
        return

    if args.json:
        p = json.loads(args.json)
        room, w, d = p["room"], float(p["width"]), float(p["depth"])
        h = p.get("height"); bed = float(p.get("bed", 1.8)); layout = p.get("layout", "L")
    else:
        if not args.room or args.width is None or args.depth is None:
            ap.print_help(); sys.exit(2)
        room, w, d, h, bed, layout = args.room, args.width, args.depth, args.height, args.bed, args.layout

    rows = check(room, w, d, h, bed, layout)
    print(render(room, w, d, h, rows))
    sys.exit(1 if any(r[3].startswith("❌") for r in rows) else 0)


if __name__ == "__main__":
    main()
