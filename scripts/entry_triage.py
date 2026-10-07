#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""entry_triage.py — 装修技能入口三选项分诊 + 小区户型图检索词 / 面积核验

用法:
  python3 entry_triage.py --gen                                # 打印三选项询问卡
  python3 entry_triage.py --gen --out card.md                  # 写入文件
  python3 entry_triage.py --parse "1"                          # 解析选择，输出分支与下一步
  python3 entry_triage.py --search-query --community 万象春天 --building 3号楼 --area 118
  python3 entry_triage.py --verify --stated 118 --found 120    # 面积交叉核对（±5%）
"""
import argparse

TOL = 0.05  # 面积匹配容差 ±5%

CARD = """请先告诉我你属于哪种情况（回复 **1 / 2 / 3** 即可）：

**1️⃣ 我有小区信息**
   请提供：**小区名称 + 楼栋号 + 建筑面积（㎡）**
   → 我会全网检索该小区该栋的公开户型图，基于真实户型做设计
   例：万象春天 3号楼 118㎡

**2️⃣ 我有户型图 / 设计图**
   直接把图发我（照片 / 截图 / PDF 均可）
   → 我识别图纸后基于原图做设计

**3️⃣ 其他情况**（说不准 / 暂无图 / 只想要个大概）
   → 我一步步问你（面积、几室几厅、风格偏好…），边问边出方案
"""

BRANCH = {
    "1": ("A · 小区户型图全网检索", [
        "校验必填项：小区名称 / 楼栋号 / 建筑面积（缺任一项先问齐）",
        "跑 `--search-query` 生成三档检索词",
        "按 references/19 §A2 来源优先级检索（search 文字+图片，必要时 agent-reach）",
        "命中后跑 `--verify` 做面积交叉核对（±5%）",
        "匹配 → 写入房屋现状档案，标『来源：公开检索，以实际测绘为准』→ 进 S2",
        "不匹配 → 列候选让用户指认；全未命中 → 降级路径 C（FM-15）",
    ]),
    "2": ("B · 上传图识别设计", [
        "收到图后用 `fetch` 读取（照片/截图/PDF）",
        "提取：面积 / 房间构成 / 开间进深 / 承重墙 / 朝向 / 门窗",
        "图模糊不可识别 → 请补传或转路径 C（FM-07）",
        "写入房屋现状档案 → 进 S2",
    ]),
    "3": ("C · 逐步询问", [
        "第一轮：补齐关键约束（面积 / 城市 / 范围），见『需求澄清』五维表",
        "第二轮：跑 questionnaire.py 出 12 题风格问卷",
        "无图 → 房间清单 + 估算面积，尺寸标【待核】",
        "边问边出，每轮给阶段小结 → 进 S2",
    ]),
}


def gen_card(out=None):
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(CARD + "\n")
        print(f"询问卡已写入 {out}")
    else:
        print(CARD)


def parse_choice(choice):
    c = (choice or "").strip()
    if c in ("1", "一") or "小区" in c or "楼栋" in c:
        key = "1"
    elif c in ("2", "二") or c.startswith("2") or "户型图" in c or "设计图" in c:
        key = "2"
    else:
        key = "3"
    name, steps = BRANCH[key]
    lines = [f"# 入口分诊结果：路径 {key} — {name}", ""]
    if key == "1":
        lines += ["**请补齐三项必填信息**：小区名称、楼栋号、建筑面积（㎡）。缺任一项先问齐。", ""]
    elif key == "2":
        lines += ["**请把户型图 / 设计图发给我**（照片 / 截图 / PDF 均可）。", ""]
    lines.append("**下一步动作**：")
    lines += [f"{i}. {s}" for i, s in enumerate(steps, 1)]
    return "\n".join(lines)


def search_query(community, building, area):
    c = community or "{小区名}"
    b = building or "{楼栋号}"
    a = area or "{面积}"
    tiers = {
        "精（逐栋 / 逐面积）": [
            f"{c} {b} 户型图",
            f"{c} {a}㎡ 户型",
            f"{c} {b} 平面图",
            f"{c} {a}㎡ 户型图",
        ],
        "中（小区级）": [
            f"{c} 户型图",
            f"{c} 户型 面积",
            f"{c} 在售 户型",
        ],
        "宽（片区 / 期数）": [
            f"{c} 楼盘 户型",
            f"{c} 一期 户型",
            f"{c} 二手房 户型图",
        ],
    }
    out = [f"# 小区户型图检索词：{c} / {b} / {a}㎡", ""]
    for tier, qs in tiers.items():
        out.append(f"## {tier}")
        out += [f"- `{q}`" for q in qs]
        out.append("")
    out.append("> 检索工具：`search`（format=text 找挂牌页/图文，format=image 找户型图本体）；"
               "必要时经 `agent-reach` 抓贝壳/安居客/小红书。命中后跑 `--verify` 核面积。")
    return "\n".join(out)


def verify(stated, found):
    try:
        s, f = float(stated), float(found)
    except (TypeError, ValueError):
        return "❌ 面积解析失败：请提供数字（如 --stated 118 --found 120）"
    if s <= 0 or f <= 0:
        return "❌ 面积须为正数。"
    diff = abs(f - s) / s
    if diff <= TOL:
        verdict = "✅ 匹配（差值 ≤±5%）：可采用此户型图，写入房屋现状档案（标『以实际测绘为准』）。"
    elif diff <= 0.10:
        verdict = "⚠️ 接近（±5%~±10%）：可能为相邻户型，建议人工确认后再用，或列候选让用户指认。"
    else:
        verdict = "❌ 不符（>±10%）：大概率非本户型，不得作为设计依据；列候选或降级路径 C（FM-16）。"
    return (f"# 面积交叉核对\n\n"
            f"- 用户提供面积：{s:g}㎡\n"
            f"- 检索到图中面积：{f:g}㎡\n"
            f"- 偏差：{diff*100:.1f}%\n"
            f"- 结论：{verdict}")


def main():
    ap = argparse.ArgumentParser(description="装修入口分诊与小区户型图检索")
    ap.add_argument("--gen", action="store_true", help="生成三选项询问卡")
    ap.add_argument("--out", help="写入文件")
    ap.add_argument("--parse", help="解析用户选择（1/2/3 或关键词）")
    ap.add_argument("--search-query", action="store_true", help="生成小区户型检索词")
    ap.add_argument("--community", help="小区名称")
    ap.add_argument("--building", help="楼栋号")
    ap.add_argument("--area", help="建筑面积（㎡）")
    ap.add_argument("--verify", action="store_true", help="面积交叉核对")
    ap.add_argument("--stated", help="用户提供面积")
    ap.add_argument("--found", help="检索到图中面积")
    args = ap.parse_args()

    if args.gen:
        gen_card(args.out); return
    if args.parse:
        print(parse_choice(args.parse)); return
    if args.search_query:
        print(search_query(args.community, args.building, args.area)); return
    if args.verify:
        print(verify(args.stated, args.found)); return
    ap.print_help()


if __name__ == "__main__":
    main()
