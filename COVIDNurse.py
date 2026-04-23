import streamlit as st
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import tempfile

# --- Register Thai font ---
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

# --- OpenAI ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
MODEL = st.secrets.get("MODEL", "gpt-4o-mini")

st.set_page_config(page_title="Long COVID Nurse Assistant", layout="wide")
st.title("🏥 Long COVID Nurse Assistant (Thai + Scoring + PDF)")

# --- Data ---
scripts = {
    "Brain Fog": {
        "script": "ทดสอบความจำ สมาธิ และ orientation",
        "checklist": [
            ("จำคำไม่ได้", 2),
            ("คำนวณผิด", 2),
            ("orientation ผิด", 3),
            ("delayed recall ไม่ได้", 3)
        ]
    },
    "POTS": {
        "script": "วัด HR/BP นอน-ยืน",
        "checklist": [
            ("HR เพิ่ม ≥30", 3),
            ("เวียนหัว", 2),
            ("ใจสั่น", 2),
            ("BP ไม่ตก", 1)
        ]
    },
    "Dysautonomia": {
        "script": "ประเมิน autonomic",
        "checklist": [
            ("เวียนหัว", 2),
            ("ใจสั่น", 2),
            ("เหงื่อผิดปกติ", 2),
            ("GI symptom", 1)
        ]
    },
    "Dyspnea": {
        "script": "ประเมินเหนื่อย",
        "checklist": [
            ("เหนื่อยมาก", 3),
            ("SpO2 ลด", 3),
            ("ใช้ accessory muscle", 2)
        ]
    },
    "Anxiety": {
        "script": "ประเมิน mental",
        "checklist": [
            ("กังวล", 2),
            ("นอนไม่หลับ", 2),
            ("ใจสั่น", 1),
            ("สมาธิลด", 1)
        ]
    },
    "Chest Pain": {
        "script": "คัดกรอง cardiac",
        "checklist": [
            ("เจ็บกดทับ", 3),
            ("ร้าวแขน", 3),
            ("exertional", 3),
            ("red flag", 5)
        ]
    }
}

# --- UI ---
option = st.selectbox("เลือกอาการ", list(scripts.keys()))

st.subheader("📜 Script")
st.write(scripts[option]["script"])

st.subheader("✅ Checklist")
score = 0
selected_items = []

for item, val in scripts[option]["checklist"]:
    if st.checkbox(f"{item} (+{val})"):
        score += val
        selected_items.append(item)

# --- Risk Level ---
def risk_level(score):
    if score >= 8:
        return "🔴 สูง"
    elif score >= 4:
        return "🟡 ปานกลาง"
    else:
        return "🟢 ต่ำ"

st.subheader("📊 Score")
st.metric("คะแนนรวม", score)
st.write("ระดับความเสี่ยง:", risk_level(score))

# --- Notes ---
notes = st.text_area("📝 Notes เพิ่มเติม")

# --- GPT ---
def generate_report():
    prompt = f"""
สรุปเคส Long COVID ภาษาไทย

อาการ: {option}
Checklist: {selected_items}
Score: {score}
Risk: {risk_level(score)}
Notes: {notes}

ให้:
1. Interpretation
2. Differential diagnosis
3. Risk
4. Recommendation
5. Need referral?
"""

    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return res.choices[0].message.content

report = ""
if st.button("🧠 วิเคราะห์ AI"):
    with st.spinner("Analyzing..."):
        report = generate_report()
        st.subheader("📋 AI Report")
        st.write(report)

# --- PDF ---
def create_pdf(option, score, risk, items, notes, report):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A4)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("Long COVID Report", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"อาการ: {option}", styles["Normal"]))
    content.append(Paragraph(f"คะแนน: {score}", styles["Normal"]))
    content.append(Paragraph(f"ความเสี่ยง: {risk}", styles["Normal"]))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Checklist:", styles["Heading2"]))
    for i in items:
        content.append(Paragraph(f"- {i}", styles["Normal"]))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Notes:", styles["Heading2"]))
    content.append(Paragraph(notes or "-", styles["Normal"]))

    content.append(Spacer(1, 10))
    content.append(Paragraph("AI Report:", styles["Heading2"]))
    content.append(Paragraph(report or "-", styles["Normal"]))

    doc.build(content)
    return tmp.name

# --- Download PDF ---
if st.button("📄 Export PDF"):
    pdf_file = create_pdf(option, score, risk_level(score), selected_items, notes, report)
    with open(pdf_file, "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name="long_covid_report.pdf")