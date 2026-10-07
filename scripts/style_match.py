#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""style_match.py — 12 种装修风格加权打分与冲突检测

用法:
  python3 style_match.py --input answers.json      # 从 JSON 文件判定
  python3 style_match.py --json '{"6":"B","7":"B","8":"B","11":"B","12":"B"}'

answers.json 形如: {"1":"C","2":"西安","6":"B","7":"B","8":"B","9":"B","10":"B","11":"B","12":"B"}
键为题号字符串，值为选项字母（约束题 2 填城市名）。
"""
import argparse, json, sys, os

STYLES = ["现代简约", "奶油风", "新中式", "日式原木", "侘寂", "工业风", "法式轻奢", "北欧",
          "中古风", "原木极简", "法式田园", "美式复古"]

# 每题各选项对应的风格加分（每选项可同时给多个风格 +1）
QUESTION_MAP = {
    "6": {"A": ["现代简约", "原木极简"], "B": ["奶油风", "法式田园"], "C": ["日式原木", "新中式"], "D": ["侘寂", "中古风"]},
    "7": {"A": ["现代简约", "原木极简"], "B": ["奶油风", "北欧"], "C": ["日式原木", "法式田园"], "D": ["中古风", "美式复古"]},
    "8": {"A": ["现代简约", "北欧"], "B": ["奶油风", "法式田园"], "C": ["新中式", "法式轻奢"], "D": ["侘寂", "中古风"]},
    "9": {"A": ["现代简约", "原木极简"], "B": ["日式原木", "北欧"], "C": ["新中式", "法式轻奢"], "D": ["现代简约", "侘寂"]},
    "10": {"A": ["现代简约", "原木极简"], "B": ["奶油风", "日式原木"], "C": ["侘寂", "法式轻奢"], "D": ["工业风", "中古风"]},
    "11": {"A": ["工业风", "中古风"], "B": ["奶油风", "北欧"], "C": ["奶油风", "日式原木"], "D": ["新中式", "美式复古"]},
    "12": {"A": ["现代简约", "原木极简"], "B": ["奶油风", "法式田园"], "C": ["日式原木", "北欧"], "D": ["新中式", "美式复古"]},
}

# 权重：色彩题(6)、材质题(7) x2；其余信号题 x1.5；约束题不计风格分
WEIGHT = {"6": 2.0, "7": 2.0, "8": 1.5, "9": 1.5, "10": 1.5, "11": 1.5, "12": 1.5}

TIER_HINT = {"A": "经济型", "B": "舒适型", "C": "轻奢型", "D": "待方案确认"}


def judge(answers: dict) -> dict:
    scores = {s: 0.0 for s in STYLES}
    for q, opt in answers.items():
        q = str(q)
        if q not in QUESTION_MAP:
            continue
        opt = str(opt).strip().upper()[:1]
        if opt not in QUESTION_MAP[q]:
            continue
        w = WEIGHT.get(q, 1.0)
        for s in QUESTION_MAP[q][opt]:
            scores[s] += w
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top1, top2 = ranked[0], ranked[1]
    gap = (top1[1] - top2[1]) / top1[1] if top1[1] > 0 else 1.0
    conflict = gap < 0.15
    tier = TIER_HINT.get(str(answers.get("5", "")).strip().upper()[:1], "待方案确认")
    return {
        "主风格": top1[0], "主风格得分": round(top1[1], 1),
        "备选风格": f"{top2[0]}（{round(top2[1],1)}）",
        "第三风格": f"{ranked[2][0]}（{round(ranked[2][1],1)}）",
        "冲突提醒": "主备风格分差＜15%，两者接近，建议对比效果图后定稿" if conflict else "主备风格区分度明显",
        "建议档位": tier,
        "全部得分": {k: round(v, 1) for k, v in ranked},
    }


def format_report(r: dict) -> str:
    lines = [
        "【风格判定结论】",
        f"主风格：{r['主风格']}（加权得分 {r['主风格得分']}）",
        f"备选风格：{r['备选风格']}／{r['第三风格']}",
        f"风格冲突提醒：{r['冲突提醒']}",
        f"建议档位：{r['建议档位']}",
        "全部得分：" + "，".join(f"{k} {v}" for k, v in r["全部得分"].items()),
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="装修风格加权打分（12 风格）")
    ap.add_argument("--input", help="answers.json 路径")
    ap.add_argument("--json", help="直接传入 JSON 字符串")
    ap.add_argument("--pretty", action="store_true", help="输出 JSON 结果")
    args = ap.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            answers = json.load(f)
    elif args.json:
        answers = json.loads(args.json)
    else:
        print("请提供 --input 或 --json", file=sys.stderr)
        sys.exit(2)

    r = judge(answers)
    if args.pretty:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(format_report(r))


if __name__ == "__main__":
    main()
