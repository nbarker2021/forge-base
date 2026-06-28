from __future__ import annotations
from pathlib import Path
from typing import Iterable, List, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted

from .kit import COLOR_FAMILIES, TOOL_CLASSES, COLOR_PURPOSES, TOOL_PURPOSES, build_eightfold_kit

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
styles.add(ParagraphStyle(name="Tight", parent=styles["BodyText"], fontSize=9, leading=11))


def _doc(path: Path, title: str):
    return SimpleDocTemplate(str(path), pagesize=letter, rightMargin=0.55*inch, leftMargin=0.55*inch, topMargin=0.55*inch, bottomMargin=0.55*inch, title=title)


def _p(text: str, style="BodyText"):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, styles[style])


def build_kit_manual_pdf(path: str | Path):
    path = Path(path)
    story = []
    story.append(_p("Analog Forge Workbook Kit - Manual", "Title"))
    story.append(_p("A hand-operated reasoning system equivalent to the ForgeFactory digital workbench.", "BodyText"))
    story.append(Spacer(1, 0.15*inch))
    story.append(_p("Core loop", "Heading1"))
    story.append(_p("observed action -> loose grey substrate -> three-color gradient -> yes/no continuation -> proof or obligation -> receipt -> bound page or open obligation"))
    story.append(_p("Production rule", "Heading1"))
    story.append(_p("Each color family contains eight copies of every tool class. The eightfold copy rule allows all visible local readout positions to be instantiated at once."))
    story.append(_p("Color families", "Heading1"))
    data = [["Color", "Purpose"]] + [[c, COLOR_PURPOSES[c]] for c in COLOR_FAMILIES]
    tbl = Table(data, colWidths=[1.35*inch, 5.8*inch])
    tbl.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.lightgrey), ("GRID", (0,0), (-1,-1), 0.25, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP"), ("FONTSIZE", (0,0), (-1,-1), 8)]))
    story.append(tbl)
    story.append(PageBreak())
    story.append(_p("Tool classes", "Heading1"))
    data = [["Tool", "Purpose"]] + [[t, TOOL_PURPOSES[t]] for t in TOOL_CLASSES]
    tbl = Table(data, colWidths=[1.6*inch, 5.55*inch], repeatRows=1)
    tbl.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.lightgrey), ("GRID", (0,0), (-1,-1), 0.25, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP"), ("FONTSIZE", (0,0), (-1,-1), 8)]))
    story.append(tbl)
    story.append(PageBreak())
    story.append(_p("Use protocol", "Heading1"))
    protocol = [
        "1. Place an observed action on a loose grey sheet.",
        "2. Add at least three color gradients.",
        "3. Place the C token at the active center.",
        "4. Use notecards to decide whether the state continues or requires a new page.",
        "5. Mark the follow-up as white proof or black obligation.",
        "6. Use strings, tokens, cards, dice, stickers, sleeves, and balsa only according to their roles.",
        "7. Test legal binding.",
        "8. Bind stable states into notebooks; carry unstable states as obligations.",
        "9. Write the receipt so the action can be recovered.",
    ]
    for line in protocol:
        story.append(_p(line))
    story.append(_p("Digital equivalence", "Heading1"))
    story.append(_p("Anything done physically must be recordable digitally. Anything done digitally must be reproducible physically."))
    _doc(path, "Analog Forge Workbook Kit Manual").build(story)


def build_printable_sheets_pdf(path: str | Path):
    path = Path(path)
    story = []
    story.append(_p("Analog Forge Printable Workbook Sheets", "Title"))
    sheet_defs = [
        ("Action Sheet", ["Action ID", "Observed action", "C token position", "Gradient colors", "Continue or new page", "Proof or obligation", "Receipt ID"]),
        ("Receipt Sheet", ["Receipt ID", "Objects used", "Colors used", "Strings connected", "Cards used", "Dice used", "Closure formula", "Open obligations"]),
        ("Gradient Sheet", ["Base grey substrate", "Color 1", "Color 2", "Color 3", "Blend path", "Conjugate trace", "Color loss check"]),
        ("String/Braid Log", ["Source", "Target", "String color", "Relation", "Knot/Braid", "Boundary crossed", "Receipt"]),
        ("Dice Boundary Log", ["Question", "Legal uncertainty condition", "Die", "Roll", "Interpretation", "Receipt"]),
        ("Card Permutation Log", ["Card", "Color", "Suit", "Rank", "Witness/setting role", "Sequence position", "Receipt"]),
        ("Balsa Lattice Log", ["Node", "Edge", "Axis", "Frame", "Spacing rule", "Physical build note", "Digital equivalent"]),
    ]
    for title, fields in sheet_defs:
        story.append(_p(title, "Heading1"))
        rows = [[field, ""] for field in fields]
        tbl = Table(rows, colWidths=[2.2*inch, 4.9*inch], rowHeights=[0.42*inch]*len(rows))
        tbl.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.35, colors.black), ("VALIGN", (0,0), (-1,-1), "TOP"), ("FONTSIZE", (0,0), (-1,-1), 8)]))
        story.append(tbl)
        story.append(PageBreak())
    _doc(path, "Analog Forge Printable Workbook Sheets").build(story)


def build_simulation_guide_pdf(path: str | Path):
    path = Path(path)
    story = []
    story.append(_p("Analog Forge Python Simulation Workbench", "Title"))
    story.append(_p("This guide explains how the Python suite simulates the by-hand kit."))
    story.append(_p("Install", "Heading1"))
    story.append(Preformatted("python -m pip install -e .\nanalog-workbench kit --out exports/kit_manifest.json\nanalog-workbench demo --out exports/demo_run\nanalog-workbench pdf --out exports/pdfs", styles["Code"]))
    story.append(_p("Module map", "Heading1"))
    module_rows = [
        ["Module", "Purpose"],
        ["kit.py", "Builds the eightfold color/tool manifest."],
        ["operators.py", "Dice, card, string, and binding operators."],
        ["receipts.py", "Recoverable proof/obligation receipt dataclass and validation."],
        ["workbook.py", "Workbook sheet object and blank sheet generator."],
        ["simulation.py", "Runs the action loop and exports manifest, receipts, and sheets."],
        ["pdf_reports.py", "Generates manual, printable sheets, and simulation report PDFs."],
        ["cli.py", "Command-line interface for kit, demo, and PDF generation."],
    ]
    tbl = Table(module_rows, colWidths=[1.7*inch, 5.3*inch])
    tbl.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.lightgrey), ("GRID", (0,0), (-1,-1), 0.25, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP"), ("FONTSIZE", (0,0), (-1,-1), 8)]))
    story.append(tbl)
    story.append(_p("Simulation meaning", "Heading1"))
    story.append(_p("The simulator is not a replacement for the physical kit. It is a digital mirror that enforces the same minimal rules: eightfold kit availability, three-color gradient, yes/no continuation, white/black proof-obligation split, and receipt recovery."))
    _doc(path, "Analog Forge Python Simulation Workbench").build(story)


def build_demo_report_pdf(path: str | Path, demo: dict):
    path = Path(path)
    story = []
    story.append(_p("Analog Forge Demo Simulation Report", "Title"))
    story.append(_p(f"Kit object count: {demo.get('kit_object_count')}"))
    run = demo.get("run", {})
    story.append(_p("Receipt", "Heading1"))
    story.append(Preformatted(str(run.get("receipt", {})), styles["Small"]))
    story.append(_p("Workbook sheet", "Heading1"))
    story.append(Preformatted(str(run.get("sheet", {})), styles["Small"]))
    story.append(_p("Boundary operators", "Heading1"))
    story.append(Preformatted(str({"dice_event": run.get("dice_event"), "card_event": run.get("card_event"), "binding": run.get("binding")}), styles["Small"]))
    _doc(path, "Analog Forge Demo Simulation Report").build(story)


def build_all_pdfs(out_dir: str | Path, demo: dict | None = None) -> List[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, fn in [
        ("AnalogForge_Kit_Manual.pdf", build_kit_manual_pdf),
        ("AnalogForge_Printable_Workbook_Sheets.pdf", build_printable_sheets_pdf),
        ("AnalogForge_Python_Simulation_Guide.pdf", build_simulation_guide_pdf),
    ]:
        p = out / name
        fn(p)
        paths.append(str(p))
    if demo is not None:
        p = out / "AnalogForge_Demo_Simulation_Report.pdf"
        build_demo_report_pdf(p, demo)
        paths.append(str(p))
    return paths
