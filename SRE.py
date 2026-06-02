import streamlit as st
import pandas as pd
import pydeck as pdk

st.title("호갱노노 스타일: 3D 부동산 데이터 지도")

# 1. 가상의 부동산 가격 데이터 (price가 높을수록 기둥이 높아짐)
df = pd.DataFrame({
    "lat": [37.5668, 37.5658, 37.5568, 37.5468, 37.5768],
    "lon": [126.9786, 126.9886, 126.9786, 126.9986, 126.9686],
    "price": [1000, 2500, 800, 3000, 1500], # 가격 (단위: 만원 등)
    "name": ["시청역", "을지로", "서울역", "동대문", "서대문"]
})

# 2. 3D 기둥(Column) 레이어 설정
layer = pdk.Layer(
    "ColumnLayer",
    data=df,
    get_position='[lon, lat]',
    get_elevation='price',      # 높이를 가격으로 설정
    elevation_scale=1.5,        # 기둥 높이 배율
    radius=150,                 # 기둥 굵기
    get_fill_color='[255, 75, 75, 200]', # 호갱노노 스타일의 붉은색
    pickable=True,
    auto_highlight=True,
)

# 3. 지도 초기 시점 설정 (pitch로 3D 기울기 설정)
view_state = pdk.ViewState(
    latitude=37.5668,
    longitude=126.9786,
    zoom=12,
    pitch=45, # 지도를 45도 기울여서 3D로 보이게 함
)

# 4. 화면에 출력 (마우스 오버 시 툴팁 표시)
r = pdk.Deck(
    layers=[layer], 
    initial_view_state=view_state, 
    tooltip={"text": "{name}\n가격 지수: {price}"}
)
st.pydeck_chart(r)
