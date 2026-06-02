import streamlit as st
import os
import json
import requests
import xml.etree.ElementTree as ET
import datetime
from groq import Groq

# ==========================================
# 1. 페이지 설정 및 UI 구성
# ==========================================
st.set_page_config(page_title="포항시 부동산 AI 컨설턴트", page_icon="🏠", layout="centered")

st.title("🏠 포항시 부동산 맞춤형 AI 컨설턴트")
st.subheader("포스코 퓨처엠 임직원을 위한 실거래가 기반 부동산 상담")
st.markdown("---")

# ==========================================
# 2. API 키 설정 (사이드바)
# ==========================================
st.sidebar.header("🔑 API 키 설정")
groq_api_key = st.sidebar.text_input("Groq API Key", type="password", placeholder="gsk_...")
data_api_key = st.sidebar.text_input("공공데이터포털 API Key (Decoding)", type="password", placeholder="국토교통부 실거래가 API 키")

if not groq_api_key:
    groq_api_key = os.environ.get("GROQ_API_KEY") or (st.secrets["GROQ_API_KEY"] if "GROQ_API_KEY" in st.secrets else None)
if not data_api_key:
    data_api_key = os.environ.get("DATA_API_KEY") or (st.secrets["DATA_API_KEY"] if "DATA_API_KEY" in st.secrets else None)

if not groq_api_key or not data_api_key:
    st.info("👈 좌측 사이드바에 Groq API Key와 공공데이터 API Key를 모두 입력해야 서비스가 시작됩니다.")
    st.stop()

client = Groq(api_key=groq_api_key)

if st.sidebar.button("대화 초기화 🔄"):
    st.session_state.messages = []
    st.rerun()

# ==========================================
# 3. 공공데이터 API 호출 함수 (최근 3개월 조회)
# ==========================================
def get_recent_transactions(gu_name, apt_name):
    """국토교통부 아파트매매 실거래 상세 자료 API 호출"""
    # 포항시 법정동코드: 남구(47111), 북구(47113)
    lawd_cd = "47111" if "남구" in gu_name else "47113"
    
    # 최근 3개월 연월(YYYYMM) 계산
    today = datetime.date.today()
    months_to_check = []
    for i in range(3):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        months_to_check.append(f"{y}{m:02d}")
        
    url = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTradeDev"
    results = []
    
    for ymd in months_to_check:
        params = {
            "serviceKey": requests.utils.unquote(data_api_key), # 디코딩된 키 사용
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": ymd,
            "numOfRows": "1000",
            "pageNo": "1"
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                items = root.findall('.//item')
                for item in items:
                    name = item.find('아파트').text if item.find('아파트') is not None else ""
                    # 검색어(아파트 이름)가 포함되어 있는지 확인 (공백 제거 후 비교)
                    if apt_name.replace(" ", "") not in name.replace(" ", ""):
                        continue
                    
                    price = item.find('거래금액').text if item.find('거래금액') is not None else ""
                    area = item.find('전용면적').text if item.find('전용면적') is not None else ""
                    dong = item.find('법정동').text if item.find('법정동') is not None else ""
                    y = item.find('년').text
                    m = item.find('월').text
                    d = item.find('일').text
                    
                    results.append(f"[{dong.strip()}] {name} - 전용면적: {area}㎡, 거래금액: {price.strip()}만원 ({y}년 {m}월 {d}일)")
        except Exception as e:
            print(f"API 호출 에러: {e}")
            
    if not results:
        return f"최근 3개월간 '{gu_name}' 지역에 '{apt_name}' 아파트의 실거래가 내역이 없습니다."
    
    return "\n".join(results)

# ==========================================
# 4. AI 도구(Tools) 및 시스템 프롬프트 정의
# ==========================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_transactions",
            "description": "포항시 특정 구와 아파트 이름을 입력받아 최근 3개월간의 국토교통부 실거래가 데이터를 조회합니다. 데이터베이스에 없는 아파트를 물어볼 때 반드시 사용하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gu_name": {"type": "string", "description": "포항시 구 이름 ('남구' 또는 '북구'). 대잠동, 효자동, 지곡동 등은 '남구'입니다."},
                    "apt_name": {"type": "string", "description": "검색할 아파트 이름 (예: '행복', '자이', 'SK뷰')"}
                },
                "required": ["gu_name", "apt_name"]
            }
        }
    }
]

SYSTEM_PROMPT = r"""당신은 포스코 퓨처엠 임직원을 위한 '포항시 부동산 맞춤형 AI 컨설턴트'입니다.

[답변 지침]
1. 사용자가 아파트에 대해 질문하면 먼저 아래 [주요 아파트 데이터베이스]를 참고하여 답변합니다.
2. 만약 데이터베이스에 없는 아파트(예: 대잠동 행복아파트)를 물어보거나, 최신 실거래가가 필요한 경우 **반드시 `get_recent_transactions` 도구를 호출**하여 실제 데이터를 확인한 후 답변하세요.
3. 도구 호출 결과 데이터가 없다면 "최근 3개월간 실거래가 내역이 없습니다"라고 안내하고, 절대 가상의 가격이나 정보를 지어내지 마세요.
4. 면적(㎡)을 평수로 변환하여 설명할 때는 아래 수식을 참고하여 정확히 계산하세요. 수식 전후에는 반드시 개행을 두 번 추가하십시오.

$$
\text{평수} = \text{전용면적}(m^2) \times 0.3025
$$

[포항시 주요 아파트 데이터베이스 (참고용)]
- 남구 대잠동: 힐스테이트 더샵 상생공원, 대잠 센트럴하이츠, 포항 자이
- 남구 효자동: 효자 SK뷰 1~3차, 효자 풍림아이원
- 남구 지곡동: 효자그린 1/2단지, 삼성/LG그린빌라, 지곡 에드빌 1/2차
- 북구 주요: 두호 SK뷰 푸르지오, 장성 푸르지오, 포항 환호공원 힐스테이트
"""

# ==========================================
# 5. 대화 세션 관리 및 UI 출력
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] not in ["tool", "system"]: # 도구 호출 내역과 시스템 프롬프트는 화면에 숨김
        # tool_calls가 있는 assistant 메시지도 숨김 처리
        if message["role"] == "assistant" and "tool_calls" in message:
            continue
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ==========================================
# 6. 사용자 입력 및 AI 응답 처리 (Tool Calling 로직)
# ==========================================
if prompt := st.chat_input("포항 부동산에 대해 물어보세요! (예: 대잠동 행복아파트 최근 실거래가 어때?)"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
        
        try:
            # 1차 API 호출 (도구 사용 여부 판단)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=api_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # AI가 도구(API)를 사용해야 한다고 판단한 경우
            if tool_calls:
                # AI의 도구 호출 메시지 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "tool_calls": [
                        {"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} 
                        for t in tool_calls
                    ]
                })
                
                # 도구 실행
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    if func_name == "get_recent_transactions":
                        with st.spinner(f"📊 국토교통부 실거래가 조회 중... ({func_args.get('apt_name')})"):
                            tool_result = get_recent_transactions(
                                gu_name=func_args.get("gu_name"),
                                apt_name=func_args.get("apt_name")
                            )
                            
                        # 도구 실행 결과 저장
                        st.session_state.messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": func_name,
                            "content": tool_result
                        })
                
                # 2차 API 호출 (도구 결과를 바탕으로 최종 답변 생성 - 스트리밍)
                api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
                second_response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=api_messages,
                    stream=True,
                    temperature=0.2
                )
                
                full_response = ""
                for chunk in second_response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content is not None:
                            full_response += delta.content
                            message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            # 도구를 사용하지 않고 바로 답변하는 경우
            else:
                full_response = response_message.content
                # 스트리밍 효과 시뮬레이션
                import time
                displayed_response = ""
                for char in full_response:
                    displayed_response += char
                    message_placeholder.markdown(displayed_response + "▌")
                    time.sleep(0.005)
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
        except Exception as e:
            error_msg = f"⚠️ API 호출 중 에러가 발생했습니다: {e}"
            message_placeholder.error(error_msg)
            st.session_state.messages.pop()
