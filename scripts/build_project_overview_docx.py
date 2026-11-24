"""Build the editable DOCX version of the consolidated project overview."""
from pathlib import Path
import re
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md"
OUTPUT = ROOT / "deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.docx"


def plain(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*`]", "", text)
    return text.strip()


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: str, *, bold=False, color=None, size=8.5) -> None:
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(plain(text))
    run.bold = bold
    run.font.name = "Aptos"
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_table(doc, lines) -> None:
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return
    cols = max(map(len, rows))
    table = doc.add_table(rows=len(rows), cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    for ri, row in enumerate(rows):
        for ci in range(cols):
            value = row[ci] if ci < len(row) else ""
            cell = table.cell(ri, ci)
            set_cell_text(cell, value, bold=(ri == 0),
                          color=(255, 255, 255) if ri == 0 else (35, 45, 58),
                          size=8 if cols >= 5 else 8.5)
            if ri == 0:
                shade(cell, "17365D")
            elif ri % 2 == 0:
                shade(cell, "EAF0F6")
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_page_field(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.addnext(fld)


def build():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.65)
    sec.bottom_margin = Inches(0.65)
    sec.left_margin = Inches(0.7)
    sec.right_margin = Inches(0.7)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor(35, 45, 58)
    normal.paragraph_format.space_after = Pt(5)
    for name, size, color in (("Title", 25, (23, 54, 93)),
                              ("Heading 1", 16, (23, 54, 93)),
                              ("Heading 2", 12, (31, 96, 133)),
                              ("Heading 3", 10, (31, 96, 133))):
        st = styles[name]
        st.font.name = "Aptos Display"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(*color)
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.space_before = Pt(10 if name != "Title" else 2)
        st.paragraph_format.space_after = Pt(5)

    header = sec.header.paragraphs[0]
    header.text = "PROJECT OVERVIEW  |  Evidence inventory and research plan"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in header.runs:
        r.font.name = "Aptos"
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor(100, 112, 125)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run("Internal project review  •  Page ")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor(100, 112, 125)
    add_page_field(footer)

    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        s = raw.strip()
        if not s or s == "---":
            i += 1
            continue
        if s.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            add_table(doc, block)
            continue
        if s.startswith("# "):
            p = doc.add_paragraph(style="Title")
            p.add_run(plain(s[2:]))
            i += 1
            continue
        if s.startswith("## "):
            doc.add_heading(plain(s[3:]), level=1)
            i += 1
            continue
        if s.startswith("### "):
            doc.add_heading(plain(s[4:]), level=2)
            i += 1
            continue
        if s.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.right_indent = Inches(0.2)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(7)
            r = p.add_run(plain(s[2:]))
            r.italic = True
            r.bold = True
            r.font.color.rgb = RGBColor(31, 96, 133)
            i += 1
            continue
        if re.match(r"^[-*] ", s):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            p.add_run(plain(re.sub(r"^[-*] ", "", s)))
            i += 1
            continue
        if re.match(r"^\d+\. ", s):
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_after = Pt(2)
            p.add_run(plain(re.sub(r"^\d+\. ", "", s)))
            i += 1
            continue
        # Merge wrapped Markdown paragraph lines until a block boundary.
        para = [s]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt or nxt == "---" or nxt.startswith(("#", "> ", "|"))
                    or re.match(r"^[-*] |^\d+\. ", nxt)):
                break
            para.append(nxt)
            i += 1
        p = doc.add_paragraph()
        p.add_run(plain(" ".join(para)))

    doc.core_properties.title = "Project Overview, Evidence Inventory, and Next Research Plan"
    doc.core_properties.subject = "Consolidated academic and provenance status of the dermoscopic image integrity project"
    doc.core_properties.author = "Project research team"
    doc.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build())
