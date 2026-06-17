import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
import pytz

st.set_page_config(page_title="Auricular Acupressure", layout="centered")

# ---------- GitHub config ----------
TOKEN = st.secrets["GITHUB_TOKEN"]
OWNER = st.secrets["GITHUB_OWNER"]
REPO = st.secrets["GITHUB_REPO"]
BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
CSV_PATH = st.secrets.get("GITHUB_CSV_PATH", "ear_acupressure.csv")

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{CSV_PATH}"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

COLUMNS = [
    "timestamp_bkk",
    "citizen_id",
    "visit_type",
    "sex",
    "age",
    "weight_kg",
    "height_cm",
    "bmi",
    "bmi_color",
    "seed_points_count",
    "regular_menses_or_menopause",
    "no_ear_inflammation",
    "appetite_score",
    "sweet_craving_score",
    "salty_craving_score",
    "exercise_score",
    "waist_cm",
]

# ---------- helper functions ----------
def bkk_now():
    tz = pytz.timezone("Asia/Bangkok")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


def calculate_bmi(weight_kg, height_cm):
    if weight_kg <= 0 or height_cm <= 0:
        return None
    h_m = height_cm / 100
    return round(weight_kg / (h_m ** 2), 2)


def bmi_category(bmi):
    if bmi is None:
        return "ไม่ทราบ", "gray", 0

    if bmi < 23:
        return "BMI < 23", "blue", 1
    elif 23 <= bmi <= 25:
        return "BMI 23–25", "green", 4
    else:
        return "BMI > 25", "red", 5


def show_bmi_box(bmi):
    label, color, points = bmi_category(bmi)

    if color == "green":
        st.success(f"BMI = {bmi:.2f} kg/m² | {label} | ติดเม็ดผักกาด {points} จุด")
    elif color == "red":
        st.error(f"BMI = {bmi:.2f} kg/m² | {label} | ติดเม็ดผักกาด {points} จุด")
    elif color == "blue":
        st.info(f"BMI = {bmi:.2f} kg/m² | {label} | ติดเม็ดผักกาด {points} จุด")
    else:
        st.warning("ยังคำนวณ BMI ไม่ได้")

    return label, color, points


def load_csv_from_github():
    r = requests.get(API_URL, headers=HEADERS, params={"ref": BRANCH})

    if r.status_code == 404:
        return pd.DataFrame(columns=COLUMNS), None

    r.raise_for_status()
    data = r.json()
    sha = data["sha"]
    content = base64.b64decode(data["content"]).decode("utf-8-sig")

    if content.strip() == "":
        return pd.DataFrame(columns=COLUMNS), sha

    df = pd.read_csv(io.StringIO(content), dtype={"citizen_id": str})

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[COLUMNS], sha


def save_csv_to_github(df, sha=None):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    content_encoded = base64.b64encode(csv_buffer.getvalue().encode("utf-8-sig")).decode()

    payload = {
        "message": f"Update auricular acupressure CSV {bkk_now()}",
        "content": content_encoded,
        "branch": BRANCH,
    }

    if sha:
        payload["sha"] = sha

    r = requests.put(API_URL, headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()


def clean_citizen_id(x):
    return "".join([c for c in str(x).strip() if c.isdigit()])


# ---------- UI ----------
st.title("นิทรรศการสุขภาพหู KU KPS Infirmary")
st.subheader("Auricular Acupressure ด้วยเม็ดผักกาด(Vaccaria Seeds)")

st.info(
    "กรุณากรอกเลขบัตรประชาชน 13 หลักเพื่อตรวจสอบว่าเป็นครั้งแรกหรือครั้งติดตาม"
)

citizen_id = st.text_input("เลขบัตรประชาชน 13 หลัก", max_chars=13)

if citizen_id:
    citizen_id = clean_citizen_id(citizen_id)

    if len(citizen_id) != 13:
        st.warning("กรุณากรอกเลขบัตรประชาชนให้ครบ 13 หลัก")
        st.stop()

    try:
        df, sha = load_csv_from_github()
    except Exception as e:
        st.error(f"โหลดข้อมูลจาก GitHub ไม่สำเร็จ: {e}")
        st.stop()

    found = not df[df["citizen_id"].astype(str) == citizen_id].empty
    visit_type = "follow_up" if found else "first_visit"

    if found:
        st.success("พบข้อมูลเดิม: ครั้งติดตาม")
        old = df[df["citizen_id"].astype(str) == citizen_id].tail(1).iloc[0]
        st.caption(
            f"ข้อมูลล่าสุด: {old.get('timestamp_bkk', '')} | "
            f"BMI เดิม: {old.get('bmi', '')}"
        )
    else:
        st.info("ไม่พบข้อมูลเดิม: ครั้งแรก")

    with st.form("ear_acupressure_form"):
        st.markdown("### ข้อมูลพื้นฐาน")

        if not found:
            sex = st.selectbox("เพศ", ["หญิง", "ชาย", "อื่น ๆ / ไม่ระบุ"])
            age = st.number_input("อายุ", min_value=1, max_value=120, value=20, step=1)

            regular_menses_or_menopause = st.checkbox(
                "ประจำเดือนมาปกติ หรือไม่เกี่ยวข้อง"
            )
            no_ear_inflammation = st.checkbox("ไม่มีหูอักเสบ / ไม่มีแผลที่ใบหู")
        else:
            sex = ""
            age = ""
            regular_menses_or_menopause = ""
            no_ear_inflammation = ""

        weight_kg = st.number_input(
            "น้ำหนักตัว (กก.)", min_value=1.0, max_value=250.0, value=60.0, step=0.1
        )
        height_cm = st.number_input(
            "ความสูง (ซม.)", min_value=50.0, max_value=230.0, value=160.0, step=0.1
        )

        bmi = calculate_bmi(weight_kg, height_cm)

        if bmi:
            st.markdown("### ผล BMI และจำนวนจุดติดเม็ดผักกาด")
            bmi_label, bmi_color, seed_points_count = show_bmi_box(bmi)

        st.markdown("### แบบประเมินพฤติกรรม")
        appetite_score = st.slider("ระดับการเจริญอาหาร", 0, 10, 5)
        sweet_craving_score = st.slider("ความอยากอาหารหวาน", 0, 10, 5)
        salty_craving_score = st.slider("ความอยากอาหารเค็ม", 0, 10, 5)
        exercise_score = st.slider("การออกกำลังกายต่อสัปดาห์ที่ผ่านมา", 0, 10, 5)

        waist_cm = st.number_input(
            "เส้นรอบเอวระดับสะดือ จังหวะกึ่งหายใจเข้า (ซม.) — ไม่บังคับ",
            min_value=0.0,
            max_value=200.0,
            value=0.0,
            step=0.1,
        )

        submitted = st.form_submit_button("บันทึกข้อมูล")

    if submitted:
        if not found:
            if not regular_menses_or_menopause:
                st.error("ยังไม่ผ่าน checkbox เรื่องประจำเดือน/หมดประจำเดือน")
                st.stop()

            if not no_ear_inflammation:
                st.error("ยังไม่ผ่าน checkbox เรื่องไม่มีหูอักเสบ")
                st.stop()

        new_row = {
            "timestamp_bkk": bkk_now(),
            "citizen_id": citizen_id,
            "visit_type": visit_type,
            "sex": sex,
            "age": age,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "bmi": bmi,
            "bmi_color": bmi_color,
            "seed_points_count": seed_points_count,
            "regular_menses_or_menopause": regular_menses_or_menopause,
            "no_ear_inflammation": no_ear_inflammation,
            "appetite_score": appetite_score,
            "sweet_craving_score": sweet_craving_score,
            "salty_craving_score": salty_craving_score,
            "exercise_score": exercise_score,
            "waist_cm": "" if waist_cm == 0 else waist_cm,
        }

        try:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_csv_to_github(df, sha)
            st.success("บันทึกข้อมูลลง GitHub CSV สำเร็จ")
            st.balloons()
        except Exception as e:
            st.error(f"บันทึกข้อมูลไม่สำเร็จ: {e}")

st.divider()
st.caption(
    "หมายเหตุ: ข้อมูลเลขบัตรประชาชนเป็นข้อมูลอ่อนไหว ควรจำกัดสิทธิ์เข้าถึง GitHub repository "
    "และใช้ private repository เท่านั้น"
)
