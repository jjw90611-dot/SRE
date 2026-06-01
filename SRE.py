import streamlit as st
import sqlite3
import datetime
import time
import requests
import re
import calendar
import pandas as pd
import math
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import json
from dateutil.relativedelta import relativedelta

# ==========================================
# [초기 설정] 페이지 세팅
# ==========================================
st.set_page_config(page_title="부동산 맛동산", page_icon="🥜", layout="wide")

# ==========================================
# [API 키 설정] Groq, Kakao, Data.go.kr
# ==========================================
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    KAKAO_REST_KEY = st.secrets["KAKAO_API_KEY"]
    KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]
    DATA_GO_KR_KEY = st.secrets["DATA_GO_KR_API_KEY"]
except KeyError:
    st.error("⚠️ 스트림릿 설정(Secrets)에 API 키(GROQ, KAKAO, DATA_GO_KR)가 모두 있는지 확인해주세요!")
    st.stop()

# ==========================================
# [데이터베이스 설정] SQLite3
# ==========================================
conn = sqlite3.connect('real_estate_matdongsan.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS chat_records (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, query TEXT, answer TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS ddays (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, title TEXT, target_date TEXT, category TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS field_diaries (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, content TEXT)''')
conn.commit()

# ==========================================
# [CSS] 서울남산체 & 고대비 다크 테마
# ==========================================
st.markdown("""
<style>
    /* 서울남산체 웹폰트 적용 */
    @font-face {
        font-family: 'SeoulNamsanM';
        src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_two@1.0/SeoulNamsanM.woff') format('woff');
        font-weight: normal;
        font-style: normal;
    }

    .stApp, p, span, div, h1, h2, h3, h4, h5, h6, label, input, textarea, button, table, th, td {
        font-family: 'SeoulNamsanM', sans-serif !important;
    }
    
    /* 배경: 다크 슬레이트 */
    .stApp { 
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
        color: #ffffff !important; 
    }
    
    /* 네온 타이틀 */
    .neon-title {
        font-size: 48px; font-weight: 900; color: #ffffff; text-align: center;
        margin-top: 20px; margin-bottom: 10px; letter-spacing: -1px; line-height: 1.2;
        text-shadow: 0 0 10px rgba(245, 158, 11, 0.8), 0 0 20px rgba(245, 158, 11, 0.5);
    }
    .sub-title { color: #fcd34d; font-size: 20px; margin-bottom: 40px; font-weight: bold; text-align: center; }

    /* 입력창 디자인 (배경을 더 어둡게 하여 글자 가독성 확보) */
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div:first-child {
        background-color: rgba(0, 0, 0, 0.6) !important; 
        border: 2px solid #d97706 !important; 
        border-radius: 12px !important;
    }
    input, textarea { color: #ffffff !important; font-size: 18px !important; font-weight: bold !important; }
    input::placeholder, textarea::placeholder { color: #9ca3af !important; font-weight: normal !important; }
    
    /* 버튼 디자인 */
    div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important; 
        color: #ffffff !important; 
        font-weight: bold !important; font-size: 18px !important; padding: 12px 24px !important;
        border: none !important; border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(217, 119, 6, 0.6) !important;
    }

    /* 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; background-color: transparent; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(0,0,0,0.4); border-radius: 10px 10px 0 0; 
        padding: 12px 20px; color: #cbd5e1; font-size: 18px; font-weight: bold; border: 1px solid #334155; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { 
        background-color: rgba(245, 158, 11, 0.2); color: #fcd34d !important; 
        border-bottom: 4px solid #f59e0b !important; 
    }

    /* 채팅 UI */
    .chat-user { text-align: right; margin-bottom: 15px; }
    .chat-user span { background-color: #3b82f6; color: white; padding: 12px 18px; border-radius: 20px 20px 0 20px; display: inline-block; font-size: 16px; font-weight: bold; }
    .chat-ai { text-align: left; margin-bottom: 25px; }
    .chat-ai span { background-color: rgba(245, 158, 11, 0.15); color: #fdf6e3; border: 1px solid #f59e0b; padding: 15px 20px; border-radius: 20px 20px 20px 0; display: inline-block; font-size: 16px; line-height: 1.6; }

    /* 카드 UI */
    .info-card {
        background: rgba(0,0,0,0.5); border: 1px solid #f59e0b;
        border-radius: 16px; padding: 20px; margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# [세션 상태 관리]
# ==========================================
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_id' not in st.session_state: st.session_state['user_id'] = ""
if 'chat_session' not in st.session_state: st.session_state['chat_session'] = [] 

# ==========================================
# [프롭테크 핵심 함수] 에러 방지 완벽 적용
# ==========================================
LAWD_CD_DICT = {
    "서울 강남구": "11680", "서울 송파구": "11710", "경기 성남 분당구": "41135", "경기 하남시": "41450",
    "부산 해운대구": "26350", "대구 수성구": "27260", "경북 포항 남구": "47111", "경북 포항 북구": "47113"
}

@st.cache_data(ttl=3600)
def get_apt_data(lawd_cd, deal_ym):
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {"serviceKey": DATA_GO_KR_KEY, "pageNo": "1", "numOfRows": "100", "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ym}
    try:
        res = requests.get(url, params=params, timeout=5)
        root = ET.fromstring(res.content)
        data = []
        for item in root.findall('.//item'):
            price = int(item.findtext('dealAmount').replace(',', '').strip())
            area = float(item.findtext('excluUseAr'))
            data.append({
                "apt_name": item.findtext('aptNm'), "price": price, "area": area, "pyung": round(area / 3.3, 1),
                "floor": item.findtext('floor'), "dong": item.findtext('umdNm'), "jibun": item.findtext('jibun'),
                "build_year": int(item.findtext('buildYear')) if item.findtext('buildYear') else 0
            })
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def get_coords(address):
    """카카오 API 에러 방지 무적 로직"""
    clean_address = address.split('(')[0].strip()
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    try:
        res = requests.get(url, headers=headers, params={"query": clean_address}).json()
        if res.get('documents'):
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
        
        url_kw = "https://dapi.kakao.com/v2/local/search/keyword.json"
        res_kw = requests.get(url_kw, headers=headers, params={"query": address}).json()
        if res_kw.get('documents'):
            return float(res_kw['documents'][0]['y']), float(res_kw['documents'][0]['x'])
    except:
        pass
    return None, None # 실패 시 None 반환하여 예외 처리

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================
# [화면 구성] 1. 로그인 / 회원가입 화면
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("<div class='neon-title'>🏢 부동산 맛동산 🥜</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>달콤하고 바삭한 부동산 정보, 2026년형 AI 프롭테크 솔루션</div>", unsafe_allow_html=True)
    
    col_empty1, col_login, col_empty2 = st.columns([1, 2, 1])
    with col_login:
        auth_tab1, auth_tab2 = st.tabs(["🔑 로그인", "📝 회원가입"])
        with auth_tab1:
            login_id = st.text_input("아이디", key="login_id")
            login_pw = st.text_input("비밀번호", type="password", key="login_pw")
            if st.button("로그인", use_container_width=True):
                c.execute("SELECT * FROM users WHERE user_id=? AND password=?", (login_id, login_pw))
                if c.fetchone():
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = login_id
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
                    
        with auth_tab2:
            reg_id = st.text_input("사용할 아이디", key="reg_id")
            reg_pw = st.text_input("사용할 비밀번호", type="password", key="reg_pw")
            reg_pw_confirm = st.text_input("비밀번호 확인", type="password", key="reg_pw_confirm")
            if st.button("가입하기", use_container_width=True):
                if reg_pw == reg_pw_confirm and reg_id:
                    try:
                        c.execute("INSERT INTO users (user_id, password) VALUES (?, ?)", (reg_id, reg_pw))
                        conn.commit()
                        st.success("가입 완료! 로그인 탭에서 로그인해주세요.")
                    except:
                        st.error("이미 존재하는 아이디입니다.")

# ==========================================
# [화면 구성] 2. 메인 서비스 화면 (5개 탭)
# ==========================================
else:
    st.markdown(f"<div class='neon-title' style='font-size: 36px;'>🏢 {st.session_state['user_id']}님의 부동산 맛동산 🥜</div>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn3:
        if st.button("🔒 로그아웃", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🤖 AI 상담", "🗺️ 실거래가 지도", "🏆 입지 추천", "📝 임장 일기", "📅 D-Day"])

    # ------------------------------------------
    # [탭 1] AI 부동산 상담 (Groq)
    # ------------------------------------------
    with tab1:
        st.markdown("### 🤖 바삭하고 명쾌한 AI 부동산 상담")
        if st.button("🔄 대화 초기화", key="reset_chat"):
            st.session_state['chat_session'] = []
            st.rerun()

        for msg in st.session_state['chat_session']:
            st.markdown(f"<div class='chat-user'><span>{msg['query']}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='chat-ai'><span>{msg['answer']}</span></div>", unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            user_query = st.text_area("질문을 입력하세요.", height=100)
            if st.form_submit_button("질문하기", use_container_width=True) and user_query.strip():
                with st.spinner("AI가 답변을 준비 중입니다..."):
                    messages = [{"role": "system", "content": "당신은 부동산 맛동산 AI입니다. 한국어만 사용하세요."}]
                    for m in st.session_state['chat_session']:
                        messages.extend([{"role": "user", "content": m['query']}, {"role": "assistant", "content": m['answer']}])
                    messages.append({"role": "user", "content": user_query})
                    
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                                        headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, 
                                        json={"model": "llama-3.3-70b-versatile", "messages": messages})
                    if res.status_code == 200:
                        answer = re.sub(r'[a-zA-Z\u4e00-\u9fff]', '', res.json()['choices'][0]['message']['content']).strip()
                        st.session_state['chat_session'].append({'query': user_query, 'answer': answer})
                        st.rerun()

    # ------------------------------------------
    # [탭 2] 🗺️ 실거래가 지도 (에러 방지)
    # ------------------------------------------
    with tab2:
        st.markdown("### 🗺️ 클릭하면 가격이 나오는 실거래가 지도")
        col_m1, col_m2 = st.columns(2)
        with col_m1: map_region = st.selectbox("지역 선택", list(LAWD_CD_DICT.keys()), index=6)
        with col_m2: map_ym = st.text_input("계약 연월", value=(datetime.datetime.now() - relativedelta(months=2)).strftime("%Y%m"))
        
        if st.button("지도 불러오기", use_container_width=True):
            with st.spinner("데이터를 불러오는 중입니다..."):
                df_map = get_apt_data(LAWD_CD_DICT[map_region], map_ym)
                if not df_map.empty:
                    df_map = df_map.drop_duplicates(subset=['apt_name'])
                    map_data = []
                    for _, row in df_map.iterrows():
                        lat, lng = get_coords(f"{row['dong']} {row['jibun']}")
                        if lat and lng:
                            map_data.append({"name": row['apt_name'], "price": row['price'], "lat": lat, "lng": lng})
                    
                    if map_data:
                        center_lat, center_lng = map_data[0]['lat'], map_data[0]['lng']
                        map_html = f"""
                        <div id="map" style="width:100%;height:500px;border-radius:10px;"></div>
                        <script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}"></script>
                        <script>
                            var map = new kakao.maps.Map(document.getElementById('map'), {{center: new kakao.maps.LatLng({center_lat}, {center_lng}), level: 5}});
                            var data = {json.dumps(map_data)};
                            data.forEach(function(d) {{
                                var content = '<div style="background:#0052A4;color:white;padding:5px;border-radius:5px;font-size:12px;">' + d.name + '<br>' + (d.price/10000).toFixed(1) + '억</div>';
                                new kakao.maps.CustomOverlay({{position: new kakao.maps.LatLng(d.lat, d.lng), content: content, map: map}});
                            }});
                        </script>
                        """
                        components.html(map_html, height=520)
                    else:
                        st.warning("해당 지역의 아파트 좌표를 변환할 수 없습니다. (카카오 API 검색 결과 없음)")
                else:
                    st.warning(f"{map_ym} 연월의 거래 데이터가 없습니다.")

    # ------------------------------------------
    # [탭 3] 🏆 브역대신평초 추천 (에러 방지 & 수식)
    # ------------------------------------------
    with tab3:
        st.markdown("### 🏆 브역대신평초 맞춤형 아파트 추천")
        with st.form("reco_form"):
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                target_region = st.selectbox("희망 거주 지역", list(LAWD_CD_DICT.keys()), index=6)
                budget_max = st.number_input("최대 예산 (만원)", value=40000, step=1000)
            with col_r2:
                work_address = st.text_input("직장 주소 (도로명)", value="경북 포항시 남구 신항로 110")
            submit_reco = st.form_submit_button("AI 분석 시작", use_container_width=True)

        if submit_reco:
            with st.spinner("분석 중입니다..."):
                work_lat, work_lng = get_coords(work_address)
                if not work_lat:
                    st.warning(f"'{work_address}' 주소를 정확히 찾지 못해 기본 좌표(시청) 기준으로 거리를 계산합니다.")
                    work_lat, work_lng = 36.0190, 129.3434 # 포항시청 기본값
                
                search_ym = (datetime.datetime.now() - relativedelta(months=2)).strftime("%Y%m")
                df = get_apt_data(LAWD_CD_DICT[target_region], search_ym)
                
                if df.empty:
                    st.error("해당 지역의 최근 거래 데이터가 없습니다.")
                else:
                    df_filtered = df[df['price'] <= budget_max].drop_duplicates(subset=['apt_name'])
                    if len(df_filtered) == 0:
                        st.warning("예산에 맞는 아파트가 없습니다.")
                    else:
                        candidates = []
                        for _, row in df_filtered.iterrows():
                            apt_lat, apt_lng = get_coords(f"{row['dong']} {row['jibun']}")
                            if apt_lat:
                                dist = haversine_distance(apt_lat, apt_lng, work_lat, work_lng)
                                candidates.append({"name": row['apt_name'], "price": row['price'], "pyung": row['pyung'], "dist": dist})
                        
                        candidates = sorted(candidates, key=lambda x: x['dist'])[:3]
                        
                        for i, apt in enumerate(candidates):
                            st.markdown(f"<div class='info-card'><h4>🥇 {i+1}위: {apt['name']}</h4>", unsafe_allow_html=True)
                            
                            st.markdown("객관적인 가격 비교를 위한 평당 단가 계산:")
                            
                            st.latex(r"평당 단가 = \frac{예상 매매가}{평수}")
                            
                            st.markdown(f"""
                            * **예상 매매가:** {apt['price']:,}만 원 ({apt['pyung']}평)
                            * **평당 단가:** {int(apt['price']/apt['pyung']):,}만 원/평
                            * **직장까지 거리:** 약 {apt['dist']:.1f}km
                            </div>
                            """, unsafe_allow_html=True)

    # ------------------------------------------
    # [탭 4] 📝 임장 일기 (기존 코드 유지)
    # ------------------------------------------
    with tab4:
        st.markdown("### 📝 스마트 임장 일기")
        today_date = datetime.date.today()
        selected_date = st.date_input("기록할 날짜", value=today_date)
        
        c.execute("SELECT content FROM field_diaries WHERE user_id=? AND date=?", (st.session_state['user_id'], str(selected_date)))
        row = c.fetchone()
        current_content = row[0] if row else ""
        
        with st.form("diary_form"):
            new_content = st.text_area("임장 기록", value=current_content, height=150)
            if st.form_submit_button("💾 기록 저장", use_container_width=True):
                if row: c.execute("UPDATE field_diaries SET content=? WHERE user_id=? AND date=?", (new_content, st.session_state['user_id'], str(selected_date)))
                else: c.execute("INSERT INTO field_diaries (user_id, date, content) VALUES (?, ?, ?)", (st.session_state['user_id'], str(selected_date), new_content))
                conn.commit()
                st.success("저장되었습니다!")
                st.rerun()

    # ------------------------------------------
    # [탭 5] 📅 D-Day (기존 코드 유지)
    # ------------------------------------------
    with tab5:
        st.markdown("### 📅 청약 및 이사 D-Day 관리")
        with st.form("dday_form"):
            d_title = st.text_input("일정 이름")
            d_date = st.date_input("목표 날짜")
            d_cat = st.selectbox("카테고리", ["청약/분양", "계약/잔금", "이사", "기타"])
            if st.form_submit_button("일정 추가", use_container_width=True) and d_title:
                c.execute("INSERT INTO ddays (user_id, title, target_date, category) VALUES (?, ?, ?, ?)", (st.session_state['user_id'], d_title, str(d_date), d_cat))
                conn.commit()
                st.rerun()
                
        c.execute("SELECT id, title, target_date, category FROM ddays WHERE user_id=? ORDER BY target_date ASC", (st.session_state['user_id'],))
        for d_id, title, t_date_str, cat in c.fetchall():
            delta = (datetime.datetime.strptime(t_date_str, "%Y-%m-%d").date() - datetime.date.today()).days
            d_text = f"D-{delta}" if delta > 0 else (f"D+{-delta}" if delta < 0 else "D-Day")
            st.markdown(f"<div class='info-card'><b>{cat}</b> | {title} <span style='float:right; color:#fcd34d; font-size:20px;'>{d_text}</span></div>", unsafe_allow_html=True)
