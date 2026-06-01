import streamlit as st
import sqlite3
import datetime
import time
import random
import requests
import re
import calendar
import streamlit.components.v1 as components

# ==========================================
# [초기 설정] 페이지 세팅 (2026년형 모던 스타일)
# ==========================================
st.set_page_config(page_title="스마트 마음 상담소", page_icon="🌙", layout="centered")

# ==========================================
# [Groq API 키 설정]
# ==========================================
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("⚠️ 스트림릿 설정(Settings) -> Secrets에 'GROQ_API_KEY'를 먼저 입력해주세요!")
    st.stop()

# ==========================================
# [데이터베이스 설정] SQLite3 (프로필 테이블 추가)
# ==========================================
conn = sqlite3.connect('mind_care_v4.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS counseling_records (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, type TEXT, worry TEXT, answer TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS game_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, score INTEGER, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS ddays (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, title TEXT, target_date TEXT, category TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS diaries (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, content TEXT)''')
# ✨ 신규: 프로필(지인) 관리 테이블
c.execute('''CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, name TEXT, gender TEXT, dob TEXT, tob TEXT, unknown_time INTEGER, city TEXT)''')
conn.commit()

# ==========================================
# [정통 만세력 계산 알고리즘]
# ==========================================
def calculate_saju_details(year, month, day, hour, minute):
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    
    solar_year = year - 1 if month == 1 or (month == 2 and day < 4) else year
    y_offset = solar_year - 1984
    y_gan_idx = y_offset % 10
    y_gan = gan[y_gan_idx]
    y_ji = ji[y_offset % 12]
    
    solar_terms = {1:6, 2:4, 3:6, 4:5, 5:6, 6:6, 7:7, 8:8, 9:8, 10:8, 11:7, 12:7}
    term_day = solar_terms.get(month, 6)
    
    m_idx = month
    if day < term_day: m_idx -= 1
    if m_idx == 0: m_idx = 12
        
    if m_idx == 12: m_ji_idx = 0
    elif m_idx == 1: m_ji_idx = 1
    else: m_ji_idx = m_idx
    m_ji = ji[m_ji_idx]
    
    if y_gan_idx in [0, 5]: m_gan_start = 2
    elif y_gan_idx in [1, 6]: m_gan_start = 4
    elif y_gan_idx in [2, 7]: m_gan_start = 6
    elif y_gan_idx in [3, 8]: m_gan_start = 8
    else: m_gan_start = 0
    
    if m_idx >= 2: m_offset = m_idx - 2
    elif m_idx == 12: m_offset = 10
    elif m_idx == 1: m_offset = 11
        
    m_gan = gan[(m_gan_start + m_offset) % 10]
    
    base_date = datetime.date(1900, 1, 1)
    target_date = datetime.date(year, month, day)
    delta_days = (target_date - base_date).days
    
    if hour == 23 and minute >= 30: delta_days += 1
        
    d_gan_idx = (0 + delta_days) % 10
    d_ji_idx = (10 + delta_days) % 12
    d_gan = gan[d_gan_idx]
    d_ji = ji[d_ji_idx]
    
    if minute < 30: h_idx = hour - 1
    else: h_idx = hour
    if h_idx < 0: h_idx = 23
    
    if h_idx in [23, 0]: h_ji_idx = 0
    elif h_idx in [1, 2]: h_ji_idx = 1
    elif h_idx in [3, 4]: h_ji_idx = 2
    elif h_idx in [5, 6]: h_ji_idx = 3
    elif h_idx in [7, 8]: h_ji_idx = 4
    elif h_idx in [9, 10]: h_ji_idx = 5
    elif h_idx in [11, 12]: h_ji_idx = 6
    elif h_idx in [13, 14]: h_ji_idx = 7
    elif h_idx in [15, 16]: h_ji_idx = 8
    elif h_idx in [17, 18]: h_ji_idx = 9
    elif h_idx in [19, 20]: h_ji_idx = 10
    elif h_idx in [21, 22]: h_ji_idx = 11
    
    h_ji = ji[h_ji_idx]
    
    if d_gan_idx in [0, 5]: h_gan_start = 0
    elif d_gan_idx in [1, 6]: h_gan_start = 2
    elif d_gan_idx in [2, 7]: h_gan_start = 4
    elif d_gan_idx in [3, 8]: h_gan_start = 6
    else: h_gan_start = 8
    
    h_gan = gan[(h_gan_start + h_ji_idx) % 10]
    
    saju_str = f"{h_gan}{h_ji} / {d_gan}{d_ji} / {m_gan}{m_ji} / {y_gan}{y_ji}"
    
    elements = {"목":0, "화":0, "토":0, "금":0, "수":0}
    for char in [y_gan, y_ji, m_gan, m_ji, d_gan, d_ji, h_gan, h_ji]:
        if char in ["갑", "을", "인", "묘"]: elements["목"] += 1
        elif char in ["병", "정", "사", "오"]: elements["화"] += 1
        elif char in ["무", "기", "진", "술", "축", "미"]: elements["토"] += 1
        elif char in ["경", "신", "유"]: elements["금"] += 1
        elif char in ["임", "계", "해", "자"]: elements["수"] += 1
        
    element_str = f"목: {elements['목']}개, 화: {elements['화']}개, 토: {elements['토']}개, 금: {elements['금']}개, 수: {elements['수']}개"
    
    return saju_str, element_str

# ==========================================
# [CSS] 2026년형 초현대적 UI & 프리텐다드 폰트
# ==========================================
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    .stApp, p, span, div, h1, h2, h3, h4, h5, h6, label, input, textarea, button, table, th, td {
        font-family: 'Pretendard', sans-serif !important;
    }
    
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); color: #f8fafc; }
    
    .neon-title {
        font-size: 45px; font-weight: 900; color: #ffffff; text-align: center;
        margin-top: 20px; margin-bottom: 10px; letter-spacing: -1px; line-height: 1.2;
        text-shadow: 0 0 10px rgba(192, 132, 252, 0.5), 0 0 20px rgba(192, 132, 252, 0.3);
    }
    .sub-title { color: #cbd5e1; font-size: 18px; margin-bottom: 40px; font-weight: 400; text-align: center; letter-spacing: -0.5px; }

    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div:first-child {
        background-color: rgba(30, 41, 59, 0.7) !important; 
        border: 1px solid #c084fc !important; 
        border-radius: 12px !important; backdrop-filter: blur(10px);
    }
    input, textarea { color: #ffffff !important; font-size: 16px !important; font-weight: 500 !important; }
    input::placeholder, textarea::placeholder { color: #94a3b8 !important; font-weight: 400 !important; }
    
    div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #8b5cf6, #c084fc) !important; 
        color: #ffffff !important; font-weight: 800 !important; font-size: 16px !important; padding: 12px 24px !important;
        border: none !important; border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(192, 132, 252, 0.4) !important; transition: all 0.2s ease !important;
    }
    div[data-testid="stButton"] > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(192, 132, 252, 0.6) !important;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255,255,255,0.05); border-radius: 10px 10px 0 0; 
        padding: 10px 16px; color: #94a3b8; font-size: 15px; font-weight: 600; border: none;
    }
    .stTabs [aria-selected="true"] { 
        background-color: rgba(192, 132, 252, 0.15); color: #fbcfe8 !important; 
        border-bottom: 3px solid #c084fc !important; 
    }

    .chat-user { text-align: right; margin-bottom: 15px; }
    .chat-user span { background-color: #334155; padding: 12px 18px; border-radius: 20px 20px 0 20px; display: inline-block; font-size: 15px; font-weight: 500; box-shadow: 0 4px 10px rgba(0,0,0,0.2); max-width: 85%; }
    .chat-ai { text-align: left; margin-bottom: 25px; }
    .chat-ai span { background-color: rgba(192, 132, 252, 0.1); border: 1px solid rgba(192, 132, 252, 0.3); padding: 15px 20px; border-radius: 20px 20px 20px 0; display: inline-block; font-size: 15px; line-height: 1.6; box-shadow: 0 4px 10px rgba(0,0,0,0.2); max-width: 90%; }

    .info-card {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px; padding: 20px; margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2); backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# [세션 상태 관리]
# ==========================================
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_id' not in st.session_state: st.session_state['user_id'] = ""
if 'chat_session' not in st.session_state: st.session_state['chat_session'] = [] 
if 'greeting_msg' not in st.session_state: 
    st.session_state['greeting_msg'] = random.choice(["오늘 하루도 정말 수고 많으셨어요. 어떤 이야기든 편하게 들려주세요.", "따뜻한 차 한 잔 마시듯, 편안하게 마주 앉아 이야기 나눠볼까요?"])

if 'saju_basic_info' not in st.session_state: st.session_state['saju_basic_info'] = ""
if 'saju_detail_result' not in st.session_state: st.session_state['saju_detail_result'] = ""
if 'saju_user_data' not in st.session_state: st.session_state['saju_user_data'] = {}

# ==========================================
# [화면 구성] 1. 로그인 / 회원가입 화면
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("<div class='neon-title'>🌙 스마트 마음 상담소</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>당신의 지친 하루를 따뜻하게 안아드릴게요. 편하게 기대어 보세요.</div>", unsafe_allow_html=True)
    
    col_empty1, col_login, col_empty2 = st.columns([1, 2, 1])
    
    with col_login:
        auth_tab1, auth_tab2 = st.tabs(["🔑 로그인", "📝 회원가입"])
        with auth_tab1:
            login_id = st.text_input("아이디", key="login_id", placeholder="아이디를 입력하세요")
            login_pw = st.text_input("비밀번호", type="password", key="login_pw", placeholder="비밀번호를 입력하세요")
            st.write("") 
            if st.button("로그인", use_container_width=True):
                c.execute("SELECT * FROM users WHERE user_id=? AND password=?", (login_id, login_pw))
                if c.fetchone():
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = login_id
                    st.session_state['chat_session'] = [] 
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
                    
        with auth_tab2:
            reg_id = st.text_input("사용할 아이디", key="reg_id")
            reg_pw = st.text_input("사용할 비밀번호", type="password", key="reg_pw")
            reg_pw_confirm = st.text_input("비밀번호 확인", type="password", key="reg_pw_confirm")
            st.write("")
            if st.button("가입하기", use_container_width=True):
                if reg_id.strip() == "" or reg_pw == "":
                    st.error("아이디와 비밀번호를 모두 입력해주세요.")
                elif reg_pw != reg_pw_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    try:
                        c.execute("INSERT INTO users (user_id, password) VALUES (?, ?)", (reg_id, reg_pw))
                        conn.commit()
                        st.success("가입 완료! 로그인 탭에서 로그인해주세요.")
                    except sqlite3.IntegrityError:
                        st.error("이미 존재하는 아이디입니다.")

# ==========================================
# [화면 구성] 2. 메인 서비스 화면
# ==========================================
else:
    st.markdown(f"<div class='neon-title' style='font-size: 32px;'>🌙 {st.session_state['user_id']}님의 마음 상담소</div>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn3:
        if st.button("🔒 로그아웃", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['user_id'] = ""
            st.session_state['chat_session'] = []
            st.rerun()
            
    st.write("")

    # ✨ 탭 구성 (프로필 관리 탭 추가)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs([
        "💬 고민상담", "👥 프로필 관리", "📜 사주상담", "✨ 별자리상담", "🃏 타로상담", 
        "🧭 직업상담", "🤝 관계상담", "📚 기록", "📊 스트레스", "🌙 사운드", 
        "🎮 게임", "📅 디데이", "📝 일기장"
    ])

    # ------------------------------------------
    # 공통 AI 호출 함수 (외국어 완벽 차단)
    # ------------------------------------------
    def get_ai_response(system_prompt, user_input, history=[], temperature=0.3):
        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": "user", "content": m['worry']})
            messages.append({"role": "assistant", "content": m['answer']})
        messages.append({"role": "user", "content": user_input})
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": temperature}
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            # 영어 알파벳, 한자, 일본어 등 외국어 강제 삭제 (환각 방지)
            foreign_pattern = re.compile(r'[a-zA-Z\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\u31f0-\u31ff\u0900-\u097f\u0400-\u04ff\u0600-\u06ff\u0e00-\u0e7f\u1e00-\u1eff]')
            answer = foreign_pattern.sub('', answer)
            return answer.strip()
        else:
            return f"오류 발생: {response.status_code}"

    # ------------------------------------------
    # [탭 1] 일반 고민 상담소
    # ------------------------------------------
    with tab1:
        st.markdown("### 💬 마음 속 고민 상담소")
        if st.button("🔄 새 상담 시작 (초기화)", key="reset_worry", use_container_width=True):
            st.session_state['chat_session'] = []
            st.rerun()
        st.write("")

        if not st.session_state['chat_session']:
            st.markdown(f"<div class='chat-ai'><span>🌿 <b>상담사:</b><br><br>{st.session_state['greeting_msg']}</span></div>", unsafe_allow_html=True)
        else:
            for msg in st.session_state['chat_session']:
                st.markdown(f"<div class='chat-user'><span>{msg['worry']}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='chat-ai'><span>{msg['answer']}</span></div>", unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            worry_input = st.text_area("고민을 자유롭게 적어주세요.", height=100)
            submitted = st.form_submit_button("상담사에게 전송", use_container_width=True)
            
            if submitted and worry_input.strip():
                with st.spinner("AI 심리상담사가 답변을 준비하고 있습니다..."):
                    sys_prompt = "당신은 따뜻하고 공감 능력이 뛰어난 전문 심리 상담사입니다. **[절대 규칙]: 오직 '한국어(한글)'만 사용하세요. 영어(English), 한자(漢字), 일본어 등 외국어는 단 한 글자도 절대 금지합니다.** 내담자의 질문에 깊이 공감해주고 마음이 편안해질 수 있는 따뜻한 위로와 조언을 작성해주세요."
                    answer = get_ai_response(sys_prompt, worry_input, st.session_state['chat_session'])
                    
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO counseling_records (user_id, date, type, worry, answer) VALUES (?, ?, ?, ?, ?)", 
                              (st.session_state['user_id'], now, "고민상담", worry_input, answer))
                    conn.commit()
                    
                    st.session_state['chat_session'].append({'worry': worry_input, 'answer': answer})
                    st.rerun()

    # ------------------------------------------
    # [탭 2] 👥 프로필 관리 (신규 기능)
    # ------------------------------------------
    with tab2:
        st.markdown("### 👥 내 프로필 및 지인 관리")
        st.markdown("본인, 가족, 친구의 정보를 한 번만 등록해두면 사주/별자리 상담 시 매번 입력할 필요 없이 편리하게 불러올 수 있습니다.")
        
        with st.form("profile_form"):
            st.markdown("#### ✨ 새 프로필 등록")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                p_name = st.text_input("이름 (또는 애칭)", placeholder="예: 나, 남편, 첫째딸")
                p_gender = st.selectbox("성별", ["남성", "여성"])
                p_city = st.text_input("태어난 도시 (별자리용)", value="서울")
            with col_p2:
                p_dob = st.date_input("태어난 날짜 (양력)", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today(), value=datetime.date(1990, 1, 1))
                p_tob = st.time_input("태어난 시간", value=datetime.time(12, 0))
                p_unknown = st.checkbox("태어난 시간을 정확히 모름")
                
            if st.form_submit_button("💾 프로필 저장하기", use_container_width=True):
                if p_name.strip():
                    c.execute("INSERT INTO profiles (user_id, name, gender, dob, tob, unknown_time, city) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (st.session_state['user_id'], p_name, p_gender, str(p_dob), p_tob.strftime("%H:%M"), int(p_unknown), p_city))
                    conn.commit()
                    st.success(f"'{p_name}'님의 프로필이 성공적으로 저장되었습니다!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("이름을 입력해주세요.")
                    
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 30px 0;'>", unsafe_allow_html=True)
        st.markdown("#### 📋 등록된 프로필 목록")
        
        c.execute("SELECT id, name, gender, dob, tob, unknown_time, city FROM profiles WHERE user_id=?", (st.session_state['user_id'],))
        saved_profiles = c.fetchall()
        
        if not saved_profiles:
            st.info("아직 등록된 프로필이 없습니다. 위에서 새 프로필을 등록해보세요!")
        else:
            for prof in saved_profiles:
                prof_id, name, gender, dob, tob, unk, city = prof
                time_str = "모름" if unk else tob
                
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    st.markdown(f"""
                    <div class="info-card" style="border-left: 4px solid #c084fc; padding: 15px;">
                        <div style="font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 5px;">{name} <span style="font-size: 14px; color: #94a3b8; font-weight: normal;">({gender})</span></div>
                        <div style="font-size: 14px; color: #cbd5e1;">🎂 생년월일: {dob} | ⏰ 시간: {time_str} | 🏙️ 도시: {city}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    if st.button("❌ 삭제", key=f"del_prof_{prof_id}", use_container_width=True):
                        c.execute("DELETE FROM profiles WHERE id=?", (prof_id,))
                        conn.commit()
                        st.rerun()

    # ------------------------------------------
    # [탭 3] 📜 사주 명리학 (프로필 연동)
    # ------------------------------------------
    with tab3:
        st.markdown("### 📜 AI 사주 명리학 & 만세력")
        
        # 프로필 불러오기 로직
        c.execute("SELECT id, name, gender, dob, tob, unknown_time, city FROM profiles WHERE user_id=?", (st.session_state['user_id'],))
        all_profiles = c.fetchall()
        profile_dict = {f"👤 {row[1]} ({row[3]})": row for row in all_profiles}
        profile_options = ["✍️ 직접 새로 입력하기"] + list(profile_dict.keys())
        
        selected_opt = st.selectbox("저장된 프로필 불러오기", profile_options)
        
        if selected_opt != "✍️ 직접 새로 입력하기":
            p_data = profile_dict[selected_opt]
            def_name, def_gender = p_data[1], p_data[2]
            def_dob = datetime.datetime.strptime(p_data[3], "%Y-%m-%d").date()
            def_tob = datetime.datetime.strptime(p_data[4], "%H:%M").time()
            def_unk = bool(p_data[5])
        else:
            def_name, def_gender = "홍길동", "남성"
            def_dob = datetime.date(1990, 1, 1)
            def_tob = datetime.time(12, 0)
            def_unk = False

        with st.form("saju_easy_form"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                s_name = st.text_input("이름", value=def_name)
                s_gender = st.selectbox("성별", ["남성", "여성"], index=0 if def_gender=="남성" else 1)
            with col_s2:
                s_dob = st.date_input("태어난 날짜 (양력)", value=def_dob)
                s_tob = st.time_input("태어난 시간", value=def_tob)
                s_unknown_time = st.checkbox("태어난 시간을 정확히 모름", value=def_unk)
                
            saju_submit = st.form_submit_button("🔍 사주/만세력 분석하기", use_container_width=True)
            
        if saju_submit:
            with st.spinner("정통 만세력 알고리즘으로 사주 명식을 계산 중입니다..."):
                h, m = (12, 0) if s_unknown_time else (s_tob.hour, s_tob.minute)
                birth_time_str = "모름" if s_unknown_time else f"{h}시 {m}분"
                
                saju_str, element_str = calculate_saju_details(s_dob.year, s_dob.month, s_dob.day, h, m)
                
                st.session_state['saju_user_data'] = {
                    "name": s_name, "gender": s_gender, "dob": str(s_dob), "tob": birth_time_str,
                    "saju_str": saju_str, "element_str": element_str
                }
                
                sys_prompt = "당신은 최고의 명리학자입니다. **[절대 규칙]: 오직 '한국어(한글)'만 사용하세요. 영어(English), 한자(漢字), 일본어 등 외국어는 단 한 글자도 절대 금지합니다.**"
                user_prompt = f"""
                이름: {s_name}, 성별: {s_gender}
                사주 명식(시/일/월/년): {saju_str}
                오행 분포: {element_str}
                
                위 정확한 사주 데이터를 바탕으로 다음 항목을 마크다운 형식으로 깔끔하게 작성해주세요.
                ### 📜 {s_name}님의 사주 명식 (만세력)
                - **시주 / 일주 / 월주 / 년주**: {saju_str}
                - **오행 분포**: {element_str}
                
                ### 🌟 타고난 성향 및 특징
                (이 사주가 가진 타고난 성향, 장점, 단점을 3~4문장으로 알기 쉽고 따뜻하게 설명해주세요. 사주 전문 용어나 동물 비유는 절대 쓰지 마세요.)
                """
                
                basic_info = get_ai_response(sys_prompt, user_prompt)
                st.session_state['saju_basic_info'] = basic_info
                st.session_state['saju_detail_result'] = "" 
                st.rerun()

        if st.session_state['saju_basic_info']:
            st.markdown(f"""
            <div class="info-card" style="border-left: 4px solid #ef4444;">
                <div style="color: #fca5a5; font-size: 16px; line-height: 1.7;">{st.session_state['saju_basic_info']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 30px 0;'>", unsafe_allow_html=True)
            st.markdown(f"#### 🔮 {st.session_state['saju_user_data'].get('name', '고객')}님, 어떤 운세가 궁금하신가요?")
            
            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            
            def fetch_saju_detail(topic):
                with st.spinner(f"'{topic}' 분석 중..."):
                    u_data = st.session_state['saju_user_data']
                    sys_prompt = "당신은 명리학 기반 데이터 분석가입니다. **[절대 규칙]: 오직 '한국어(한글)'만 사용하세요. 외국어/한자 절대 금지.**"
                    user_prompt = f"이름: {u_data['name']}, 사주: {u_data['saju_str']}, 오행: {u_data['element_str']}\n이 사주를 바탕으로 '{topic}'에 대해 상세히 분석해주세요. 전문 용어 없이 아주 쉽게 설명하세요."
                    result = get_ai_response(sys_prompt, user_prompt)
                    st.session_state['saju_detail_result'] = f"### 📌 {topic} 분석 결과\n\n" + result
                    
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO counseling_records (user_id, date, type, worry, answer) VALUES (?, ?, ?, ?, ?)", 
                              (st.session_state['user_id'], now, "사주상담", f"[{topic}] {u_data['name']}님의 사주 분석", result))
                    conn.commit()

            with col_b1:
                if st.button("🌅 오늘의 운세", use_container_width=True): fetch_saju_detail("오늘의 운세")
            with col_b2:
                if st.button("🎆 신년 운세", use_container_width=True): fetch_saju_detail("올해의 신년 운세 및 흐름")
            with col_b3:
                if st.button("📜 정통 사주", use_container_width=True): fetch_saju_detail("평생의 재물운, 직업운, 건강운")
            with col_b4:
                if st.button("💕 짝궁합", use_container_width=True): fetch_saju_detail("나와 잘 맞는 짝궁합 (추천 출생연도 및 띠)")

            if st.session_state['saju_detail_result']:
                st.markdown(f"""
                <div class="info-card" style="border-left: 4px solid #ef4444;">
                    <div style="color: #ffffff; font-size: 15px; line-height: 1.7;">{st.session_state['saju_detail_result']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ------------------------------------------
    # [탭 4] ✨ 서양 점성술 (프로필 연동)
    # ------------------------------------------
    with tab4:
        st.markdown("### ✨ AI 서양 점성술 & 심리 상담")
        
        selected_opt_astro = st.selectbox("저장된 프로필 불러오기 (별자리)", profile_options, key="astro_prof")
        
        if selected_opt_astro != "✍️ 직접 새로 입력하기":
            p_data = profile_dict[selected_opt_astro]
            def_dob_a = datetime.datetime.strptime(p_data[3], "%Y-%m-%d").date()
            def_tob_a = datetime.datetime.strptime(p_data[4], "%H:%M").time()
            def_unk_a = bool(p_data[5])
            def_city_a = p_data[6]
        else:
            def_dob_a = datetime.date(1990, 1, 1)
            def_tob_a = datetime.time(12, 0)
            def_unk_a = False
            def_city_a = "서울"

        with st.form("astro_form"):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                dob = st.date_input("태어난 날짜", value=def_dob_a)
                city = st.text_input("태어난 도시", value=def_city_a)
            with col_d2:
                tob = st.time_input("태어난 시간", value=def_tob_a)
                unknown_time = st.checkbox("태어난 시간을 정확히 모름", value=def_unk_a)
            
            astro_topic = st.selectbox("어떤 분석과 상담을 원하시나요?", ["오늘의 운세 및 주의해야 할 점", "인생의 변곡점 및 10년 운세", "진로 및 직업 분석", "연애 및 결혼 스타일", "올해의 금전운"])
            astro_submit = st.form_submit_button("✨ 별자리 운세 및 상담 받기", use_container_width=True)
            
        if astro_submit:
            with st.spinner("천체 위치를 계산하고 AI가 운세와 심리 상담을 준비 중입니다..."):
                birth_time_str = "모름" if unknown_time else tob.strftime("%H:%M")
                
                sys_prompt = f"당신은 전문 서양 점성술사입니다. **[절대 규칙]: 오직 '한국어(한글)'만 사용하세요. 외국어 절대 금지.** 내담자의 생년월일({dob}), 시간({birth_time_str}), 도시({city})를 바탕으로 '{astro_topic}'에 대해 상세히 분석하고 따뜻한 조언을 추가해주세요."
                user_input = f"제 생년월일은 {dob}, 시간은 {birth_time_str}, 도시는 {city}입니다. '{astro_topic}'에 대해 분석해주세요."
                
                answer = get_ai_response(sys_prompt, user_input)
                
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO counseling_records (user_id, date, type, worry, answer) VALUES (?, ?, ?, ?, ?)", 
                          (st.session_state['user_id'], now, "별자리상담", f"[{astro_topic}] 생일:{dob} 시간:{birth_time_str} 도시:{city}", answer))
                conn.commit()
                
                st.success("✨ 별의 메시지가 도착했습니다.")
                st.markdown(f"""
                <div class="info-card" style="border-left: 4px solid #f59e0b;">
                    <div style="color: #fde68a; font-size: 16px; line-height: 1.7;">{answer}</div>
                </div>
                """, unsafe_allow_html=True)

    # ------------------------------------------
    # [탭 5~13] 타로, 직업, 관계, 기록, 스트레스, 사운드, 게임, 디데이, 일기장
    # (기존 로직과 동일하게 유지하되, CSS 클래스만 info-card 등으로 모던하게 적용)
    # ------------------------------------------
    with tab5:
        st.markdown("### 🃏 타로 3카드 스프레드 리딩")
        tarot_question = st.text_input("질문을 입력하세요 (예: 이번 프로젝트가 성공할까요?)")
        if st.button("🃏 카드 3장 뽑기 및 리딩", use_container_width=True):
            if not tarot_question.strip(): st.warning("질문을 먼저 입력해주세요!")
            else:
                major = ["바보", "마법사", "고위 여사제", "여황제", "황제", "교황", "연인", "전차", "힘", "은둔자", "운명의 수레바퀴", "정의", "매달린 사람", "죽음", "절제", "악마", "탑", "별", "달", "태양", "심판", "세계"]
                suits, ranks = ["완드", "컵", "소드", "펜타클"], ["에이스", "2", "3", "4", "5", "6", "7", "8", "9", "10", "시종", "기사", "여왕", "왕"]
                tarot_deck = major + [f"{s} {r}" for s in suits for r in ranks]
                drawn_cards = random.sample(tarot_deck, 3)
                
                st.info(f"🃏 뽑힌 카드:\n1. {drawn_cards[0]} (과거)\n2. {drawn_cards[1]} (현재)\n3. {drawn_cards[2]} (미래)")
                
                with st.spinner("카드의 흐름을 직관적으로 리딩 중입니다..."):
                    sys_prompt = "당신은 직관적인 타로 마스터입니다. **[절대 규칙]: 오직 '한국어(한글)'만 사용하세요. 외국어 절대 금지.**"
                    user_prompt = f"질문: {tarot_question}\n카드: 1.{drawn_cards[0]} 2.{drawn_cards[1]} 3.{drawn_cards[2]}\n세 카드의 연결성을 파악하여 하나의 이야기로 풀어주고 조언을 덧붙여주세요."
                    answer = get_ai_response(sys_prompt, user_prompt)
                    
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO counseling_records (user_id, date, type, worry, answer) VALUES (?, ?, ?, ?, ?)", 
                              (st.session_state['user_id'], now, "타로상담", f"[질문] {tarot_question}\n[카드] {drawn_cards[0]}, {drawn_cards[1]}, {drawn_cards[2]}", answer))
                    conn.commit()
                    
                    st.markdown(f"<div class='info-card' style='border-left: 4px solid #8b5cf6;'><div style='color: #ddd6fe; font-size: 16px; line-height: 1.7;'>{answer}</div></div>", unsafe_allow_html=True)

    with tab6:
        st.markdown("### 🧭 맞춤형 직업/진로 상담소")
        with st.form("career_form"):
            col_age, col_apt = st.columns([1, 2])
            with col_age: user_age = st.number_input("현재 나이", min_value=15, max_value=100, value=30)
            with col_apt: aptitude = st.selectbox("가장 흥미를 느끼는 분야", ["현장/실무 중심", "탐구/연구 중심", "예술/창의 중심", "사회/봉사 중심", "진취/경영 중심", "사무/관습 중심"])
            career_input = st.text_area("평소 좋아하거나 잘하는 것을 적어주세요.", height=100)
            if st.form_submit_button("🔍 나의 맞춤 직업 찾기", use_container_width=True) and career_input.strip():
                with st.spinner("분석 중..."):
                    sys_prompt = f"당신은 진로 상담 전문가입니다. **[절대 규칙]: 오직 '한국어(한글)'만 사용하세요. 외국어 절대 금지.** 내담자 나이: {user_age}세, 관심분야: {aptitude}. 가장 잘 어울리는 직업 3가지를 추천해주세요."
                    answer = get_ai_response(sys_prompt, career_input)
                    st.markdown(f"<div class='chat-ai'><span>{answer}</span></div>", unsafe_allow_html=True)

    with tab7:
        st.markdown("### 🤝 인간관계/소통 상담소")
        with st.form("relation_form"):
            relation_target = st.selectbox("누구와의 관계가 고민이신가요?", ["직장 상사", "직장 동료/후배", "가족", "배우자/연인", "친구/지인"])
            relation_input = st.text_area("구체적인 상황을 적어주세요.", height=100)
            if st.form_submit_button("💡 현명한 대처법 알아보기", use_container_width=True) and relation_input.strip():
                with st.spinner("해결책을 찾는 중..."):
                    sys_prompt = f"당신은 인간관계 전문가입니다. **[절대 규칙]: 오직 '한국어(한글)'만 사용하세요. 외국어 절대 금지.** 대상: {relation_target}. 갈등 상황에 대한 현명한 대처법과 대화법을 조언해주세요."
                    answer = get_ai_response(sys_prompt, relation_input)
                    st.markdown(f"<div class='chat-ai'><span>{answer}</span></div>", unsafe_allow_html=True)

    with tab8:
        st.markdown("### 🕰️ 내가 걸어온 마음의 발자취")
        if st.button("🗑️ 전체 삭제", use_container_width=True):
            c.execute("DELETE FROM counseling_records WHERE user_id=?", (st.session_state['user_id'],))
            conn.commit()
            st.rerun()
        c.execute("SELECT id, date, type, worry, answer FROM counseling_records WHERE user_id=? ORDER BY id DESC", (st.session_state['user_id'],))
        records = c.fetchall()
        if not records: st.info("아직 상담 기록이 없습니다.")
        else:
            for record in records:
                r_id, date, c_type, worry, answer = record
                st.markdown(f"""
                <div class="info-card" style="border-left: 4px solid #c084fc;">
                    <div style="color: #fbcfe8; font-size: 13px; font-weight: bold; margin-bottom: 8px;">🕒 {date} | {c_type}</div>
                    <div style="color: #ffffff; font-size: 16px; font-weight: 700; margin-bottom: 12px;">Q. {worry}</div>
                    <div style="color: #e2e8f0; font-size: 15px; background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px;">A. {answer}</div>
                </div>
                """, unsafe_allow_html=True)

    with tab9:
        st.markdown("### 📋 직무 스트레스 자가진단")
        st.info("최근 1개월 동안 직장에서 느낀 감정에 대해 선택해 주세요. (총 5문항 간소화 버전)")
        questions = ["1. 업무량이 너무 많다.", "2. 상사나 동료와 충돌이 잦다.", "3. 업무 결과에 대해 정당한 평가를 받지 못한다.", "4. 퇴근 후에도 업무 걱정을 한다.", "5. 회사의 장래가 불투명하다."]
        options = ["전혀 그렇지 않다", "그렇지 않다", "보통이다", "그렇다", "매우 그렇다"]
        with st.form("stress_test_form"):
            scores = []
            for q in questions:
                st.markdown(f"**{q}**")
                choice = st.radio("선택", options, horizontal=True, key=q, label_visibility="collapsed")
                scores.append(options.index(choice) + 1)
            if st.form_submit_button("📊 진단 결과 확인하기", use_container_width=True):
                total_score = sum(scores) * 4 # 100점 만점 환산
                st.success(f"총점: {total_score}점 / 100점 (점수가 높을수록 스트레스가 높습니다.)")

    with tab10:
        st.markdown("### 🌙 깊은 수면과 휴식을 위한 사운드")
        sound_choice = st.selectbox("듣고 싶은 테마를 선택하세요:", ["🔥 장작 타는 소리", "🌧️ 차분해지는 빗소리", "🌊 잔잔한 파도 소리"])
        if "장작" in sound_choice: st.video("https://youtu.be/Bb0d96fC7bc?si=NDPL1dN7bmsd6DhT") 
        elif "빗소리" in sound_choice: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
        elif "파도" in sound_choice: st.video("https://www.youtube.com/watch?v=bn9F19Hi1Lk")

    with tab11:
        st.markdown("### 🎮 스트레스 타파 미니게임")
        st.info("준비 중인 기능입니다. (이전 버전의 식빵 지키기 게임 코드를 여기에 삽입하시면 됩니다.)")

    with tab12:
        st.markdown("### 📅 나의 D-Day & 기념일 관리")
        with st.form("dday_form"):
            col_d1, col_d2 = st.columns([2, 1])
            with col_d1: d_title = st.text_input("제목")
            with col_d2: d_date = st.date_input("목표 날짜")
            d_cat = st.selectbox("카테고리", ["일반 D-Day", "기념일", "생일", "아기 개월수"])
            if st.form_submit_button("디데이 추가하기", use_container_width=True) and d_title.strip():
                c.execute("INSERT INTO ddays (user_id, title, target_date, category) VALUES (?, ?, ?, ?)", (st.session_state['user_id'], d_title, str(d_date), d_cat))
                conn.commit()
                st.rerun()
        
        c.execute("SELECT id, title, target_date, category FROM ddays WHERE user_id=? ORDER BY target_date ASC", (st.session_state['user_id'],))
        for d in c.fetchall():
            d_id, title, t_date_str, cat = d
            t_date = datetime.datetime.strptime(t_date_str, "%Y-%m-%d").date()
            delta = (t_date - datetime.date.today()).days
            st.markdown(f"<div class='info-card'><b>{title}</b> ({cat}) : D-{delta if delta>0 else '+'+str(-delta)}</div>", unsafe_allow_html=True)

    with tab13:
        st.markdown("### 📝 나의 마음 일기장")
        selected_date = st.date_input("일기를 작성할 날짜를 선택하세요", value=datetime.date.today())
        selected_date_str = str(selected_date)
        
        c.execute("SELECT id, content FROM diaries WHERE user_id=? AND date=?", (st.session_state['user_id'], selected_date_str))
        row = c.fetchone()
        current_content = row[1] if row else ""
        
        with st.form("diary_form"):
            new_content = st.text_area(f"{selected_date_str}의 일기", value=current_content, height=150)
            if st.form_submit_button("💾 일기 저장하기", use_container_width=True) and new_content.strip():
                if row: c.execute("UPDATE diaries SET content=? WHERE id=?", (new_content, row[0]))
                else: c.execute("INSERT INTO diaries (user_id, date, content) VALUES (?, ?, ?)", (st.session_state['user_id'], selected_date_str, new_content))
                conn.commit()
                st.success("저장되었습니다!")
                time.sleep(1)
                st.rerun()

# ==========================================
# [푸터]
# ==========================================
st.markdown("""
<hr style="border-color: rgba(255,255,255,0.1); margin-top: 40px;">
<div style="text-align: center; color: #64748b; font-size: 13px; line-height: 1.6;">
    🌙 <b>스마트 마음 상담소 V4</b> | 2026 AI Care Solution<br>
    본 서비스의 AI 답변은 참고용이며, 전문적인 심리 치료를 대체할 수 없습니다.
</div>
""", unsafe_allow_html=True)
