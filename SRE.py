import streamlit as st
import streamlit.components.v1 as components

st.title("카카오 맵 테스트")

# Secrets에서 키 가져오기
api_key = st.secrets["KAKAO_API_KEY"]

# 지도만 띄우는 가장 단순하고 확실한 HTML/JS 코드
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body>
    <div id="map" style="width:100%;height:400px;"></div>
    
    <script>
        // 1. 스크립트 동적 로드 (Streamlit 환경에서 가장 안전한 방식)
        var script = document.createElement('script');
        script.src = "https://dapi.kakao.com/v2/maps/sdk.js?appkey={api_key}&autoload=false";
        document.head.appendChild(script);

        // 2. 스크립트 로드가 끝나면 지도 그리기
        script.onload = function() {{
            kakao.maps.load(function() {{
                var mapContainer = document.getElementById('map');
                var mapOption = {{
                    center: new kakao.maps.LatLng(37.566826, 126.9786567), // 서울시청 좌표
                    level: 3
                }};
                var map = new kakao.maps.Map(mapContainer, mapOption);
            }});
        }};
    </script>
</body>
</html>
"""

# 화면에 출력
components.html(map_html, height=450)
