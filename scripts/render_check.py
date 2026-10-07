#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_check.py — 效果图出图质检（高清级）

检查项（对齐 references/07 出图纪律与高清要求）：
  - 分辨率：长边是否达标（默认 ≥1536px；放大后 ≥3000px）
  - 长宽比：是否落在合理区间（横构图 1.4–1.9；竖构图 0.65–0.85）
  - 亮度：平均灰度是否过曝（>230）/过暗（<40）
  - 对比度：灰度标准差是否过低（<20，画面发灰）
  - 文件体积：是否 ≥80KB（过小疑似失败或占位图）

用法：
  python3 render_check.py --dir renders/ --min-side 1536
  python3 render_check.py --image 客厅_4x.png --min-side 3000
  python3 render_check.py --dir renders/ --json report.json
退出码：0 全过；1 存在不达标项。
"""
import argparse, glob, json, os, sys


def analyze(path):
    from PIL import Image, ImageStat
    with Image.open(path) as im:
        w, h = im.size
        grey = im.convert("L")
        stat = ImageStat.Stat(grey)
        mean, std = stat.mean[0], stat.stddev[0]
    ratio = w / h
    size_kb = os.path.getsize(path) // 1024
    issues = []
    # 分辨率
    long_side = max(w, h)
    # 比例
    if ratio >= 1.0:
        if not (1.3 <= ratio <= 2.0):
            issues.append(f"横构图比例异常 {ratio:.2f}（宜 1.4–1.9）")
    else:
        if not (0.6 <= ratio <= 0.9):
            issues.append(f"竖构图比例异常 {ratio:.2f}（宜 0.65–0.85）")
    # 亮度
    if mean > 230:
        issues.append(f"疑似过曝（均灰度 {mean:.0f}）")
    elif mean < 40:
        issues.append(f"疑似过暗（均灰度 {mean:.0f}）")
    # 对比度
    if std < 20:
        issues.append(f"画面对比度低（标准差 {std:.0f}）")
    # 体积
    if size_kb < 80:
        issues.append(f"文件过小 {size_kb}KB（疑似失败/占位图）")
    return {"file": os.path.basename(path), "size": f"{w}x{h}", "long_side": long_side,
            "ratio": round(ratio, 2), "mean": round(mean, 1), "std": round(std, 1),
            "kb": size_kb, "issues": issues}


def main():
    ap = argparse.ArgumentParser(description="效果图出图质检")
    ap.add_argument("--image", help="单张图片")
    ap.add_argument("--dir", help="图片目录")
    ap.add_argument("--min-side", type=int, default=1536, help="长边最小像素（清晰度门槛）")
    ap.add_argument("--json", help="报告 JSON 落盘路径")
    args = ap.parse_args()

    targets = []
    if args.image:
        targets = [args.image]
    elif args.dir:
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            targets += glob.glob(os.path.join(args.dir, ext))
    if not targets:
        print("未找到图片", file=sys.stderr); sys.exit(2)

    results, bad = [], 0
    for t in targets:
        try:
            r = analyze(t)
        except Exception as e:
            r = {"file": os.path.basename(t), "size": "-", "long_side": 0, "ratio": 0,
                 "mean": 0, "std": 0, "kb": 0, "issues": [f"无法解析：{e}"]}
        if r["long_side"] and r["long_side"] < args.min_side:
            r["issues"].append(f"分辨率不足（长边 {r['long_side']}＜{args.min_side}），建议 upscale_bridge.py 放大")
        if r["issues"]:
            bad += 1
        results.append(r)

    print(f"=== 效果图质检：{len(results)} 张 ===")
    print("| 文件 | 尺寸 | 比例 | 均灰度 | 标准差 | 体积 | 结论 |")
    print("|------|------|------|--------|--------|------|------|")
    for r in results:
        verdict = "❌ " + "；".join(r["issues"]) if r["issues"] else "✅ 通过"
        print(f"| {r['file']} | {r['size']} | {r['ratio']} | {r['mean']} | {r['std']} | {r['kb']}KB | {verdict} |")
    print(f"\n结论：{len(results)-bad}/{len(results)} 通过" + ("" if bad == 0 else f"，{bad} 张需处理"))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
