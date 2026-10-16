#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prompt_builder.py — 效果图提示词构建（v2 · 高清级）

特性：
  1. 机位×空间矩阵：每空间给多个专业机位（含焦距、机位高度、构图，见 CAMERA 库）
  2. 分辨率参数：--size（默认 1664*928 16:9），交给 image_gen 的 width/height 落实
  3. 负向提示词：默认生成（防变形/文字/多手/低质/畸变）
  4. 材质细节：STYLE_SPEC 的 mat_detail 物理材质描述，提升渲染真实度
  5. 批次一致性：--seed 固定 + 统一色板 palette（同一户多图风格/色调统一）
  6. JSON 输出：供批量出图与放大链路（upscale_bridge.py）消费
  7. 多后端降级：image_gen → pollinations → 仅提示词卡片（见 references/07）

用法:
  python3 prompt_builder.py --style 奶油风 --room 客厅 --shots all
  python3 prompt_builder.py --style 新中式 --room 主卧 --size 1536*1024 --seed 20261006
  python3 prompt_builder.py --style 原木极简 --room all --json
  python3 prompt_builder.py --list
"""
import argparse, json, re, sys

# ---- 风格库（含物理材质细节 mat_detail，用于提升渲染真实度）----
STYLE_SPEC = {
    "现代简约": dict(color="暖白#F5F5F3与深灰#4A4A48", mat="哑光大板砖、金属细框、超白玻璃、木饰面",
                 mat_detail="哑光岩板细腻无反射、拉丝铝细框、超白玻璃通透、浅色木饰面开放纹理",
                 furn="直线条低矮沙发、悬空电视柜", light="无主灯磁吸轨道+线性灯，3500-4000K，见光不见灯", mood="简洁通透、克制大气"),
    "奶油风": dict(color="奶油杏#F1E4D6与浅燕麦#D9C7B0", mat="奶油哑光砖、艺术涂料弧形墙、亚麻布艺、羊羔绒",
                 mat_detail="微水泥质感墙面柔光、亚麻布艺粗织纹理、羊羔绒蓬松、圆弧倒角柔和高光",
                 furn="圆弧倒角沙发、原木茶几", light="暖光3000K、灯带洗墙、云朵灯", mood="温馨治愈、柔和放松"),
    "新中式": dict(color="月白#E8E2D5与胡桃木、朱砂红点缀", mat="木饰面、岩板、水墨石材、铜件、丝绢",
                 mat_detail="胡桃木饰面板深纹、水墨岩板肌理、铜件哑光做旧、丝绢半透光",
                 furn="改良圈椅、条案、对称布局", light="格栅灯、灯笼造型、暖光见光不见灯", mood="禅意文雅、留白借景"),
    "日式原木": dict(color="米白#EFEAD8与浅橡木#C9A86A", mat="白蜡木/橡木哑光开放漆、棉麻、席纹",
                 mat_detail="白蜡木开放漆木纹清晰、棉麻织物质感、席纹编织、纸障子半透光",
                 furn="矮家具、悬空柜、榻榻米、格栅门", light="暖光2700-3000K、纸灯、间接照明", mood="自然本真、松弛克制"),
    "侘寂": dict(color="燕麦#E5E0D5与灰褐#9A9384", mat="微水泥、夯土墙、手工陶砖、亚麻、旧化黄铜",
                 mat_detail="微水泥细腻毛孔、夯土墙粗粝肌理、手工陶砖不规则边缘、亚麻粗织",
                 furn="粗粝质感、异形陶器、藤麻编织", light="极暗调、间接光、局部重点光", mood="静谧艺术、朴素自然"),
    "工业风": dict(color="炭黑#3B3B3B与做旧砖#6E6259、黄铜点缀", mat="水泥自流平、文化砖、黑铁、实木、皮革",
                 mat_detail="水泥自流平哑光斑驳、做旧砖粗糙、黑铁件锈感、皮革自然纹理",
                 furn="金属框架、皮质沙发、铁艺置物架", light="爱迪生灯泡、轨道灯、黑铁吊灯", mood="粗犷个性、Loft 感"),
    "法式轻奢": dict(color="象牙白#F3EFE9与香槟金#C9A227", mat="石膏线护墙板、大理石、人字拼木地板、丝绒",
                 mat_detail="石膏线细腻阴影、大理石自然纹、人字拼木地板光泽、丝绒反光柔",
                 furn="弧线绒面沙发、金属腿单椅", light="水晶/玻璃吊灯、壁灯、暖光", mood="优雅浪漫、精致仪式感"),
    "北欧": dict(color="白#FFFFFF与雾绿#5B8C85跳色", mat="浅色木地板、棉麻、羊毛、软木",
                 mat_detail="浅橡木地板自然纹、棉麻织物、羊毛毯蓬松、软木温润",
                 furn="原木家具、布艺沙发、几何纹样", light="吊灯+落地灯+台灯组合，暖白光", mood="清爽明亮、功能主义"),
    "中古风": dict(color="米灰#E8DFD0与胡桃木#6B4F3A、黄铜/砖红点缀", mat="胡桃木/柚木、黄铜、皮革、羊毛、玻璃砖",
                 mat_detail="胡桃木油润深纹、黄铜金属反光、全粒面皮革纹理、玻璃砖半透",
                 furn="低矮细腿沙发、异形茶几、弧形单椅", light="黄铜吊灯、球形壁灯、暖光2700K", mood="复古质感、中古腔调"),
    "原木极简": dict(color="暖白#F2EFE9与橡木#D6C4A8、灰绿点缀", mat="橡木/白蜡木、微水泥、棉麻、藤编、哑光五金",
                 mat_detail="橡木开放漆细纹、微水泥柔肌理、棉麻朴素、藤编孔隙、哑光五金无高光",
                 furn="低矮原木家具、无把手一体柜、细腿悬空款", light="无主灯+间接光，暖白3000K，见光不见灯", mood="极简温润、克制高级"),
    "法式田园": dict(color="奶白#F5EFE3与鼠尾草绿#C8D6C0、干玫瑰点缀", mat="做旧实木、藤编、碎花布艺、复古砖、铜件",
                 mat_detail="做旧实木做旧漆面、藤编自然纹、碎花棉布、复古花砖、铜件氧化",
                 furn="弧形木质餐椅、藤编柜、褶皱布艺沙发", light="铁艺枝形吊灯、暖光壁灯", mood="自然浪漫、田园清新"),
    "美式复古": dict(color="米白#EDE6DA与深棕#5B4636、酒红/墨绿点缀", mat="实木、全粒面皮革、黄铜五金、亚麻、地毯",
                 mat_detail="实木深色木纹、皮革油润、黄铜做旧、羊毛地毯厚实",
                 furn="铆钉皮沙发、实木餐桌、四柱床", light="铁艺/黄铜吊灯、台灯，暖光", mood="沉稳厚重、经典美式"),
}

# ---- 机位库：房间 -> [(机位名, 镜头与机位描述)] ----
CAMERA = {
    "客厅": [("入户视角", "24mm 广角镜头，机位高 1.5m，从入户方向框住客餐厅全景"),
            ("沙发区平视", "35mm 镜头，机位高 1.2m，45° 侧向看沙发区与背景墙"),
            ("电视墙正对", "35mm 镜头，机位高 1.5m，正对电视墙")],
    "餐厅": [("餐桌主视角", "35mm 镜头，机位高 1.4m，从餐边柜方向看餐桌"),
            ("俯视全局", "28mm 镜头，机位高 1.6m，45° 俯视餐区")],
    "主卧": [("床头全景", "24mm 广角，机位高 1.4m，从床尾看床头背景墙"),
            ("床尾平视", "35mm，机位高 1.2m，侧看床与衣柜")],
    "次卧": [("全景", "24mm 广角，机位高 1.4m，框住全屋")],
    "儿童房": [("全景", "24mm 广角，机位高 1.2m，平视儿童活动区")],
    "厨房": [("门口俯视全局", "28mm，机位高 1.6m，从门口 45° 俯视操作区"),
            ("操作台平视", "35mm，机位高 1.4m，正对操作台")],
    "卫生间": [("干区全景", "24mm 广角，机位高 1.4m，从门口看干区"),
             ("淋浴区视角", "28mm，机位高 1.5m，看淋浴隔断")],
    "阳台": [("全景", "24mm 广角，机位高 1.4m，看洗衣与休闲区")],
    "玄关": [("入户视角", "28mm，机位高 1.5m，看鞋柜与换鞋区")],
    "书房": [("全景", "24mm 广角，机位高 1.4m，看书桌与书架")],
}
ROOMS = list(CAMERA.keys())

# 默认分辨率（长边×短边，16:9 为主）
SIZE_DEFAULT = "1664*928"
BUILD_SIZE = {  # 16:9 机位用横构图；竖构图空间用 4:5
    "卫生间": "1024*1280", "玄关": "1024*1280",
}

NEGATIVE = ("变形, 扭曲, 畸变, 错误透视, 多余手指, 残缺, 文字, 水印, logo, 商标, 人脸扭曲, "
            "家具畸形, 比例失调, 低分辨率, 模糊, 噪点, 过曝, 欠曝, 杂乱, 廉价感, 卡通, 插画风")
QUALITY = "超写实建筑渲染, 真实全局光照, 材质细节清晰, 物理正确阴影, 专业室内摄影, 建筑可视化, 高清, 电影级画质"


def palette(style):
    return re.findall(r"#[0-9A-Fa-f]{6}", STYLE_SPEC[style]["color"])


def build(style, room, shot, size, seed):
    s = STYLE_SPEC[style]
    cam = dict(CAMERA[room])[shot]
    prompt = (f"{room}室内设计效果图，{style}，{s['color']}，{s['mat']}，"
              f"{s['mat_detail']}，{s['furn']}，{s['light']}，{s['mood']}，"
              f"自然采光充足，{cam}，{QUALITY}。")
    return {
        "style": style, "room": room, "shot": shot,
        "prompt": prompt, "negative": NEGATIVE, "size": size, "seed": seed,
        "palette": palette(style),
    }


def main():
    ap = argparse.ArgumentParser(description="装修效果图提示词构建（高清级 v2）")
    ap.add_argument("--style", help="风格名：" + "/".join(STYLE_SPEC))
    ap.add_argument("--room", default="客厅", help="空间名或 all")
    ap.add_argument("--shots", default="all", help="机位：all 或 机位名")
    ap.add_argument("--size", default=None, help=f"分辨率 长*宽，默认 {SIZE_DEFAULT}（按空间）")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（同户多图固定以保一致性）")
    ap.add_argument("--json", action="store_true", help="输出 JSON（供批量出图/放大链路）")
    ap.add_argument("--list", action="store_true", help="列出风格与机位")
    args = ap.parse_args()

    if args.list:
        print("风格：" + "、".join(STYLE_SPEC))
        print("\n机位：")
        for r in ROOMS:
            print(f"  {r}: " + "、".join(s for s, _ in CAMERA[r]))
        return

    if args.style not in STYLE_SPEC:
        print(f"未知风格：{args.style}\n可选：" + "、".join(STYLE_SPEC), file=sys.stderr)
        sys.exit(2)

    rooms = ROOMS if args.room == "all" else [args.room]
    seed = args.seed if args.seed is not None else 20261006  # 批次一致性默认种子
    items = []
    for r in rooms:
        if r not in CAMERA:
            print(f"未知空间：{r}", file=sys.stderr); continue
        shots = [s for s, _ in CAMERA[r]] if args.shots == "all" else [args.shots]
        for sh in shots:
            if sh not in dict(CAMERA[r]):
                print(f"未知机位：{sh}（{r} 支持：" + "、".join(dict(CAMERA[r])) + "）", file=sys.stderr); continue
            size = args.size or BUILD_SIZE.get(r, SIZE_DEFAULT)
            items.append(build(args.style, r, sh, size, seed))

    if args.json:
        print(json.dumps({"style": args.style, "seed": seed,
                          "palette": palette(args.style), "images": items},
                         ensure_ascii=False, indent=2))
        return

    print(f"# 效果图提示词（{args.style} · 种子 {seed} · 批次一致性）\n")
    print(f"> 色板：{'、'.join(palette(args.style))}（同户多图统一）\n")
    for it in items:
        print(f"## {it['room']} · {it['shot']}（{it['size']}）")
        print("```")
        print(it["prompt"])
        print("```")
        print(f"- 负向：{it['negative']}")
        print()
    print("> 出图后接 `upscale_bridge.py` 做 4× 无损放大（可印刷）；图注须标注：效果图仅示意风格与氛围，尺寸与工艺以方案及施工图为准。")


if __name__ == "__main__":
    main()
