import streamlit as st
import streamlit.components.v1 as components

st.title("카카오 맵 테스트")

# 1. Streamlit Secrets에서 API 키 불러오기
try:
    kakao_api_key = st.secrets["KAKAO_API_KEY"]
except KeyError:
    st.error("Streamlit Cloud Secrets에 'KAKAO_API_KEY'가 설정되지 않았습니다.")
    st.stop()

# 2. 카카오맵 HTML 코드 (동적 스크립트 로딩 방식)
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body>
    <div id="map" style="width:100%;height:400px;"></div>
    <script>
        // 1. 카카오맵 스크립트를 동적으로 생성하여 로드합니다.
        var script = document.createElement('script');
        script.src = "https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_api_key}&autoload=false";
        document.head.appendChild(script);

        // 2. 스크립트 다운로드가 '완전히 끝난 후(onload)' 지도를 실행합니다.
        script.onload = function() {{
            kakao.maps.load(function() {{
                var container = document.getElementById('map');
                var options = {{
                    center: new kakao.maps.LatLng(37.566826, 126.9786567),
                    level: 3
                }};
                var map = new kakao.maps.Map(container, options);
            }});
        }};
    </script>
</body>
</html>
"""

# 3. Streamlit 화면에 HTML 렌더링
components.html(map_html, height=450)
