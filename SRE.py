import streamlit as st
from groq import Groq

# ==========================================
# 1. 페이지 설정 및 UI 구성
# ==========================================
st.set_page_config(
    page_title="포항시 부동산 맞춤형 AI 컨설턴트",
    page_icon="🏠",
    layout="centered"
)

st.title("🏠 포항시 부동산 맞춤형 AI 컨설턴트")
st.subheader("포스코 퓨처엠 임직원을 위한 맞춤형 부동산 상담 서비스")
st.markdown("---")

# ==========================================
# 2. API 키 설정 (사이드바)
# ==========================================
# Streamlit Secrets 또는 환경 변수에서 키를 가져오고, 없을 경우 사이드바에서 입력받습니다.
api_key = st.sidebar.text_input("Groq API Key", type="password", placeholder="gsk_...")
if not api_key:
    # Secrets에 등록되어 있는지 확인
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
    else:
        st.sidebar.warning("⚠️ 서비스를 이용하려면 Groq API Key를 입력해주세요.")
        st.stop()

# Groq 클라이언트 초기화
client = Groq(api_key=api_key)

# 대화 리셋 버튼
if st.sidebar.button("대화 초기화 🔄"):
    st.session_state.messages = []
    st.rerun()

# ==========================================
# 3. 시스템 프롬프트 정의 (할루시네이션 방지 및 지식 주입)
# ==========================================
SYSTEM_PROMPT = """당신은 첨단 소재 회사 포스코 퓨처엠 임직원을 위한 '포항시 부동산 맞춤형 AI 컨설턴트'입니다.
반드시 아래의 지침과 [포항시 주요 아파트 데이터베이스]를 기반으로 답변하며, 데이터에 없는 아파트 브랜드(예: 대잠동 아이파크, 대잠동 푸르지오 등)를 임의로 지어내지 마십시오.

[할루시네이션(거짓 정보) 방지 엄격 지침]
1. 아파트 명칭, 위치, 세대수 등은 반드시 아래 제공된 [포항시 주요 아파트 데이터베이스] 내에서만 추천하십시오.
2. 사용자가 데이터베이스에 없는 지역이나 아파트를 물어볼 경우, "현재 제가 가진 데이터에는 해당 지역의 정확한 아파트 정보가 없습니다. 대신 인근의 OOO 아파트를 추천해 드릴 수 있습니다."라고 솔직하게 답변하십시오.
3. '힐스테이트 더샵 상생공원'과 같은 복합 브랜드 명칭을 정확히 표기하십시오. (단순 '힐스테이트'로 축약 금지)
4. 존재하지 않는 가상의 단지(예: 대잠동 푸르지오, 대잠동 아이파크 등)를 절대 생성하지 마십시오.

[포항시 주요 아파트 데이터베이스 (참고용)]
- 남구 대잠동 (포스코 출퇴근 용이, 신축 및 인프라 우수): 
  * 힐스테이트 더샵 상생공원 (1, 2단지 총 2,667세대, 신축 대장 아파트)
  * 대잠 센트럴하이츠 (550세대)
  * 포항 자이 (1,567세대)
- 남구 효자동 (상권 및 강변 인프라 우수):
  * 효자 SK뷰 1~3차 (대단지, 포스텍/포스코 접근성 우수)
  * 효자 풍림아이원 (583세대)
- 남구 지곡동 (학군 우수, 쾌적한 환경, 포스코 임직원 선호도 최상):
  * 효자그린 1, 2단지
  * 삼성그린빌라, LG그린빌라
  * 지곡 에드빌 1, 2차
- 북구 주요 대장 아파트:
  * 두호 SK뷰 푸르지오 (두호동)
  * 장성 푸르지오 (장성동)
  * 포항 환호공원 힐스테이트 (양덕동)

[답변 형식]
- 임직원의 상황(예산, 가족 구성원, 출퇴근 거리 등)에 맞춰 위 데이터베이스의 아파트를 매칭하여 추천합니다.
- 면적(㎡)을 평수로 변환하여 설명할 때는 아래 수식을 참고하여 정확히 계산하세요. 수식 전후에는 반드시 개행을 두 번 추가하여 구분되도록 하십시오.

$$
평수 = 전용면적(m^2) \\times 0.3025
$$

- 친절하고 전문적인 컨설턴트의 톤앤매너를 유지하십시오.
"""

# ==========================================
# 4. 대화 세션 관리 및 UI 출력
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 대화 기록 출력 (시스템 메시지 제외)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==========================================
# 5. 사용자 입력 및 AI 응답 처리
# ==========================================
if prompt := st.chat_input("포항 부동산에 대해 궁금한 점을 물어보세요! (예: 대잠동 신축 아파트 추천해줘)"):
    # 사용자 메시지 출력 및 저장
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AI 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # API 호출을 위한 메시지 구성 (시스템 프롬프트 포함)
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
        ]
        
        try:
            # Groq API 스트리밍 호출
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=api_messages,
                temperature=0.2,  # 일관성 있는 답변을 위해 온도를 낮춤 (할루시네이션 방지)
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"에러가 발생했습니다: {e}")
            
    # AI 응답 저장
    st.session_state.messages.append({"role": "assistant", "content": full_response})
