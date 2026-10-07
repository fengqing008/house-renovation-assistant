#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""平面 2.5D 彩平示意图生成器（plan_render.py v3）—— 奶油风 2.5D 彩平。
特征：家具"挤出"成立体块（顶面＋前/右侧面，统一光照右下）、通铺木纹地板、
外粗内细墙、门洞弧线、绿植点缀、低饱和高明亮留白。输出单张 PNG。
命令：python3 plan_render.py --out 彩平2.5D.png
"""
import argparse, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, Arc
import matplotlib.patheffects as pe
from matplotlib import font_manager as fm

for fp in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
           "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
           "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    try: fm.fontManager.addfont(fp)
    except Exception: pass
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP","Noto Sans CJK SC","Noto Serif CJK JP","WenQuanYi Zen Hei","DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

W, H = 8500, 12929
BG="#FBF9F4"
FG={"wood":"#F0E3CE","woodln":"#E4D3B8","tile":"#ECE7DD","wet":"#E7EBE9","balc":"#E3E0D8"}
WL_EXT="#7C6E5C"; WL_INT="#CFC4B3"; INK="#57493A"; SUB="#9A8A76"
# 家具：顶面色、类型、挤出高度(mm)
C={"sofa":("#DCC8AB","#C7AF8C"),"bed":("#E4D2B8","#CDB291"),"cab":("#C8AE86","#AD9166"),
   "table":("#DAC4A4","#C2A87F"),"fix":("#DEE3E2","#C4CCCA"),"appl":("#D2D7D9","#B9C0C3"),
   "shelf":("#C6A87E","#A98C61"),"desk":("#D1B48E","#B99A72"),"child":("#EAD6B0","#D2BB92"),
   "rug":("#EEE2CE",None)}
HGT={"sofa":330,"bed":300,"cab":420,"table":250,"fix":320,"appl":520,"shelf":620,"desk":320,"child":420,"rug":18}

ROOMS=[
 (0,0,3657,1557,"阳台","5.7㎡","","balc"),
 (0,1557,3657,8769,"客厅","26.4㎡","","wood"),
 (0,8769,3657,10726,"餐厅","","","tile"),
 (0,10726,1270,12929,"玄关","2.8㎡","","tile"),
 (1270,8769,2978,12929,"厨房","6.9㎡","","wet"),
 (2978,11252,4589,12929,"卫生间","2.7㎡","","wet"),
 (2978,9472,4589,11252,"过道","","","tile"),
 (4589,9472,7365,12929,"儿童房","9.6㎡","","wood"),
 (4589,6230,7365,9472,"老人房","9.0㎡","","wood"),
 (2978,6915,4589,9472,"过道","","","tile"),
 (3657,1557,7365,6230,"主卧","17.2㎡","","wood"),
 (5365,1557,7365,3957,"主卫","4.8㎡","","wet"),
]
FURN=[
 (1600,8050,2000,780,"sofa","沙发"),(2300,4800,1050,560,"table","茶几"),
 (215,4300,340,5600,"shelf","通顶书柜墙"),(1600,9750,1250,860,"table","餐桌"),
 (225,11800,340,1950,"cab","鞋柜"),(1620,10820,560,3800,"cab","橱柜"),
 (2350,9020,1250,500,"cab",""),(3350,12620,500,420,"fix","台盆"),
 (3950,11900,420,520,"fix","马桶"),(4300,12660,500,480,"fix","淋浴"),
 (5100,12400,980,680,"child","上下床"),(6900,9700,780,1850,"cab","双人衣柜"),
 (6500,12200,680,380,"desk","书桌"),(5150,6350,980,680,"bed","1.5m床"),
 (6900,6450,780,1750,"cab","衣柜"),(4520,2500,700,980,"bed","1.8m大床"),
 (5550,2450,1650,2150,"rug",""),(4200,5550,340,2500,"cab","衣柜"),
 (6880,3050,700,1750,"desk","书桌书柜"),(5700,1820,1450,500,"cab","双台盆"),
 (6880,3350,560,650,"fix","淋浴"),(3180,760,640,1050,"appl","洗烘"),
]
PLANTS=[(2450,6500),(3250,1600),(5750,11300),(6200,5000),(1150,1900),(4700,8900)]

def fr(x): return x/1000.0

def iso(ax,x,y,w,d,h,face,side,edge="#A08C6E",z=6):
    """2.5D 挤出块：右下光照，前(下)侧面较亮、右(外)侧面较暗，顶面最亮。"""
    ex=h*0.40; ey=-h
    front=[(x-w/2,y-d/2),(x+w/2,y-d/2),(x+w/2+ex,y-d/2+ey),(x-w/2+ex,y-d/2+ey)]
    right=[(x+w/2,y-d/2),(x+w/2,y+d/2),(x+w/2+ex,y+d/2+ey),(x+w/2+ex,y-d/2+ey)]
    ax.add_patch(Polygon([(fr(a),fr(b)) for a,b in front],closed=True,facecolor=face,edgecolor=edge,lw=0.5,zorder=z))
    ax.add_patch(Polygon([(fr(a),fr(b)) for a,b in right],closed=True,facecolor=side,edgecolor=edge,lw=0.5,zorder=z))
    ax.add_patch(FancyBboxPatch((fr(x-w/2),fr(y-d/2)),fr(w),fr(d),
                 boxstyle="round,pad=0,rounding_size=0.09",facecolor=face,edgecolor=edge,lw=0.85,zorder=z+1))
    return ex,ey

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="平面2.5D彩平.png")
    ap.add_argument("--title",default="阳光城上林府 · 三居室平面彩平示意图（2.5D·奶油风）")
    a=ap.parse_args()
    fig,ax=plt.subplots(figsize=(9,13.6),dpi=190); ax.set_facecolor(BG)
    # 地面
    for (x0,y0,x1,y1,n,ar,dd,fl) in ROOMS:
        p=Rectangle((fr(x0),fr(y0)),fr(x1-x0),fr(y1-y0),facecolor=FG[fl],edgecolor="none",zorder=2)
        ax.add_patch(p)
        if fl=="wood":
            yy=fr(y0)+0.14
            while yy<fr(y1):
                ln=ax.plot([fr(x0),fr(x1)],[yy,yy],color=FG["woodln"],lw=0.5,alpha=0.7,zorder=3)[0]
                ln.set_clip_path(p); yy+=0.16
    # 家具（2.5D）
    for (x,y,w,d,k,lab) in FURN:
        face,side=C[k]; h=HGT[k]
        if k=="rug":
            ax.add_patch(FancyBboxPatch((fr(x-w/2),fr(y-d/2)),fr(w),fr(d),boxstyle="round,pad=0,rounding_size=0.12",
                         facecolor=face,edgecolor="#D8C9AF",lw=0.6,zorder=4)); continue
        iso(ax,x,y,w,d,h,face,side)
        if k in ("sofa","bed","child"):   # 床/沙发靠背（顶部条）
            iso(ax,x,y+d/2-140,w,140,h*0.9,face,side,z=8)
        if lab:
            ax.text(fr(x),fr(y-d/2)-0.30,lab,ha="center",va="top",fontsize=6.3,color=INK,zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.4,foreground=BG)])
    # 绿植
    for (px,py) in PLANTS:
        for dx,dy,rad,c in [(0,0,0.30,"#A8BFA0"),(-0.16,0.16,0.20,"#93B08C"),(0.18,0.12,0.17,"#B4C7AC")]:
            ax.add_patch(Circle((fr(px)+dx,fr(py)+dy),rad,facecolor=c,edgecolor="#8AA383",lw=0.4,alpha=0.9,zorder=6))
    # 内墙（细）
    for (x0,y0,x1,y1,n,ar,dd,fl) in ROOMS:
        ax.add_patch(Rectangle((fr(x0),fr(y0)),fr(x1-x0),fr(y1-y0),facecolor="none",edgecolor=WL_INT,linewidth=1.0,zorder=5))
    # 外墙（粗）＋ 2.5D 基座
    ax.add_patch(Rectangle((0,0),fr(7365),fr(H),facecolor="none",edgecolor=WL_EXT,linewidth=4.4,zorder=5))
    ax.add_patch(Polygon([(0,0),(fr(7365),0),(fr(7365)+0.5,-0.6),(0.5,-0.6)],closed=True,facecolor="#E9E3D8",edgecolor="none",zorder=1))
    ax.add_patch(Polygon([(fr(7365),0),(fr(7365),fr(H)),(fr(7365)+0.5,fr(H)-0.6),(fr(7365)+0.5,-0.6)],closed=True,facecolor="#DED7CA",edgecolor="none",zorder=1))
    # 门洞弧线
    for (dx,dy,rad,th) in [(900,1557,900,0)]:
        ax.add_patch(Arc((fr(dx),fr(dy)),rad*2/1000,rad*2/1000,theta1=th,theta2=th+90,color="#B7A98F",lw=0.9,zorder=6))
    # 飘窗
    for (x,y,w,d) in [(7365,11200,300,1900),(7365,7000,300,1900),(3700,1230,1650,300)]:
        ax.add_patch(Rectangle((fr(x),fr(y)),fr(w),fr(d),facecolor="#EFF4F1",edgecolor="#A9BCB2",linewidth=1.0,zorder=4))
        ax.text(fr(x+w/2),fr(y+d/2),"飘窗",ha="center",va="center",fontsize=6.2,color="#7c8f86",
                rotation=(90 if d>w else 0),zorder=8,path_effects=[pe.withStroke(linewidth=2,foreground=BG)])
    for (x,y) in [(7720,11200),(7720,7000),(4550,900)]:
        ax.add_patch(FancyBboxPatch((fr(x-320),fr(y-140)),fr(640),fr(280),boxstyle="round,pad=0,rounding_size=0.06",
                     facecolor="#DEEAF2",edgecolor="#8FAEC5",lw=0.8,zorder=9))
        ax.text(fr(x),fr(y),"空调",ha="center",va="center",fontsize=6.2,color="#5f7f9c",zorder=10)
    # 房间标注
    LP={"客厅":(1750,5450),"餐厅":(1850,9760),"阳台":(1750,780),"主卧":(4650,5150),"主卫":(6365,2850)}
    halo=[pe.withStroke(linewidth=3.0,foreground=BG)]
    for (x0,y0,x1,y1,n,ar,dd,fl) in ROOMS:
        if n=="过道": continue
        cx,cy=(LP[n] if n in LP else ((x0+x1)/2,(y0+y1)/2)); cx,cy=fr(cx),fr(cy)
        ax.text(cx,cy+0.26,n,ha="center",va="center",fontsize=11.5,color=INK,fontweight="bold",zorder=12,path_effects=halo)
        if ar: ax.text(cx,cy-0.14,ar,ha="center",va="center",fontsize=9,color=SUB,zorder=12,path_effects=halo)
    # 指北针
    ax.annotate("",xy=(fr(W)+0.35,fr(H)-0.5),xytext=(fr(W)+0.35,fr(H)-2.4),arrowprops=dict(arrowstyle="-|>",color=WL_EXT,lw=2.4))
    ax.text(fr(W)+0.35,fr(H)-0.15,"N",ha="center",fontsize=12,color=WL_EXT,fontweight="bold")
    ax.text(fr(W)+0.35,fr(H)-2.9,"北",ha="center",fontsize=8.5,color=SUB)
    ax.set_xlim(-0.9,fr(W)+1.1); ax.set_ylim(-1.3,fr(H)+0.7); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(a.title,fontsize=15.5,color="#5a4632",pad=16,fontweight="bold")
    import matplotlib.patches as mp
    leg=[mp.Patch(facecolor=FG["wood"],edgecolor="#C9B79E",label="木纹地板"),
         mp.Patch(facecolor=FG["tile"],edgecolor="#C9B79E",label="哑光砖"),
         mp.Patch(facecolor=FG["wet"],edgecolor="#C9B79E",label="厨卫砖"),
         mp.Patch(facecolor=C["cab"][0],edgecolor="#A79578",label="柜体/定制"),
         mp.Patch(facecolor="#A8BFA0",edgecolor="none",label="绿植"),
         mp.Patch(facecolor="#EFF4F1",edgecolor="#A9BCB2",label="飘窗")]
    ax.legend(handles=leg,loc="lower left",bbox_to_anchor=(0.0,-0.05),ncol=3,fontsize=8.2,frameon=False)
    ax.text(0.0,-0.08,"注：2.5D 彩平为布置示意，尺寸以平面图/DXF 为准；飘窗距地500mm，空调移至飘窗上方。",
            transform=ax.transAxes,fontsize=7.4,color=SUB)
    fig.savefig(a.out,bbox_inches="tight",facecolor=BG)
    print("已生成 2.5D 彩平图：",a.out)

if __name__=="__main__":
    main()
