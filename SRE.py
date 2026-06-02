import streamlit as st

st.title("카카오 정적 지도(이미지) 테스트")

# REST API 키가 필요합니다. (JavaScript 키 아님)
# 카카오 디벨로퍼스 -> 내 애플리케이션 -> 앱 키 -> REST API 키
rest_api_key = st.secrets["KAKAO_REST_API_KEY"] 

# 서울시청 좌표
lat = 37.566826
lng = 126.9786567

# 카카오 Static Map 이미지 URL
map_image_url = f"https://dapi.kakao.com/v2/maps/staticmap?appkey={rest_api_key}&center={lng},{lat}&level=3&w=700&h=500"

# 이미지로 지도 출력
st.image(map_image_url, caption="카카오 정적 지도")
