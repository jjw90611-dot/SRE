import streamlit as st
import streamlit.components.v1 as components

st.title("카카오 맵 테스트")

# 1. Streamlit Secrets에서 API 키 불러오기
try:
    kakao_api_key = st.secrets["KAKAO_API_KEY"]
except KeyError:
    st.error("Streamlit Cloud Secrets에 'KAKAO_API_KEY'가 설정되지 않았습니다.")
    st.stop()

# 2. 카카오맵 HTML 코드 (autoload=false 및 kakao.maps.load 적용)
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <!-- 파이썬에서 불러온 API 키를 주입하고 autoload=false 설정 -->
    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_api_key}&autoload=false"></script>
</head>
<body>
    <div id="map" style="width:100%;height:400px;"></div>
    <script>
        // 카카오맵 SDK가 완전히 로드된 후 실행되도록 보장
        kakao.maps.load(function() {{
            var container = document.getElementById('map');
            var options = {{
                center: new kakao.maps.LatLng(37.566826, 126.9786567), // 기본 좌표 (서울시청)
                level: 3
            }};
            var map = new kakao.maps.Map(container, options);
        }});
    </script>
</body>
</html>
"""

# 3. Streamlit 화면에 HTML 렌더링
components.html(map_html, height=450)
