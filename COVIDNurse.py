import streamlit as st
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile
from datetime import datetime
import pytz
import os

# ---------- FONT (Thai PERFECT) ----------
FONT_PATH = "THSarabunNew.ttf"

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("THSarabun", FONT_PATH))
    THAI_FONT = "THSarabun"
else:
    THAI_FONT = "Helvetica"  # fallback

# ---------- OpenAI ----------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
MODEL = st.secrets.get("MODEL", "gpt-4o-mini")

st.set_page_config(page_title="Long COVID Nurse Assistant", layout="wide")
st.title("🏥 Long COVID Nurse Assistant (Thai Clinical Tool)")

# ---------- Time ----------
def get_bkk_time():
    tz = pytz.timezone("Asia/Bangkok")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# ---------- Clinical Scripts ----------
scripts = {
    "Brain Fog": {
        "script": """
🧠 การทดสอบ Brain Fog

1. ความจำทันที:
“กรุณาจำคำ 3 คำ: ดอกไม้ – รถยนต์ – แม่น้ำ”

2. สมาธิ:
“100 ลบ 7 ไปเรื่อย ๆ”

3. Orientation:
“วันนี้วันที่อะไร / อยู่ที่ไหน”

4. Delayed recall:
“เมื่อกี้จำคำอะไรได้บ้าง”
""",
        "checklist": [
            ("จำคำไม่ได้", 2),
            ("คำนวณผิด", 2),
            ("orientation ผิด", 3),
            ("recall ไม่ได้", 3)
        ]
    },

    "POTS": {
        "script": """
❤️ POTS Test

1. นอนพัก 5 นาที → วัด HR/BP
2. ลุกยืน
3. วัด HR นาทีที่ 1 และ 3

เกณฑ์:
HR เพิ่ม ≥30 bpm + มีอาการ
""",
        "checklist": [
            ("HR เพิ่ม ≥30", 3),
            ("เวียนหัว", 2),
            ("ใจสั่น", 2),
            ("เป็นลม", 3)
        ]
    },

    "Dyspnea": {
        "script": """
🫁 ทดสอบเหนื่อย

Sit-to-stand 1 นาที
ถามระดับเหนื่อย (0–10)
วัด SpO₂
""",
        "checklist": [
            ("เหนื่อยมาก", 3),
            ("SpO2 ลด", 3),
            ("พูดเป็นคำ ๆ", 2)
        ]
    },

    "Anxiety": {
        "script": """
🧠 คัดกรอง Anxiety

“ช่วงนี้กังวลไหม”
“นอนไม่หลับไหม”
“ยังสนุกกับสิ่งเดิมไหม”
""",
        "checklist": [
            ("กังวล", 2),
            ("นอนไม่หลับ", 2),
            ("ใจสั่น", 1)
        ]
    },

    "Chest Pain": {
        "script": """
🫀 Chest Pain

ถาม:
- ลักษณะเจ็บ
- ร้าวหรือไม่
- เกิดตอน exertion หรือไม่
""",
        "checklist": [
            ("เจ็บกดทับ", 3),
            ("ร้าวแขน", 3),
            ("exertional", 3),
            ("red flag", 5)
        ]
    }
}

# ---------- UI ----------
option = st.selectbox("เลือกอาการ", list(scripts.keys()))

st.subheader("📜 Script")
st.text_area("", scripts[option]["script"], height=250)

st.subheader("✅ Checklist")
score = 0
selected_items = []

for item, val in scripts[option]["checklist"]:
    if st.checkbox(f"{item} (+{val})"):
        score += val
        selected_items.append(item)

def risk_level(score):
    if score >= 8:
        return "สูง"
    elif score >= 4:
        return "ปานกลาง"
    return "ต่ำ"

st.metric("Score", score)
st.write("Risk:", risk_level(score))

notes = st.text_area("📝 Notes")

# ---------- AI ----------
def generate_report():
    prompt = f"""
สรุปเคส Long COVID ภาษาไทย

อาการ: {option}
Checklist: {selected_items}
Score: {score}
Risk: {risk_level(score)}
Notes: {notes}

ตอบ:
1. สรุป
2. ความเสี่ยง
3. คำแนะนำ
"""

    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return res.choices[0].message.content

report = ""
if st.button("🧠 วิเคราะห์ AI"):
    report = generate_report()
    st.write(report)

# ---------- PDF ----------
def create_pdf():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A4)

    styles = getSampleStyleSheet()
    thai_style = ParagraphStyle(
        name="Thai",
        fontName=THAI_FONT,
        fontSize=14,
        leading=18
    )

    content = []

    content.append(Paragraph("รายงาน Long COVID", thai_style))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"วันที่: {get_bkk_time()}", thai_style))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"อาการ: {option}", thai_style))
    content.append(Paragraph(f"คะแนน: {score}", thai_style))
    content.append(Paragraph(f"ความเสี่ยง: {risk_level(score)}", thai_style))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Checklist:", thai_style))
    for i in selected_items:
        content.append(Paragraph(f"- {i}", thai_style))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Notes:", thai_style))
    content.append(Paragraph(notes or "-", thai_style))

    content.append(Spacer(1, 10))
    content.append(Paragraph("AI Report:", thai_style))
    content.append(Paragraph(report or "-", thai_style))

    doc.build(content)
    return tmp.name

if st.button("📄 Export PDF"):
    pdf_file = create_pdf()
    with open(pdf_file, "rb") as f:
        st.download_button("Download PDF", f, file_name="long_covid_report.pdf")
