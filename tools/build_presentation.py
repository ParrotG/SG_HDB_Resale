"""Rebuild the CA6003 presentation from the verified notebook figures and script."""

from __future__ import annotations

import argparse
import copy
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PPTX = ROOT / "docs" / "CA6003_HDB_Resale.pptx"
SCRIPT = ROOT / "docs" / "presentation_script.md"
TEMP_PPTX = PPTX.with_suffix(".rebuilt.pptx")

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"

SLIDE_W = 12_192_000
SLIDE_H = 6_858_000
INCH = 914_400

COLORS = {
    "ink": "173238",
    "teal": "1D5C59",
    "teal2": "3A7771",
    "coral": "D6654F",
    "gold": "E4A64A",
    "cream": "F4F0E8",
    "paper": "FBFAF7",
    "white": "FFFFFF",
    "muted": "5E6E70",
    "pale_teal": "DDE9E5",
    "pale_coral": "F4DFD9",
    "line": "D6DDD9",
}


def emu(value: float) -> int:
    return int(round(value * INCH))


def rgb_fill(color: str) -> str:
    return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'


def no_line() -> str:
    return '<a:ln><a:noFill/></a:ln>'


class SlideBuilder:
    def __init__(self, number: int, title: str, presenter: str, time_range: str, dark: bool = False):
        self.number = number
        self.title = title
        self.presenter = presenter
        self.time_range = time_range
        self.dark = dark
        self.shape_id = 1
        self.relationships: list[tuple[str, Path, str]] = []
        self.parts: list[str] = []
        self.background = COLORS["ink"] if dark else COLORS["cream"]

    def next_id(self) -> int:
        self.shape_id += 1
        return self.shape_id

    def add_text(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        text: str,
        *,
        size: float = 18,
        color: str | None = None,
        bold: bool = False,
        font: str = "Aptos",
        align: str = "l",
        valign: str = "t",
        fill: str | None = None,
        line: str | None = None,
        radius: bool = False,
        margin: float = 0.08,
        name: str = "Text",
    ) -> None:
        sid = self.next_id()
        color = color or (COLORS["white"] if self.dark else COLORS["ink"])
        geometry = "roundRect" if radius else "rect"
        sp_fill = rgb_fill(fill) if fill else "<a:noFill/>"
        sp_line = f'<a:ln w="12700">{rgb_fill(line)}</a:ln>' if line else no_line()
        paragraphs = []
        for line_text in text.split("\n"):
            safe = escape(line_text)
            paragraphs.append(
                f'<a:p><a:pPr algn="{align}"/>'
                f'<a:r><a:rPr lang="en-SG" sz="{int(size * 100)}" '
                f'b="{1 if bold else 0}" dirty="0">{rgb_fill(color)}'
                f'<a:latin typeface="{escape(font)}"/></a:rPr><a:t>{safe}</a:t></a:r>'
                f'<a:endParaRPr lang="en-SG" sz="{int(size * 100)}"/></a:p>'
            )
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)} {sid}"/>'
            '<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/>'
            f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geometry}"><a:avLst/></a:prstGeom>{sp_fill}{sp_line}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="{emu(margin)}" tIns="{emu(margin)}" '
            f'rIns="{emu(margin)}" bIns="{emu(margin)}" anchor="{valign}"/>'
            f'<a:lstStyle/>{"".join(paragraphs)}</p:txBody></p:sp>'
        )

    def add_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str,
        line: str | None = None,
        radius: bool = False,
        name: str = "Panel",
    ) -> None:
        sid = self.next_id()
        geometry = "roundRect" if radius else "rect"
        sp_line = f'<a:ln w="12700">{rgb_fill(line)}</a:ln>' if line else no_line()
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)} {sid}"/>'
            '<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geometry}"><a:avLst/></a:prstGeom>{rgb_fill(fill)}{sp_line}'
            '</p:spPr></p:sp>'
        )

    def add_line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: int = 2) -> None:
        sid = self.next_id()
        self.parts.append(
            f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{sid}" name="Line {sid}"/>'
            '<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{emu(x1)}" y="{emu(y1)}"/>'
            f'<a:ext cx="{emu(x2-x1)}" cy="{emu(y2-y1)}"/></a:xfrm>'
            f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f'<a:ln w="{width * 12700}">{rgb_fill(color)}</a:ln></p:spPr></p:cxnSp>'
        )

    def add_image(
        self,
        path: Path,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        contain: bool = True,
        alt: str = "Notebook figure",
        card: bool = True,
    ) -> None:
        if card:
            self.add_rect(x, y, w, h, fill=COLORS["white"], line=COLORS["line"], radius=True, name="Figure card")
        with Image.open(path) as image:
            iw, ih = image.size
        if contain:
            scale = min(w / iw, h / ih)
            pw, ph = iw * scale, ih * scale
            px, py = x + (w - pw) / 2, y + (h - ph) / 2
        else:
            px, py, pw, ph = x, y, w, h
        rid = f"rId{3 + len(self.relationships)}"
        media_name = f"slide{self.number}_{len(self.relationships)+1}_{path.name}"
        self.relationships.append((rid, path, media_name))
        sid = self.next_id()
        self.parts.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="Figure {sid}" descr="{escape(alt)}"/>'
            '<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr><a:xfrm><a:off x="{emu(px)}" y="{emu(py)}"/>'
            f'<a:ext cx="{emu(pw)}" cy="{emu(ph)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        )

    def add_header(self, kicker: str, title_size: float = 27) -> None:
        if self.dark:
            return
        self.add_text(0.45, 0.20, 8.7, 0.30, kicker.upper(), size=10.5, color=COLORS["teal2"], bold=True)
        self.add_text(0.45, 0.52, 10.9, 0.58, self.title, size=title_size, color=COLORS["ink"], bold=True)
        self.add_text(10.65, 0.24, 2.20, 0.32, f"{self.presenter}  ·  {self.time_range}", size=9.5,
                      color=COLORS["white"], bold=True, align="ctr", valign="ctr",
                      fill=COLORS["teal"], radius=True, margin=0.02)
        self.add_line(0.45, 1.14, 12.88, 1.14, COLORS["line"], 1)
        self.add_text(12.42, 6.48, 0.46, 0.22, f"{self.number:02d}", size=9.5, color=COLORS["muted"], align="r")

    def add_bullet(self, x: float, y: float, w: float, text: str, *, color: str | None = None, size: float = 17) -> None:
        dot_color = color or COLORS["coral"]
        self.add_text(x, y + 0.02, 0.23, 0.25, "●", size=8, color=dot_color)
        self.add_text(x + 0.28, y, w - 0.28, 0.55, text, size=size, color=COLORS["ink"], margin=0)

    def xml(self) -> bytes:
        background = rgb_fill(self.background)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sld xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}" showMasterSp="0">'
            f'<p:cSld><p:bg><p:bgPr>{background}<a:effectLst/></p:bgPr></p:bg>'
            '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/>'
            '</p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            f'{"".join(self.parts)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/>'
            '</p:clrMapOvr></p:sld>'
        ).encode("utf-8")

    def rels_xml(self) -> bytes:
        rels = [
            f'<Relationship Id="rId1" Type="{R}/slideLayout" Target="../slideLayouts/slideLayout6.xml"/>',
            f'<Relationship Id="rId2" Type="{R}/notesSlide" Target="../notesSlides/notesSlide{self.number}.xml"/>',
        ]
        for rid, _, media_name in self.relationships:
            rels.append(f'<Relationship Id="{rid}" Type="{R}/image" Target="../media/{escape(media_name)}"/>')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{REL}">{"".join(rels)}</Relationships>'
        ).encode("utf-8")


def metric(builder: SlideBuilder, x: float, y: float, w: float, value: str, label: str,
           color: str = "teal", fill: str = "white") -> None:
    builder.add_rect(x, y, w, 1.0, fill=COLORS[fill], line=COLORS["line"], radius=True, name="Metric")
    builder.add_text(x + 0.15, y + 0.09, w - 0.30, 0.40, value, size=23, color=COLORS[color], bold=True, margin=0)
    builder.add_text(x + 0.15, y + 0.54, w - 0.30, 0.30, label, size=10.5, color=COLORS["muted"], margin=0)


def panel_label(builder: SlideBuilder, x: float, y: float, w: float, text: str, number: str,
                fill: str = "pale_teal", accent: str = "teal") -> None:
    builder.add_rect(x, y, w, 0.72, fill=COLORS[fill], radius=True, name="Process step")
    builder.add_text(x + 0.12, y + 0.13, 0.45, 0.32, number, size=12, color=COLORS[accent], bold=True, margin=0)
    builder.add_text(x + 0.56, y + 0.11, w - 0.68, 0.40, text, size=14, color=COLORS["ink"], bold=True, margin=0)


def parse_notes() -> dict[int, str]:
    text = SCRIPT.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## Slide (\d+) — .*?$", text)
    notes = {}
    for i in range(1, len(sections), 2):
        number = int(sections[i])
        body = sections[i + 1].strip()
        lines = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^[-*]\s+", "", line)
            line = line.replace("**", "")
            lines.append(line)
        notes[number] = "\n\n".join(lines)
    return notes


def notes_xml(number: int, text: str) -> bytes:
    paragraphs = []
    for paragraph in text.split("\n\n"):
        paragraphs.append(
            '<a:p><a:r><a:rPr lang="en-SG" sz="1200" dirty="0"/>'
            f'<a:t>{escape(paragraph)}</a:t></a:r><a:endParaRPr lang="en-SG" sz="1200"/></a:p>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:notes xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"><p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image Placeholder 1"/>'
        '<p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph type="sldImg"/></p:nvPr></p:nvSpPr><p:spPr/></p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes Placeholder 2"/>'
        '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/>'
        f'</p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{"".join(paragraphs)}'
        '</p:txBody></p:sp><p:sp><p:nvSpPr><p:cNvPr id="4" name="Slide Number Placeholder 3"/>'
        '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldNum" idx="5"/>'
        '</p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>'
        f'<a:p><a:r><a:t>{number}</a:t></a:r></a:p></p:txBody></p:sp>'
        '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>'
    ).encode("utf-8")


def build_slides() -> list[SlideBuilder]:
    slides: list[SlideBuilder] = []

    s = SlideBuilder(1, "The question behind a town price map", "ParrotG", "0:00–0:45", dark=True)
    s.add_text(0.60, 0.45, 4.0, 0.32, "CA6003  ·  HDB RESALE  ·  2017–2025", size=11, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(0.60, 1.05, 7.2, 1.38, "When does a town\npremium disappear?", size=34, color=COLORS["white"], bold=True, margin=0)
    s.add_text(0.60, 2.62, 5.7, 0.72, "Housing composition, prediction reliability\nand data governance", size=17.5, color="CFDEDA", margin=0)
    s.add_rect(0.60, 4.00, 5.0, 1.20, fill="23454A", line="3E6668", radius=True)
    s.add_text(0.82, 4.17, 1.80, 0.48, "+26.0%", size=27, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(2.52, 4.20, 0.55, 0.40, "→", size=23, color=COLORS["white"], bold=True, align="ctr", margin=0)
    s.add_text(3.08, 4.17, 1.90, 0.48, "−12.5%", size=27, color=COLORS["coral"], bold=True, margin=0)
    s.add_text(0.82, 4.68, 4.40, 0.25, "PASIR RIS relative to BEDOK: M0 → M4", size=10.5, color="CFDEDA", margin=0)
    s.add_text(0.60, 5.72, 5.9, 0.35, "222,066 resale registrations  ·  Evidence before complexity", size=11.5, color=COLORS["white"], margin=0)
    s.add_image(ROOT / "figures" / "06_town_premium_maps_dark.png", 6.65, 0.70, 6.05, 5.55,
                alt="Town premium maps before and after housing controls", card=False)
    s.add_text(11.90, 6.48, 0.55, 0.22, "01", size=9.5, color="A9BEBA", align="r")
    slides.append(s)

    s = SlideBuilder(2, "Data quality: small counts, mandatory decisions", "ParrotG", "0:45–1:40")
    s.add_header("Profile → decide → audit")
    metric(s, 0.55, 1.38, 2.55, "222,066", "SOURCE ROWS", "teal")
    metric(s, 3.25, 1.38, 2.55, "−437", "RESOLVED EXCLUSIONS", "coral")
    metric(s, 5.95, 1.38, 2.55, "221,629", "ANALYTICAL ROWS", "teal")
    metric(s, 8.65, 1.38, 2.55, "99.803%", "SOURCE RETAINED", "gold")
    panel_label(s, 0.65, 2.72, 3.62, "Literal and type checks", "01")
    s.add_text(0.84, 3.58, 3.25, 1.16, "No missing values\nNo blank or padded labels\nNo numeric parse failures", size=16, color=COLORS["ink"], margin=0)
    panel_label(s, 4.57, 2.72, 3.62, "Evidence-based exclusions", "02", "pale_coral", "coral")
    s.add_text(4.76, 3.58, 3.25, 1.16, "309 duplicate excess rows\n128 unresolved lease records\nOne representative per group", size=16, color=COLORS["ink"], margin=0)
    panel_label(s, 8.49, 2.72, 3.62, "Keep valid market tails", "03", "pale_teal", "teal")
    s.add_text(8.68, 3.58, 3.25, 1.16, "No automatic IQR deletion\nHigh-price MAE worsens\nby SGD 4,009 after trimming", size=16, color=COLORS["ink"], margin=0)
    s.add_rect(0.65, 5.42, 11.45, 0.72, fill=COLORS["ink"], radius=True)
    s.add_text(0.90, 5.59, 10.90, 0.30, "Audit assertions keep every excluded index out of EDA, inference, training, validation and test.",
               size=14, color=COLORS["white"], bold=True, align="ctr", margin=0)
    slides.append(s)

    s = SlideBuilder(3, "Encoding follows the meaning of each field", "ParrotG", "1:40–2:40")
    s.add_header("Semantics before algorithms")
    items = [
        ("Flat Type / Model", "One-hot categories", "No artificial order"),
        ("Storey Range", "Ordinal summary; categorical fit", "No equal-step assumption"),
        ("Remaining Lease", "Fractional years", "Comparable numeric scale"),
        ("Month", "Time trend + seasonality", "Chronological evaluation"),
        ("Town → Street → Block", "Earlier-year hierarchy", "Sparse addresses shrink upward"),
    ]
    y = 1.45
    for i, (field, encoding, reason) in enumerate(items, 1):
        fill = "pale_teal" if i % 2 else "white"
        s.add_rect(0.55, y, 4.95, 0.78, fill=COLORS[fill], line=COLORS["line"], radius=True)
        s.add_text(0.72, y + 0.13, 1.56, 0.28, field, size=12.5, color=COLORS["teal"], bold=True, margin=0)
        s.add_text(2.28, y + 0.10, 2.98, 0.34, encoding, size=11.8, color=COLORS["ink"], bold=True, margin=0)
        s.add_text(2.28, y + 0.48, 2.98, 0.18, reason, size=9.0, color=COLORS["muted"], margin=0)
        y += 0.88
    s.add_image(ROOT / "figures" / "01_category_shares.png", 5.75, 1.43, 6.45, 2.62,
                alt="Flat type and flat model transaction shares")
    s.add_rect(5.75, 4.26, 6.45, 1.64, fill=COLORS["ink"], radius=True)
    s.add_text(6.03, 4.52, 2.88, 0.42, "0.959 → 0.038", size=22, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(6.03, 5.03, 2.82, 0.30, "Price skewness after log transform", size=10.0, color="CFDEDA", margin=0)
    s.add_text(9.05, 4.48, 2.78, 0.86, "Log price limits domination by the most expensive sales and supports percentage-style coefficients.",
               size=13, color=COLORS["white"], margin=0)
    slides.append(s)

    s = SlideBuilder(4, "Imbalance changes what ‘average performance’ means", "YuyaoWu61", "2:40–3:35")
    s.add_header("Coverage and weighting")
    metric(s, 0.55, 1.48, 2.20, "42.3%", "4 ROOM SHARE", "teal")
    metric(s, 2.95, 1.48, 2.20, "79 / 84", "TWO RAREST TYPES", "coral")
    s.add_bullet(0.62, 2.80, 4.55, "Town × Flat Type support is uneven.")
    s.add_bullet(0.62, 3.48, 4.55, "No category is entirely unseen in 2025.")
    s.add_bullet(0.62, 4.16, 4.55, "Small groups still yield unstable errors.")
    s.add_rect(0.62, 5.05, 4.55, 0.94, fill=COLORS["ink"], radius=True)
    s.add_text(0.85, 5.19, 1.52, 0.36, "48,728 → 47,265", size=18, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(2.42, 5.20, 2.48, 0.42, "Town macro-MAE after equal-Town weighting", size=11, color=COLORS["white"], margin=0)
    s.add_image(ROOT / "figures" / "04_representation_support.png", 5.48, 1.40, 6.70, 4.88,
                alt="Heatmap of common support across Town and Flat Type")
    slides.append(s)

    s = SlideBuilder(5, "Hedonic pricing makes the comparison explicit", "YuyaoWu61", "3:35–4:30")
    s.add_header("Same rows, sequential controls")
    stages = [
        ("M0", "Town only"),
        ("M1", "+ registration month"),
        ("M2", "+ log floor area"),
        ("M3", "+ Flat Type and Model"),
        ("M4", "+ Storey Range and lease"),
    ]
    y = 1.44
    for code, label in stages:
        s.add_text(0.62, y, 0.64, 0.52, code, size=15, color=COLORS["white"], bold=True,
                   align="ctr", valign="ctr", fill=COLORS["teal"], radius=True, margin=0)
        s.add_text(1.40, y + 0.04, 3.22, 0.38, label, size=15, color=COLORS["ink"], bold=True, margin=0)
        y += 0.86
    s.add_text(0.66, 5.76, 3.95, 0.40, "Outcome: log(resale price)\nBEDOK reference · building-clustered uncertainty", size=10.5, color=COLORS["muted"], margin=0)
    s.add_image(ROOT / "figures" / "05_town_coefficient_path.png", 4.92, 1.40, 7.23, 4.86,
                alt="Town coefficients and PASIR RIS path before and after controls")
    slides.append(s)

    s = SlideBuilder(6, "The non-obvious finding survives stronger comparisons", "YuyaoWu61", "4:30–5:55")
    s.add_header("Interpret the reversal; challenge the attribution", title_size=23.5)
    s.add_rect(0.55, 1.42, 4.30, 1.12, fill=COLORS["ink"], radius=True)
    s.add_text(0.80, 1.63, 3.60, 0.48, "+26.0%  →  −12.5%", size=22, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(0.80, 2.09, 3.65, 0.20, "PASIR RIS relative to BEDOK · M0 → M4", size=9.5, color="CFDEDA", margin=0)
    s.add_rect(0.55, 2.78, 2.04, 1.00, fill=COLORS["white"], line=COLORS["line"], radius=True)
    s.add_text(0.70, 2.91, 1.72, 0.34, "1.1–84.0%", size=17, color=COLORS["coral"], bold=True, margin=0)
    s.add_text(0.70, 3.38, 1.72, 0.22, "AREA SHARE ACROSS ORDERS", size=8.5, color=COLORS["muted"], margin=0)
    s.add_rect(2.80, 2.78, 2.04, 1.00, fill=COLORS["white"], line=COLORS["line"], radius=True)
    s.add_text(2.95, 2.91, 1.72, 0.34, "−10.8%", size=20, color=COLORS["teal"], bold=True, margin=0)
    s.add_text(2.95, 3.38, 1.72, 0.22, "STRICT SUPPORT RESULT", size=8.5, color=COLORS["muted"], margin=0)
    s.add_bullet(0.62, 4.10, 4.16, "Type/Model first also reverses the sign.", size=15)
    s.add_bullet(0.62, 4.77, 4.16, "Strict joint support: 387 transactions.", size=15)
    s.add_bullet(0.62, 5.44, 4.16, "Composition reversal; not a causal Town effect.", size=15)
    s.add_image(ROOT / "figures" / "09_control_order_sensitivity.png", 5.14, 1.40, 7.04, 2.45,
                alt="Sensitivity of housing-block attribution to control order")
    s.add_image(ROOT / "figures" / "08_common_support_sensitivity.png", 5.14, 4.02, 7.04, 2.12,
                alt="PASIR RIS and BEDOK effects under common-support restrictions")
    slides.append(s)

    s = SlideBuilder(7, "Minimal versus systematic preparation", "drury", "5:55–7:05")
    s.add_header("One model class; five preparation stages")
    s.add_image(ROOT / "figures" / "12_preparation_comparison.png", 4.43, 1.42, 7.78, 4.70,
                alt="Prediction error across B0 to B4 preparation stages")
    stages = [
        ("B0", "Minimal source-like"),
        ("B1", "Categorical structure"),
        ("B2", "Functional forms"),
        ("B3", "Log target"),
        ("B4", "Historical address"),
    ]
    y = 1.50
    for code, label in stages:
        s.add_text(0.58, y, 0.62, 0.48, code, size=14, color=COLORS["white"], bold=True,
                   align="ctr", valign="ctr", fill=COLORS["teal"] if code != "B4" else COLORS["coral"],
                   radius=True, margin=0)
        s.add_text(1.38, y + 0.04, 2.65, 0.34, label, size=14, color=COLORS["ink"], bold=True, margin=0)
        y += 0.70
    s.add_rect(0.58, 5.22, 3.43, 0.89, fill=COLORS["ink"], radius=True)
    s.add_text(0.78, 5.35, 1.42, 0.35, "−22.6%", size=22, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(2.13, 5.34, 1.60, 0.38, "2025 MAE\n59,789 → 46,298", size=10.5, color=COLORS["white"], margin=0)
    slides.append(s)

    s = SlideBuilder(8, "Aggregate improvement concealed local failure", "drury", "7:05–8:15")
    s.add_header("Error analysis before claiming reliability")
    metric(s, 0.55, 1.40, 2.06, "+20,310", "BUKIT BATOK · B4−B0 MAE", "coral")
    metric(s, 2.82, 1.40, 2.06, "+10,873", "TAMPINES · B4−B0 MAE", "coral")
    s.add_bullet(0.62, 2.77, 4.23, "Deterioration persists across all 12 months.", size=15)
    s.add_bullet(0.62, 3.44, 4.23, "Common 4 ROOM and 5 ROOM groups dominate.", size=15)
    s.add_bullet(0.62, 4.11, 4.23, "Mix standardization explains little.", size=15)
    s.add_rect(0.62, 5.02, 4.20, 1.05, fill=COLORS["ink"], radius=True)
    s.add_text(0.84, 5.17, 1.58, 0.36, "+330 → +14,603", size=17.5, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(2.47, 5.16, 2.08, 0.42, "Signed error when nominal\naddress encoding enters", size=10.5, color=COLORS["white"], margin=0)
    s.add_image(ROOT / "error_analysis_outputs" / "01_stage_error.png", 5.10, 1.40, 7.10, 2.37,
                alt="Preparation-stage errors overall and in two focus Towns")
    s.add_image(ROOT / "error_analysis_outputs" / "04_address_mechanism.png", 5.10, 3.95, 7.10, 2.17,
                alt="Prediction decomposition and frozen-history sensitivity")
    slides.append(s)

    s = SlideBuilder(9, "Remove market time from the address feature", "TomoyoCin", "8:15–9:45")
    s.add_header("Diagnose → redesign → validate")
    s.add_rect(0.55, 1.40, 3.88, 1.03, fill=COLORS["ink"], radius=True)
    s.add_text(0.78, 1.56, 1.30, 0.40, "0.195 → −0.001", size=21, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(2.08, 1.57, 2.02, 0.40, "Feature–time correlation\nnominal → residual", size=10.5, color=COLORS["white"], margin=0)
    metric(s, 0.55, 2.68, 1.80, "47,232", "NO ADDRESS MAE", "muted")
    metric(s, 2.56, 2.68, 1.87, "31,606", "RESIDUAL ADDRESS MAE", "teal")
    s.add_bullet(0.62, 4.03, 3.75, "N3 uses strictly earlier-year residuals.", size=14.5)
    s.add_bullet(0.62, 4.70, 3.75, "Selected on 2024 validation only.", size=14.5)
    s.add_bullet(0.62, 5.37, 3.75, "Lowest MAE in 3 of 4 origins.", size=14.5)
    s.add_image(ROOT / "section16_outputs" / "01_time_normalized_address.png", 4.73, 1.40, 7.47, 2.36,
                alt="Time-normalized address encoding results")
    s.add_image(ROOT / "section16_outputs" / "02_rolling_origin.png", 4.73, 3.94, 7.47, 2.18,
                alt="Rolling-origin MAE and signed error")
    slides.append(s)

    s = SlideBuilder(10, "Block precision has a measurable governance cost", "TomoyoCin", "9:45–10:40")
    s.add_header("Privacy–utility trade-off")
    metric(s, 0.55, 1.45, 2.08, "95.1%", "UNIQUE AT BLOCK LEVEL", "coral")
    metric(s, 2.84, 1.45, 2.08, "60.1%", "UNIQUE AT STREET LEVEL", "teal")
    s.add_bullet(0.62, 2.82, 4.22, "Street retains 74.5% of the address gain.", size=15)
    s.add_bullet(0.62, 3.52, 4.22, "Block adds SGD 3,989 of MAE improvement.", size=15)
    s.add_bullet(0.62, 4.22, 4.22, "Block raises uniqueness by 35.0 points.", size=15)
    s.add_rect(0.62, 5.12, 4.22, 0.98, fill=COLORS["pale_teal"], line=COLORS["teal"], radius=True)
    s.add_text(0.84, 5.32, 3.80, 0.38, "Street precision is a plausible policy compromise—subject to further testing.",
               size=12.5, color=COLORS["ink"], bold=True, margin=0)
    s.add_image(ROOT / "section17_outputs" / "02_privacy_utility_frontier.png", 5.14, 1.40, 7.02, 4.75,
                alt="Privacy-utility frontier for Town, Street and Block precision")
    slides.append(s)

    s = SlideBuilder(11, "What the evidence changes", "TomoyoCin + team", "10:40–11:20", dark=True)
    s.add_text(0.60, 0.38, 5.80, 0.32, "CONCLUSION  ·  DATA-CENTRIC REASONING", size=10.5, color=COLORS["gold"], bold=True, margin=0)
    s.add_text(0.60, 0.92, 8.90, 0.70, "A raw Town map was the beginning, not the answer.", size=29, color=COLORS["white"], bold=True, margin=0)
    flow = [
        ("PROFILE", "Surface quality\n+ hidden decisions"),
        ("PREPARE", "Semantics\n+ consistent exclusions"),
        ("CHALLENGE", "Support, order\n+ subgroup errors"),
        ("REVISE", "Residual address\n+ time separation"),
        ("VALIDATE", "Rolling origins\n+ governance cost"),
    ]
    x = 0.62
    for i, (head, body) in enumerate(flow):
        fill = "24464A" if i % 2 == 0 else "1E3C40"
        s.add_rect(x, 2.02, 2.22, 1.48, fill=fill, line="456A6B", radius=True)
        s.add_text(x + 0.16, 2.20, 1.90, 0.28, head, size=11, color=COLORS["gold"], bold=True, margin=0)
        s.add_text(x + 0.16, 2.62, 1.90, 0.52, body, size=13.5, color=COLORS["white"], bold=True, margin=0)
        x += 2.46
    s.add_rect(0.62, 4.08, 7.15, 1.48, fill="23454A", line="3E6668", radius=True)
    s.add_text(0.88, 4.28, 6.62, 0.94, "Housing composition reverses the PASIR RIS comparison.\nPrediction gains are real—but reliability is uneven and period-dependent.",
               size=16.5, color=COLORS["white"], bold=True, margin=0)
    s.add_rect(8.07, 4.08, 4.02, 1.48, fill=COLORS["coral"], radius=True)
    s.add_text(8.34, 4.28, 3.50, 0.94, "Interpret the model as evidence\nfor preparation decisions.",
               size=16.5, color=COLORS["white"], bold=True, margin=0)
    s.add_text(0.62, 5.82, 11.35, 0.42, "Limits: observational data · omitted renovation and accessibility · planning-area map proxies · imperfect future time trends",
               size=11.5, color="CFDEDA", margin=0)
    s.add_text(11.85, 6.48, 0.60, 0.22, "11", size=9.5, color="A9BEBA", align="r")
    slides.append(s)

    return slides


def update_content_types(data: bytes) -> bytes:
    root = ET.fromstring(data)
    has_png = any(node.tag == f"{{{CT}}}Default" and node.attrib.get("Extension") == "png" for node in root)
    if not has_png:
        root.insert(0, ET.Element(f"{{{CT}}}Default", Extension="png", ContentType="image/png"))
    for node in list(root):
        part = node.attrib.get("PartName", "")
        if part in {
            "/ppt/slides/slide12.xml", "/ppt/slides/slide13.xml",
            "/ppt/notesSlides/notesSlide12.xml", "/ppt/notesSlides/notesSlide13.xml",
        }:
            root.remove(node)
    ET.register_namespace("", CT)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_presentation(data: bytes, removed_rids: set[str]) -> bytes:
    root = ET.fromstring(data)
    for parent in root.iter():
        for child in list(parent):
            if child.tag == f"{{{P}}}sldId" and child.attrib.get(f"{{{R}}}id") in removed_rids:
                parent.remove(child)
    ET.register_namespace("a", A)
    ET.register_namespace("r", R)
    ET.register_namespace("p", P)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_presentation_rels(data: bytes) -> tuple[bytes, set[str]]:
    root = ET.fromstring(data)
    removed = set()
    for node in list(root):
        if node.attrib.get("Target") in {"slides/slide12.xml", "slides/slide13.xml"}:
            removed.add(node.attrib["Id"])
            root.remove(node)
    ET.register_namespace("", REL)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), removed


def update_app(data: bytes) -> bytes:
    root = ET.fromstring(data)
    for node in root.iter():
        if node.tag.endswith("Slides") or node.tag.endswith("Notes"):
            node.text = "11"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_core(data: bytes) -> bytes:
    root = ET.fromstring(data)
    for node in root.iter():
        if node.tag.endswith("title"):
            node.text = "When Does a Town Premium Disappear?"
        elif node.tag.endswith("subject"):
            node.text = "CA6003 HDB resale data preparation, hedonic regression and governance"
        elif node.tag.endswith("modified"):
            node.text = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def normalize_presentation() -> None:
    """Round-trip the generated deck through LibreOffice for PowerPoint compatibility."""
    executable = shutil.which("libreoffice")
    if executable is None:
        raise RuntimeError("LibreOffice is required to normalize the generated PPTX.")

    with tempfile.TemporaryDirectory(prefix="hdb-pptx-") as directory:
        work = Path(directory)
        source = work / "CA6003_HDB_Resale.pptx"
        output = work / "normalized"
        runtime = work / "runtime"
        profile = work / "profile"
        output.mkdir()
        runtime.mkdir(mode=0o700)
        shutil.copy2(PPTX, source)

        environment = os.environ.copy()
        environment["XDG_RUNTIME_DIR"] = str(runtime)
        subprocess.run(
            [
                executable,
                f"-env:UserInstallation=file://{profile}",
                "--headless",
                "--convert-to",
                "pptx",
                "--outdir",
                str(output),
                str(source),
            ],
            check=True,
            env=environment,
        )
        normalized = output / source.name
        if not normalized.exists():
            raise RuntimeError("LibreOffice did not produce the normalized PPTX.")
        shutil.copy2(normalized, TEMP_PPTX)
        TEMP_PPTX.replace(PPTX)


def main(*, normalize_only: bool = False) -> None:
    if normalize_only:
        normalize_presentation()
        print(f"Normalized {PPTX} for PowerPoint compatibility.")
        return

    notes = parse_notes()
    slides = build_slides()
    assert len(slides) == 11
    assert set(notes) == set(range(1, 12))

    with zipfile.ZipFile(PPTX, "r") as source:
        entries = {name: source.read(name) for name in source.namelist()}

    new_presentation_rels, removed_rids = update_presentation_rels(entries["ppt/_rels/presentation.xml.rels"])
    entries["ppt/_rels/presentation.xml.rels"] = new_presentation_rels
    entries["ppt/presentation.xml"] = update_presentation(entries["ppt/presentation.xml"], removed_rids)
    entries["[Content_Types].xml"] = update_content_types(entries["[Content_Types].xml"])
    if "docProps/app.xml" in entries:
        entries["docProps/app.xml"] = update_app(entries["docProps/app.xml"])
    if "docProps/core.xml" in entries:
        entries["docProps/core.xml"] = update_core(entries["docProps/core.xml"])

    remove_paths = {
        "ppt/slides/slide12.xml", "ppt/slides/slide13.xml",
        "ppt/slides/_rels/slide12.xml.rels", "ppt/slides/_rels/slide13.xml.rels",
        "ppt/notesSlides/notesSlide12.xml", "ppt/notesSlides/notesSlide13.xml",
        "ppt/notesSlides/_rels/notesSlide12.xml.rels", "ppt/notesSlides/_rels/notesSlide13.xml.rels",
    }
    for path in remove_paths:
        entries.pop(path, None)

    for slide in slides:
        entries[f"ppt/slides/slide{slide.number}.xml"] = slide.xml()
        entries[f"ppt/slides/_rels/slide{slide.number}.xml.rels"] = slide.rels_xml()
        entries[f"ppt/notesSlides/notesSlide{slide.number}.xml"] = notes_xml(slide.number, notes[slide.number])
        for _, path, media_name in slide.relationships:
            entries[f"ppt/media/{media_name}"] = path.read_bytes()

    with zipfile.ZipFile(TEMP_PPTX, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name, data in entries.items():
            target.writestr(name, data)
    TEMP_PPTX.replace(PPTX)
    normalize_presentation()
    print(f"Rebuilt and normalized {PPTX} with {len(slides)} slides and speaker notes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="Round-trip the existing deck through LibreOffice without rebuilding it.",
    )
    arguments = parser.parse_args()
    main(normalize_only=arguments.normalize_only)
