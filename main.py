import streamlit as st
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt
import os

# ตั้งค่าเพจ
st.set_page_config(page_title="พยากรณ์น้ำขึ้นน้ำลง", page_icon="🌊")

# สร้างสถานะเริ่มต้น
if 'app_started' not in st.session_state:
    st.session_state.app_started = False

# CSS + JS
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
    st.markdown("""
    <div class="fade-box">
        <h2>🌾 ระบบพยากรณ์น้ำขึ้นน้ำลง</h2>
        <p>ยินดีต้อนรับ! คุณสามารถเลือกวันและดูแนวโน้มระดับน้ำได้เพื่อการเพาะปลูกที่แม่นยำ</p>
    </div>
    """, unsafe_allow_html=True)

    file_path = r"BP2025_all_months_for_prophet.csv"

    if not os.path.isfile(file_path):
        st.error(f"❌ ไม่พบไฟล์: {file_path}")
    else:
        df = pd.read_csv(file_path)

        date_col = next((c for c in ['ds', 'date', 'วันที่', 'Date', 'datetime'] if c in df.columns), None)
        if not date_col:
            st.error("❌ ไม่พบคอลัมน์วันที่ในไฟล์")
        else:
            df['ds'] = pd.to_datetime(df[date_col])

            if 'y' not in df.columns:
                st.error("❌ ไม่พบคอลัมน์ 'y' (ค่าระดับน้ำ)")
            else:
                menu = st.sidebar.selectbox("เลือกเมนู", ["เลือกวันและพยากรณ์", "สรุปผลการพยากรณ์"])

                # กำหนดค่ากลางและเกณฑ์แจ้งเตือน
                median_level = 2.82
                high_threshold = 3.51
                low_threshold = 1.90

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
