import streamlit as st
import sqlite3
import datetime
import requests
import json
import re

# ==========================================
# [초기 설정] 페이지 세팅 (밝고 넓은 레이아웃)
# ==========================================
st.set_page_config(page_title="스마트 부동산 입지 분석기", page_icon="🏡", layout="centered")

# ==========================================
# [Groq API 키 설정]
# ==========================================
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("⚠️ 스트림릿 설정(Settings) -> Secrets에 'GROQ_API_KEY'를 먼저 입력해주세요!")
    st.stop()

# ==========================================
# [데이터베이스 설정] SQLite3 (관심 지역 스크랩용)
# ==========================================
conn = sqlite3.connect('real_estate_v1.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS saved_areas (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, budget TEXT, addresses TEXT, result TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, question TEXT, answer TEXT)''')
conn.commit()

# ==========================================
# [CSS] 밝고 신뢰감 있는 화이트/블루 톤 디자인
# ==========================================
st.markdown("""
<style>
    @font-face {
        font-family: 'Pretendard-Regular';
        src: url('https://cdn.jsdelivr.net/gh/Project-Noonnu/noonfonts_2107@1.1/Pretendard-Regular.woff') format('woff');
        font-weight: 400; font-style: normal;
    }

    /* 전체 배경 및 폰트 설정 (화이트 톤) */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp table, .stApp th, .stApp td {
        font-family: 'Pretendard-Regular', sans-serif !important;
    }
    .stApp { background-color: #f8fafc; color: #1e293b; }
    
    /* 제목 스타일 */
    .main-title {
        font-size: 42px; font-weight: 800; color: #0f172a; text-align: center;
        margin-top: 20px; margin-bottom: 10px; letter-spacing: -1px;
    }
    .main-title span { color: #2563eb; } /* 포인트 컬러 (블루) */
    .sub-title { color: #64748b; font-size: 18px; margin-bottom: 40px; font-weight: 500; text-align: center; }

    /* 입력창 스타일 (깔끔한 화이트) */
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div:first-child {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    input, textarea { color: #0f172a !important; font-size: 15px !important; }
    label { color: #334155 !important; font-size: 15px !important; font-weight: 600 !important; }

    /* 버튼 스타일 (신뢰감 있는 블루) */
    div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important; 
        color: #ffffff !important; 
        font-weight: 700 !important; font-size: 16px !important; padding: 10px 20px !important;
        border: none !important; border-radius: 8px !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2) !important; transition: all 0.2s ease !important;
    }
    div[data-testid="stButton"] > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) !important; box-shadow: 0 6px 12px rgba(37, 99, 235, 0.3) !important;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; border-bottom: 2px solid #e2e8f0; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; padding: 10px 15px; color: #64748b; font-size: 16px; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #2563eb !important; border-bottom: 3px solid #2563eb; }

    /* 결과 카드 스타일 */
    .result-card {
        background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 25px; margin-top: 20px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);
        line-height: 1.7; color: #334155;
    }
    .result-card h3, .result-card h4 { color: #0f172a; font-weight: 700; margin-top: 0; }
    
    /* 채팅 스타일 */
    .chat-user { text-align: right; margin-bottom: 15px; }
    .chat-user span { background-color: #2563eb; color: white; padding: 12px 18px; border-radius: 15px 15px 0 15px; display: inline-block; font-size: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .chat-ai { text-align: left; margin-bottom: 25px; }
    .chat-ai span { background-color: #ffffff; border: 1px solid #e2e8f0; color: #1e293b; padding: 15px 20px; border-radius: 15px 15px 15px 0; display: inline-block; font-size: 15px; line-height: 1.6; box-shadow: 0 2px 5px rgba(0,0,0,0.05); width: 100%; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# [공통 AI 호출 함수]
# ==========================================
def get_ai_response(system_prompt, user_input, temperature=0.3):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": temperature}
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"오류 발생: {response.status_code}"

# ==========================================
# [헤더 영역]
# ==========================================
st.markdown("<div class='main-title'>스마트 <span>부동산</span> 입지 분석기</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>직장, 부모님, 친구... 내 라이프스타일에 딱 맞는 최적의 동네를 찾아드려요.</div>", unsafe_allow_html=True)

# ==========================================
# [탭 구성]
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📍 맞춤 입지 분석", "📊 인프라 점수화", "💬 부동산 AI 상담", "🧮 필수 계산기"])

# ------------------------------------------
# [탭 1] 다중 목적지 기반 맞춤 입지 분석
# ------------------------------------------
with tab1:
    st.markdown("### 📍 나의 라이프스타일 맞춤 지역 찾기")
    st.info("💡 예산과 자주 가는 목적지들을 입력하면, 이동 시간을 최소화하는 최적의 교집합 지역과 아파트를 추천합니다.")
    
    with st.form("location_form"):
        st.markdown("#### 1. 예산 및 조건 설정")
        col1, col2 = st.columns(2)
        with col1:
            deal_type = st.selectbox("거래 종류", ["매매", "전세", "월세"])
        with col2:
            budget = st.text_input("가용 예산 (예: 5억~7억, 보증금 1억/월 100만)")
            
        st.markdown("#### 2. 주요 목적지 입력 (최대 4곳)")
        st.caption("중요도(가중치)가 높을수록 해당 위치와 가까운 곳을 우선 추천합니다.")
        
        c1, c2 = st.columns([3, 1])
        with c1: addr1 = st.text_input("🏢 직장 주소 (또는 지하철역)", placeholder="예: 강남역, 판교역, 여의도")
        with c2: weight1 = st.selectbox("중요도 (직장)", ["매우 중요 (5점)", "중요 (3점)", "보통 (1점)"], index=0)
        
        c3, c4 = st.columns([3, 1])
        with c3: addr2 = st.text_input("🏡 부모님 댁 (또는 본가)", placeholder="예: 분당구 정자동, 일산 마두동")
        with c4: weight2 = st.selectbox("중요도 (부모님)", ["매우 중요 (5점)", "중요 (3점)", "보통 (1점)"], index=1)
        
        c5, c6 = st.columns([3, 1])
        with c5: addr3 = st.text_input("🍻 자주 만나는 친구/모임 장소", placeholder="예: 홍대입구, 성수동")
        with c6: weight3 = st.selectbox("중요도 (모임)", ["매우 중요 (5점)", "중요 (3점)", "보통 (1점)"], index=2)
        
        c7, c8 = st.columns([3, 1])
        with c7: addr4 = st.text_input("⚽ 취미/좋아하는 장소", placeholder="예: 한강공원, 올림픽공원")
        with c8: weight4 = st.selectbox("중요도 (취미)", ["매우 중요 (5점)", "중요 (3점)", "보통 (1점)"], index=2)
        
        submit_location = st.form_submit_button("🔍 최적의 입지 및 아파트 분석하기", use_container_width=True)
        
    if submit_location:
        if not budget or not addr1:
            st.warning("예산과 직장 주소는 필수 입력 항목입니다.")
        else:
            with st.spinner("AI가 지도 데이터와 실거래가 데이터를 종합하여 최적의 교집합을 계산 중입니다..."):
                sys_prompt = """
                당신은 대한민국 최고의 부동산 입지 분석 전문가입니다.
                사용자가 입력한 여러 목적지(직장, 부모님, 친구 등)의 지리적 위치와 대중교통/자차 이동 시간을 종합적으로 계산하여 최적의 교집합 지역(동 단위) 3곳을 추천해야 합니다.
                
                [분석 조건]
                1. 사용자의 '거래 종류'와 '예산'에 현실적으로 부합하는 지역이어야 합니다.
                2. 각 목적지별 '중요도(가중치)'를 반영하여, 중요도가 높은 곳으로의 출퇴근/이동이 가장 편리한 곳을 중심점으로 잡으세요.
                3. 추천 지역별로 구체적인 '아파트 단지명(또는 오피스텔/빌라 밀집 구역)'을 2~3개씩 예시로 들어주세요.
                4. 수식을 포함하여 점수 산출 방식을 설명할 때, 반드시 수식 전후에 개행을 두 번 추가하여 명확히 구분되도록 하세요.
                
                출력 형식은 마크다운을 사용하여 깔끔하고 가독성 좋게 작성해주세요.
                """
                
                user_prompt = f"""
                - 거래 종류: {deal_type}
                - 예산: {budget}
                - 목적지 1 (직장): {addr1} / {weight1}
                - 목적지 2 (부모님): {addr2} / {weight2}
                - 목적지 3 (모임): {addr3} / {weight3}
                - 목적지 4 (취미): {addr4} / {weight4}
                
                위 데이터를 바탕으로 최적의 지역 3곳과 추천 아파트를 분석해주세요. 분석 시 사용된 입지 점수화 수식(가중치와 이동시간 반비례 등)도 함께 설명해주세요.
                """
                
                result = get_ai_response(sys_prompt, user_prompt, temperature=0.2)
                
                # DB 저장
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                addresses = f"{addr1}, {addr2}, {addr3}, {addr4}"
                c.execute("INSERT INTO saved_areas (date, type, budget, addresses, result) VALUES (?, ?, ?, ?, ?)", 
                          (now, deal_type, budget, addresses, result))
                conn.commit()
                
                st.success("분석이 완료되었습니다!")
                st.markdown(f"<div class='result-card'>{result}</div>", unsafe_allow_html=True)

# ------------------------------------------
# [탭 2] 인프라 및 환경 점수화 (Scoring)
# ------------------------------------------
with tab2:
    st.markdown("### 📊 관심 지역 인프라 종합 점수")
    st.info("특정 아파트나 동네 이름을 입력하면, 슬세권, 스세권, 공세권 등 인프라를 점수화하여 보여줍니다.")
    
    target_area = st.text_input("분석할 아파트명 또는 동네 입력 (예: 마포구 공덕동, 잠실 엘스 아파트)")
    
    if st.button("인프라 점수 분석하기", use_container_width=True):
        if target_area:
            with st.spinner(f"'{target_area}' 주변의 상권, 교통, 자연환경 데이터를 분석 중입니다..."):
                sys_prompt = """
                당신은 부동산 데이터 분석가입니다. 사용자가 입력한 아파트나 동네의 주변 인프라를 분석하여 100점 만점 기준으로 점수화해주세요.
                
                [평가 항목]
                1. 교통 점수 (역세권, 버스 노선 등)
                2. 상권 점수 (슬세권, 대형마트, 스세권 등)
                3. 환경 점수 (공세권, 숲세권, 한강뷰 등)
                4. 학군 점수 (초품아, 학원가 등)
                
                각 항목별 점수(100점 만점)와 그 이유를 상세히 설명하고, 마지막에 종합 점수(Total Score)를 산출하는 수식을 보여주세요.
                수식을 작성할 때는 반드시 수식 전후에 개행을 두 번 추가하여 명확히 구분되도록 하세요.
                """
                
                result = get_ai_response(sys_prompt, f"분석 대상: {target_area}", temperature=0.3)
                st.markdown(f"<div class='result-card'>{result}</div>", unsafe_allow_html=True)
        else:
            st.warning("분석할 지역을 입력해주세요.")

# ------------------------------------------
# [탭 3] 부동산 AI 상담소
# ------------------------------------------
with tab3:
    st.markdown("### 💬 부동산 정책 & 세금 AI 상담")
    st.info("청약 조건, 취득세, 양도소득세, 전세사기 예방법 등 궁금한 점을 자유롭게 물어보세요.")
    
    if 're_chat' not in st.session_state:
        st.session_state['re_chat'] = []
        
    for msg in st.session_state['re_chat']:
        if msg['role'] == 'user':
            st.markdown(f"<div class='chat-user'><span>{msg['content']}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-ai'><span>{msg['content']}</span></div>", unsafe_allow_html=True)
            
    with st.form("chat_form", clear_on_submit=True):
        user_q = st.text_input("질문을 입력하세요 (예: 생애최초 주택구입 시 취득세 감면 조건이 어떻게 되나요?)")
        submitted_q = st.form_submit_button("질문하기")
        
        if submitted_q and user_q:
            st.session_state['re_chat'].append({"role": "user", "content": user_q})
            
            with st.spinner("AI 공인중개사가 답변을 작성 중입니다..."):
                sys_prompt = "당신은 친절하고 전문적인 대한민국 공인중개사이자 세무사입니다. 최신 부동산 정책과 세법을 바탕으로 정확하고 알기 쉽게 답변해주세요."
                answer = get_ai_response(sys_prompt, user_q)
                st.session_state['re_chat'].append({"role": "ai", "content": answer})
                st.rerun()

# ------------------------------------------
# [탭 4] 부동산 필수 계산기
# ------------------------------------------
with tab4:
    st.markdown("### 🧮 부동산 필수 계산기")
    
    calc_type = st.radio("계산기 종류 선택", ["중개수수료 계산기", "전월세 전환율 계산기"], horizontal=True)
    
    st.markdown("<hr style='border-color: #e2e8f0;'>", unsafe_allow_html=True)
    
    if calc_type == "중개수수료 계산기":
        st.markdown("#### 🤝 중개수수료 (복비) 계산")
        c1, c2 = st.columns(2)
        with c1:
            house_type = st.selectbox("주택 종류", ["주택 (아파트, 빌라 등)", "오피스텔", "그 외 (상가, 토지)"])
            deal_type_calc = st.selectbox("거래 종류", ["매매/교환", "전세", "월세"])
        with c2:
            if deal_type_calc == "월세":
                deposit = st.number_input("보증금 (만원)", min_value=0, value=1000, step=100)
                monthly = st.number_input("월세 (만원)", min_value=0, value=50, step=10)
                total_amount = deposit + (monthly * 100)
                st.info(f"환산 보증금: {total_amount:,} 만원")
            else:
                total_amount = st.number_input("거래 금액 (만원)", min_value=0, value=50000, step=1000)
                
        if st.button("수수료 계산하기", use_container_width=True):
            # 간략한 요율 적용 (실제 법정 요율표 기준 근사치)
            rate = 0.004 # 기본 0.4% 가정
            if house_type == "오피스텔": rate = 0.005 if deal_type_calc == "매매/교환" else 0.004
            elif house_type == "그 외 (상가, 토지)": rate = 0.009
            else:
                if deal_type_calc == "매매/교환":
                    if total_amount < 5000: rate = 0.006
                    elif total_amount < 20000: rate = 0.005
                    elif total_amount < 90000: rate = 0.004
                    elif total_amount < 120000: rate = 0.005
                    else: rate = 0.007
                else: # 임대차
                    if total_amount < 5000: rate = 0.005
                    elif total_amount < 10000: rate = 0.004
                    elif total_amount < 60000: rate = 0.003
                    else: rate = 0.004
                    
            fee = int(total_amount * 10000 * rate)
            vat = int(fee * 0.1)
            
            st.markdown(f"""
            <div class='result-card' style='text-align: center;'>
                <h4 style='color: #64748b;'>최대 중개보수 (VAT 별도)</h4>
                <h2 style='color: #2563eb; margin: 10px 0;'>{fee:,} 원</h2>
                <p style='font-size: 14px; color: #94a3b8;'>적용 상한요율: {rate*100:.2f}% (부가세 10% 포함 시: {fee+vat:,} 원)</p>
            </div>
            """, unsafe_allow_html=True)

    elif calc_type == "전월세 전환율 계산기":
        st.markdown("#### 🔄 전세 ↔ 월세 전환 계산")
        st.caption("전세금을 월세로 돌리거나, 월세를 전세로 환산할 때 사용합니다.")
        
        c1, c2 = st.columns(2)
        with c1:
            current_jeonse = st.number_input("기존 전세금 (만원)", min_value=0, value=30000, step=1000)
            target_deposit = st.number_input("변경할 보증금 (만원)", min_value=0, value=5000, step=1000)
        with c2:
            conversion_rate = st.number_input("전월세 전환율 (%)", min_value=0.0, value=5.0, step=0.1)
            
        if st.button("월세 계산하기", use_container_width=True):
            diff = current_jeonse - target_deposit
            if diff <= 0:
                st.error("변경할 보증금이 기존 전세금보다 작아야 월세가 발생합니다.")
            else:
                monthly_rent = (diff * (conversion_rate / 100)) / 12
                
                st.markdown(f"""
                <div class='result-card' style='text-align: center;'>
                    <h4 style='color: #64748b;'>적정 월세 금액</h4>
                    <h2 style='color: #2563eb; margin: 10px 0;'>보증금 {target_deposit:,}만원 / 월 {int(monthly_rent):,}만원</h2>
                    <p style='font-size: 14px; color: #94a3b8;'>계산식: (전세금 차액 {diff:,}만원 × 전환율 {conversion_rate}%) ÷ 12개월</p>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# [푸터]
# ==========================================
st.markdown("""
<hr style="border-color: #e2e8f0; margin-top: 50px;">
<div style="text-align: center; color: #94a3b8; font-size: 13px;">
    ⚠️ 본 서비스의 분석 결과 및 계산 금액은 참고용이며, 실제 거래 시 공인중개사 및 전문가와 상담하시기 바랍니다.<br>
    © Smart Real Estate Analyzer. All rights reserved.
</div>
""", unsafe_allow_html=True)
