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
import urllib.parse
from dateutil.relativedelta import relativedelta

# ==========================================
# [초기 설정] 페이지 세팅
# ==========================================
st.set_page_config(page_title="부동산 맛동산", page_icon="🥜", layout="wide")

# ==========================================
# [API 키 설정 및 디코딩]
# ==========================================
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    KAKAO_REST_KEY = st.secrets["KAKAO_API_KEY"]
    KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]
    DATA_GO_KR_KEY = urllib.parse.unquote(st.secrets["DATA_GO_KR_API_KEY"])
except KeyError:
    st.error("⚠️ 스트림릿 설정(Secrets)에 API 키(GROQ, KAKAO, DATA_GO_KR)가 모두 있는지 확인해주세요!")
    st.stop()

# ==========================================
# [데이터베이스 설정] SQLite3
# ==========================================
conn = sqlite3.connect('real_estate_matdongsan.db', check_same_thread=False)
c = conn.cursor()
# 개발 모드이므로 users 테이블은 생략합니다.
c.execute('''CREATE TABLE IF NOT EXISTS chat_records (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, query TEXT, answer TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS field_diaries (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, content TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS ddays_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, title TEXT, target_date TEXT, category TEXT, tasks TEXT)''')
conn.commit()

# ==========================================
# [지역별 기본 중심 좌표 및 법정동 코드]
# ==========================================
REGION_INFO = {
    "경북 포항 남구": {"code": "47111", "lat": 36.0190, "lng": 129.3434},
    "경북 포항 북구": {"code": "47113", "lat": 36.0425, "lng": 129.3644},
    "서울 강남구": {"code": "11680", "lat": 37.5172, "lng": 127.0473},
    "서울 송파구": {"code": "11710", "lat": 37.5145, "lng": 127.1062},
    "경기 성남 분당구": {"code": "41135", "lat": 37.3827, "lng": 127.1189},
    "경기 하남시": {"code": "41450", "lat": 37.5392, "lng": 127.2148},
    "부산 해운대구": {"code": "26350", "lat": 35.1631, "lng": 129.1636},
    "대구 수성구": {"code": "27260", "lat": 35.8581, "lng": 128.6306}
}

# ==========================================
# [CSS] 가독성 극대화 및 글자색 분리
# ==========================================
st.markdown("""
<style>
    @font-face {
        font-family: 'SeoulNamsanM';
        src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_two@1.0/SeoulNamsanM.woff') format('woff');
        font-weight: normal; font-style: normal;
    }
    .stApp, p, span, div, h1, h2, h3, h4, h5, h6, table, th, td {
        font-family: 'SeoulNamsanM', sans-serif !important;
        color: #ffffff !important;
    }
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    label, .st-emotion-cache-10trnc, .st-emotion-cache-1y4p8pa {
        color: #fcd34d !important; font-size: 18px !important; font-weight: bold !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div:first-child {
        background-color: rgba(0, 0, 0, 0.8) !important; border: 2px solid #d97706 !important; border-radius: 10px !important;
    }
    input, textarea { color: #ffffff !important; font-size: 18px !important; font-weight: bold !important; }
    input::placeholder, textarea::placeholder { color: #9ca3af !important; }
    div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important; 
        color: #ffffff !important; font-weight: bold !important; font-size: 18px !important; 
        border: none !important; border-radius: 10px !important;
    }
    button[data-baseweb="tab"] { 
        background-color: #334155 !important; border: 1px solid #475569 !important;
        border-radius: 10px 10px 0 0 !important; margin-right: 5px !important;
    }
    button[data-baseweb="tab"] p { color: #cbd5e1 !important; font-size: 18px !important; font-weight: bold !important; }
    button[data-baseweb="tab"][aria-selected="true"] { background-color: #f59e0b !important; border-bottom: none !important; }
    button[data-baseweb="tab"][aria-selected="true"] p { color: #000000 !important; font-weight: 900 !important; }
    .info-card { background: rgba(0,0,0,0.6); border: 1px solid #f59e0b; border-radius: 12px; padding: 20px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# [세션 상태 관리] 개발 모드 임시 계정
# ==========================================
if 'user_id' not in st.session_state: st.session_state['user_id'] = "개발자"
if 'chat_session' not in st.session_state: st.session_state['chat_session'] = [] 

# ==========================================
# [핵심 API 연동 함수]
# ==========================================
@st.cache_data(ttl=3600)
def get_apt_data(lawd_cd, deal_ym):
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {"serviceKey": DATA_GO_KR_KEY, "pageNo": "1", "numOfRows": "150", "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ym}
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200: return pd.DataFrame()
        
        root = ET.fromstring(res.content)
        data = []
        for item in root.findall('.//item'):
            try:
                price_str = item.findtext('dealAmount')
                if not price_str: continue
                price = int(price_str.replace(',', '').strip())
                area = float(item.findtext('excluUseAr'))
                data.append({
                    "apt_name": item.findtext('aptNm'), "price": price, "area": area, "pyung": round(area / 3.3, 1),
                    "dong": item.findtext('umdNm'), "jibun": item.findtext('jibun')
                })
            except Exception:
                continue
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_coords(address, keyword=None):
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    
    # 1차: 정확한 주소 검색
    url_addr = "https://dapi.kakao.com/v2/local/search/address.json"
    try:
        res = requests.get(url_addr, headers=headers, params={"query": address}).json()
        if res.get('documents'):
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except: pass

    # 2차: 주소 검색 실패 시 키워드(아파트 이름 포함) 검색
    if keyword:
        url_kw = "https://dapi.kakao.com/v2/local/search/keyword.json"
        try:
            res_kw = requests.get(url_kw, headers=headers, params={"query": keyword}).json()
            if res_kw.get('documents'):
                return float(res_kw['documents'][0]['y']), float(res_kw['documents'][0]['x'])
        except: pass
        
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================
# [화면 구성] 메인 서비스 화면 (5개 탭)
# ==========================================
st.markdown(f"<h1 style='font-size: 36px; color:#fcd34d !important; text-align:center;'>🏢 부동산 맛동산 🥜 (개발 모드)</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#ffffff !important; font-size:20px; margin-bottom:30px;'>달콤하고 바삭한 부동산 정보, 2026년형 AI 프롭테크 솔루션</p>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🤖 AI 상담", "🗺️ 실거래가 지도", "🏆 입지 추천", "📝 임장 일기", "📅 D-Day 관리"])

# ------------------------------------------
# [탭 1] AI 부동산 상담
# ------------------------------------------
with tab1:
    st.markdown("### 🤖 바삭하고 명쾌한 AI 부동산 상담")
    if st.button("🔄 대화 초기화", key="reset_chat"):
        st.session_state['chat_session'] = []
        st.rerun()

    for msg in st.session_state['chat_session']:
        st.markdown(f"<div style='text-align:right; margin-bottom:10px;'><span style='background:#3b82f6; padding:10px 15px; border-radius:15px;'>{msg['query']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:left; margin-bottom:20px;'><span style='background:rgba(245,158,11,0.2); border:1px solid #f59e0b; padding:10px 15px; border-radius:15px;'>{msg['answer']}</span></div>", unsafe_allow_html=True)

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
# [탭 2] 🗺️ 실거래가 지도
# ------------------------------------------
with tab2:
    st.markdown("### 🗺️ 실거래가 지도 (지도를 움직이며 가격을 확인하세요)")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1: 
        map_region = st.selectbox("지역 선택", list(REGION_INFO.keys()), index=0, key="map_reg")
    with col_m2: 
        default_ym = (datetime.datetime.now() - relativedelta(months=2)).strftime("%Y%m")
        map_ym = st.text_input("계약 연월 (YYYYMM)", value=default_ym, key="map_ym")
    
    center_lat = REGION_INFO[map_region]["lat"]
    center_lng = REGION_INFO[map_region]["lng"]
    lawd_code = REGION_INFO[map_region]["code"]
    
    with st.spinner("실거래가 데이터와 지도를 불러오는 중입니다..."):
        df_map = get_apt_data(lawd_code, map_ym)
        map_data = []
        
        if not df_map.empty:
            df_map = df_map.drop_duplicates(subset=['apt_name'])
            for _, row in df_map.iterrows():
                full_address = f"{map_region.split()[-1]} {row['dong']} {row['jibun']}"
                keyword_address = f"{map_region.split()[-1]} {row['dong']} {row['apt_name']}"
                
                lat, lng = get_coords(full_address, keyword_address)
                if lat and lng:
                    map_data.append({
                        "name": row['apt_name'], 
                        "price": row['price'], 
                        "lat": lat, 
                        "lng": lng,
                        "pyung": row['pyung']
                    })
        
        map_html = f"""
        <div id="map" style="width:100%;height:600px;border-radius:12px;border:2px solid #f59e0b;"></div>
        <script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}"></script>
        <script>
            var mapContainer = document.getElementById('map'),
                mapOption = {{ 
                    center: new kakao.maps.LatLng({center_lat}, {center_lng}), 
                    level: 5 
                }};
            
            var map = new kakao.maps.Map(mapContainer, mapOption);
            var mapTypeControl = new kakao.maps.MapTypeControl();
            map.addControl(mapTypeControl, kakao.maps.ControlPosition.TOPRIGHT);
            var zoomControl = new kakao.maps.ZoomControl();
            map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);

            var data = {json.dumps(map_data)};
            
            if (data.length > 0) {{
                data.forEach(function(d) {{
                    var content = '<div style="background:#d97706;color:white;padding:6px 10px;border-radius:8px;font-size:12px;font-weight:bold;border:1px solid #ffffff;box-shadow: 0px 2px 5px rgba(0,0,0,0.3); text-align:center;">' + 
                                  d.name + '<br>' + 
                                  '<span style="color:#fcd34d;">' + (d.price/10000).toFixed(1) + '억</span> (' + d.pyung + '평)</div>';
                    
                    var customOverlay = new kakao.maps.CustomOverlay({{
                        position: new kakao.maps.LatLng(d.lat, d.lng),
                        content: content,
                        map: map
                    }});
                }});
                
                map.setCenter(new kakao.maps.LatLng(data[0].lat, data[0].lng));
            }}
        </script>
        """
        components.html(map_html, height=620)
        
        if not map_data:
            st.warning(f"⚠️ {map_ym}에 해당하는 실거래 데이터가 없거나 좌표 변환에 실패했습니다. 지도는 기본 위치로 표시됩니다.")
        else:
            st.success(f"✅ 총 {len(map_data)}개의 실거래가 마커를 지도에 표시했습니다.")

# ------------------------------------------
# [탭 3] 🏆 브역대신평초 추천
# ------------------------------------------
with tab3:
    st.markdown("### 🏆 브역대신평초 맞춤형 아파트 추천")
    with st.form("reco_form"):
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            target_region = st.selectbox("희망 거주 지역", list(REGION_INFO.keys()), index=0, key="reco_reg")
            budget_max = st.number_input("최대 예산 (만원)", value=40000, step=1000)
        with col_r2:
            work_address = st.text_input("직장 주소 (도로명)", value="경북 포항시 남구 신항로 110")
        submit_reco = st.form_submit_button("AI 분석 시작", use_container_width=True)

    if submit_reco:
        with st.spinner("분석 중입니다..."):
            work_lat, work_lng = get_coords(work_address)
            if not work_lat:
                st.info(f"'{work_address}' 주소를 찾지 못해 선택하신 지역의 중심 좌표 기준으로 거리를 계산합니다.")
                work_lat, work_lng = REGION_INFO[target_region]["lat"], REGION_INFO[target_region]["lng"]
            
            search_ym = (datetime.datetime.now() - relativedelta(months=2)).strftime("%Y%m")
            df = get_apt_data(REGION_INFO[target_region]["code"], search_ym)
            
            if df.empty:
                st.error("해당 지역의 최근 거래 데이터가 없습니다.")
            else:
                df_filtered = df[df['price'] <= budget_max].drop_duplicates(subset=['apt_name'])
                if len(df_filtered) == 0:
                    st.warning("예산에 맞는 아파트가 없습니다. 예산을 올려보세요.")
                else:
                    candidates = []
                    for _, row in df_filtered.iterrows():
                        full_address = f"{target_region.split()[-1]} {row['dong']} {row['jibun']}"
                        keyword_address = f"{target_region.split()[-1]} {row['dong']} {row['apt_name']}"
                        apt_lat, apt_lng = get_coords(full_address, keyword_address)
                        
                        if apt_lat:
                            dist = haversine_distance(apt_lat, apt_lng, work_lat, work_lng)
                            candidates.append({"name": row['apt_name'], "price": row['price'], "pyung": row['pyung'], "dist": dist})
                    
                    candidates = sorted(candidates, key=lambda x: x['dist'])[:3]
                    
                    for i, apt in enumerate(candidates):
                        st.markdown(f"<div class='info-card'><h3 style='color:#fcd34d !important;'>🥇 {i+1}위: {apt['name']}</h3>", unsafe_allow_html=True)
                        
                        st.markdown("객관적인 가격 비교를 위한 평당 단가 계산:")
                        
                        
                        st.latex(r"\text{평당 단가} = \frac{\text{예상 매매가}}{\text{평수}}")
                        
                        
                        st.markdown(f"""
                        * **예상 매매가:** {apt['price']:,}만 원 ({apt['pyung']}평)
                        * **평당 단가:** {int(apt['price']/apt['pyung']):,}만 원/평
                        * **직장까지 거리:** 약 {apt['dist']:.1f}km
                        </div>
                        """, unsafe_allow_html=True)

# ------------------------------------------
# [탭 4] 📝 임장 일기
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
# [탭 5] 📅 D-Day 관리
# ------------------------------------------
with tab5:
    st.markdown("### 📅 청약 및 이사 D-Day 관리 (스마트 체크리스트)")
    
    checklist_templates = {
        "청약/분양": "- [ ] 공인인증서(공동인증서) 갱신 확인\n- [ ] 청약통장 예치금 지역별 기준 충족 확인\n- [ ] 입주자 모집공고문 정독 및 자격 요건 체크\n- [ ] 무주택 기간 및 부양가족 수 정확히 산정\n- [ ] 청약홈(ApplyHome) 모의 청약 연습하기",
        "계약/잔금": "- [ ] 등기부등본 당일 재발급 및 권리관계 확인\n- [ ] 은행 이체 한도 1일/1회 증액 확인\n- [ ] 신분증, 인감도장, 인감증명서 지참\n- [ ] 취등록세 및 법무사 비용 현금 준비\n- [ ] 선수관리비 정산 및 영수증 수령",
        "이사": "- [ ] 포장이사 3곳 이상 견적 비교 및 예약\n- [ ] 대형 폐기물 스티커 발급 및 배출\n- [ ] 도시가스, 인터넷, 정수기 이전 설치 예약\n- [ ] 전출입 관리비 정산 및 장기수선충당금 환급\n- [ ] 전입신고 및 확정일자(임대차 신고) 완료",
        "기타": "- [ ] 필요한 일정을 자유롭게 메모하세요."
    }

    with st.form("dday_form"):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            d_title = st.text_input("일정 이름 (예: 래미안 청약일)")
            d_date = st.date_input("목표 날짜")
        with col_d2:
            d_cat = st.selectbox("카테고리 (선택 시 체크리스트 자동 생성)", list(checklist_templates.keys()))
            
        d_tasks = st.text_area("상세 체크리스트 (자유롭게 수정 가능)", value=checklist_templates[d_cat], height=150)
        
        if st.form_submit_button("일정 및 체크리스트 추가", use_container_width=True) and d_title:
            c.execute("INSERT INTO ddays_v2 (user_id, title, target_date, category, tasks) VALUES (?, ?, ?, ?, ?)", 
                      (st.session_state['user_id'], d_title, str(d_date), d_cat, d_tasks))
            conn.commit()
            st.rerun()
            
    st.markdown("---")
    
    c.execute("SELECT id, title, target_date, category, tasks FROM ddays_v2 WHERE user_id=? ORDER BY target_date ASC", (st.session_state['user_id'],))
    ddays = c.fetchall()
    
    if not ddays:
        st.info("등록된 일정이 없습니다. 위에서 새로운 일정을 추가해보세요!")
    else:
        for d_id, title, t_date_str, cat, tasks in ddays:
            delta = (datetime.datetime.strptime(t_date_str, "%Y-%m-%d").date() - datetime.date.today()).days
            d_text = f"D-{delta}" if delta > 0 else (f"D+{-delta}" if delta < 0 else "D-Day (오늘!)")
            
            with st.expander(f"[{cat}] {title} - {t_date_str} ( {d_text} )", expanded=True):
                st.markdown(f"<div style='white-space: pre-wrap; color:#e2e8f0; line-height:1.8;'>{tasks}</div>", unsafe_allow_html=True)
                if st.button("❌ 이 일정 삭제", key=f"del_{d_id}"):
                    c.execute("DELETE FROM ddays_v2 WHERE id=?", (d_id,))
                    conn.commit()
                    st.rerun()
