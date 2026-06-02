import streamlit as st
from groq import Groq
import os

# 페이지 설정
st.set_page_config(page_title="포항 부동산 컨설턴트", page_icon="🏠", layout="centered")

# 제목 및 설명
st.title("🏠 포항시 맞춤형 부동산 추천 서비스")
st.markdown("**포스코퓨처엠 임직원**을 위한 직장/예산 맞춤형 실거주 아파트 추천 시스템입니다.")

# 사이드바: API 키 입력 (또는 Streamlit Secrets 사용)
with st.sidebar:
    st.header("설정")
    api_key = st.text_input("Groq API Key를 입력하세요", type="password")
    st.markdown("[Groq API Key 발급받기](https://console.groq.com/keys)")

# 사용자 입력 폼
with st.form("real_estate_form"):
    workplace = st.text_input("🏢 직장 주소", value="경북 포항시 남구 신항로 110 포스코퓨처엠 본사")
    location = st.text_input("📍 희망 거주지", placeholder="예: 포항시 남구 오천읍")
    budget = st.text_input("💰 가용 예산", placeholder="예: 3억 원")
    
    submit_button = st.form_submit_button(label="분석 및 추천 받기")

# 프롬프트 템플릿
system_prompt = """
당신은 포항시 부동산 시장에 정통한 '부동산 투자 및 실거주 맞춤형 컨설턴트'입니다. 
고객이 입력한 [직장 주소], [희망 거주지], [예산]을 바탕으로, 부동산 핵심 선호 조건인 '브역대신평초'를 분석하여 최적의 아파트 매수 후보 3곳을 순위별로 추천해 주세요.

🚨 [매우 중요한 필수 준수 사항: 할루시네이션 방지] 🚨
1. 절대 허구의 아파트 이름이나 타 지역의 아파트를 지어내어 추천하지 마세요.
2. 반드시 고객이 입력한 [희망 거주지] 행정구역 내에 '실제로 존재하는 아파트'만 검색하여 추천해야 합니다.
3. 해당 지역에 조건(예산 등)을 완벽히 만족하는 아파트가 3개가 안 될 경우, 억지로 지어내지 말고 "조건에 맞는 실재하는 아파트는 X개입니다"라고 명시한 뒤, 예산을 살짝 초과하거나 인접한 동네의 실제 아파트를 대안으로 제시하세요.
4. 세대수, 입주 연도(연식), 초등학교 배정 정보는 사실에 기반하여 작성하세요.

[분석 기준: 포항형 브역대신평초]
* 브 (브랜드): 1군 건설사 브랜드 (자이, 더샵, 푸르지오, 힐스테이트, 아이파크 등)
* 역 (교통/출퇴근): 주요 대로 및 KTX 포항역 접근성, [직장 주소]까지의 차량 출퇴근 소요 시간
* 대 (대단지): 세대수 (최소 500세대 이상)
* 신 (신축): 입주 연도 (10년 이내 신축 및 준신축 우대)
* 평 (평지): 단지 및 주변 지형의 평탄화 정도
* 초 (초품아): 도보 통학 가능한 배정 초등학교 유무 및 거리

[출력 형식]
1. 📊 맞춤형 요약 분석
- 예산 및 직장 위치를 고려한 거주 지역 특징 및 출퇴근 동선 분석

2. 🏆 추천 아파트 TOP 3 (1위~3위)
각 순위별로 아래 내용을 포함해 주세요.
- 아파트명 및 정확한 위치 (법정동)
- 예상 매매가 및 평형 (최근 실거래가 또는 호가 기준)
- 직장까지의 예상 출퇴근 시간 (차량 기준)
- '브역대신평초' 6가지 조건에 대한 상세 평가
- 객관적인 가격 비교를 위한 평당 단가 계산 (반드시 아래 수식 형식을 지킬 것)
- 추천 사유 (장점 및 단점 포함)

3. 💡 매수 시 유의사항 및 최종 조언
- 해당 지역의 공급 물량, 교통 체증 구간, 환경적 요인 등 실거주 시 반드시 체크해야 할 현실적인 조언

[수식 작성 규칙]
수식을 포함한 답변을 작성할 때, 수식 전후에 개행을 두 번 추가하여 수식이 명확하게 구분되도록 하세요.
예시:

$$ 평당 단가 = \\frac{예상 매매가}{평수} $$

"""

# 실행 로직
if submit_button:
    if not api_key:
        st.warning("좌측 사이드바에 Groq API Key를 입력해주세요.")
    elif not location or not budget:
        st.warning("희망 거주지와 가용 예산을 모두 입력해주세요.")
    else:
        with st.spinner("부동산 데이터를 분석하고 있습니다. 잠시만 기다려주세요..."):
            try:
                # Groq 클라이언트 초기화
                client = Groq(api_key=api_key)
                
                # 사용자 입력 메시지 구성
                user_message = f"""
                [고객 입력 정보]
                1. 직장 주소: {workplace}
                2. 희망 거주지: {location}
                3. 가용 예산: {budget}
                """
                
                # API 호출 (llama3-70b 모델 사용 - 추론 능력이 뛰어남)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    model="llama3-70b-8192",
                    temperature=0.3, # 사실 기반 답변을 위해 온도를 낮춤
                    max_tokens=3000
                )
                
                # 결과 출력
                result = chat_completion.choices[0].message.content
                st.success("분석이 완료되었습니다!")
                st.markdown("---")
                st.markdown(result)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
