"""
Generate user manual PDF for the Triaxial Corrected Area app.
Takes screenshots with Playwright, then builds PDF with ReportLab.
"""

import io
import os
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SCREENSHOT_DIR = BASE_DIR / "manual_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)
OUTPUT_PDF = BASE_DIR / "User_Manual_Triaxial_App.pdf"
APP_URL = "http://localhost:8501"
DAT_FILE = BASE_DIR.parent / "SL_1T60.dat"

# ── Register Thai-capable font ────────────────────────────────────────────────
# Try to register a Thai font from Windows. Fall back to built-in if not found.
THAI_FONT = "Helvetica"   # fallback
THAI_FONT_BOLD = "Helvetica-Bold"

_font_candidates = [
    r"C:\Windows\Fonts\THSarabunNew.ttf",
    r"C:\Windows\Fonts\Tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]
for _path in _font_candidates:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont("ThaiFont", _path))
            THAI_FONT = "ThaiFont"
            # Try bold variant
            _bold = _path.replace(".ttf", " Bold.ttf").replace("arial", "arialbd")
            if os.path.exists(_bold):
                pdfmetrics.registerFont(TTFont("ThaiFont-Bold", _bold))
                THAI_FONT_BOLD = "ThaiFont-Bold"
        except Exception:
            pass
        break

# ── Styles ────────────────────────────────────────────────────────────────────
W, H = A4
MARGIN = 2 * cm

def make_styles():
    styles = getSampleStyleSheet()

    body = ParagraphStyle(
        "ThaiBody",
        parent=styles["Normal"],
        fontName=THAI_FONT,
        fontSize=11,
        leading=16,
        spaceAfter=6,
    )
    h1 = ParagraphStyle(
        "ThaiH1",
        parent=styles["Heading1"],
        fontName=THAI_FONT_BOLD,
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#1a5276"),
    )
    h2 = ParagraphStyle(
        "ThaiH2",
        parent=styles["Heading2"],
        fontName=THAI_FONT_BOLD,
        fontSize=13,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#1a5276"),
    )
    note = ParagraphStyle(
        "Note",
        parent=body,
        fontSize=10,
        leftIndent=12,
        textColor=colors.HexColor("#555555"),
    )
    code = ParagraphStyle(
        "Code",
        parent=body,
        fontName="Courier",
        fontSize=9,
        backColor=colors.HexColor("#f5f5f5"),
        leftIndent=12,
        rightIndent=12,
        spaceAfter=8,
    )
    caption = ParagraphStyle(
        "Caption",
        parent=body,
        fontSize=9,
        alignment=1,   # centre
        textColor=colors.HexColor("#666666"),
        spaceAfter=10,
    )
    return {"body": body, "h1": h1, "h2": h2, "note": note, "code": code, "caption": caption}


# ── Screenshot helpers ────────────────────────────────────────────────────────
def add_border(path: Path, border=3, color=(70, 130, 180)):
    """Add a thin blue border to a screenshot PNG."""
    img = Image.open(path)
    w, h = img.size
    bordered = Image.new("RGB", (w + 2 * border, h + 2 * border), color)
    bordered.paste(img, (border, border))
    bordered.save(path)


def screenshot_to_flowable(path: Path, max_width_cm=16, caption_text=""):
    """Return [RLImage, Spacer] or [RLImage, Paragraph(caption)]."""
    max_w = max_width_cm * cm
    img = Image.open(path)
    w, h = img.size
    scale = min(max_w / w, (H - 6 * cm) / h)
    items = [
        RLImage(str(path), width=w * scale, height=h * scale),
    ]
    if caption_text:
        items.append(Paragraph(caption_text, make_styles()["caption"]))
    else:
        items.append(Spacer(1, 6))
    return items


# ── Take screenshots ──────────────────────────────────────────────────────────
def take_screenshots():
    shots = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 820})
        page.goto(APP_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # 1. Full initial view
        p = SCREENSHOT_DIR / "01_initial.png"
        page.screenshot(path=str(p), full_page=False)
        add_border(p)
        shots["initial"] = p

        # 2. Sidebar scrolled to show Rowe's constants + smoothing
        page.evaluate("""
            const el = document.querySelector('div.st-emotion-cache-155jwzh');
            if (el) el.scrollTop = 360;
        """)
        time.sleep(0.5)
        p = SCREENSHOT_DIR / "02_sidebar_rowe.png"
        page.screenshot(path=str(p), full_page=False)
        add_border(p)
        shots["sidebar_rowe"] = p

        # 3. Sidebar scrolled to Save button
        page.evaluate("""
            const el = document.querySelector('div.st-emotion-cache-155jwzh');
            if (el) el.scrollTop = 600;
        """)
        time.sleep(0.5)
        p = SCREENSHOT_DIR / "03_sidebar_save.png"
        page.screenshot(path=str(p), full_page=False)
        add_border(p)
        shots["sidebar_save"] = p

        # 4. Reset scroll, highlight upload area (zoom in via clip)
        page.evaluate("""
            const el = document.querySelector('div.st-emotion-cache-155jwzh');
            if (el) el.scrollTop = 0;
        """)
        time.sleep(0.5)
        # Clip to main content area only
        main = page.query_selector('[data-testid="stMain"]')
        if main:
            box = main.bounding_box()
            p = SCREENSHOT_DIR / "04_upload_area.png"
            page.screenshot(path=str(p), clip=box)
            add_border(p)
            shots["upload"] = p

        # 5. Simulate file upload and processing
        if DAT_FILE.exists():
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(str(DAT_FILE))
                time.sleep(3)   # wait for Streamlit to register the upload

                # Take screenshot after upload
                p = SCREENSHOT_DIR / "05_after_upload.png"
                page.screenshot(path=str(p), full_page=False)
                add_border(p)
                shots["after_upload"] = p

                # Click Process button
                process_btn = page.query_selector('button:has-text("Process")')
                if process_btn:
                    process_btn.click()
                    time.sleep(15)   # wait for computation (142k rows)
                    p = SCREENSHOT_DIR / "06_results.png"
                    page.screenshot(path=str(p), full_page=False)
                    add_border(p)
                    shots["results"] = p

                    # Scroll down to see download button
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                    p = SCREENSHOT_DIR / "07_download.png"
                    page.screenshot(path=str(p), full_page=False)
                    add_border(p)
                    shots["download"] = p

        browser.close()
    return shots


# ── Build PDF ─────────────────────────────────────────────────────────────────
def build_pdf(shots: dict):
    S = make_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="Triaxial App — User Manual",
        author="Lab Manual",
    )
    story = []

    def H1(text): return Paragraph(text, S["h1"])
    def H2(text): return Paragraph(text, S["h2"])
    def P(text):  return Paragraph(text, S["body"])
    def Note(text): return Paragraph(f"&#x2139;&#xFE0F; {text}", S["note"])
    def HR(): return HRFlowable(width="100%", thickness=1, color=colors.HexColor("#aed6f1"), spaceAfter=8)
    def SP(h=8): return Spacer(1, h)

    # ── Cover ──────────────────────────────────────────────────────────────────
    story += [
        SP(80),
        Paragraph(
            "คู่มือการใช้งาน",
            ParagraphStyle("CoverSub", parent=S["body"], fontSize=16, alignment=1,
                           textColor=colors.HexColor("#555555")),
        ),
        SP(12),
        Paragraph(
            "Triaxial Test",
            ParagraphStyle("CoverTitle", parent=S["h1"], fontSize=32, alignment=1,
                           textColor=colors.HexColor("#1a5276")),
        ),
        Paragraph(
            "Corrected Cross-Section Area",
            ParagraphStyle("CoverTitle2", parent=S["h1"], fontSize=22, alignment=1,
                           textColor=colors.HexColor("#2980b9")),
        ),
        SP(20),
        HR(),
        SP(12),
        Paragraph(
            "โปรแกรมคำนวณพื้นที่หน้าตัดปรับแก้สำหรับ Drained Triaxial Test<br/>"
            "โดยใช้ Rowe's Modified Stress-Dilatancy Relation",
            ParagraphStyle("CoverDesc", parent=S["body"], fontSize=13, alignment=1,
                           textColor=colors.HexColor("#555555")),
        ),
        SP(40),
        Paragraph(
            "รองรับ: Windows 10/11 &nbsp;|&nbsp; Python 3.9+ &nbsp;|&nbsp; ไม่ต้องการ MATLAB License",
            ParagraphStyle("CoverTech", parent=S["body"], fontSize=10, alignment=1,
                           textColor=colors.HexColor("#777777")),
        ),
        PageBreak(),
    ]

    # ── Overview ──────────────────────────────────────────────────────────────
    story += [
        H1("1. ภาพรวมและขั้นตอนการทำงาน"),
        HR(),
        P("โปรแกรมนี้ทดแทน MATLAB live script ที่เคยใช้คำนวณ corrected cross-section area "
          "ในการทดสอบ drained triaxial test โดยเปิดใช้งานผ่าน web browser ไม่ต้องการ license"),
        SP(8),
        H2("กระบวนการใหม่ (ลดขั้นตอนจาก 3 เป็น 1)"),
    ]

    # Comparison table
    comp_data = [
        ["กระบวนการเดิม", "กระบวนการใหม่"],
        ["1. รับไฟล์ .dat จาก lab", "1. รับไฟล์ .dat จาก lab"],
        ["2. คัดลอก Displacement column", ""],
        ["3. คำนวณ axial strain ด้วยมือ", ""],
        ["4. วางข้อมูลลง Excel (.xlsx)", ""],
        ["5. เปิด MATLAB + ใส่ license", ""],
        ["6. รัน MATLAB script", "2. เปิดโปรแกรม (คลิก run_app.bat)"],
        ["7. ได้ผลลัพธ์ .dat", "3. อัปโหลดไฟล์ .dat แล้วคลิก Process"],
        ["", "4. ดาวน์โหลดผลลัพธ์ .dat"],
    ]
    tbl = Table(comp_data, colWidths=[8 * cm, 8 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), THAI_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aed6f1")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf4fb")]),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 2), (0, 5), colors.HexColor("#c0392b")),
        ("BACKGROUND", (1, 2), (1, 5), colors.HexColor("#fdfefe")),
    ]))
    story += [tbl, SP(12)]

    story += [
        H2("Output ที่ได้"),
        P("ไฟล์ผลลัพธ์ เป็น <b>.dat</b> comma-separated มี <b>19 คอลัมน์</b>:"),
        P("<b>9 คอลัมน์เดิม</b> (จาก input) + <b>10 คอลัมน์ที่คำนวณ</b>"),
    ]

    col_data = [
        ["คอลัมน์", "ชื่อ", "หน่วย", "ที่มา"],
        ["1", "Time", "s", "Input"],
        ["2", "Load", "N", "Input"],
        ["3", "Disp.", "mm", "Input"],
        ["4", "Cell_P.", "kPa", "Input"],
        ["5-9", "LDT/CG sensors", "mm", "Input"],
        ["10", "eAxis", "%", "คำนวณ"],
        ["11", "del_e_v", "%/s", "คำนวณ"],
        ["12", "D (Dilatancy)", "-", "คำนวณ"],
        ["13", "del_e_vol", "%/s", "คำนวณ"],
        ["14", "e_vol", "%", "คำนวณ"],
        ["15", "A (Corrected Area)", "mm2", "คำนวณ"],
        ["16", "q", "kPa", "คำนวณ"],
        ["17", "sig_1", "kPa", "คำนวณ"],
        ["18", "eff_sig_1", "kPa", "คำนวณ"],
        ["19", "R (Stress Ratio)", "-", "คำนวณ"],
    ]
    t2 = Table(col_data, colWidths=[2 * cm, 5 * cm, 2.5 * cm, 2.5 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), THAI_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aed6f1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf4fb")]),
        ("BACKGROUND", (0, 6), (-1, -1), colors.HexColor("#eafaf1")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [t2, PageBreak()]

    # ── System Requirements ──────────────────────────────────────────────────
    story += [
        H1("2. ความต้องการของระบบและการติดตั้ง"),
        HR(),
        H2("ความต้องการของระบบ"),
    ]
    req_data = [
        ["รายการ", "รายละเอียด"],
        ["ระบบปฏิบัติการ", "Windows 10 / 11"],
        ["Python", "เวอร์ชัน 3.9 ขึ้นไป (ดาวน์โหลดจาก python.org)"],
        ["หน่วยความจำ", "RAM 4 GB ขึ้นไป (แนะนำ 8 GB สำหรับไฟล์ขนาดใหญ่)"],
        ["พื้นที่ดิสก์", "100 MB"],
        ["เบราว์เซอร์", "Chrome, Firefox, Edge (เวอร์ชันใหม่)"],
        ["License", "ไม่ต้องการ MATLAB หรือ software license ใดๆ"],
    ]
    t3 = Table(req_data, colWidths=[4 * cm, 12 * cm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), THAI_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aed6f1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf4fb")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [t3, SP(12)]

    story += [
        H2("การติดตั้งครั้งแรก (ทำครั้งเดียว)"),
        P("เปิด Command Prompt หรือ PowerShell แล้วพิมพ์คำสั่ง:"),
        Paragraph("py -m pip install streamlit numpy pandas", S["code"]),
        Note("หากยังไม่มี Python ให้ดาวน์โหลดและติดตั้งจาก python.org ก่อน แล้วเลือกติ๊ก "
             '"Add Python to PATH" ระหว่างการติดตั้ง'),
        SP(8),
        H2("โครงสร้างไฟล์โปรแกรม"),
        Paragraph(
            "triaxial_app/<br/>"
            "&nbsp;&nbsp;app.py &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "# โปรแกรมหลัก<br/>"
            "&nbsp;&nbsp;calculator.py &nbsp;&nbsp;&nbsp;&nbsp;# เครื่องคำนวณ<br/>"
            "&nbsp;&nbsp;config.json &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# ค่า default parameters<br/>"
            "&nbsp;&nbsp;run_app.bat &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# ไฟล์สำหรับเปิดโปรแกรม",
            S["code"],
        ),
        PageBreak(),
    ]

    # ── Step 1: Start ────────────────────────────────────────────────────────
    story += [
        H1("3. ขั้นตอนการใช้งาน"),
        HR(),
        H2("ขั้นตอนที่ 1 — เปิดโปรแกรม"),
        P("ดับเบิลคลิกที่ไฟล์ <b>run_app.bat</b> ในโฟลเดอร์ <b>triaxial_app</b>"),
        SP(6),
    ]
    if "initial" in shots:
        story += screenshot_to_flowable(
            shots["initial"], caption_text="ภาพที่ 1: หน้าต่างโปรแกรมเมื่อเปิดครั้งแรกในเบราว์เซอร์"
        )
    story += [
        P("โปรแกรมจะเปิดขึ้นในเบราว์เซอร์อัตโนมัติที่ <b>http://localhost:8501</b>"),
        Note("หากเบราว์เซอร์ไม่เปิดอัตโนมัติ ให้พิมพ์ http://localhost:8501 ในช่อง address bar"),
        Note("หน้าต่าง Command Prompt ที่เปิดขึ้นมาต้องคาเอาไว้ตลอดเวลาที่ใช้งาน ห้ามปิด"),
        SP(12),
        H2("ขั้นตอนที่ 2 — ตั้งค่า Parameters"),
        P("ที่ <b>แถบด้านซ้าย (Sidebar)</b> ให้กรอกค่าพารามิเตอร์ของตัวอย่างดิน:"),
        SP(6),
    ]
    if "initial" in shots:
        story += screenshot_to_flowable(
            shots["initial"],
            caption_text="ภาพที่ 2: Sidebar ด้านซ้ายสำหรับกรอกค่าพารามิเตอร์",
        )

    # Parameter reference table
    param_data = [
        ["พารามิเตอร์", "คำอธิบาย", "หน่วย", "ค่า default"],
        ["H0", "ความสูงเริ่มต้นของตัวอย่างดิน", "mm", "140.0"],
        ["Dia", "เส้นผ่านศูนย์กลางตัวอย่างดิน", "mm", "70.0"],
        ["s3 (sig_3)", "ความดันด้านข้าง (Confining pressure)", "kPa", "30.0"],
        ["u", "Pore pressure (0 สำหรับ air-dried)", "kPa", "0.0"],
        ["C", "Rowe's constant C0", "-", "-4.42395"],
        ["C1", "Rowe's constant C1", "-", "10.00"],
        ["C2", "Rowe's constant C2", "-", "-2.77"],
        ["Smoothing window", "ขนาด rolling mean (1 = ไม่ smooth)", "points", "1"],
    ]
    tp = Table(param_data, colWidths=[3 * cm, 6 * cm, 2 * cm, 3 * cm])
    tp.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), THAI_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aed6f1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf4fb")]),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [tp, SP(10)]
    story += [
        Note("หลังจากกรอกค่าครบแล้ว กดปุ่ม 'Save as default config' เพื่อบันทึกค่าไว้ใช้ครั้งถัดไป"),
    ]

    if "sidebar_rowe" in shots:
        story += [SP(8)] + screenshot_to_flowable(
            shots["sidebar_rowe"],
            caption_text="ภาพที่ 3: ส่วน Rowe's constants และ Displacement smoothing",
        )
    if "sidebar_save" in shots:
        story += screenshot_to_flowable(
            shots["sidebar_save"],
            caption_text="ภาพที่ 4: ปุ่ม Save as default config",
        )

    story.append(PageBreak())

    # ── Step 3: Upload ───────────────────────────────────────────────────────
    story += [
        H2("ขั้นตอนที่ 3 — อัปโหลดไฟล์ .dat จาก Lab"),
        P("ในส่วนกลางของหน้าจอ คลิกปุ่ม <b>Browse files</b> หรือลากไฟล์มาวางที่ช่อง upload"),
        SP(6),
    ]
    if "upload" in shots:
        story += screenshot_to_flowable(
            shots["upload"],
            caption_text="ภาพที่ 5: ส่วน Upload ไฟล์ .dat",
        )
    elif "initial" in shots:
        story += screenshot_to_flowable(
            shots["initial"],
            caption_text="ภาพที่ 5: คลิก Browse files เพื่อเลือกไฟล์ .dat",
        )
    story += [
        P("สามารถเลือกได้หลายไฟล์พร้อมกันโดยกด <b>Ctrl+Click</b> หรือ <b>Shift+Click</b>"),
        Note("รองรับเฉพาะไฟล์นามสกุล .dat จากเครื่อง logging ในห้อง lab เท่านั้น"),
        Note("ขนาดไฟล์สูงสุด 200 MB ต่อไฟล์"),
        SP(12),
        H2("ขั้นตอนที่ 4 — ประมวลผล"),
        P("เมื่ออัปโหลดไฟล์แล้ว ปุ่ม <b>'Process All Files'</b> จะปรากฏขึ้น ให้คลิกเพื่อเริ่มคำนวณ"),
        SP(6),
    ]
    if "after_upload" in shots:
        story += screenshot_to_flowable(
            shots["after_upload"],
            caption_text="ภาพที่ 6: หลังอัปโหลดไฟล์ — คลิกปุ่ม 'Process All Files'",
        )
    story += [
        Note("ระยะเวลาการประมวลผลขึ้นอยู่กับขนาดไฟล์ โดยทั่วไปใช้เวลา 10-30 วินาทีต่อไฟล์"),
        PageBreak(),
    ]

    # ── Step 5: Results ──────────────────────────────────────────────────────
    story += [
        H2("ขั้นตอนที่ 5 — ดูผลลัพธ์และดาวน์โหลด"),
        P("เมื่อประมวลผลเสร็จ ระบบจะแสดง:"),
        P("&bull; &nbsp;ตารางแสดงข้อมูล 10 แถวแรกของผลลัพธ์"),
        P("&bull; &nbsp;ข้อมูลสรุป: จำนวนแถว, A<sub rise=2 size=8>0</sub>, R<sub rise=2 size=8>0</sub>"),
        P("&bull; &nbsp;ปุ่ม <b>Download</b> สำหรับดาวน์โหลดไฟล์ผลลัพธ์ .dat"),
        SP(6),
    ]
    if "results" in shots:
        story += screenshot_to_flowable(
            shots["results"],
            caption_text="ภาพที่ 7: หน้าแสดงผลลัพธ์พร้อม preview ตาราง",
        )
    if "download" in shots:
        story += screenshot_to_flowable(
            shots["download"],
            caption_text="ภาพที่ 8: ปุ่ม Download สำหรับดาวน์โหลดไฟล์ผลลัพธ์",
        )

    story += [
        H2("ชื่อไฟล์ผลลัพธ์"),
        P("ไฟล์ผลลัพธ์จะถูกตั้งชื่อโดยอัตโนมัติตามรูปแบบ:"),
        Paragraph("Result_{ชื่อไฟล์ต้นฉบับ}_{YYMMDD}.dat", S["code"]),
        P("ตัวอย่าง: ไฟล์ input คือ <b>SL_1T60.dat</b> → ผลลัพธ์คือ <b>Result_SL_1T60_260611.dat</b>"),
        SP(12),
        H2("Batch Processing (หลายไฟล์)"),
        P("เมื่ออัปโหลดหลายไฟล์พร้อมกัน ระบบจะแสดงผลลัพธ์แยกแต่ละไฟล์ "
          "และมีปุ่ม <b>'Download All as ZIP'</b> เพิ่มขึ้นมาเพื่อดาวน์โหลดทั้งหมดในคราวเดียว"),
        PageBreak(),
    ]

    # ── Formulas ──────────────────────────────────────────────────────────────
    story += [
        H1("4. สูตรการคำนวณ"),
        HR(),
        H2("พื้นที่หน้าตัดเริ่มต้น"),
        Paragraph("A<sub rise=2 size=8>0</sub> = (pi/4) x Dia<super>2</super>", S["body"]),
        SP(4),
        H2("Axial Strain"),
        Paragraph(
            "eAxis(%) = (Disp(i) - Disp(0)) / H0 x 100",
            S["code"],
        ),
        SP(4),
        H2("Deviatoric Stress"),
        Paragraph("q = Load(N) x 1000 / A(i) &nbsp;&nbsp;&nbsp;&nbsp;[หน่วย kPa]", S["body"]),
        SP(4),
        H2("Stress Ratio"),
        Paragraph(
            "R = (sig_3 + q - u) / (sig_3 - u)",
            S["code"],
        ),
        SP(4),
        H2("Dilatancy Parameter D (Rowe's Relation)"),
        P("แก้สมการกำลังสอง:"),
        Paragraph(
            "C2 x D<super>2</super> + C1 x D + (C - R) = 0",
            S["code"],
        ),
        P("เลือก root ที่มีค่าน้อยกว่า (minimum real root)"),
        SP(4),
        H2("Cumulative Volumetric Strain"),
        Paragraph(
            "del_e_vol(i) = (1 - D(i)) x del_e_v(i)<br/>"
            "e_vol(i) = e_vol(i-1) + del_e_vol(i)",
            S["code"],
        ),
        SP(4),
        H2("Corrected Cross-Section Area"),
        Paragraph(
            "A(i) = A0 x [1 - e_vol(i)/100] / [1 - eAxis(i)/100]",
            S["code"],
        ),
        SP(12),
        H2("วิธีคำนวณ del_e_v (Finite Difference)"),
    ]
    fd_data = [
        ["จุด", "สูตร"],
        ["แรก (i=0)", "Forward: [eAxis(1) - eAxis(0)] / [t(1) - t(0)]"],
        ["กลาง", "Central: 0.5 x (forward rate + backward rate)"],
        ["สุดท้าย (i=n-1)", "Backward: [eAxis(n-1) - eAxis(n-2)] / [t(n-1) - t(n-2)]"],
    ]
    tfd = Table(fd_data, colWidths=[3.5 * cm, 12.5 * cm])
    tfd.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), THAI_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aed6f1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf4fb")]),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [tfd, PageBreak()]

    # ── Troubleshooting ───────────────────────────────────────────────────────
    story += [
        H1("5. การแก้ปัญหาเบื้องต้น"),
        HR(),
    ]
    ts_data = [
        ["ปัญหา", "วิธีแก้ไข"],
        [
            "เปิด run_app.bat แล้วไม่มีอะไรเกิดขึ้น",
            "ตรวจสอบว่า Python ถูกติดตั้งแล้ว โดยพิมพ์ 'py --version' ใน Command Prompt",
        ],
        [
            "เบราว์เซอร์ไม่เปิดอัตโนมัติ",
            "เปิดเบราว์เซอร์แล้วพิมพ์ http://localhost:8501 ใน address bar",
        ],
        [
            "Error: ModuleNotFoundError",
            "รัน: py -m pip install streamlit numpy pandas",
        ],
        [
            "ไฟล์ .dat อ่านไม่ได้",
            "ตรวจสอบว่าไฟล์เป็น tab-delimited .dat จาก logging software "
            "มี header row และ column 1-3 คือ Time, Load, Displacement",
        ],
        [
            "ผลลัพธ์ A[0] ไม่ตรง 3848.451",
            "ตรวจสอบค่า Dia = 70 mm (A0 = pi/4 x 70^2 = 3848.45 mm2)",
        ],
        [
            "การประมวลผลช้ามาก",
            "ไฟล์ .dat ขนาดใหญ่ (100k+ แถว) ใช้เวลา 10-30 วินาที เป็นเรื่องปกติ",
        ],
        [
            "Port 8501 ถูกใช้อยู่",
            "ปิดหน้าต่าง Command Prompt เก่าก่อน หรือ Restart เครื่อง",
        ],
    ]
    tts = Table(ts_data, colWidths=[6 * cm, 10 * cm])
    tts.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), THAI_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aed6f1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf4fb")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [tts, SP(20)]
    story += [
        H1("6. ข้อมูลทางเทคนิคเพิ่มเติม"),
        HR(),
        H2("ความแตกต่างจากกระบวนการเดิม (MATLAB)"),
        P("1. <b>Raw displacement</b>: โปรแกรมนี้คำนวณ eAxis โดยตรงจาก Disp.(mm) column "
          "โดยไม่ผ่านการ smooth ด้วยมือในขั้นตอนก่อน (default: Smoothing window = 1)"),
        P("2. <b>จำนวนแถวข้อมูล</b>: โปรแกรมนี้ประมวลผลข้อมูลทุกแถวในไฟล์ .dat "
          "(ต่างจากกระบวนการเดิมที่คัดลอกข้อมูลบางส่วนลง Excel)"),
        P("3. <b>การ Smooth</b>: หากต้องการให้ผลลัพธ์ใกล้เคียง MATLAB มากขึ้น "
          "ให้ปรับ 'Smoothing window' เป็นค่าที่เหมาะสม (เช่น 10-50)"),
        SP(8),
        H2("การตรวจสอบความถูกต้อง"),
        P("ค่าที่ใช้ตรวจสอบเมื่อทดสอบกับไฟล์ <b>SL_1T60.dat</b>:"),
    ]
    vfy_data = [
        ["ตัวแปร", "ค่าที่ได้", "หน่วย"],
        ["A[0] (initial area)", "3848.451", "mm2"],
        ["q[0]", "0.136118", "kPa"],
        ["R[0]", "1.004537", "-"],
        ["Dia", "70", "mm"],
        ["sig_3", "30", "kPa"],
    ]
    tv = Table(vfy_data, colWidths=[5 * cm, 5 * cm, 4 * cm])
    tv.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), THAI_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aed6f1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eaf4fb")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [tv]

    doc.build(story)
    print(f"PDF saved: {OUTPUT_PDF}")
    return OUTPUT_PDF


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Taking screenshots...")
    shots = take_screenshots()
    print(f"Screenshots: {list(shots.keys())}")
    print("Building PDF...")
    build_pdf(shots)
