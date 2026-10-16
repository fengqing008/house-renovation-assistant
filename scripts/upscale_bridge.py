#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""upscale_bridge.py — 效果图 4× 无损放大桥（高清级 / 可印刷）

链路（多通道自动降级）：
  ① 远程 AI 放大：优先调用 ai-upscaler 技能脚本（Pollinations Kontext 图生图增强）
  ② 本地插值放大：PIL LANCZOS 4× + UnsharpMask 锐化（离线兜底，非 AI 增强，会标注）
  ③ 全部失败：明确报错并给出提示词卡片降级说明

用法：
  python3 upscale_bridge.py --input 客厅.png --outdir out --scale 4
  python3 upscale_bridge.py --dir renders/ --scale 4          # 批量
  python3 upscale_bridge.py --input a.png --mode local        # 强制本地

输出：<原名>_4x.png，并在 stderr 打印实际采用的通道（remote/local）。
"""
import argparse, os, sys, glob


def _local_upscale(inp, out, scale=4):
    from PIL import Image, ImageFilter
    im = Image.open(inp).convert("RGB")
    w, h = im.size
    im = im.resize((w * scale, h * scale), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=120, threshold=3))
    im.save(out)
    return f"local-{scale}x LANCZOS+USM"


def _remote_upscale(inp, out, scale=4):
    """调用 ai-upscaler 技能脚本（若存在），否则内联 Pollinations Kontext。"""
    candidate = "/root/.skills/ai-upscaler/scripts/ai_upscaler.py"
    if os.path.exists(candidate):
        import subprocess
        r = subprocess.run([sys.executable, candidate, inp, out, "--scale", str(scale), "--mode", "remote"],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1024:
            return f"remote-ai (ai-upscaler, {scale}x)"
        raise RuntimeError((r.stderr or "ai-upscaler 返回非零").strip()[:160])

    # 内联兜底：Pollinations Kontext
    import base64, mimetypes, time, urllib.request
    from urllib.parse import quote
    mime = mimetypes.guess_type(inp)[0] or "image/png"
    with open(inp, "rb") as f:
        data_url = f"data:{mime};base64," + base64.b64encode(f.read()).decode("ascii")
    prompt = f"Upscale and enhance to {scale}x, sharper details, keep composition, professional interior photography"
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
           f"?image={quote(data_url, safe='')}&model=kontext&nologo=true")
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ima-renov-upscale/1.0"})
            with urllib.request.urlopen(req, timeout=150) as resp:
                buf = resp.read()
            if len(buf) < 1024:
                raise ValueError(f"返回过小({len(buf)}B)")
            with open(out, "wb") as f:
                f.write(buf)
            return f"remote-ai (pollinations kontext, {scale}x)"
        except Exception as e:
            print(f"[upscale] 远程尝试 {i+1}/3 失败：{e}", file=sys.stderr)
            time.sleep(2 ** i)
    raise RuntimeError("远程放大失败（已重试 3 次）")


def run_one(inp, outdir, scale=4, mode="auto"):
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(inp))[0]
    out = os.path.join(outdir, f"{base}_{scale}x.png")
    if mode in ("auto", "remote"):
        try:
            ch = _remote_upscale(inp, out, scale)
            return out, ch
        except Exception as e:
            if mode == "remote":
                raise
            print(f"[upscale] 远程不可用（{e}），降级本地插值放大", file=sys.stderr)
    ch = _local_upscale(inp, out, scale)
    return out, ch


def main():
    ap = argparse.ArgumentParser(description="效果图 4× 无损放大（多通道降级）")
    ap.add_argument("--input", help="单张图片路径")
    ap.add_argument("--dir", help="批量目录")
    ap.add_argument("--outdir", default="out_upscaled", help="输出目录")
    ap.add_argument("--scale", type=int, default=4, choices=[2, 4], help="放大倍数")
    ap.add_argument("--mode", default="auto", choices=["auto", "remote", "local"])
    args = ap.parse_args()

    if not args.input and not args.dir:
        ap.print_help(); sys.exit(2)

    targets = []
    if args.input:
        targets = [args.input]
    else:
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            targets += glob.glob(os.path.join(args.dir, ext))
        targets = [t for t in targets if "_4x" not in t and "_2x" not in t]

    if not targets:
        print("未找到待放大图片", file=sys.stderr); sys.exit(1)

    ok = 0
    for t in targets:
        try:
            out, ch = run_one(t, args.outdir, args.scale, args.mode)
            sz = os.path.getsize(out) // 1024
            print(f"✅ {os.path.basename(t)} → {os.path.basename(out)}（{ch}，{sz}KB）")
            ok += 1
        except Exception as e:
            print(f"❌ {os.path.basename(t)} 失败：{e}", file=sys.stderr)

    print(f"\n完成 {ok}/{len(targets)}；输出目录：{args.outdir}")
    print("> 提示：本地插值放大为离线兜底（非 AI 增强），可印刷级建议走远程 AI 通道；图注须注明“效果图仅示意”。")
    sys.exit(0 if ok == len(targets) else 1)


if __name__ == "__main__":
    main()
