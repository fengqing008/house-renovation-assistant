#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""questionnaire.py — 生成装修需求问卷 / 按作答判定风格

用法:
  python3 questionnaire.py --gen                    # 打印问卷（Markdown）
  python3 questionnaire.py --gen --out q.md         # 写入文件
  python3 questionnaire.py --answer "1:C 2:西安 3:A 4:A 5:B 6:B 7:B 8:B 9:B 10:B 11:B 12:B"
"""
import argparse, json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_match import judge, format_report  # noqa: E402

QUESTIONS = [
    ("1", "房屋建筑面积", {"A": "≤70㎡", "B": "70-110㎡", "C": "110-150㎡", "D": "＞150㎡"}),
    ("2", "所在城市", {"__fill__": "填写城市名（如：西安），或填 一线/新一线/二线/三四线"}),
    ("3", "装修范围", {"A": "全屋整装", "B": "硬装+定制", "C": "仅软装焕新", "D": "局部改造（厨房/卫生间）"}),
    ("4", "交房状态", {"A": "毛坯", "B": "精装房", "C": "二手房", "D": "旧房翻新"}),
    ("5", "预算档位", {"A": "经济型（控成本）", "B": "舒适型（主流品质）", "C": "轻奢型（追求质感）", "D": "不确定，看方案"}),
    ("6", "色彩偏好", {"A": "冷静中性（灰白黑）", "B": "温暖奶油（杏/咖/米）", "C": "自然木色（原木/米白）", "D": "低饱和灰调（燕麦/灰褐）"}),
    ("7", "材质取向", {"A": "哑光+金属+玻璃", "B": "布艺+圆弧+原木", "C": "实木+棉麻+藤编", "D": "水泥+铁艺+皮革"}),
    ("8", "核心诉求", {"A": "好打理、不过时", "B": "温馨治愈、有温度", "C": "文化感、待客有面", "D": "艺术感、独树一帜"}),
    ("9", "收纳需求", {"A": "极简收纳、够用即可", "B": "收纳至上是刚需", "C": "要展示区（博古/酒柜）", "D": "隐藏式收纳为主"}),
    ("10", "灯光偏好", {"A": "明亮通透、无主灯", "B": "暖光氛围、洗墙灯带", "C": "重点照明、艺术感", "D": "工业吊灯、粗犷感"}),
    ("11", "家庭结构", {"A": "单身/情侣", "B": "新婚二人", "C": "有小孩", "D": "与长辈同住/长辈家"}),
    ("12", "审美倾向", {"A": "极简克制", "B": "柔和浪漫", "C": "自然本真", "D": "传统底蕴"}),
]


def gen_markdown() -> str:
    out = ["# 装修需求问卷（请逐题作答）", "", "> 一次性答完，用于判定装修风格与档位。", ""]
    for num, title, opts in QUESTIONS:
        out.append(f"**{num}. {title}**")
        if "__fill__" in opts:
            out.append(f"  - 填写：{opts['__fill__']}")
        else:
            for k, v in opts.items():
                out.append(f"  - {k}. {v}")
        out.append("")
    out.append("作答格式示例：`1:C 2:西安 3:A 4:A 5:B 6:B 7:B 8:B 9:B 10:B 11:B 12:B`")
    return "\n".join(out)


def parse_answer(s: str) -> dict:
    answers = {}
    for token in s.replace(",", " ").replace("；", " ").split():
        if ":" in token:
            k, v = token.split(":", 1)
            answers[k.strip()] = v.strip()
    return answers


def main():
    ap = argparse.ArgumentParser(description="装修需求问卷")
    ap.add_argument("--gen", action="store_true", help="生成问卷")
    ap.add_argument("--out", help="问卷输出路径")
    ap.add_argument("--answer", help='作答串，如 "1:C 2:西安 3:A ..."')
    args = ap.parse_args()

    if args.gen:
        md = gen_markdown()
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"问卷已写入 {args.out}")
        else:
            print(md)
        return

    if args.answer:
        answers = parse_answer(args.answer)
        print("=== 作答解析 ===")
        print(json.dumps(answers, ensure_ascii=False))
        print()
        print(format_report(judge(answers)))
        return

    ap.print_help()


if __name__ == "__main__":
    main()
