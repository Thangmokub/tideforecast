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

# CSS + JS + fade-in animation
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
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #388e3c;
        transform: scale(1.03);
    }
    .green-table {
        background-color: #f1f8e9;
        border-collapse: collapse;
        width: 100%;
        font-family: 'Kanit', sans-serif;
        font-size: 18px;
        margin-top: 20px;
    }
    .green-table th, .green-table td {
        border: 1px solid #c5e1a5;
        padding: 10px;
        text-align: center;
    }
    .green-table th {
        background-color: #aed581;
        color: #1b5e20;
    }
    .green-table tr:nth-child(odd) {
        background-color: #cbe0b1;
    }
    /* Fade-in animation */
    .fade-in {
        animation: fadeInAnimation ease 1.2s;
        animation-iteration-count: 1;
        animation-fill-mode: forwards;
    }
    @keyframes fadeInAnimation {
        0% {
            opacity: 0;
        }
        100% {
            opacity: 1;
        }
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
    <div class="fade-box fade-in" style="text-align:center; margin-top:100px;">
        <h1>👩‍🌾 ยินดีต้อนรับสู่ระบบพยากรณ์น้ำขึ้นน้ำลงเพื่อการเกษตร</h1>
        <p style="font-size:20px;">กดปุ่มด้านล่างเพื่อเข้าสู่แอป</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("เริ่มใช้งาน"):
        st.session_state.app_started = True
        

# ========================
# ส่วนหลักของแอป (หน้าหลักหลังจากกดเริ่ม)
# ========================
else:
    st.markdown("""
    <div class="fade-in">
        <div class="fade-box">
            <h2>🌾 ระบบพยากรณ์น้ำขึ้นน้ำลง</h2>
            <p>ระบบนี้จะแสดงแนวโน้มระดับน้ำรายวันเพื่อช่วยในการวางแผนเพาะปลูก</p>
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

    # เลือกเดือน
    month = st.selectbox("เลือกเดือน", pd.date_range(df['ds'].min(), df['ds'].max(), freq='MS').strftime("%B %Y"))
    month_dt = pd.to_datetime("01 " + month, format="%d %B %Y")
    df_month = df[df['ds'].dt.to_period("M") == month_dt.to_period("M")]

    if df_month.empty:
        st.warning("❌ ไม่มีข้อมูลในเดือนนี้")
    else:
        # สรุปรายวัน
        daily = df_month.groupby(df_month['ds'].dt.date)['y'].mean().reset_index()
        daily.columns = ['date', 'level_avg']

        rows = []
        for i in range(len(daily)):
            today = daily.iloc[i]
            if i > 0:
                prev = daily.iloc[i - 1]
                diff = today['level_avg'] - prev['level_avg']
                delta = f"{diff:+.2f}"
                trend = "🌊 น้ำขึ้น" if diff > 0 else "⬇️ น้ำลง"
            else:
                delta = "-"
                trend = "-"

            # กำหนดสถานะเกลือ/จืด/ปกติ ตามระดับน้ำเฉลี่ย
            if today['level_avg'] >= high_threshold:
                salinity = "เค็ม"
            elif today['level_avg'] <= low_threshold:
                salinity = "จืด"
            else:
                salinity = "ปกติ"

            # เพิ่มแนวโน้มความเค็มโดยประมาณตามแนวโน้มน้ำขึ้นน้ำลง
            if trend == "🌊 น้ำขึ้น":
                salinity_trend = "น้ำเค็ม"
            elif trend == "⬇️ น้ำลง":
                salinity_trend = "น้ำจืด"
            else:
                salinity_trend = "-"

            rows.append({
                "วันที่": today['date'].strftime("%-d %b %Y"),
                "ระดับเฉลี่ย (ม.)": f"{today['level_avg']:.2f} ({salinity})",
                "แนวโน้ม": trend,
                "Δ จากวันก่อน (ม.)": delta,
                "แนวโน้มความเค็ม (โดยประมาณ)": salinity_trend
            })

        df_summary = pd.DataFrame(rows)

        # สร้าง HTML ตาราง (เพิ่มคอลัมน์แนวโน้มความเค็ม)
        table_html = "<table class='green-table'><tr><th>วันที่</th><th>ระดับเฉลี่ย (ม.)</th><th>แนวโน้ม</th><th>Δ จากวันก่อน (ม.)</th><th>แนวโน้มความเค็ม (โดยประมาณ)</th></tr>"
        for _, row in df_summary.iterrows():
            table_html += f"<tr><td>{row['วันที่']}</td><td>{row['ระดับเฉลี่ย (ม.)']}</td><td>{row['แนวโน้ม']}</td><td>{row['Δ จากวันก่อน (ม.)']}</td><td>{row['แนวโน้มความเค็ม (โดยประมาณ)']}</td></tr>"
        table_html += "</table>"

        st.markdown("🗓️ **แนวโน้มรายวันของเดือน**", unsafe_allow_html=True)
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # ปิด div.fade-in
