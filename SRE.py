import streamlit as st
import requests
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import urllib.parse

st.set_page_config(page_title="API 테스트", layout="wide")
st.title("🛠️ API 연결 상태 진단기")

# 1. 키 불러오기
try:
    KAKAO_REST_KEY = st.secrets["KAKAO_API_KEY"]
    KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]
    DATA_GO_KR_KEY = urllib.parse.unquote(st.secrets["DATA_GO_KR_API_KEY"])
    st.success("✅ Secrets에서 API 키를 성공적으로 불러왔습니다.")
except Exception as e:
    st.error(f"❌ API 키를 불러오는 중 오류 발생: {e}")
    st.stop()

st.divider()

# 2. 공공데이터포털 실거래가 API 테스트
st.subheader("1️⃣ 공공데이터포털 실거래가 API 테스트")
url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
# 강남구(11680), 2023년 12월 데이터 요청
params = {"serviceKey": DATA_GO_KR_KEY, "pageNo": "1", "numOfRows": "5", "LAWD_CD": "11680", "DEAL_YMD": "202312"}
try:
    res = requests.get(url, params=params, timeout=10)
    if res.status_code == 200:
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        if items:
            st.success(f"✅ 공공데이터 정상 수신! (예시: {items[0].findtext('aptNm')} 아파트)")
        else:
            st.warning("⚠️ 데이터는 수신했으나 해당 월에 거래 내역이 없습니다. (또는 키 권한 문제)")
            st.write("응답 내용:", res.text[:200])
    else:
        st.error(f"❌ API 호출 실패 (상태 코드: {res.status_code})")
except Exception as e:
    st.error(f"❌ 에러 발생: {e}")

st.divider()

# 3. 카카오 REST API (좌표 변환) 테스트
st.subheader("2️⃣ 카카오 REST API (좌표 변환) 테스트")
headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
try:
    res_kakao = requests.get("https://dapi.kakao.com/v2/local/search/address.json", 
                             headers=headers, params={"query": "서울특별시 강남구 테헤란로 152"}).json()
    if res_kakao.get('documents'):
        lat = res_kakao['documents'][0]['y']
        lng = res_kakao['documents'][0]['x']
        st.success(f"✅ 좌표 변환 성공! (위도: {lat}, 경도: {lng})")
    else:
        st.error("❌ 주소를 찾을 수 없거나 REST API 키가 잘못되었습니다.")
except Exception as e:
    st.error(f"❌ 에러 발생: {e}")

st.divider()

# 4. 카카오 JS API (지도 렌더링) 테스트
st.subheader("3️⃣ 카카오 JS API (지도 렌더링) 테스트")
st.info("💡 아래에 지도가 보이지 않는다면 카카오 디벨로퍼스 'Web 플랫폼'에 http://localhost:8501 이 등록되지 않은 것입니다.")

map_html = f"""
<div id="map" style="width:100%;height:400px;border:2px solid red;"></div>
<script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}"></script>
<script>
    var mapContainer = document.getElementById('map'),
        mapOption = {{ 
            center: new kakao.maps.LatLng(37.500, 127.036), 
            level: 3 
        }};
    var map = new kakao.maps.Map(mapContainer, mapOption);
</script>
"""
components.html(map_html, height=420)
