import streamlit as st
import folium
from streamlit_folium import st_folium

st.title("Folium 지도 테스트")

# 1. 지도 객체 생성 (서울시청 좌표)
m = folium.Map(location=[37.566826, 126.9786567], zoom_start=15)

# 2. 마커 추가
folium.Marker(
    [37.566826, 126.9786567], 
    popup="서울시청", 
    tooltip="클릭해보세요"
).add_to(m)

# 3. Streamlit 화면에 출력
st_folium(m, width=700, height=500)
