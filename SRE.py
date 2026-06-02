import streamlit as st
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import json
from groq import Groq

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(page_title="포항시 부동산 AI 컨설턴트", page_icon="🏠", layout="wide")
st.title("🏠 포항시 부동산 AI 컨설턴트")
st.caption("포스코퓨처엠 임직원 여러분을 위한 포항시 맞춤형 부동산 실거래가 조회 서비스입니다.")

# ==========================================
# 2. API 키 설정 (사이드바)
# ==========================================
st.sidebar.header("🔑 API 키 설정")

# secrets.toml 또는 환경변수에서 키 불러오기
groq_api_key = os.environ.get("GROQ_API_KEY") or (st.secrets["GROQ_API_KEY"] if "GROQ_API_KEY" in st.secrets else None)
data_api_key = os.environ.get("DATA_API_KEY") or (st.secrets["DATA_API_KEY"] if "DATA_API_KEY" in st.secrets else None)

# 키가 없으면 입력창 띄우기, 있으면 성공 메시지
if not groq_api_key:
    groq_api_key = st.sidebar.text_input("Groq API Key", type="password", placeholder="gsk_...")
else:
    st.sidebar.success("✅ Groq API Key 자동 연동 완료")

if not data_api_key:
    data_api_key = st.sidebar.text_input("공공데이터포털 API Key", type="password", placeholder="국토교통부 실거래가 API 키")
else:
    st.sidebar.success("✅ 공공데이터 API Key 자동 연동 완료")

# 둘 중 하나라도 없으면 앱 실행 중단
if not groq_api_key or not data_api_key:
    st.info("👈 좌측 사이드바에 API Key를 입력하거나, .streamlit/secrets.toml 파일을 설정해주세요.")
    st.stop()

# Groq 클라이언트 초기화
client = Groq(api_key=groq_api_key)

if st.sidebar.button("대화 초기화 🔄"):
    st.session_state.messages = []
    st.rerun()

# ==========================================
# 3. 공공데이터포털 실거래가 API 호출 함수
# ==========================================
def get_real_estate_data(lawd_cd, apt_name):
    """국토교통부 API를 호출하여 최근 3개월 실거래가를 가져오는 함수"""
    url = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTradeDev"
    
    # 최근 3개월 연월(YYYYMM) 계산
    today = datetime.today()
    months_to_check = []
    for i in range(3):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        months_to_check.append(f"{y}{m:02d}")

    # 검색어 공백 제거 (예: "힐스테이트 포항" -> "힐스테이트포항")
    search_name = apt_name.replace(" ", "")
    results = []

    for ymd in months_to_check:
        # URL 직접 조립 (requests params 사용 시 인코딩 오류 방지)
        full_url = f"{url}?serviceKey={data_api_key}&pageNo=1&numOfRows=1000&LAWD_CD={lawd_cd}&DEAL_YMD={ymd}"
        
        try:
            response = requests.get(full_url)
            root = ET.fromstring(response.content)
            
            for item in root.findall('.//item'):
                api_apt_name = item.find('아파트').text if item.find('아파트') is not None else ""
                # API에서 온 아파트 이름도 공백 제거 후 비교
                if search_name in api_apt_name.replace(" ", ""):
                    price = item.find('거래금액').text.strip()
                    area = float(item.find('전용면적').text.strip())
                    pyeong = round(area / 3.3058, 1) # 평수 변환
                    day = item.find('일').text.strip()
                    floor = item.find('층').text.strip()
                    
                    results.append(f"- {ymd[:4]}년 {ymd[4:]}월 {day}일: {price}만원 (전용 {area}㎡ / {pyeong}평, {floor}층)")
        except Exception as e:
            print(f"API Error: {e}")
            continue
            
    if not results:
        return f"'{apt_name}'의 최근 3개월간 실거래가 내역을 찾을 수 없습니다. (지역코드: {lawd_cd})"
    
    return "\n".join(results)

# ==========================================
# 4. Groq Function Calling 도구 정의
# ==========================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_real_estate_data",
            "description": "국토교통부 실거래가 API를 호출하여 특정 지역의 아파트 실거래가(최근 3개월)를 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lawd_cd": {
                        "type": "string",
                        "description": "지역코드 5자리 (포항 남구: 47111, 포항 북구: 47113)"
                    },
                    "apt_name": {
                        "type": "string",
                        "description": "검색할 아파트 이름 (예: 힐스테이트, 행복아파트)"
                    }
                },
                "required": ["lawd_cd", "apt_name"]
            }
        }
    }
]

# ==========================================
# 5. 시스템 프롬프트 및 세션 상태 초기화
# ==========================================
system_prompt = """
당신은 첨단 소재 회사 포스코 퓨처엠 직원의 질문에 정성껏 답변해주는 포항시 부동산 맞춤형 AI 컨설턴트입니다.
단, 이 GPT는 개인적인 정보나 회사의 기밀 정보는 학습되어 있지 않으니 참고 바랍니다.

사용자가 아파트 실거래가를 물어보면 반드시 제공된 함수(get_real_estate_data)를 호출하여 답변하세요.

[포항시 지역코드(LAWD_CD) 가이드]
- 포항시 남구 (47111): 대잠동, 오천읍, 효자동, 지곡동, 이동, 연일읍, 구룡포읍 등
- 포항시 북구 (47113): 장성동, 양덕동, 두호동, 창포동, 우현동, 흥해읍 등

사용자가 '오천읍 힐스테이트포항'을 물어보면 lawd_cd는 '47111', apt_name은 '힐스테이트' 또는 '힐스테이트포항'으로 검색하세요.
수식을 포함한 답변을 작성할 때, 수식 전후에 개행을 두 번 추가하여 수식이 명확하게 구분되도록 하세요.
"""

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "안녕하세요! 포스코퓨처엠 임직원 여러분을 위한 포항시 부동산 컨설턴트입니다. 궁금한 아파트의 실거래가를 물어보세요! (예: 대잠동 행복아파트 어때요?)"
    })

# ==========================================
# 6. 채팅 UI 및 로직
# ==========================================
# 기존 대화 내용 출력
for msg in st.session_state.messages:
    if msg["role"] not in ["system", "tool"]:
        # tool_calls가 있는 메시지는 화면에 표시하지 않음
        if msg.get("tool_calls"):
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 사용자 입력 처리
if prompt := st.chat_input("질문을 입력하세요... (예: 오천읍 힐스테이트포항 실거래가 알려줘)"):
    # 사용자 메시지 추가 및 출력
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        try:
            # 1차 API 호출 (도구 사용 여부 판단)
            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile", # Function Calling에 최적화된 모델
                messages=st.session_state.messages,
                tools=tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            
            # AI가 함수 호출(도구 사용)을 결정한 경우
            if response_message.tool_calls:
                # AI의 도구 호출 메시지를 세션에 저장 (딕셔너리 형태로 변환)
                st.session_state.messages.append({
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        } for tool_call in response_message.tool_calls
                    ]
                })
                
                # 각 도구 호출 실행
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "get_real_estate_data":
                        args = json.loads(tool_call.function.arguments)
                        
                        with st.spinner(f"🔍 '{args['apt_name']}' 실거래가 데이터 조회 중..."):
                            function_response = get_real_estate_data(args["lawd_cd"], args["apt_name"])
                            
                        # 함수 실행 결과를 세션에 저장
                        st.session_state.messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "get_real_estate_data",
                            "content": function_response
                        })
                        
                # 2차 API 호출 (함수 결과를 바탕으로 최종 답변 생성)
                second_response = client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=st.session_state.messages
                )
                
                final_answer = second_response.choices[0].message.content
                response_placeholder.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                
            # AI가 함수 호출 없이 바로 답변한 경우
            else:
                final_answer = response_message.content
                response_placeholder.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
