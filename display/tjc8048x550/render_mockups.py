#!/usr/bin/env python3
"""Render the TJC8048X550 screen design in layout.json.

Needs only Pillow.  Run from anywhere:

    python render_mockups.py            # resources/*.png, mockups/*.png, checks
    python render_mockups.py --outline  # also draw every component's box
    python render_mockups.py --tables   # print the per-page tables of BUILD.md

resources/NN_bg_<page>.png  the 800 x 480 background picture of each page, to
                            import into the USART HMI editor (NN = picture id)
mockups/<page>.png          the page with sample values, as it should look

The mock-up draws text the way the editor's font tool does for a monospaced
face: every character in a cell `height` high and `height / 2` wide.  The
checks at the end (text wider than its field, fields overlapping, a field's
background colour differing from the picture under it, ...) exit with status 1
if anything is wrong.
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

FONT_FILES = [
    "C:/Windows/Fonts/consolab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
    "/Library/Fonts/Courier New Bold.ttf",
    "C:/Windows/Fonts/courbd.ttf",
]

VISIBLE = ("Text", "Number", "Button")


def rgb(c565):
    """RGB565 -> the RGB888 a 16-bit panel shows."""
    r, g, b = c565 >> 11, (c565 >> 5) & 63, c565 & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def to565(pixel):
    r, g, b = pixel[:3]
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def quantise(img):
    """Reduce an image to what RGB565 can hold."""
    r, g, b = img.convert("RGB").split()
    r = r.point(lambda v: (v >> 3) << 3 | v >> 5)
    g = g.point(lambda v: (v >> 2) << 2 | v >> 6)
    b = b.point(lambda v: (v >> 3) << 3 | v >> 5)
    return Image.merge("RGB", (r, g, b))


_font_file = None
_font_cache = {}


def font_file():
    global _font_file
    if _font_file is None:
        for f in FONT_FILES:
            if os.path.exists(f):
                _font_file = f
                break
        else:
            sys.exit("no monospaced bold TrueType font found; add one to FONT_FILES")
    return _font_file


def label_font(size):
    key = ("label", size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(font_file(), size)
    return _font_cache[key]


def cell_font(height):
    """The largest size whose ascent + descent fits a cell `height` high."""
    key = ("cell", height)
    if key not in _font_cache:
        best = None
        for size in range(6, height * 2):
            f = ImageFont.truetype(font_file(), size)
            ascent, descent = f.getmetrics()
            if ascent + descent > height:
                break
            best = f
        _font_cache[key] = best
    return _font_cache[key]


def wrap(text, columns):
    """Word wrap, as isbr=1 does."""
    lines, line = [], ""
    for word in text.split(" "):
        while len(word) > columns:              # a word longer than a line
            room = columns - len(line) - (1 if line else 0)
            if room <= 0:
                lines.append(line)
                line, room = "", columns
            line += (" " if line else "") + word[:room]
            word = word[room:]
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= columns:
            line += " " + word
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_cells(img, comp, text, fonts, colour):
    """Draw `text` in the component's box, clipped to it."""
    height = fonts[comp["font"]]["height"]
    cw = height // 2
    box = Image.new("RGB", (comp["w"], comp["h"]), rgb(comp["bco"]))
    d = ImageDraw.Draw(box)
    f = cell_font(height)
    ascent, descent = f.getmetrics()
    pad = (height - ascent - descent) // 2

    lines = wrap(text, max(1, comp["w"] // cw)) if comp.get("isbr") else [text]
    total_h = len(lines) * height
    y = {0: 0, 1: (comp["h"] - total_h) // 2, 2: comp["h"] - total_h}[comp.get("ycen", 1)]
    for line in lines:
        width = len(line) * cw
        x = {0: 0, 1: (comp["w"] - width) // 2, 2: comp["w"] - width}[comp.get("xcen", 0)]
        for ch in line:
            adv = f.getlength(ch)
            d.text((x + (cw - adv) / 2, y + pad), ch, font=f, fill=colour)
            x += cw
        y += height
    img.paste(box, (comp["x"], comp["y"]))


def render_background(page):
    img = Image.new("RGB", (800, 480), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for e in page["background"]["elements"]:
        if e["kind"] == "rect":
            xy = (e["x"], e["y"], e["x"] + e["w"] - 1, e["y"] + e["h"] - 1)
            if e.get("radius"):
                d.rounded_rectangle(xy, e["radius"], fill=rgb(e["color"]))
            else:
                d.rectangle(xy, fill=rgb(e["color"]))
        elif e["kind"] == "label":
            d.text((e["x"], e["y"]), e["text"], font=label_font(e["size"]), fill=rgb(e["color"]),
                   anchor=e.get("anchor", "lm"))
        else:
            sys.exit("unknown background element %r" % e["kind"])
    return quantise(img)


def render_page(page, bg, fonts, outline):
    img = bg.copy()
    for c in page["components"]:
        if c["type"] == "Text":
            draw_cells(img, c, c.get("sample", ""), fonts, rgb(c.get("sample_pco", c["pco"])))
        elif c["type"] == "Number":
            draw_cells(img, c, c.get("sample", str(c.get("val", 0))), fonts, rgb(c["pco"]))
        elif c["type"] == "Button":
            draw_cells(img, c, c["txt"], fonts, rgb(c["pco"]))
            ImageDraw.Draw(img).rectangle(
                (c["x"], c["y"], c["x"] + c["w"] - 1, c["y"] + c["h"] - 1), outline=rgb(c["pco"]), width=2)
    if outline:
        d = ImageDraw.Draw(img)
        for c in page["components"]:
            if "x" in c:
                d.rectangle((c["x"], c["y"], c["x"] + c["w"] - 1, c["y"] + c["h"] - 1), outline=(255, 0, 255))
                d.text((c["x"] + 2, c["y"] + 1), c["objname"], font=label_font(12), fill=(255, 0, 255))
    return quantise(img)


def check_page(page, bg, fonts):
    """Return a list of problems with this page."""
    bad = []
    name = page["name"]
    seen = set()
    boxes = []
    for c in page["components"]:
        who = "%s.%s" % (name, c["objname"])
        if c["objname"] in seen:
            bad.append("%s: object name used twice" % who)
        seen.add(c["objname"])
        if "x" not in c:
            continue
        if c["x"] < 0 or c["y"] < 0 or c["x"] + c["w"] > 800 or c["y"] + c["h"] > 480:
            bad.append("%s: outside the screen" % who)
        if c["type"] not in VISIBLE:
            continue
        if c["type"] == "Button" and min(c["w"], c["h"]) < 60:
            bad.append("%s: touch target under 60 px" % who)
        if not c.get("hidden"):
            for other, obox in boxes:
                if (c["x"] < obox[2] and obox[0] < c["x"] + c["w"] and
                        c["y"] < obox[3] and obox[1] < c["y"] + c["h"]):
                    bad.append("%s: overlaps %s" % (who, other))
            boxes.append((who, (c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"])))

        # the solid background of a field must be the colour of the picture under it
        if c["type"] in ("Text", "Number"):
            colours = bg.crop((c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"])).getcolors(4096)
            if colours is None or len(colours) != 1 or to565(colours[0][1]) != c["bco"]:
                found = "several colours" if (colours is None or len(colours) != 1) else str(to565(colours[0][1]))
                bad.append("%s: bco %d but the background picture there is %s" % (who, c["bco"], found))

        if c.get("hidden"):
            continue
        height = fonts[c["font"]]["height"]
        cw = height // 2
        if height > c["h"]:
            bad.append("%s: font %d px in a field %d px high" % (who, height, c["h"]))
        for what in ("sample", "longest", "txt"):
            s = c.get(what, "")
            if c.get("isbr"):
                lines = wrap(s, c["w"] // cw)
                if len(lines) * height > c["h"]:
                    bad.append("%s: %s text needs %d lines, the field holds %d" %
                               (who, what, len(lines), c["h"] // height))
            elif len(s) * cw > c["w"]:
                bad.append("%s: %s text %r is %d px wide, the field is %d" % (who, what, s, len(s) * cw, c["w"]))
            if c["type"] in ("Text", "Button") and len(s) > c["txt_maxl"]:
                bad.append("%s: %s text longer than txt_maxl %d" % (who, what, c["txt_maxl"]))
        if c["type"] == "Text" and c["pco"] == c["bco"]:
            bad.append("%s: text colour equals background colour" % who)
    if "S0" not in seen:
        bad.append("%s: no S0 (the driver clicks it on every page)" % name)
    return bad


TYPE_ZH = {"Text": "文本", "Number": "数字", "Button": "按钮", "Variable": "变量", "Timer": "定时器",
           "Hotspot": "触摸热区"}
EVENT_ZH = {"touch_press": "按下事件 (Touch Press)", "touch_release": "弹起事件 (Touch Release)",
            "timer": "定时事件 (Timer)", "preinitialize": "前初始化事件 (Preinitialize)",
            "postinitialize": "后初始化事件 (Postinitialize)"}


def tables(doc):
    """The per-page part of BUILD.md, in Traditional Chinese."""
    out = []
    for n, page in enumerate(doc["pages"]):
        out.append("### 5.%d 頁面 `%s`（page id %d）" % (n + 1, page["name"], page["id"]))
        out.append("")
        out.append("- 頁面屬性：`sta` = 圖片（image），`pic` = **%d**（`%s`）。"
                   % (page["background"]["pic_id"], page["background"]["file"]))
        out.append("- 完成後應該長這樣：`mockups/%s.png`。" % page["name"])
        out.append("")
        out.append("| id | objname | 類型 | x | y | w | h | font | pco | bco | xcen | ycen | 初始 txt / val | txt_maxl | vscope | 其他 |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for c in page["components"]:
            def g(key):
                return str(c[key]) if key in c else "–"
            extra = []
            if c["type"] == "Variable":
                extra.append("sta = 数值 (int32)")
            if c["type"] == "Timer":
                extra.append("tim = %d，en = %d" % (c["tim"], c["en"]))
            if c["type"] == "Button":
                extra.append("bco2 = %d，pco2 = %d" % (c["bco2"], c["pco2"]))
            if c["type"] == "Number":
                extra.append("lenth = %d" % c["lenth"])
            if c.get("isbr"):
                extra.append("isbr = 1（自動換行）")
            if c.get("hidden"):
                extra.append("隱藏欄位：文字色 = 底色")
            if c["type"] == "Hotspot":
                extra.append("看不見；事件碼見下")
            if c["type"] in ("Text", "Button"):
                init = '`"%s"`' % c["txt"] if c["txt"] else "（空白）"
            elif "val" in c:
                init = str(c["val"])
            else:
                init = "–"
            out.append("| %d | **%s** | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                c["id"], c["objname"], TYPE_ZH[c["type"]], g("x"), g("y"), g("w"), g("h"), g("font"),
                g("pco"), g("bco"), g("xcen"), g("ycen"), init, g("txt_maxl"),
                "**global**" if c.get("vscope") == "global" else "local", "；".join(extra) or "–"))
        out.append("")
        events = [("頁面", k, v) for k, v in page.get("events", {}).items()]
        for c in page["components"]:
            events += [("`%s`" % c["objname"], k, v) for k, v in c.get("events", {}).items()]
        for owner, kind, code in events:
            out.append("%s 的 **%s**：" % (owner, EVENT_ZH[kind]))
            out.append("")
            out.append("```")
            out.extend(code)
            out.append("```")
            out.append("")
    return "\n".join(out)


def main():
    with open(os.path.join(HERE, "layout.json"), encoding="utf-8") as f:
        doc = json.load(f)

    if "--tables" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        print(tables(doc))
        return 0

    outline = "--outline" in sys.argv
    fonts = {f["id"]: f for f in doc["fonts"]["table"]}
    res_dir = os.path.join(HERE, "resources")
    mock_dir = os.path.join(HERE, "mockups")
    os.makedirs(res_dir, exist_ok=True)
    os.makedirs(mock_dir, exist_ok=True)

    problems = []
    for want, page in enumerate(doc["pages"]):
        if page["id"] != want:
            problems.append("%s: page id %d, expected %d" % (page["name"], page["id"], want))
        bg = render_background(page)
        bg.save(os.path.join(res_dir, page["background"]["file"]))
        suffix = "_outline" if outline else ""
        render_page(page, bg, fonts, outline).save(os.path.join(mock_dir, page["name"] + suffix + ".png"))
        problems += check_page(page, bg, fonts)
        print("%-7s %2d components  resources/%s  mockups/%s%s.png" % (
            page["name"], len(page["components"]), page["background"]["file"], page["name"], suffix))

    if problems:
        print("\n%d problem(s):" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
