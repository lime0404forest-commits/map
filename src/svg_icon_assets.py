# -*- coding: utf-8 -*-
"""
SVG マーカーアイコン共通アセット（エディター・エクスポート・本番の前提を揃える）。

- 共通: <PROJECT_ROOT>/assets/icons/*.svg
- ゲーム別: <game_path>/assets/icons/*.svg（同一 ID はゲーム側が優先）

本番（ブラウザ）では map.js 側で、具象色を currentColor に正規化してから「currentColor を #RRGGBB に置換」して表示する。

エディタは refresh_svg_icon_catalog 時に batch_normalize_icon_svgs_inplace でディスク上の SVG も同じルールで上書きする（変更があったファイルのみ）。
"""
from __future__ import annotations

import io
import os
import re
from typing import Any, Dict, List, Optional, Set

# ID はファイル名（拡張子除く）。英数字・ハイフン・アンダースコア・ドット
_ID_RE = re.compile(r"^[\w.\-]+$")

_cairo_svg_ok: Optional[bool] = None
_pymupdf_svg_ok: Optional[bool] = None


def _probe_cairo_svg() -> bool:
    """cairosvg + システム Cairo が読み込めるか。"""
    global _cairo_svg_ok
    if _cairo_svg_ok is None:
        try:
            import cairosvg  # noqa: F401
            _cairo_svg_ok = True
        except (ImportError, OSError):
            _cairo_svg_ok = False
    return _cairo_svg_ok


def _probe_pymupdf() -> bool:
    """PyMuPDF（エディタ用・ホイール同梱のネイティブ）が使えるか。"""
    global _pymupdf_svg_ok
    if _pymupdf_svg_ok is None:
        try:
            import fitz  # noqa: F401
            _pymupdf_svg_ok = True
        except ImportError:
            _pymupdf_svg_ok = False
    return _pymupdf_svg_ok


def is_svg_raster_available() -> bool:
    """SVG をピクセル化できるか（Cairo 経路または PyMuPDF 経路のいずれか）。"""
    return _probe_cairo_svg() or _probe_pymupdf()


def common_icons_dir(project_root: str) -> str:
    return os.path.join(project_root, "assets", "icons")


def game_icons_dir(game_path: str) -> str:
    return os.path.join(game_path, "assets", "icons")


def replace_current_color(svg_text: str, hex_color: str) -> str:
    """
    SVG 文字列内の currentColor（大文字小文字無視）を指定色に置換。
    エディター（CairoSVG 前処理）と本番（map.js）で同じ契約にする。
    """
    if not svg_text:
        return svg_text
    h = (hex_color or "#ffffff").strip()
    if not h.startswith("#") or len(h) != 7:
        h = "#ffffff"
    return re.sub(r"currentColor", h, svg_text, flags=re.IGNORECASE)


def _ensure_root_svg_fill_current_color(svg_text: str) -> str:
    """
    fill/stroke の属性が無く currentColor も無い単純な SVG（既定の黒塗り）向けに、
    先頭の <svg> に fill="currentColor" を付与する。
    """
    if re.search(r"currentColor", svg_text, flags=re.IGNORECASE):
        return svg_text
    m = re.search(r"<svg\b([^>]*)>", svg_text, flags=re.IGNORECASE)
    if not m:
        return svg_text
    inner = m.group(1)
    if re.search(r"\bfill\s*=", inner, flags=re.IGNORECASE):
        return svg_text
    start, end = m.span()
    return svg_text[:start] + "<svg" + inner + ' fill="currentColor"' + ">" + svg_text[end:]


def normalize_svg_paints_to_current_color(svg_text: str) -> str:
    """
    単色シルエット向け: fill / stroke / stop-color / flood-color の具象指定を currentColor に統一する。
    none / transparent / currentColor / url() / var() はそのまま。登録時・ラスタ化前の双方で使う。
    置換後も currentColor が無い場合はルート <svg> に fill="currentColor" を付与する。
    """
    if not isinstance(svg_text, str) or not svg_text.strip():
        return svg_text

    def _skip_paint_value(val: str) -> bool:
        v = (val or "").strip().lower()
        if not v or v in ("none", "currentcolor", "transparent"):
            return True
        if v.startswith("url(") or v.startswith("var("):
            return True
        return False

    s = svg_text

    def repl_attr(m):
        prefix, val, suffix = m.group(1), m.group(2), m.group(3)
        if _skip_paint_value(val):
            return m.group(0)
        return prefix + "currentColor" + suffix

    s = re.sub(r'(fill\s*=\s*["\'])([^"\']+)(["\'])', repl_attr, s, flags=re.IGNORECASE)
    s = re.sub(r'(stroke\s*=\s*["\'])([^"\']+)(["\'])', repl_attr, s, flags=re.IGNORECASE)
    s = re.sub(r'(stop-color\s*=\s*["\'])([^"\']+)(["\'])', repl_attr, s, flags=re.IGNORECASE)
    s = re.sub(r'(flood-color\s*=\s*["\'])([^"\']+)(["\'])', repl_attr, s, flags=re.IGNORECASE)

    def repl_style_prop(m):
        prefix, val = m.group(1), m.group(2)
        if _skip_paint_value(val):
            return m.group(0)
        return prefix + "currentColor"

    s = re.sub(r"(fill\s*:\s*)([^;\"']+)(?=[;\"'\]])", repl_style_prop, s, flags=re.IGNORECASE)
    s = re.sub(r"(stroke\s*:\s*)([^;\"']+)(?=[;\"'\]])", repl_style_prop, s, flags=re.IGNORECASE)
    s = re.sub(r"(stop-color\s*:\s*)([^;\"']+)(?=[;\"'\]])", repl_style_prop, s, flags=re.IGNORECASE)
    s = re.sub(r"(flood-color\s*:\s*)([^;\"']+)(?=[;\"'\]])", repl_style_prop, s, flags=re.IGNORECASE)

    if not re.search(r"currentColor", s, flags=re.IGNORECASE):
        s = _ensure_root_svg_fill_current_color(s)
    return s


def normalize_svg_file_inplace_if_needed(abs_path: str) -> bool:
    """
    1 ファイルを読み、normalize_svg_paints_to_current_color 適用後に内容が変われば UTF-8 で上書きする。
    変更したら True。
    """
    if not abs_path or not os.path.isfile(abs_path):
        return False
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            original = f.read()
    except OSError:
        return False
    normalized = normalize_svg_paints_to_current_color(original)
    if normalized == original:
        return False
    try:
        with open(abs_path, "w", encoding="utf-8", newline="\n") as wf:
            wf.write(normalized)
    except OSError:
        return False
    return True


def batch_normalize_icon_svgs_inplace(project_root: str, game_path: str) -> List[str]:
    """
    共通 assets/icons とゲーム assets/icons 内の全 .svg を走査し、
    具象色を currentColor に寄せた版へ上書きする（内容が変わったファイルのみ）。

    戻り値: 更新したファイルの絶対パス（空なら無変更）。
    """
    seen: Set[str] = set()
    changed: List[str] = []

    def scan_dir(d: str) -> None:
        if not d or not os.path.isdir(d):
            return
        try:
            names = sorted(os.listdir(d), key=lambda x: x.lower())
        except OSError:
            return
        for fn in names:
            if not fn.lower().endswith(".svg"):
                continue
            ap = os.path.normpath(os.path.join(d, fn))
            if ap in seen:
                continue
            seen.add(ap)
            if normalize_svg_file_inplace_if_needed(ap):
                changed.append(ap)

    scan_dir(common_icons_dir(project_root))
    scan_dir(game_icons_dir(game_path))
    return changed


def list_svg_icon_entries(project_root: str, game_path: str) -> List[Dict[str, Any]]:
    """
    利用可能な SVG アイコン一覧。同一 ID は game が common を上書き。
    各要素: id, abs_path, scope ('common'|'game')
    """
    by_id: Dict[str, Dict[str, Any]] = {}

    cdir = common_icons_dir(project_root)
    if os.path.isdir(cdir):
        for fn in sorted(os.listdir(cdir), key=lambda x: x.lower()):
            if not fn.lower().endswith(".svg"):
                continue
            bid = fn[:-4]
            if not _ID_RE.match(bid):
                continue
            by_id[bid] = {"id": bid, "abs_path": os.path.join(cdir, fn), "scope": "common"}

    gdir = game_icons_dir(game_path)
    if os.path.isdir(gdir):
        for fn in sorted(os.listdir(gdir), key=lambda x: x.lower()):
            if not fn.lower().endswith(".svg"):
                continue
            bid = fn[:-4]
            if not _ID_RE.match(bid):
                continue
            by_id[bid] = {"id": bid, "abs_path": os.path.join(gdir, fn), "scope": "game"}

    return sorted(by_id.values(), key=lambda x: (x["scope"] == "common", x["id"].lower()))


def resolve_svg_icon(project_root: str, game_path: str, icon_id: str) -> Optional[Dict[str, Any]]:
    """icon_id に対応するファイルを解決。無ければ None。"""
    if not icon_id or not isinstance(icon_id, str):
        return None
    icon_id = icon_id.strip()
    if not _ID_RE.match(icon_id):
        return None
    gpath = os.path.join(game_icons_dir(game_path), icon_id + ".svg")
    if os.path.isfile(gpath):
        return {"id": icon_id, "abs_path": os.path.normpath(gpath), "scope": "game"}
    cpath = os.path.join(common_icons_dir(project_root), icon_id + ".svg")
    if os.path.isfile(cpath):
        return {"id": icon_id, "abs_path": os.path.normpath(cpath), "scope": "common"}
    return None


def svg_placeholder_pil_rgba(size_px: int, current_color_hex: str):
    """
    Cairo 未使用時など SVG をラスタ化できない場合の簡易アイコン（＋印）。
    Pillow のみで描画する。
    """
    from PIL import Image, ImageDraw

    size_px = max(4, int(round(size_px)))
    h = (current_color_hex or "#ffffff").strip()
    if not h.startswith("#") or len(h) != 7:
        h = "#ffffff"
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    im = Image.new("RGBA", (size_px, size_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    pad = max(1, size_px // 6)
    bar = max(2, size_px // 8)
    cx, cy = size_px // 2, size_px // 2
    arm = size_px // 2 - pad
    draw.rectangle([cx - bar // 2, cy - arm, cx + bar // 2, cy + arm], fill=(r, g, b, 255))
    draw.rectangle([cx - arm, cy - bar // 2, cx + arm, cy + bar // 2], fill=(r, g, b, 255))
    return im


def _svg_text_to_pil_cairo(svg_text: str, size_px: int):
    if not _probe_cairo_svg():
        return None
    import cairosvg
    from PIL import Image

    size_px = max(4, int(round(size_px)))
    try:
        png_bytes = cairosvg.svg2png(
            bytestring=svg_text.encode("utf-8"),
            output_width=size_px,
            output_height=size_px,
        )
    except Exception:
        return None
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def _svg_text_to_pil_pymupdf(svg_text: str, size_px: int):
    """
    PyMuPDF で SVG→PDF→ビットマップ。エディタ専用。Cairo 不要。
    複雑な CSS 付き SVG は欠ける場合あり（アイコン用途を想定）。
    """
    if not _probe_pymupdf():
        return None
    import fitz
    from PIL import Image

    size_px = max(4, int(round(size_px)))
    doc = None
    pdf = None
    try:
        doc = fitz.open(stream=svg_text.encode("utf-8"), filetype="svg")
        if doc.page_count < 1:
            return None
        pdf_bytes = doc.convert_to_pdf()
    except Exception:
        return None
    finally:
        if doc is not None:
            doc.close()

    if not pdf_bytes:
        return None
    try:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = pdf[0]
        r = page.rect
        w, h = float(r.width), float(r.height)
        if w <= 0 or h <= 0:
            return None
        scale = size_px / max(w, h)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        png_data = pix.tobytes("png")
        im = Image.open(io.BytesIO(png_data)).convert("RGBA")
        if im.width != size_px or im.height != size_px:
            im = im.resize((size_px, size_px), Image.Resampling.LANCZOS)
        return im
    except Exception:
        return None
    finally:
        if pdf is not None:
            pdf.close()


def svg_file_to_pil_rgba(abs_path: str, size_px: int, current_color_hex: str):
    """
    SVG を指定サイズの PIL RGBA にラスタ化。currentColor は事前に置換。
    利用順: cairosvg（Cairo 利用可時）→ PyMuPDF → None。
    """
    size_px = max(4, int(round(size_px)))
    if not is_svg_raster_available():
        return None
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            svg_text = f.read()
    except OSError:
        return None
    svg_text = normalize_svg_paints_to_current_color(svg_text)
    svg_text = replace_current_color(svg_text, current_color_hex)
    im = _svg_text_to_pil_cairo(svg_text, size_px)
    if im is not None:
        return im
    im = _svg_text_to_pil_pymupdf(svg_text, size_px)
    if im is not None:
        return im
    return None


def svg_or_placeholder_pil_rgba(abs_path: str, size_px: int, current_color_hex: str):
    """
    SVG をラスタ化。Cairo 不可・変換失敗時は、ファイルが存在すればプレースホルダーを返す。
    """
    im = svg_file_to_pil_rgba(abs_path, size_px, current_color_hex)
    if im is not None:
        return im
    if abs_path and os.path.isfile(abs_path):
        return svg_placeholder_pil_rgba(size_px, current_color_hex)
    return None
