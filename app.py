import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ==========================================
# 1. CẤU HÌNH & CSS (CHUẨN CHUYÊN NGHIỆP - EDUTECH)
# ==========================================
st.set_page_config(page_title="EWS - THPT Nguyễn Huệ", page_icon="🏫", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #F8FAFC; }
    
    /* Màu sắc chữ và tiêu đề */
    h1, h2, h3, h4 { color: #0F172A !important; font-weight: 700 !important; }
    p, span, label { color: #334155 !important; }
    
    /* Form đăng nhập */
    .login-container {
        background-color: #FFFFFF; padding: 40px; border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08); max-width: 450px;
        margin: 80px auto; border-top: 5px solid #1E3A8A; 
    }
    .sys-title { color: #1E3A8A; font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 5px; }
    .sys-subtitle { color: #64748B; font-size: 14px; text-align: center; margin-bottom: 30px; }
    
    /* Nút bấm (Button) */
    div[data-testid="stButton"] button { border-radius: 6px !important; font-weight: 600 !important; transition: all 0.2s; }
    div[data-testid="stButton"] button[kind="primary"] { background-color: #1E3A8A !important; color: #FFFFFF !important; border: none !important; }
    div[data-testid="stButton"] button[kind="primary"]:hover { background-color: #1E40AF !important; }
    
    /* Metrics / Thẻ Chỉ số */
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: 700; color: #0F172A; }
    div[data-testid="stMetricLabel"] { font-size: 14px; font-weight: 600; color: #64748B; text-transform: uppercase; }
    
    /* Khung kết quả phân tích */
    .card-box { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# Khởi tạo bộ nhớ an toàn (Session State)
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'analyzed' not in st.session_state: st.session_state.analyzed = False
for key, val in {'val_hs': "Nhập thủ công", 'val_gpa': 5.0, 'val_vang': 0, 'val_kc': 5, 'val_hc': "Bình thường"}.items():
    if key not in st.session_state: st.session_state[key] = val

# ==========================================
# 2. MÀN HÌNH ĐĂNG NHẬP
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown('''
            <div class="login-container">
                <div class="sys-title">HỆ THỐNG CẢNH BÁO SỚM (EWS)</div>
                <div class="sys-subtitle">Đơn vị: THPT Nguyễn Huệ</div>
        ''', unsafe_allow_html=True)
        
        user = st.text_input("Tên đăng nhập", placeholder="Nhập tài khoản quản trị")
        pw = st.text_input("Mật khẩu", type="password", placeholder="••••••")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Đăng nhập hệ thống", use_container_width=True, type="primary"):
            if user == "admin" and pw == "123456":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Tài khoản hoặc mật khẩu không chính xác.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. KẾT NỐI CƠ SỞ DỮ LIỆU & LÕI ĐỒNG BỘ
# ==========================================
def get_db_conn():
    return sqlite3.connect('hethong_ews.db', check_same_thread=False)

def db_query(q, params=(), fetch=False):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(q, params)
    if fetch: 
        res = cursor.fetchall()
        conn.close()
        return res
    conn.commit()
    conn.close()

db_query('''CREATE TABLE IF NOT EXISTS LichSu (id INTEGER PRIMARY KEY AUTOINCREMENT, ma TEXT, gpa REAL, vang INTEGER, ngay TEXT, rui_ro TEXT, ghi_chu TEXT)''')

# HÀM ĐỒNG BỘ DỮ LIỆU THÔNG MINH (ĐÃ ĐƯỢC NÂNG CẤP)
def sync_data():
    if st.session_state.file_select != "Nhập thủ công" and 'current_df' in st.session_state:
        df = st.session_state.current_df
        id_col = st.session_state.id_col
        row = df[df[id_col].astype(str) == st.session_state.file_select].iloc[0]
        
        st.session_state.val_hs = str(st.session_state.file_select)
        st.session_state.val_hc = "Bình thường"
        
        # Quét thông minh qua tất cả các cột
        for c in df.columns:
            c_low = str(c).lower().strip()
            val_str = str(row[c]).replace(',', '.').strip()
            
            try:
                # 1. Tìm GPA
                if any(x in c_low for x in ['gpa', 'diem', 'điểm', 'score', 'tb']):
                    if val_str.upper() in ['A','B','C','D','F']:
                        st.session_state.val_gpa = {'A':9.0, 'B':7.5, 'C':6.0, 'D':4.0, 'F':2.0}.get(val_str.upper(), 5.0)
                    else:
                        parsed_val = float(val_str)
                        if parsed_val > 0: # Tránh gán bằng 0.0 nếu cột bị nhiễu
                            st.session_state.val_gpa = min(max(parsed_val, 0.0), 10.0)
                
                # 2. Tìm Ngày Vắng
                elif any(x in c_low for x in ['vang', 'vắng', 'absent', 'nghỉ']):
                    if val_str.lower() not in ['nan', 'null', '']:
                        st.session_state.val_vang = int(float(val_str))
                
                # 3. Tìm Khoảng cách
                elif any(x in c_low for x in ['cach', 'distance', 'kc']):
                    if val_str.lower() not in ['nan', 'null', '']:
                        st.session_state.val_kc = int(float(val_str))
                
                # 4. AI nhận diện Gia đình đơn thân
                elif any(x in c_low for x in ['cha', 'mẹ', 'father', 'mother', 'phụ huynh', 'parent']):
                    if pd.isna(row[c]) or val_str == "" or val_str.lower() == "nan" or val_str == "0":
                        st.session_state.val_hc = "Gia đình đơn thân"
            except: pass

def predict_dropout(data):
    score = 0.05
    if data['SoNgayVang'] > 10: score += 0.35
    if data['SoNgayVang'] > 20: score += 0.20
    if data['DiemTrungBinh'] < 5.0: score += 0.25
    if data['KhoangCach'] > 15: score += 0.08
    if data['HoanCanh'] == "Gia đình đơn thân": score += 0.12
    elif data['HoanCanh'] != "Bình thường": score += 0.15
    return min(score, 0.98)

# ==========================================
# 4. DASHBOARD CHÍNH
# ==========================================
col_title, col_logout = st.columns([9, 1])
with col_title: 
    st.markdown("<div style='border-bottom: 1px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 20px;'><h2 style='margin:0;'>Phân tích & Cảnh báo nguy cơ học sinh</h2></div>", unsafe_allow_html=True)
with col_logout: 
    if st.button("Đăng xuất", use_container_width=True): st.session_state.logged_in = False; st.rerun()

with st.sidebar:
    st.markdown("### 📊 Dữ liệu đầu vào")
    up_file = st.file_uploader("Nạp dữ liệu (CSV/Excel)", type=["csv", "xlsx"])
    
    if up_file:
        df = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
        st.session_state.current_df = df
        all_c = df.columns.tolist()
        st.session_state.id_col = next((c for c in all_c if 'mã' in c.lower() or 'id' in c.lower() or 'student' in c.lower()), all_c[0])
        
        st.selectbox("Chọn hồ sơ học sinh:", ["Nhập thủ công"] + df[st.session_state.id_col].astype(str).tolist(), 
                     key="file_select", on_change=sync_data)
        st.success(f"Đã nạp thành công {len(df)} bản ghi.")

    st.markdown("---")
    st.markdown("### ⚙️ Thông số chi tiết")
    # Các trường này lấy value trực tiếp từ session_state thông qua key
    st.text_input("Mã định danh:", key="val_hs")
    st.slider("Điểm trung bình (GPA):", 0.0, 10.0, key="val_gpa", step=0.1)
    st.number_input("Số ngày vắng mặt:", 0, 100, key="val_vang")
    st.number_input("Khoảng cách đến trường (km):", 0, 100, key="val_kc")
    st.selectbox("Tình trạng gia đình:", ["Bình thường", "Gia đình đơn thân", "Hộ nghèo", "Khó khăn đặc biệt"], key="val_hc")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Tiến hành phân tích", use_container_width=True, type="primary"): 
        st.session_state.analyzed = True

# ==========================================
# 5. KHU VỰC KẾT QUẢ
# ==========================================
if st.session_state.analyzed:
    input_dict = {'DiemTrungBinh': st.session_state.val_gpa, 'SoNgayVang': st.session_state.val_vang, 
                  'KhoangCach': st.session_state.val_kc, 'HoanCanh': st.session_state.val_hc}
    risk = predict_dropout(input_dict)
    pct = int(risk * 100)
    
    if risk < 0.3: status, color_hex = "AN TOÀN", "#10B981" # Xanh lục
    elif risk < 0.6: status, color_hex = "CẦN LƯU Ý", "#F59E0B" # Vàng cam
    else: status, color_hex = "NGUY HIỂM", "#EF4444" # Đỏ

    # Card Metrics
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.markdown(f"<h4 style='color: #1E3A8A; margin-top:0;'>Báo cáo tổng quan: {st.session_state.val_hs}</h4>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mức độ rủi ro", f"{pct}%")
    m2.metric("Trạng thái", status)
    m3.metric("GPA hiện tại", f"{st.session_state.val_gpa}")
    m4.metric("Ngày vắng", f"{st.session_state.val_vang}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Card Tabs
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Biểu đồ Phân tích", "Kế hoạch Can thiệp", "Nhật ký Hệ thống"])
    
    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("**Chỉ số nguy cơ bỏ học**")
            fig = go.Figure(go.Indicator(mode="gauge+number", value=pct, number={'suffix': "%", 'font': {'color': '#0F172A'}},
                gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"}, 'bar': {'color': color_hex}, 
                       'steps': [{'range': [0, 30], 'color': "#D1FAE5"}, {'range': [30, 60], 'color': "#FEF3C7"}, {'range': [60, 100], 'color': "#FEE2E2"}]}))
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.markdown("**Mức độ tác động của các yếu tố**")
            hc_impact = 0.12 if st.session_state.val_hc == "Gia đình đơn thân" else (0.15 if st.session_state.val_hc != "Bình thường" else -0.05)
            impact_data = pd.DataFrame({'Tiêu chí': ["GPA", "Gia đình", "Khoảng cách", "Vắng mặt"],
                'Chỉ số': [-0.1 if st.session_state.val_gpa > 5 else 0.25, hc_impact, 0.08 if st.session_state.val_kc > 15 else -0.02, 0.45 if st.session_state.val_vang > 10 else -0.1]})
            
            fig_bar = px.bar(impact_data, x='Chỉ số', y='Tiêu chí', orientation='h', color='Chỉ số', color_continuous_scale=[[0, '#3B82F6'], [1, '#EF4444']])
            fig_bar.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0), coloraxis_showscale=False, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.markdown("**Đề xuất hành động hỗ trợ từ hệ thống:**")
        col_c1, col_c2 = st.columns(2)
        with col_c1: 
            st.markdown("<span style='color:#1E3A8A; font-weight:600;'>Hỗ trợ Học tập & Tâm lý:</span>", unsafe_allow_html=True)
            st.checkbox("Bố trí giáo viên phụ đạo học lực", value=(st.session_state.val_gpa < 5))
            st.checkbox("Linh động hạn nộp bài tập", value=(st.session_state.val_vang > 5))
            st.checkbox("Chuyển thông tin tới ban tư vấn tâm lý", value=(risk > 0.5))
        with col_c2: 
            st.markdown("<span style='color:#1E3A8A; font-weight:600;'>Hỗ trợ Gia đình & Tài chính:</span>", unsafe_allow_html=True)
            st.checkbox("Tổ chức họp với Phụ huynh học sinh", value=(st.session_state.val_vang > 10))
            st.checkbox("Tổ chức thăm hỏi gia đình", value=(st.session_state.val_hc == "Gia đình đơn thân"))
            st.checkbox("Rà soát chính sách hỗ trợ học phí", value=(st.session_state.val_hc != "Bình thường"))
        
        ghi_chu = st.text_area("Cập nhật ý kiến xử lý của Giáo viên / Ban Giám hiệu:")
        if st.button("💾 Lưu biên bản đánh giá", type="primary"):
            db_query("INSERT INTO LichSu (ma, gpa, vang, ngay, rui_ro, ghi_chu) VALUES (?,?,?,?,?,?)", 
                     (st.session_state.val_hs, st.session_state.val_gpa, st.session_state.val_vang, datetime.now().strftime("%d/%m/%Y %H:%M"), status, ghi_chu))
            st.success("Hệ thống đã lưu trữ thành công vào Cơ sở dữ liệu!")

    with tab3:
        st.markdown("**Cơ sở dữ liệu lưu trữ**")
        data = db_query("SELECT * FROM LichSu ORDER BY id DESC", fetch=True)
        if data:
            df_log = pd.DataFrame(data, columns=['ID', 'Mã HS', 'GPA', 'Vắng', 'Ngày lưu', 'Rủi ro', 'Ghi chú'])
            st.dataframe(df_log, use_container_width=True, hide_index=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Quản lý dữ liệu**")
            col_del1, col_del2 = st.columns([2, 3])
            with col_del1:
                delete_list = [f"{r[0]} - Mã: {r[1]} ({r[4]})" for r in data]
                to_delete = st.selectbox("Chọn bản ghi cần xóa:", delete_list, label_visibility="collapsed")
            with col_del2:
                if st.button("❌ Xóa bản ghi", type="secondary"):
                    target_id = to_delete.split(" - ")[0]
                    db_query("DELETE FROM LichSu WHERE id=?", (target_id,))
                    st.rerun()
        else: st.info("Hệ thống chưa có dữ liệu lưu trữ.")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("💡 Hệ thống đang ở trạng thái chờ. Vui lòng nhập thông tin tại menu bên trái và chọn 'Tiến hành phân tích'.")
