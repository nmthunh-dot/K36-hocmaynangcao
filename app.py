import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN CHUNG & TRẠNG THÁI
# ==========================================
st.set_page_config(page_title="Hệ thống EWS - Ban Giám Hiệu", page_icon="🏫", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

# ==========================================
# 2. MÀN HÌNH ĐĂNG NHẬP (KHUNG HỒNG PHẤN - NÚT VIỀN XANH)
# ==========================================
if not st.session_state.logged_in:
    # CSS Đặc trị chỉ dành cho màn hình đăng nhập
    st.markdown("""
        <style>
        [data-testid="column"]:nth-of-type(2) {
            background-color: white !important; 
            border: 2px solid #FFD1DC !important; /* Viền hồng phấn */
            padding: 40px; 
            border-radius: 12px;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.05); 
            margin-top: 60px;
        }
        [data-testid="column"]:nth-of-type(2) label p { color: #31333F !important; font-weight: 500 !important; }
        .topic-title { color: #1A365D; font-size: 26px; font-weight: 700; text-align: center; margin-bottom: 30px; line-height: 1.4; }
        
        /* CSS cho nút đăng nhập viền xanh */
        div[data-testid="stButton"] button { 
            background-color: transparent !important; 
            color: #327BB5 !important; 
            border: 2px solid #327BB5 !important; 
            font-weight: bold !important; 
            border-radius: 8px !important;
        }
        div[data-testid="stButton"] button:hover { 
            background-color: #327BB5 !important; 
            color: white !important; 
        }
        </style>
        """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        # BẠN SỬA TÊN ĐỀ TÀI Ở DÒNG DƯỚI ĐÂY NHÉ:
        st.markdown('<div class="topic-title">MÔ PHỎNG: HỆ THỐNG CẢNH BÁO SỚM HỌC SINH (EWS)</div>', unsafe_allow_html=True)
        
        user = st.text_input("Tên đăng nhập")
        pw = st.text_input("Mật khẩu", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        # Nút đăng nhập đã được đóng khung
        if st.button("Đăng nhập", use_container_width=True):
            if user == "admin" and pw == "123456":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Sai thông tin đăng nhập!")
    st.stop()

# ==========================================
# 3. KHỞI TẠO CƠ SỞ DỮ LIỆU & HÀM AI (ĐÃ TRẢ LẠI NGUYÊN VẸN)
# ==========================================
# Trả lại nút bấm bình thường cho giao diện bên trong
st.markdown("""
    <style>
    .main {background-color: #F8F9FA;}
    div[data-testid="stButton"] button {background-color: transparent !important; color: inherit !important; border: 1px solid rgba(49, 51, 63, 0.2) !important; font-weight: normal !important;}
    div[data-testid="stMetricValue"] { font-size: 30px; font-weight: 700; color: #1A365D;}
    </style>
""", unsafe_allow_html=True)

def init_db():
    conn = sqlite3.connect('hethong_ews.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS LichSuCanThiep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_hoc_sinh TEXT,
            gpa REAL,
            ngay_vang INTEGER,
            ngay_luu TEXT,
            muc_do_rui_ro TEXT,
            ghi_chu TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def predict_dropout(data):
    risk_score = 0.05
    if data['SoNgayVang'] > 10: risk_score += 0.35
    if data['SoNgayVang'] > 20: risk_score += 0.20
    if data['DiemTrungBinh'] < 5.0: risk_score += 0.25
    if data['DiemTrungBinh'] < 3.5: risk_score += 0.15
    if data['KhoangCach'] > 15: risk_score += 0.08
    if data['HoanCanh'] != "Bình thường": risk_score += 0.1
    return min(risk_score, 0.98)

# ==========================================
# 4. GIAO DIỆN CHÍNH THỨC (CÓ AI VÀ TẢI FILE)
# ==========================================
col_l, col_t, col_btn = st.columns([1, 7, 1])
with col_l:
    st.image("https://cdn-icons-png.flaticon.com/512/2941/2941658.png", width=60)
with col_t:
    st.markdown("### HỆ THỐNG CẢNH BÁO SỚM HỌC SINH (EWS)")
    st.markdown("**Đơn vị:** Ban Giám Hiệu | **Trạng thái:** Đã xác thực")
with col_btn:
    if st.button("🚪 Đăng xuất"):
        st.session_state.logged_in = False
        st.session_state.analyzed = False
        st.rerun()
st.divider()

# ==========================================
# 5. SIDEBAR: TẢI FILE VÀ NHẬP LIỆU (ĐÃ TRẢ LẠI 100%)
# ==========================================
with st.sidebar:
    st.header("📂 1. Nguồn Dữ Liệu")
    uploaded_file = st.file_uploader("Tải file Dataset (CSV/Excel)", type=["csv", "xlsx"])
    
    def_hs, def_gpa, def_vang, def_khoangcach = "Nhập thủ công", 5.0, 0, 5
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.success(f"Đã nạp {len(df)} hồ sơ!")
            all_cols = df.columns.tolist()
            id_col = next((c for c in all_cols if 'id' in str(c).lower() or 'mã' in str(c).lower()), all_cols[0])
            selected_hs = st.selectbox("📌 Chọn học sinh:", ["Nhập thủ công"] + df[id_col].astype(str).tolist())
            
            if selected_hs != "Nhập thủ công":
                row = df[df[id_col].astype(str) == selected_hs].iloc[0]
                def_hs = str(selected_hs)
                st.write("**Dữ liệu gốc:**")
                st.dataframe(row.to_frame().T)
                
                # Bộ lọc điểm số siêu chống lỗi
                for c in all_cols:
                    c_low = str(c).lower()
                    val_str = str(row[c]).replace(',', '.').strip()
                    try:
                        if any(x in c_low for x in ['gpa', 'diem', 'điểm', 'score']): 
                            if val_str.upper() == 'A': parsed_val = 9.0
                            elif val_str.upper() == 'B': parsed_val = 7.5
                            elif val_str.upper() == 'C': parsed_val = 6.0
                            elif val_str.upper() == 'D': parsed_val = 4.0
                            elif val_str.upper() == 'F': parsed_val = 2.0
                            elif val_str.lower() in ['nan', 'null', '']: parsed_val = 5.0
                            else: parsed_val = float(val_str)
                            def_gpa = min(max(parsed_val, 0.0), 10.0)
                        elif any(x in c_low for x in ['vang', 'vắng', 'absent']): 
                            def_vang = int(float(val_str)) if val_str.lower() not in ['nan', 'null', ''] else 0
                        elif any(x in c_low for x in ['cach', 'cách', 'distance']): 
                            def_khoangcach = int(float(val_str)) if val_str.lower() not in ['nan', 'null', ''] else 5
                    except: pass
        except Exception as e: st.error(f"Lỗi đọc file: {e}")

    st.header("📝 2. Thông số Phân tích")
    def_gpa = float(def_gpa) if not pd.isna(def_gpa) else 5.0
    def_vang = int(def_vang) if not pd.isna(def_vang) else 0
    def_khoangcach = int(def_khoangcach) if not pd.isna(def_khoangcach) else 5

    hs_name = st.text_input("Họ tên / Mã HS:", value=def_hs)
    diem_tb = st.slider("Điểm trung bình (GPA):", 0.0, 10.0, def_gpa, 0.1)
    ngay_vang = st.number_input("Số ngày nghỉ học:", 0, 200, def_vang)
    khoang_cach = st.number_input("Khoảng cách (km):", 0, 100, def_khoangcach)
    hoan_canh = st.selectbox("Hoàn cảnh gia đình:", ["Bình thường", "Hộ nghèo", "Khó khăn đặc biệt"])
    
    st.markdown("---")
    # Nút AI đã được trả lại
    if st.button("🚀 TIẾN HÀNH PHÂN TÍCH AI", use_container_width=True):
        st.session_state.analyzed = True

# ==========================================
# 6. KHU VỰC KẾT QUẢ VÀ TABS AI
# ==========================================
if st.session_state.analyzed:
    input_data = {'DiemTrungBinh': diem_tb, 'SoNgayVang': ngay_vang, 'KhoangCach': khoang_cach, 'HoanCanh': hoan_canh}
    risk_prob = predict_dropout(input_data)
    risk_pct = int(risk_prob * 100)
    
    if risk_prob < 0.3: status, color = "✅ AN TOÀN", "green"
    elif risk_prob < 0.6: status, color = "⚠️ NGUY CƠ", "orange"
    else: status, color = "🚨 BÁO ĐỘNG", "red"

    st.subheader(f"📊 Kết quả phân tích AI: {hs_name}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("GPA", f"{diem_tb}/10")
    m2.metric("Nghỉ học", f"{ngay_vang} ngày")
    m3.metric("Trạng thái", status)
    m4.metric("Chỉ số rủi ro", f"{risk_pct}%")

    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Báo cáo rủi ro", "🧠 Giải thích AI", "📝 Lập Kế hoạch Can thiệp", "📜 Nhật ký hệ thống"])

    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = risk_pct,
                number = {'suffix': "%", 'font': {'size': 40, 'color': color}},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': color},
                    'steps': [{'range': [0, 30], 'color': "#d4edda"}, {'range': [30, 60], 'color': "#fff3cd"}, {'range': [60, 100], 'color': "#f8d7da"}], 
                    'threshold': {'line': {'color': color, 'width': 5}, 'thickness': 0.75, 'value': risk_pct}
                }))
            fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if risk_pct >= 60: st.error("🚨 Cảnh báo: Học sinh cần sự can thiệp khẩn cấp từ Ban giám hiệu.")
            elif risk_pct >= 30: st.warning("⚠️ Lưu ý: Học sinh có dấu hiệu bất thường về chuyên cần hoặc học lực.")
            else: st.success("✅ Học sinh đang duy trì trạng thái học tập tốt.")

    with tab2:
        st.markdown("#### Các yếu tố ảnh hưởng chính (XAI)")
        impact_data = pd.DataFrame({
            'Yếu tố': ["Học lực (GPA)", "Hoàn cảnh GĐ", "Khoảng cách", "Vắng mặt"],
            'Mức độ tác động': [-0.1 if diem_tb > 5 else 0.25, 0.15 if hoan_canh != "Bình thường" else -0.05, 0.08 if khoang_cach > 15 else -0.02, 0.45 if ngay_vang > 10 else -0.1]
        })
        fig_bar = px.bar(impact_data, x='Mức độ tác động', y='Yếu tố', orientation='h', color='Mức độ tác động', color_continuous_scale='RdBu_r')
        fig_bar.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0), coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.markdown("#### 🛠️ Các hành động can thiệp khuyến nghị:")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.write("**Hành động ưu tiên:**")
            st.checkbox("Tổ chức họp phụ huynh đột xuất", value=(ngay_vang > 10))
            st.checkbox("Xếp lớp phụ đạo/Kèm cặp 1-1", value=(diem_tb < 5.0))
            st.checkbox("Tham vấn tâm lý học đường", value=(risk_pct > 50))
        with col_c2:
            st.write("**Hành động bổ trợ:**")
            st.checkbox("Xét duyệt học bổng/Trợ cấp", value=(hoan_canh != "Bình thường"))
            st.checkbox("Gia hạn thời gian nộp bài tập/học phí")
            st.checkbox("Theo dõi đặc biệt từ GV Chủ nhiệm")

        ghi_chu = st.text_area("Ghi chú chi tiết của Cán bộ Giáo vụ:", placeholder="Nhập thêm nội dung can thiệp tại đây...")
        
        if st.button("💾 XÁC NHẬN & LƯU VÀO CSDL"):
            conn = sqlite3.connect('hethong_ews.db')
            c = conn.cursor()
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO LichSuCanThiep (ma_hoc_sinh, gpa, ngay_vang, ngay_luu, muc_do_rui_ro, ghi_chu) VALUES (?, ?, ?, ?, ?, ?)",
                      (hs_name, diem_tb, ngay_vang, time_now, status, ghi_chu))
            conn.commit(); conn.close()
            st.success(f"✅ Đã lưu hồ sơ của {hs_name} vào CSDL thành công!")

    with tab4:
        st.markdown("#### 📜 Danh sách các hồ sơ đã lưu")
        conn = sqlite3.connect('hethong_ews.db')
        df_db = pd.read_sql_query("SELECT * FROM LichSuCanThiep ORDER BY ngay_luu DESC", conn)
        conn.close()
        if not df_db.empty:
            df_db.columns = ['STT', 'Mã Học Sinh', 'GPA', 'Số Ngày Vắng', 'Ngày Lưu', 'Mức Độ Rủi Ro', 'Ghi Chú']
            st.dataframe(df_db, use_container_width=True)
            st.download_button("📥 Xuất báo cáo CSV", df_db.to_csv(index=False).encode('utf-8-sig'), "lich_su_can_thiep.csv", "text/csv")
        else:
            st.info("Cơ sở dữ liệu đang trống.")
else:
    st.info("💡 Hãy nạp dữ liệu ở bên trái và nhấn 'PHÂN TÍCH AI' để bắt đầu.")
