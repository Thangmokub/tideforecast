# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import locale

# ==========================
# ตั้งค่าเบื้องต้น
# ==========================
st.set_page_config(page_title="พยากรณ์น้ำขึ้นน้ำลง", page_icon="🌊")

if 'app_started' not in st.session_state:
    st.session_state.app_started = False

try:
    locale.setlocale(locale.LC_TIME, "th_TH.UTF-8")
except:
    pass

# ==========================
# CSS + JS ตกแต่ง
# ==========================
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
        table-layout: fixed;
    }
    .green-table th, .green-table td {
        border: 1px solid #c5e1a5;
        padding: 10px;
        text-align: center;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    .green-table th {
        background-color: #aed581;
        color: #1b5e20;
    }
    .green-table tr:nth-child(odd) {
        background-color: #cbe0b1;
    }
    .green-table th:nth-child(1), .green-table td:nth-child(1) { width: 18%; }
    .green-table th:nth-child(2), .green-table td:nth-child(2) { width: 22%; }
    .green-table th:nth-child(3), .green-table td:nth-child(3) { width: 20%; }
    .green-table th:nth-child(4), .green-table td:nth-child(4) { width: 20%; }
    .green-table th:nth-child(5), .green-table td:nth-child(5) { width: 20%; }

    .fade-in {
        animation: fadeInAnimation ease 1.2s;
        animation-iteration-count: 1;
        animation-fill-mode: forwards;
    }
    @keyframes fadeInAnimation {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }
    </style>
    <script>
    document.addEventListener('contextmenu', e => {
        e.preventDefault();
        alert('ไม่สามารถคลิกขวาได้บนเว็บไซต์นี้');
    });
    </script>
""", unsafe_allow_html=True)

# ==========================
# ฟังก์ชันทำความสะอาด CSV (แก้ชื่อคอลัมน์แปลกๆ)
# ==========================
def load_and_clean_csv(file):
    try:
        df = pd.read_csv(file, encoding='utf-8')

        # ลบอักขระแปลกในชื่อคอลัมน์
        df.columns = [col.strip().replace('\ufeff', '').replace('', '') for col in df.columns]

        # แปลงชื่อคอลัมน์ที่มีโอกาสต่างกันให้เป็นมาตรฐาน
        col_map = {}
        for col in df.columns:
            c = col.lower()
            if c.startswith('ds'):
                col_map[col] = 'วันที่'
            elif c == 'time':
                col_map[col] = 'เวลา'
            elif c == 'y':
                col_map[col] = 'ระดับน้ำ'
        df.rename(columns=col_map, inplace=True)

        # เช็คว่ามีคอลัมน์ครบหรือไม่
        if not {'วันที่', 'เวลา', 'ระดับน้ำ'}.issubset(df.columns):
            return pd.DataFrame()

        def convert(row):
            try:
                d, m, y_th = map(int, str(row['วันที่']).split("/"))
                y_ad = y_th - 543
                time_parts = str(row['เวลา']).split(":")
                h = int(time_parts[0])
                mi = int(time_parts[1]) if len(time_parts) > 1 else 0
                s = int(time_parts[2]) if len(time_parts) > 2 else 0
                return datetime(y_ad, m, d, h, mi, s)
            except:
                return pd.NaT

        df['ds'] = df.apply(convert, axis=1)
        df['y'] = pd.to_numeric(df['ระดับน้ำ'], errors='coerce')

        df_clean = df[['ds', 'y']].dropna().sort_values(by='ds').reset_index(drop=True)
        return df_clean

    except Exception as e:
        st.warning(f"⚠️ อ่านไฟล์ {file} ไม่ได้: {e}")
        return pd.DataFrame()

# ==========================
# ส่วนต้อนรับ
# ==========================
if not st.session_state.app_started:
    st.markdown("""<div class="fade-box fade-in" style="text-align:center; margin-top:100px;">
        <h1>ยินดีต้อนรับสู่ระบบพยากรณ์น้ำขึ้นน้ำลงเพื่อการเกษตร</h1>
        <p style="font-size:20px;">กดปุ่มด้านล่างเพื่อเข้าสู่แอป</p>
    </div>""", unsafe_allow_html=True)

    if st.button("เริ่มใช้งาน"):
        st.session_state.app_started = True

# ==========================
# ส่วนหลัก
# ==========================
else:
    st.markdown("""<div class="fade-in">
        <div class="fade-box">
            <h2>ระบบพยากรณ์น้ำขึ้นน้ำลง</h2>
            <p>ระบบนี้จะแสดงแนวโน้มระดับน้ำรายวันเพื่อช่วยในการวางแผนเพาะปลูก</p>
        </div>
    </div>""", unsafe_allow_html=True)

    files = [
        'BP2025_all_months_for_prophet.csv',
        'บางปะกง.csv',
        'บางปะกง (3).csv',
        'บางปะกง (2).csv',
        'กรกฏา.csv',
        'สิงหา.csv'
    ]

    dfs = []
    for f in files:
        if os.path.isfile(f):
            df_temp = load_and_clean_csv(f)
            if not df_temp.empty:
                st.success(f"✅ โหลดข้อมูลจาก {f} สำเร็จ ({len(df_temp)} แถว)")
                dfs.append(df_temp)
            else:
                st.warning(f"⚠️ ไฟล์ {f} ไม่มีข้อมูลที่ใช้ได้")
        else:
            st.warning(f"❌ ไม่พบไฟล์ {f}")

    if not dfs:
        st.error("❌ ไม่พบข้อมูลที่ใช้งานได้")
        st.stop()

    df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset='ds').sort_values(by='ds')

    median_level = 2.82
    high_threshold = 3.51
    low_threshold = 1.90

    months = pd.date_range(df['ds'].min(), df['ds'].max(), freq='MS').strftime("%B %Y").tolist()
    month = st.selectbox("เลือกเดือน", months)

    try:
        month_dt = pd.to_datetime("01 " + month, format="%d %B %Y")
    except:
        st.error("❌ ไม่สามารถแปลงชื่อเดือนเป็นวันที่ได้")
        st.stop()

    df_month = df[df['ds'].dt.to_period("M") == month_dt.to_period("M")]

    if df_month.empty:
        st.warning("❌ ไม่มีข้อมูลในเดือนนี้")
    else:
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

            if today['level_avg'] >= high_threshold:
                salinity = "เค็ม"
            elif today['level_avg'] <= low_threshold:
                salinity = "จืด"
            else:
                salinity = "ปกติ"

            salinity_trend = "น้ำเค็ม" if trend == "🌊 น้ำขึ้น" else ("น้ำจืด" if trend == "⬇️ น้ำลง" else "-")

            rows.append({
                "วันที่": today['date'].strftime("%-d %b %Y"),
                "ระดับเฉลี่ย (ม.)": f"{today['level_avg']:.2f} ({salinity})",
                "แนวโน้ม": trend,
                "Δ จากวันก่อน (ม.)": delta,
                "แนวโน้มความเค็ม": salinity_trend
            })

        df_summary = pd.DataFrame(rows)

        def connect_to_google_sheets():
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("bangprakong-e632dd777e72.json", scope)
            return gspread.authorize(creds)

        def write_to_google_sheets(dataframe):
            try:
                client = connect_to_google_sheets()
                sheet = client.open_by_key("1RHi72uEhlTXParxn0jDfLwKJcQGJoamW7XYjvvnhIac").sheet1
                data = [["วันที่", "ระดับเฉลี่ย (ม.)", "แนวโน้ม", "Δ จากวันก่อน (ม.)", "แนวโน้มความเค็ม"]]
                for _, row in dataframe.iterrows():
                    data.append([row["วันที่"], row["ระดับเฉลี่ย (ม.)"], row["แนวโน้ม"], row["Δ จากวันก่อน (ม.)"], row["แนวโน้มความเค็ม"]])
                sheet.clear()
                sheet.update("A1", data)
                st.success("✅ ส่งข้อมูลไป Google Sheets สำเร็จ!")
            except Exception as e:
                st.error(f"❌ ไม่สามารถเขียน Google Sheets: {e}")

        if st.button("ส่งข้อมูลไป Google Sheets"):
            write_to_google_sheets(df_summary)

        table_html = "<table class='green-table'><tr><th>วันที่</th><th>ระดับเฉลี่ย (ม.)</th><th>แนวโน้ม</th><th>Δ จากวันก่อน (ม.)</th><th>แนวโน้มความเค็ม</th></tr>"
        for _, row in df_summary.iterrows():
            table_html += f"<tr><td>{row['วันที่']}</td><td>{row['ระดับเฉลี่ย (ม.)']}</td><td>{row['แนวโน้ม']}</td><td>{row['Δ จากวันก่อน (ม.)']}</td><td>{row['แนวโน้มความเค็ม']}</td></tr>"
        table_html += "</table>"

        st.markdown("🗓️ **แนวโน้มรายวันของเดือน**", unsafe_allow_html=True)
        st.markdown(table_html, unsafe_allow_html=True)
