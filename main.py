import streamlit as st
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# -------------------------------
# ฟังก์ชันดึงข้อมูลจากเว็บไซต์
# -------------------------------
@st.cache_data(ttl=3600)
def fetch_tide_data():
    url = "https://www.thailandtidetables.com/ไทย/ตารางน้ำขึ้นน้ำลง-ปากน้ำบางปะกง-ฉะเชิงเทรา-480.php"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", {"class": "tide-table"})

    if not table:
        return pd.DataFrame(), "❌ ไม่พบตารางในเว็บไซต์"

    rows = table.find_all("tr")
    data = []

    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            time_str = cols[0].text.strip()
            level_str = cols[1].text.strip().replace("m", "")
            try:
                dt = datetime.strptime(time_str, "%H:%M")
                full_dt = datetime.combine(datetime.today(), dt.time())
                level = float(level_str)
                data.append({"ds": full_dt, "y": level})
            except:
                continue

    if not data:
        return pd.DataFrame(), "⚠️ ไม่พบข้อมูลที่แปลงได้"

    df = pd.DataFrame(data)
    return df, None

# -------------------------------
# เริ่มต้น Streamlit App
# -------------------------------
st.set_page_config(page_title="พยากรณ์น้ำขึ้นน้ำลง", page_icon="🌊")

if 'app_started' not in st.session_state:
    st.session_state.app_started = False

# CSS/JS Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit&display=swap');
    html, body, .stApp {
        background-color: #f1f8e9;
        font-family: 'Kanit', sans-serif;
        color: #1b5e20;
    }
    .block-container { padding-top: 2rem; }
    .fade-box {
        background: linear-gradient(to right, #dcedc8, #f0f4c3);
        border-left: 8px solid #81c784;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #66bb6a;
        color: white;
        border-radius: 8px;
        font-size: 18px;
    }
    .stButton>button:hover {
        background-color: #388e3c;
        transform: scale(1.03);
    }
    </style>
""", unsafe_allow_html=True)

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
        st.rerun()

# -------------------------------
# หน้าแอปหลัก
# -------------------------------
else:
    st.markdown("""
    <div class="fade-box">
        <h2>🌾 ระบบพยากรณ์น้ำขึ้นน้ำลง</h2>
        <p>แสดงข้อมูลจากปากน้ำบางปะกงแบบเรียลไทม์</p>
    </div>
    """, unsafe_allow_html=True)

    df, error = fetch_tide_data()

    if error:
        st.error(error)
    elif df.empty:
        st.warning("ไม่พบข้อมูล")
    else:
        df['ds'] = pd.to_datetime(df['ds'])

        menu = st.sidebar.selectbox("เลือกเมนู", ["เลือกวันและพยากรณ์", "สรุปผลการพยากรณ์"])

        if menu == "เลือกวันและพยากรณ์":
            st.title("📅 พยากรณ์น้ำขึ้น-น้ำลงแบบเรียลไทม์")

            selected_date = st.date_input("เลือกวันที่", value=datetime.today())
            selected_date = pd.to_datetime(selected_date)

            df_today = df[df['ds'].dt.date == selected_date.date()]
            if df_today.empty:
                st.warning("❌ ไม่มีข้อมูลของวันนี้")
            else:
                st.dataframe(df_today)

            st.subheader("🔮 พยากรณ์ล่วงหน้า")
            periods = st.slider("พยากรณ์กี่ชั่วโมง?", 6, 72, 24)

            df_past = df[df['ds'] <= datetime.now()]
            if len(df_past) < 10:
                st.warning("⚠️ ข้อมูลไม่เพียงพอ")
            else:
                model = Prophet()
                with st.spinner("กำลังพยากรณ์..."):
                    model.fit(df_past)
                    future = model.make_future_dataframe(periods=periods, freq='H')
                    forecast = model.predict(future)

                st.session_state['forecast'] = forecast
                st.session_state['periods'] = periods

                st.subheader("📈 กราฟผลลัพธ์")
                fig = model.plot(forecast)
                st.pyplot(fig)

                st.subheader("📊 ตารางคาดการณ์ล่าสุด")
                st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail())

        elif menu == "สรุปผลการพยากรณ์":
            if 'forecast' in st.session_state:
                forecast = st.session_state['forecast']
                periods = st.session_state['periods']
                if len(forecast) > periods:
                    delta = forecast.iloc[-1]['yhat'] - forecast.iloc[-periods]['yhat']
                    if delta > 0:
                        st.success(f"🌊 คาดว่าน้ำจะขึ้น {delta:.2f} เมตร")
                    else:
                        st.info(f"⬇️ คาดว่าน้ำจะลด {abs(delta):.2f} เมตร")
                else:
                    st.warning("⚠️ ข้อมูลไม่เพียงพอสำหรับเปรียบเทียบ")
            else:
                st.warning("⚠️ กรุณาพยากรณ์ก่อนในเมนูแรก")
