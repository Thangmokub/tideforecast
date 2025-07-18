# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt
import os
from datetime import datetime

st.set_page_config(page_title="พยากรณ์น้ำขึ้นน้ำลง", page_icon="🌊")

if 'app_started' not in st.session_state:
    st.session_state.app_started = False

# CSS + JS
st.markdown(r"""
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
        padding: 0.5em 1.5em;
        font-size: 18px;
    }
    .stButton>button:hover {
        background-color: #388e3c;
        transform: scale(1.03);
    }
    </style>
    <script>
    document.addEventListener('contextmenu', e => {
        e.preventDefault();
        alert('ไม่สามารถคลิกขวาได้บนเว็บไซต์นี้');
    });
    </script>
""", unsafe_allow_html=True)

# ส่วนต้อนรับ
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

# ========================
# ส่วนหลักของแอป
# ========================
else:
    st.markdown("""
    <div class="fade-box">
        <h2>🌾 ระบบพยากรณ์น้ำขึ้นน้ำลง</h2>
        <p>ยินดีต้อนรับ! คุณสามารถเลือกวันและดูแนวโน้มระดับน้ำได้เพื่อการเพาะปลูกที่แม่นยำ</p>
    </div>
    """, unsafe_allow_html=True)

    def load_and_clean_df(df):
        try:
            def convert(row):
                try:
                    d, m, y_th = map(int, str(row['วันที่']).split("/"))
                    y_ad = y_th - 543
                    h, mi, s = map(int, str(row['เวลา']).split(":"))
                    return datetime(y_ad, m, d, h, mi, s)
                except:
                    return pd.NaT

            df['ds'] = df.apply(convert, axis=1)
            df['y'] = pd.to_numeric(df['ระดับน้ำ'], errors='coerce')
            return df[['ds', 'y']].dropna()
        except:
            return pd.DataFrame()

    def load_and_clean_csv(file):
        try:
            df = pd.read_csv(file, encoding='utf-8')

            if {'วันที่', 'เวลา', 'ระดับน้ำ'}.issubset(df.columns):
                return load_and_clean_df(df)

            elif {'ds', 'y'}.issubset(df.columns):
                df['ds'] = pd.to_datetime(df['ds'], errors='coerce')
                df['y'] = pd.to_numeric(df['y'], errors='coerce')
                return df[['ds', 'y']].dropna()

            elif df.shape[1] >= 3:
                df.columns = ['วันที่', 'เวลา', 'ระดับน้ำ']
                return load_and_clean_df(df)

            return pd.DataFrame()
        except Exception as e:
            st.warning(f"⚠️ อ่านไฟล์ {file} ไม่ได้: {e}")
            return pd.DataFrame()

    files = ['BP2025_all_months_for_prophet.csv','บางปะกง.csv', 'บางปะกง (3).csv']
    dfs = [load_and_clean_csv(f) for f in files if os.path.isfile(f)]
    df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset='ds').sort_values(by='ds')

    if df.empty:
        st.error("❌ ไม่พบข้อมูลที่ใช้งานได้")
        st.stop()

    median_level = 2.82
    high_threshold = 3.51
    low_threshold = 1.90

    menu = st.sidebar.selectbox("เลือกเมนู", ["เลือกวันและพยากรณ์", "สรุปผลการพยากรณ์"])

    if menu == "เลือกวันและพยากรณ์":
        st.title("📅 พยากรณ์น้ำขึ้น-น้ำลงแบบเลือกวัน")
        selected_date = st.date_input("เลือกวันที่ต้องการดู", value=pd.to_datetime("2025-01-01"))
        selected_date = pd.to_datetime(selected_date)

        df_today = df[df['ds'].dt.normalize() == selected_date]
        if df_today.empty:
            st.warning("❌ ไม่มีข้อมูลในวันนี้")
        else:
            st.dataframe(df_today)

        st.subheader("🔮 พยากรณ์ล่วงหน้า")
        periods = st.slider("พยากรณ์กี่ชั่วโมง?", 6, 168, 24)

        df_past = df[df['ds'] <= selected_date]
        if len(df_past) < 10:
            st.warning("⚠️ ข้อมูลในอดีตไม่เพียงพอ")
        else:
            model = Prophet()
            try:
                with st.spinner("กำลังพยากรณ์..."):
                    model.fit(df_past)
                    future = model.make_future_dataframe(periods=periods, freq='H')
                    forecast = model.predict(future)

                st.session_state['forecast'] = forecast
                st.session_state['periods'] = periods

                st.subheader("📈 กราฟผลลัพธ์")
                fig = model.plot(forecast)
                ax = fig.gca()
                ax.axhline(median_level, color='green', linestyle='--', label=f'ระดับน้ำปกติ ({median_level} ม.)')
                ax.axhline(high_threshold, color='red', linestyle='--', label=f'🚨 น้ำขึ้นสูงเกิน (≥ {high_threshold} ม.)')
                ax.axhline(low_threshold, color='blue', linestyle='--', label=f'⚠️ น้ำลดต่ำเกิน (≤ {low_threshold} ม.)')
                ax.legend()
                st.pyplot(fig)

                st.subheader("📊 ตารางคาดการณ์ล่าสุด")
                st.dataframe(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail())
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    elif menu == "สรุปผลการพยากรณ์":
        if 'forecast' in st.session_state:
            forecast = st.session_state['forecast']
            periods = st.session_state['periods']

            if len(forecast) > periods:
                delta = forecast.iloc[-1]['yhat'] - forecast.iloc[-periods]['yhat']
                current_level = forecast.iloc[-1]['yhat']

                if delta > 0:
                    msg = f"🌊 คาดว่าน้ำจะขึ้น {delta:.2f} เมตร"
                else:
                    msg = f"⬇️ คาดว่าน้ำจะลด {abs(delta):.2f} เมตร"

                if current_level >= high_threshold:
                    msg += " (🚨 น้ำขึ้นสูงเกินค่าปกติ!)"
                    st.error(msg)
                elif current_level <= low_threshold:
                    msg += " (⚠️ น้ำลดต่ำเกินค่าปกติ!)"
                    st.warning(msg)
                else:
                    st.success(msg)
            else:
                st.warning("⚠️ ข้อมูลไม่เพียงพอสำหรับการเปรียบเทียบ")
        else:
            st.warning("⚠️ กรุณาพยากรณ์ก่อนในเมนูแรก")
