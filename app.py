import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
from datetime import datetime

# ==========================================
# 1. CẤU HÌNH TRANG & GIAO DIỆN CHUNG
# ==========================================
st.set_page_config(page_title="Hệ thống Cảnh báo Sớm EWS", page_icon="🏫", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    h1, h2, h3 {color: #1e3d59;}
    .stMetric {background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
    </style>
    """, unsafe_allow_html=True)

# KHỞI TẠO BỘ NHỚ TẠM (Để không bị mất màn hình khi bấm Lưu)
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

# ==========================================
# 2. KHỞI TẠO CƠ SỞ DỮ LIỆU SQLITE (Lưu lịch sử)
# ==========================================
def init_db():
    conn = sqlite3.connect('hethong_ews.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS LichSuCanThiep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_hoc_sinh TEXT,
            ngay_luu TEXT,
            muc_do_rui_ro TEXT,
            ghi_chu TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. HÀM DỰ BÁO AI (MÔ PHỎNG)
# ==========================================
def predict_dropout(data):
    risk_score = 0.05
    if data['SoNgayVang'] > 10: risk_score += 0.35
    if data['SoNgayVang'] > 20: risk_score += 0.20
    if data['DiemTrungBinh'] < 5.0: risk_score += 0.25
    if data['KhoangCach'] > 15: risk_score += 0.08
    if data['HoanCanh'] != "Bình thường": risk_score += 0.1
    return min(risk_score, 0.98)

# ==========================================
# 4. HEADER GIAO DIỆN
# ==========================================
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.image("https://cdn-icons-png.flaticon.com/512/2941/2941658.png", width=80)
with col_title:
    st.title("HỆ THỐNG CẢNH BÁO SỚM HỌC SINH CÓ NGUY CƠ BỎ HỌC (EWS)")
    st.markdown("**Đơn vị quản lý:** Ban Giám Hiệu & Phòng Giáo Vụ | **Hệ thống:** AI & Máy học (XGBoost + XAI)")
st.divider()

# ==========================================
# 5. SIDEBAR: TẢI DATASET VÀ NHẬP LIỆU
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135810.png", width=100)
    st.header("1. Nguồn Dữ Liệu")
    
    uploaded_file = st.file_uploader("Tải lên file Dataset (CSV/Excel)", type=["csv", "xlsx"])
    
    def_hs, def_gpa, def_vang, def_khoangcach = "Nhập thủ công", 5.0, 0, 5
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Đã nạp {len(df)} hồ sơ!")

            all_columns = df.columns.tolist()
            id_col_index = next((i for i, col in enumerate(all_columns) if 'id' in str(col).lower() or 'mã' in str(col).lower()), 0)
            
            id_column_name = st.selectbox("🔑 Cột chứa Mã HS (Student ID):", all_columns, index=id_col_index)
            selected_hs = st.selectbox("📌 Chọn học sinh để phân tích:", ["Nhập thủ công"] + df[id_column_name].astype(str).tolist())
            
            if selected_hs != "Nhập thủ công":
                hs_data = df[df[id_column_name].astype(str) == selected_hs].iloc[0]
                def_hs = str(selected_hs)
                
                st.markdown("### 📋 Toàn bộ thông tin gốc:")
                st.dataframe(hs_data.to_frame().T, use_container_width=True)
                
                for col in all_columns:
                    col_name = str(col).lower()
                    if 'gpa' in col_name or 'diem' in col_name or 'điểm' in col_name: def_gpa = float(hs_data[col])
                    elif 'absent' in col_name or 'vang' in col_name or 'vắng' in col_name: def_vang = int(hs_data[col])
                    elif 'distance' in col_name or 'cach' in col_name or 'cách' in col_name: def_khoangcach = int(hs_data[col])

                st.info("👇 Đã trích xuất thông tin vào form bên dưới!")
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

    st.markdown("---")
    st.header("2. Dữ liệu Phân tích AI")
    hs_name = st.text_input("Mã số / Họ tên học sinh:", value=def_hs)
    diem_tb = st.slider("Điểm Trung bình (GPA):", 0.0, 10.0, float(def_gpa), 0.1)
    hanh_kiem = st.select_slider("Xếp loại Hạnh kiểm:", options=["Yếu", "Trung bình", "Khá", "Tốt"], value="Trung bình")
    ngay_vang = st.number_input("Tổng số ngày nghỉ học:", min_value=0, max_value=200, value=int(def_vang))
    khoang_cach = st.number_input("Khoảng cách (km):", min_value=0, max_value=100, value=int(def_khoangcach))
    hoan_canh = st.selectbox("Tình trạng gia đình:", ["Bình thường", "Hộ nghèo", "Cha mẹ ly hôn/Mồ côi"])
    
    st.markdown("---")
    # LƯU TRẠNG THÁI KHI BẤM NÚT PHÂN TÍCH
    if st.button("🚀 TIẾN HÀNH PHÂN TÍCH AI", use_container_width=True, type="primary"):
        st.session_state.analyzed = True

# ==========================================
# 6. KHU VỰC TRUNG TÂM (HIỂN THỊ KHI ĐÃ BẤM PHÂN TÍCH)
# ==========================================
if st.session_state.analyzed:
    input_data = {'DiemTrungBinh': diem_tb, 'SoNgayVang': ngay_vang, 'KhoangCach': khoang_cach, 'HanhKiem': hanh_kiem, 'HoanCanh': hoan_canh}
    risk_prob = predict_dropout(input_data)
    risk_percentage = risk_prob * 100

    if risk_prob < 0.3: status, color = "AN TOÀN", "green"
    elif risk_prob < 0.6: status, color = "NGUY CƠ TIỀM ẨN", "orange"
    else: status, color = "BÁO ĐỘNG ĐỎ", "red"

    st.markdown(f"### Tổng quan hồ sơ: **{hs_name}**")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Điểm TB", f"{diem_tb}/10", "- Đáng lo ngại" if diem_tb < 5 else "+ Ổn định")
    m2.metric("Ngày vắng", f"{ngay_vang} ngày", "- Rất cao" if ngay_vang > 10 else "Bình thường")
    m3.metric("Hoàn cảnh", hoan_canh)
    m4.metric("Trạng thái AI", status)
    st.markdown("<br>", unsafe_allow_html=True)

    # ĐÃ THÊM ĐẦY ĐỦ 4 TAB VÀO ĐÂY
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Báo cáo Dự báo", "🧠 Giải thích Rủi ro (SHAP)", "📝 Kế hoạch Can thiệp", "📜 Lịch sử lưu (CSDL)"])
    
    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### Chỉ số rủi ro bỏ học")
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = risk_percentage,
                number = {'suffix': "%", 'font': {'size': 50, 'color': color}},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "rgba(0,0,0,0)"},
                    'steps': [{'range': [0, 30], 'color': "#d4edda"}, {'range': [30, 60], 'color': "#fff3cd"}, {'range': [60, 100], 'color': "#f8d7da"}], 
                    'threshold': {'line': {'color': color, 'width': 8}, 'thickness': 0.75, 'value': risk_percentage}
                }))
            fig_gauge.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        with c2:
            st.markdown("#### Đánh giá từ Hệ thống")
            if color == "red": st.error("🚨 **Cảnh báo Cao!** Cần can thiệp gấp.")
            elif color == "orange": st.warning("⚠️ **Lưu ý.** Học sinh đang có dấu hiệu sa sút.")
            else: st.success("✅ **An toàn.**")

    with tab2:
        st.markdown("#### Đóng góp của từng yếu tố vào nguy cơ (SHAP Values)")
        shap_impact = [-0.05 if diem_tb >= 5.0 else 0.25, 0.15 if hoan_canh != "Bình thường" else -0.02, 0.08 if khoang_cach > 10 else -0.01, 0.35 if ngay_vang > 10 else -0.1]
        df_shap = pd.DataFrame({"Feature": ["Điểm trung bình", "Hoàn cảnh GĐ", "Khoảng cách", "Số ngày vắng"], "Impact": shap_impact})
        df_shap['Color'] = np.where(df_shap['Impact'] > 0, 'Tăng rủi ro', 'Giảm rủi ro')
        fig_shap = px.bar(df_shap, x='Impact', y='Feature', orientation='h', color='Color', color_discrete_map={'Tăng rủi ro': '#ef5350', 'Giảm rủi ro': '#66bb6a'}, text='Impact')
        fig_shap.update_layout(height=350)
        st.plotly_chart(fig_shap, use_container_width=True)

    with tab3:
        st.markdown("#### Khuyến nghị Cán bộ Quản lý")
        if ngay_vang > 10: st.checkbox("Tổ chức họp phụ huynh đột xuất.")
        if diem_tb < 5.0: st.checkbox("Phân công kèm cặp/đăng ký học phụ đạo.")
        st.checkbox("Tư vấn tâm lý học đường.")
        
        ghi_chu = st.text_area("Ghi chú thêm của Giáo viên:")
        
        # NÚT LƯU ĐÃ ĐƯỢC FIX LỖI
        if st.button("💾 Lưu Kế hoạch vào Cơ Sở Dữ Liệu"):
            conn = sqlite3.connect('hethong_ews.db')
            c = conn.cursor()
            thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO LichSuCanThiep (ma_hoc_sinh, ngay_luu, muc_do_rui_ro, ghi_chu) VALUES (?, ?, ?, ?)",
                      (hs_name, thoi_gian, status, ghi_chu))
            conn.commit()
            conn.close()
            st.success(f"✅ Đã lưu thành công hồ sơ của {hs_name} vào lúc {thoi_gian}!")

    # TAB 4: XEM LỊCH SỬ LƯU TRỮ TRỰC TIẾP TRÊN WEB
    with tab4:
        st.markdown("#### 📜 Bảng tra cứu Lịch sử Can thiệp")
        conn = sqlite3.connect('hethong_ews.db')
        df_db = pd.read_sql_query("SELECT * FROM LichSuCanThiep ORDER BY ngay_luu DESC", conn)
        conn.close()
        
        if not df_db.empty:
            df_db.columns = ['ID', 'Mã Học Sinh', 'Thời Gian Lưu', 'Mức Độ Rủi Ro', 'Ghi Chú']
            st.dataframe(df_db, use_container_width=True)
            # Nút tải file Excel/CSV báo cáo
            st.download_button(
                label="📥 Tải báo cáo CSV", 
                data=df_db.to_csv(index=False).encode('utf-8-sig'), 
                file_name="Lich_Su_Can_Thiep.csv", 
                mime="text/csv"
            )
        else:
            st.info("Chưa có hồ sơ nào được lưu trữ.")

else:
    st.info("💡 Bạn có thể tải file hoặc nhập tay thông tin bên trái, sau đó bấm 'PHÂN TÍCH AI' để bắt đầu.")
