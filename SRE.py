import streamlit as st
import sqlite3
import datetime
import time
import requests
import re
import calendar

# ==========================================
# [초기 설정] 페이지 세팅 (2026년형 모던 스타일)
# ==========================================
st.set_page_config(page_title="부동산 맛동산", page_icon="🥜", layout="centered")

# ==========================================
# [Groq API 키 설정]
# ==========================================
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("⚠️ 스트림릿 설정(Settings) -> Secrets에 'GROQ_API_KEY'를 먼저 입력해주세요!")
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
# [CSS] 2026년형 초현대적 UI & 프리텐다드 폰트 & 맛동산 테마
# ==========================================
st.markdown("""
<style>
    /* 2026년형 모던 폰트: Pretendard 적용 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    .stApp, p, span, div, h1, h2, h3, h4, h5, h6, label, input, textarea, button, table, th, td {
        font-family: 'Pretendard', sans-serif !important;
    }
    
    /* 배경: 다크 슬레이트 + 맛동산(피넛/골드) 포인트 */
    .stApp { 
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
        color: #f8fafc; 
    }
    
    /* 네온 타이틀 (부동산 맛동산 전용) */
    .neon-title {
        font-size: 48px; font-weight: 900; color: #ffffff; text-align: center;
        margin-top: 20px; margin-bottom: 10px; letter-spacing: -1px; line-height: 1.2;
        text-shadow: 0 0 10px rgba(245, 158, 11, 0.5), 0 0 20px rgba(245, 158, 11, 0.3);
    }
    .sub-title { color: #cbd5e1; font-size: 18px; margin-bottom: 40px; font-weight: 400; text-align: center; letter-spacing: -0.5px; }

    /* 입력창 디자인 (글래스모피즘) */
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div:first-child {
        background-color: rgba(30, 41, 59, 0.7) !important; 
        border: 1px solid #d97706 !important; 
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
    }
    input, textarea { color: #ffffff !important; font-size: 16px !important; font-weight: 500 !important; }
    input::placeholder, textarea::placeholder { color: #94a3b8 !important; font-weight: 400 !important; }
    
    /* 버튼 디자인 (맛동산 골드 그라데이션) */
    div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important; 
        color: #ffffff !important; 
        font-weight: 800 !important; font-size: 16px !important; padding: 12px 24px !important;
        border: none !important; border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(217, 119, 6, 0.4) !important; transition: all 0.2s ease !important;
    }
    div[data-testid="stButton"] > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(217, 119, 6, 0.6) !important;
    }

    /* 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255,255,255,0.05); border-radius: 10px 10px 0 0; 
        padding: 10px 16px; color: #94a3b8; font-size: 16px; font-weight: 600; border: none;
    }
    .stTabs [aria-selected="true"] { 
        background-color: rgba(245, 158, 11, 0.15); color: #fcd34d !important; 
        border-bottom: 3px solid #f59e0b !important; 
    }

    /* 채팅 UI */
    .chat-user { text-align: right; margin-bottom: 15px; }
    .chat-user span { background-color: #334155; padding: 12px 18px; border-radius: 20px 20px 0 20px; display: inline-block; font-size: 15px; font-weight: 500; box-shadow: 0 4px 10px rgba(0,0,0,0.2); max-width: 85%; }
    .chat-ai { text-align: left; margin-bottom: 25px; }
    .chat-ai span { background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 15px 20px; border-radius: 20px 20px 20px 0; display: inline-block; font-size: 15px; line-height: 1.6; box-shadow: 0 4px 10px rgba(0,0,0,0.2); max-width: 90%; }

    /* 카드 UI */
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

# ==========================================
# [화면 구성] 1. 로그인 / 회원가입 화면
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("<div class='neon-title'>🏢 부동산 맛동산 🥜</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>달콤하고 바삭한 부동산 정보, 2026년형 AI 프롭테크 솔루션</div>", unsafe_allow_html=True)
    
    # 맛동산 & 부동산 테마의 시각적 요소 (CSS 그라데이션 카드)
    st.markdown("""
    <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 40px; flex-wrap: wrap;">
        <div style="background: linear-gradient(135deg, #f59e0b, #d97706); padding: 20px; border-radius: 16px; width: 140px; text-align: center; box-shadow: 0 10px 20px rgba(217,119,6,0.3);">
            <div style="font-size: 30px; margin-bottom: 10px;">🍯</div>
            <div style="color: white; font-weight: bold; font-size: 14px;">꿀 떨어지는<br>청약 정보</div>
        </div>
        <div style="background: linear-gradient(135deg, #3b82f6, #2563eb); padding: 20px; border-radius: 16px; width: 140px; text-align: center; box-shadow: 0 10px 20px rgba(37,99,235,0.3);">
            <div style="font-size: 30px; margin-bottom: 10px;">🏢</div>
            <div style="color: white; font-weight: bold; font-size: 14px;">스마트한<br>임장 일기</div>
        </div>
        <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 20px; border-radius: 16px; width: 140px; text-align: center; box-shadow: 0 10px 20px rgba(16,185,129,0.3);">
            <div style="font-size: 30px; margin-bottom: 10px;">🥜</div>
            <div style="color: white; font-weight: bold; font-size: 14px;">바삭하고 명쾌한<br>AI 상담</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
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
    st.markdown(f"<div class='neon-title' style='font-size: 32px;'>🏢 {st.session_state['user_id']}님의 부동산 맛동산 🥜</div>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn3:
        if st.button("🔒 로그아웃", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['user_id'] = ""
            st.session_state['chat_session'] = []
            st.rerun()
            
    st.write("")

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["🤖 AI 부동산 상담", "📝 임장 일기 (달력)", "📅 청약/이사 D-Day"])

    # ------------------------------------------
    # 공통 AI 호출 함수 (외국어 완벽 차단)
    # ------------------------------------------
    def get_ai_response(system_prompt, user_input, history=[]):
        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": "user", "content": m['query']})
            messages.append({"role": "assistant", "content": m['answer']})
        messages.append({"role": "user", "content": user_input})
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.3}
        
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
    # [탭 1] AI 부동산 상담
    # ------------------------------------------
    with tab1:
        st.markdown("### 🤖 바삭하고 명쾌한 AI 부동산 상담")
        st.markdown("청약, 대출, 세금, 부동산 용어 등 궁금한 점을 무엇이든 물어보세요. 맛동산처럼 달콤하고 쉽게 풀어드립니다.")
        
        if st.button("🔄 대화 초기화", use_container_width=True):
            st.session_state['chat_session'] = []
            st.rerun()
        st.write("")

        if not st.session_state['chat_session']:
            st.markdown("<div class='chat-ai'><span>🥜 <b>부동산 맛동산 AI:</b><br><br>안녕하세요! 부동산에 대해 어떤 점이 궁금하신가요? 어려운 용어도 아주 쉽게 설명해 드릴게요!</span></div>", unsafe_allow_html=True)
        else:
            for msg in st.session_state['chat_session']:
                st.markdown(f"<div class='chat-user'><span>{msg['query']}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='chat-ai'><span>{msg['answer']}</span></div>", unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            user_query = st.text_area("질문을 입력하세요.", height=100, placeholder="예: 디딤돌 대출 조건이 어떻게 되나요? / LTV가 무슨 뜻인가요?")
            submitted = st.form_submit_button("질문하기", use_container_width=True)
            
            if submitted and user_query.strip():
                with st.spinner("AI가 명쾌한 답변을 준비하고 있습니다..."):
                    sys_prompt = "당신은 2026년 최고의 프롭테크 AI '부동산 맛동산'입니다. **[절대 규칙]: 오직 '한국어(한글)'와 '숫자'만 사용하세요. 영어 알파벳(a-z, A-Z), 한자(漢字) 등 외국어는 단 한 글자도 절대 금지합니다. (엘티브이, 디에스알 처럼 무조건 한글 발음으로 적으세요.)** 사용자의 부동산 관련 질문(청약, 대출, 세금, 용어 등)에 대해 아주 쉽고 친절하게, 가독성 좋은 마크다운으로 답변해주세요."
                    answer = get_ai_response(sys_prompt, user_query, st.session_state['chat_session'])
                    
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO chat_records (user_id, date, query, answer) VALUES (?, ?, ?, ?)", 
                              (st.session_state['user_id'], now, user_query, answer))
                    conn.commit()
                    
                    st.session_state['chat_session'].append({'query': user_query, 'answer': answer})
                    st.rerun()

    # ------------------------------------------
    # [탭 2] 📝 임장 일기 (달력)
    # ------------------------------------------
    with tab2:
        st.markdown("### 📝 스마트 임장 일기")
        st.markdown("직접 발로 뛴 임장(현장 방문) 기록을 달력에 체계적으로 남겨보세요.")
        
        col_y, col_m = st.columns(2)
        today_date = datetime.date.today()
        with col_y:
            sel_year = st.selectbox("년도", range(2024, 2031), index=today_date.year - 2024)
        with col_m:
            sel_month = st.selectbox("월", range(1, 13), index=today_date.month - 1)
            
        # 해당 월의 임장 일기 데이터 가져오기
        c.execute("SELECT date, content FROM field_diaries WHERE user_id=? AND date LIKE ?", (st.session_state['user_id'], f"{sel_year}-{sel_month:02d}-%"))
        diary_data = {row[0]: row[1] for row in c.fetchall()}
        
        # HTML/CSS 달력 렌더링
        cal = calendar.monthcalendar(sel_year, sel_month)
        
        cal_html = f"""
        <div style="background: rgba(30, 41, 59, 0.8); border-radius: 16px; padding: 20px; border: 1px solid rgba(245, 158, 11, 0.3); margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <h4 style="text-align: center; color: #fcd34d; margin-bottom: 20px; font-weight: 800;">{sel_year}년 {sel_month}월</h4>
            <table style="width: 100%; text-align: center; border-collapse: collapse; table-layout: fixed;">
                <tr style="color: #94a3b8; font-weight: bold; font-size: 15px;">
                    <th style="padding-bottom: 15px;">월</th><th>화</th><th>수</th><th>목</th><th>금</th><th style="color:#60a5fa;">토</th><th style="color:#f87171;">일</th>
                </tr>
        """
        
        for week in cal:
            cal_html += "<tr>"
            for i, day in enumerate(week):
                if day == 0:
                    cal_html += "<td style='padding: 15px 5px; border-top: 1px solid rgba(255,255,255,0.05);'></td>"
                else:
                    date_str = f"{sel_year}-{sel_month:02d}-{day:02d}"
                    is_today = (date_str == str(today_date))
                    has_diary = date_str in diary_data
                    
                    day_color = "#f8fafc"
                    if i == 5: day_color = "#93c5fd" # 토요일
                    elif i == 6: day_color = "#fca5a5" # 일요일
                    
                    bg_style = "background: rgba(245, 158, 11, 0.2); border-radius: 10px;" if is_today else ""
                    icon = "<div style='font-size: 14px; margin-top: 5px;'>🏢</div>" if has_diary else "<div style='font-size: 14px; margin-top: 5px; opacity: 0;'>-</div>"
                    
                    cal_html += f"<td style='padding: 10px 5px; border-top: 1px solid rgba(255,255,255,0.05); {bg_style}'>"
                    cal_html += f"<div style='color: {day_color}; font-size: 16px; font-weight: {'800' if is_today else '500'};'>{day}</div>"
                    cal_html += f"{icon}</td>"
            cal_html += "</tr>"
            
        cal_html += "</table></div>"
        st.markdown(cal_html, unsafe_allow_html=True)
        
        # 일기 작성 영역
        st.markdown("#### ✍️ 임장 기록 작성")
        selected_date = st.date_input("기록할 날짜를 선택하세요", value=today_date)
        selected_date_str = str(selected_date)
        
        current_content = diary_data.get(selected_date_str, "")
        
        with st.form("diary_form"):
            new_content = st.text_area(f"{selected_date_str} 임장 기록", value=current_content, height=150, placeholder="방문한 아파트 이름, 주변 인프라, 느낀 점, 호가 등을 자유롭게 기록하세요.")
            
            col_sub1, col_sub2 = st.columns(2)
            with col_sub1:
                submitted_diary = st.form_submit_button("💾 기록 저장", use_container_width=True)
            with col_sub2:
                deleted_diary = st.form_submit_button("🗑️ 기록 삭제", use_container_width=True)
                
            if submitted_diary:
                if new_content.strip():
                    c.execute("SELECT id FROM field_diaries WHERE user_id=? AND date=?", (st.session_state['user_id'], selected_date_str))
                    row = c.fetchone()
                    if row:
                        c.execute("UPDATE field_diaries SET content=? WHERE id=?", (new_content, row[0]))
                    else:
                        c.execute("INSERT INTO field_diaries (user_id, date, content) VALUES (?, ?, ?)", (st.session_state['user_id'], selected_date_str, new_content))
                    conn.commit()
                    st.success("임장 기록이 저장되었습니다!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("내용을 입력해주세요.")
                    
            if deleted_diary:
                c.execute("DELETE FROM field_diaries WHERE user_id=? AND date=?", (st.session_state['user_id'], selected_date_str))
                conn.commit()
                st.success("기록이 삭제되었습니다.")
                time.sleep(1)
                st.rerun()

    # ------------------------------------------
    # [탭 3] 📅 청약/이사 D-Day
    # ------------------------------------------
    with tab3:
        st.markdown("### 📅 청약 및 이사 D-Day 관리")
        st.markdown("놓치기 쉬운 청약일, 계약일, 이사일, 잔금일 등을 한눈에 관리하세요.")
        
        with st.form("dday_form"):
            col_d1, col_d2 = st.columns([2, 1])
            with col_d1:
                d_title = st.text_input("일정 이름 (예: 래미안 청약일, 전세 잔금일)")
            with col_d2:
                d_date = st.date_input("목표 날짜")
                
            d_cat = st.selectbox("카테고리", ["청약/분양", "계약/잔금", "이사", "기타 일정"])
            
            if st.form_submit_button("일정 추가하기", use_container_width=True):
                if d_title.strip():
                    c.execute("INSERT INTO ddays (user_id, title, target_date, category) VALUES (?, ?, ?, ?)", 
                              (st.session_state['user_id'], d_title, str(d_date), d_cat))
                    conn.commit()
                    st.success("일정이 추가되었습니다!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("일정 이름을 입력해주세요.")
                    
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 30px 0;'>", unsafe_allow_html=True)
        
        c.execute("SELECT id, title, target_date, category FROM ddays WHERE user_id=? ORDER BY target_date ASC", (st.session_state['user_id'],))
        ddays = c.fetchall()
        
        if not ddays:
            st.info("등록된 일정이 없습니다. 위에서 새로운 일정을 추가해보세요!")
        else:
            today = datetime.date.today()
            for d in ddays:
                d_id, title, t_date_str, cat = d
                t_date = datetime.datetime.strptime(t_date_str, "%Y-%m-%d").date()
                delta = (t_date - today).days
                
                if cat == "청약/분양": badge_color = "#f59e0b" # 골드
                elif cat == "계약/잔금": badge_color = "#ef4444" # 레드
                elif cat == "이사": badge_color = "#3b82f6" # 블루
                else: badge_color = "#10b981" # 그린
                
                if delta > 0: display_text = f"D-{delta}"
                elif delta < 0: display_text = f"D+{-delta}"
                else: display_text = "D-Day (오늘!)"

                col_text, col_btn = st.columns([5, 1])
                with col_text:
                    st.markdown(f"""
                    <div class="info-card" style="border-left: 5px solid {badge_color}; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="color: #94a3b8; font-size: 13px; margin-bottom: 5px; font-weight: 600;">{cat} • {t_date_str}</div>
                            <div style="color: #ffffff; font-size: 18px; font-weight: 800;">{title}</div>
                        </div>
                        <div style="color: {badge_color}; font-size: 24px; font-weight: 900;">{display_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_btn:
                    if st.button("❌", key=f"del_dday_{d_id}", help="삭제"):
                        c.execute("DELETE FROM ddays WHERE id=?", (d_id,))
                        conn.commit()
                        st.rerun()

# ==========================================
# [푸터]
# ==========================================
st.markdown("""
<hr style="border-color: rgba(255,255,255,0.1); margin-top: 50px;">
<div style="text-align: center; color: #64748b; font-size: 13px; line-height: 1.6;">
    🏢 <b>부동산 맛동산</b> | 2026 AI PropTech Solution<br>
    본 서비스의 AI 답변은 참고용이며, 실제 부동산 계약 및 투자 시에는 반드시 전문가와 상의하시기 바랍니다.
</div>
""", unsafe_allow_html=True)
