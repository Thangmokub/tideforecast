import streamlit as st
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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

# ฟังก์ชันดึงข้อมูลแบบ retry และ timeout
def get_with_retry(url):
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    try:
        response = session.get(url, timeout=20)
        response.raise_for_status()
        return response.text, None
    except Exception as e:
        return None, f"❌ ดึงข้อมูลไม่ได้: {e}"

# ฟังก์ชันดึงข้อมูลน้ำขึ้นน้ำลงจาก hydro.md.go.th (ปรับแต่งตามโครงสร้างเว็บจริง)
def fetch_tide_data_hydro():
    url = "http://hydro.md.go.th/MD/Station?code=MD14"
    html, error = get_with_retry(url)
    if error:
        return pd.DataFrame(), error

    soup = BeautifulSoup(html, "html.parser")

    # หาตารางข้อมูล (ปรับ selector ตามเว็บจริง)
    table = soup.find("table", {"class": "table table-bordered table-hover"})
    if not table:
        return pd.DataFrame(), "❌ ไม่พบตารางข้อมูลน้ำขึ้นน้ำลง"

    # ดึงหัวข้อวันที่จากหน้า (ถ้ามี) หรือกำหนดเอง
    date_div = soup.find("div", {"class": "date-class-or-similar"})  # ตัวอย่าง ต้องแก้ตามจริง
    if date_div:
        date_str = date_div.text.strip()
        # แปลง string เป็น datetime ตามรูปแบบจริง
        # ตัวอย่าง:
        # base_date = datetime.strptime(date_str, "%d/%m/%Y")
    else:
        base_date = datetime.now().date()

    data = []
    rows = table.find_all("tr")
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
            except Exception:
                continue

    if not data:
        return pd.DataFrame(), "⚠️ ไม่พบข้อมูลที่แปลงได้"

    df = pd.DataFrame(data)
    return df, None

# เริ่มต้น session_state
if 'app_started' not in st.session_state:
    st.session_state.app_started = False

# หน้าเริ่มต้น
if not st.session_state.app_started:
    st.markdown("""
    <div class="fade-box" style="text-align:center; margin-top:100px;">
        <h1>👩‍🌾 ยินดีต้อนรับสู่ระบบพยากรณ์น้ำขึ้นน้ำลงเพื่อการเกษตร</h1>
        <p style="font-size:20px;">กดปุ่มด้านล่างเพื่อเข้าสู่แอป</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("เริ่มใช้งาน"):
        st.session_state.app_started = True
        st.experimental_rerun()

# หน้าแอปหลัก
else:
    df, error = fetch_tide_data_hydro()

    st.markdown("""
    <div class="fade-box">
        <h2>🌾 ระบบพยากรณ์น้ำขึ้นน้ำลง (ข้อมูลวันนี้)</h2>
        <p>ดึงข้อมูลจาก hydro.md.go.th แบบเรียลไทม์</p>
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
