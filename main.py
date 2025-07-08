import streamlit as st
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import re

# ตั้งค่าหน้า
st.set_page_config(page_title="พยากรณ์น้ำขึ้นน้ำลง", page_icon="🌊")

# CSS + JS สำหรับหน้าตาและป้องกันคลิกขวา คัดลอก
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit&display=swap');
    html, body, .stApp {
        background-color: #f1f8e9;
        font-family: 'Kanit', sans-serif;
        color: #1b5e20;
        transition: all 0.3s ease-in-out;
    }
    .block-container { padding-top: 2rem; }
    h1, h2, h3, h4 {
        color: #2e7d32;
        animation: fadeIn 1s ease-out;
    }
    .fade-box {
        background: linear-gradient(to right, #dcedc8, #f0f4c3);
        border-left: 8px solid #81c784;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        animation: fadeInUp 1s ease-out;
    }
    .stButton>button {
        background-color: #66bb6a;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1.5em;
        font-size: 18px;
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #388e3c;
        transform: scale(1.03);
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    <script>
    document.addEventListener('contextmenu', function(event) {
        event.preventDefault();
        alert('❌ ไม่สามารถคลิกขวาได้บนเว็บไซต์นี้');
    });
    document.addEventListener('keydown', function (event) {
        if ((event.ctrlKey && event.key.toLowerCase() === 'c') ||
            (event.ctrlKey && event.key.toLowerCase() === 'u') ||
            event.key === 'F12') {
            event.preventDefault();
            alert('🔒 ห้ามคัดลอกหรือดูซอร์สโค้ดหน้านี้');
        }
    });
    </script>
""", unsafe_allow_html=True)


def find_date_text(soup):
    # หาแท็กหลายแบบที่อาจมีวันที่
    candidates = []
    for tag_name in ['h3', 'caption', 'p', 'strong']:
        elements = soup.find_all(tag_name)
        for el in elements:
            text = el.get_text(strip=True)
            if "วันที่" in text or "ประจำวันที่" in text:
                candidates.append(text)
    date_pattern = re.compile(r"(?:วันที่|ประจำวันที่)\s*(\d{1,2})\s*(\S+)\s*(\d{4})")
    for text in candidates:
        if date_pattern.search(text):
            return text
    return None


@st.cache_data(ttl=3600)
def fetch_tide_data():
    url = "https://www.thailandtidetables.com/ไทย/ตารางน้ำขึ้นน้ำลง-ปากน้ำบางปะกง-ฉะเชิงเทรา-480.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/114.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return pd.DataFrame(), f"❌ ดึงข้อมูลไม่ได้: {e}"

    soup = BeautifulSoup(response.content, "html.parser")
    # แก้ตรงนี้
    table = soup.find("table", {"class": "table table-bordered table-hover"})
    if not table:
        return pd.DataFrame(), "❌ ไม่พบตารางข้อมูลน้ำขึ้นน้ำลง"

    # (ส่วนอื่น ๆ ของโค้ดยังคงเหมือนเดิม)


    date_text_str = find_date_text(soup)
    if not date_text_str:
        return pd.DataFrame(), "❌ ไม่พบวันที่จากเว็บไซต์"

    # Debug: แสดงวันที่ที่เจอ (ลบออกได้ถ้าอยาก)
    st.write("วันที่ที่เจอ:", date_text_str)

    match = re.search(r"(?:วันที่|ประจำวันที่)\s*(\d{1,2})\s*(\S+)\s*(\d{4})", date_text_str)
    if not match:
        return pd.DataFrame(), "❌ ไม่สามารถอ่านวันที่ได้"

    day, month_th, year_str = match.groups()
    year = int(year_str)
    if year > 2500:  # แปลงปี พ.ศ. เป็น ค.ศ.
        year -= 543

    month_map = {
        "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
        "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
        "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
    }
    month = month_map.get(month_th)
    if not month:
        return pd.DataFrame(), f"❌ ไม่รู้จักเดือน: {month_th}"

    try:
        base_date = datetime(year, month, int(day))
    except:
        return pd.DataFrame(), "❌ วันที่ไม่ถูกต้อง"

    rows = table.find_all("tr")
    data = []
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            time_str = cols[0].text.strip()
            level_str = cols[1].text.strip().replace("m", "").replace("เมตร", "")
            try:
                dt = datetime.strptime(time_str, "%H:%M")
                full_dt = datetime.combine(base_date, dt.time())
                level = float(level_str)
                data.append({"ds": full_dt, "y": level})
            except:
                continue

    if not data:
        return pd.DataFrame(), "⚠️ ไม่พบข้อมูลที่แปลงได้"

    df = pd.DataFrame(data)
    return df, None


# เริ่มต้นตัวแปร session_state
if 'app_started' not in st.session_state:
    st.session_state.app_started = False

# หน้าเริ่มต้นถ้ายังไม่เริ่มใช้งาน
if not st.session_state.app_started:
    st.markdown("""
    <div class="fade-box" style="text-align:center; margin-top:100px;">
        <h1>👩‍🌾 ยินดีต้อนรับสู่ระบบพยากรณ์น้ำขึ้นน้ำลงเพื่อการเกษตร</h1>
        <p style="font-size:20px;">กดปุ่มด้านล่างเพื่อเข้าสู่แอป</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("เริ่มใช้งาน"):
        st.session_state.app_started = True
        st.experimental_rerun()  # เรียกตรงนี้เลย

# หน้าแอปหลักเมื่อเริ่มใช้งานแล้ว
else:
    df, error = fetch_tide_data()

    st.markdown("""
    <div class="fade-box">
        <h2>🌾 ระบบพยากรณ์น้ำขึ้นน้ำลง (ข้อมูลวันนี้)</h2>
        <p>ดึงข้อมูลจากเว็บไซต์โดยตรงแบบเรียลไทม์</p>
    </div>
    """, unsafe_allow_html=True)

    if error:
        st.error(error)
    elif df.empty:
        st.warning("⚠️ ไม่มีข้อมูลจากเว็บไซต์")
    else:
        df['ds'] = pd.to_datetime(df['ds'])

        menu = st.sidebar.selectbox("เลือกเมนู", ["ดูข้อมูลวันนี้", "พยากรณ์ล่วงหน้า", "สรุปแนวโน้ม"])

        if menu == "ดูข้อมูลวันนี้":
            st.subheader("📅 ตารางระดับน้ำวันนี้")
            st.dataframe(df)

        elif menu == "พยากรณ์ล่วงหน้า":
            st.subheader("🔮 พยากรณ์น้ำล่วงหน้า")
            periods = st.slider("พยากรณ์กี่ชั่วโมง?", 6, 72, 24)

            df_past = df[df['ds'] <= datetime.now()]
            if len(df_past) < 10:
                st.warning("⚠️ ข้อมูลย้อนหลังไม่เพียงพอ")
            else:
                model = Prophet()
                with st.spinner("📈 กำลังพยากรณ์..."):
                    model.fit(df_past)
                    future = model.make_future_dataframe(periods=periods, freq='H')
                    forecast = model.predict(future)

                st.session_state['forecast'] = forecast
                st.session_state['periods'] = periods

                fig = model.plot(forecast)
                st.pyplot(fig)

                st.subheader("📊 ตารางผลลัพธ์")
                st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail())

        elif menu == "สรุปแนวโน้ม":
            st.subheader("📈 สรุปแนวโน้ม")
            if 'forecast' in st.session_state:
                forecast = st.session_state['forecast']
                periods = st.session_state['periods']
                if len(forecast) > periods:
                    delta = forecast.iloc[-1]['yhat'] - forecast.iloc[-periods]['yhat']
                    if delta > 0:
                        st.success(f"🌊 คาดว่าน้ำจะเพิ่มขึ้น {delta:.2f} เมตร")
                    else:
                        st.info(f"⬇️ คาดว่าน้ำจะลดลง {abs(delta):.2f} เมตร")
                else:
                    st.warning("⚠️ ข้อมูลไม่เพียงพอสำหรับเปรียบเทียบ")
            else:
                st.warning("⚠️ กรุณาพยากรณ์ก่อนในเมนูพยากรณ์ล่วงหน้า")
