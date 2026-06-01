import streamlit as st
import requests
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import json
import pandas as pd

# 페이지 기본 설정 (넓게 쓰기)
st.set_page_config(page_title="30년차 전문가의 종합 입지 분석기", layout="wide")

# 시크릿 키 불러오기
try:
    KAKAO_REST_KEY = st.secrets["KAKAO_API_KEY"]
    KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]
    DATA_GO_KR_KEY = st.secrets["DATA_GO_KR_API_KEY"]
except KeyError:
    st.error("API 키가 설정되지 않았습니다. Streamlit Secrets 설정을 확인해주세요.")
    st.stop()

# 메인 타이틀
st.title("🏆 30년차 전문가의 종합 입지 분석기")
st.markdown("**부동산 실거래가**는 물론, 주변 **숨은 맛집**과 **캠핑장**까지 한 번에 분석해 드립니다.")

# 탭 생성 (3가지 기능 분리)
tab1, tab2, tab3 = st.tabs(["🏢 부동산 실거래가 지도", "🍽️ 만다라트 맛집 찾기", "🏕️ 주변 힐링 캠핑장"])

# --- 공통 함수: 카카오 키워드 검색 API ---
def search_kakao_keyword(query, radius=2000):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    params = {"query": query, "size": 15} # 15개까지 검색
    try:
        response = requests.get(url, headers=headers, params=params)
        return response.json().get('documents', [])
    except:
        return []

# ==========================================
# 탭 1: 부동산 실거래가 지도 (기존 기능 유지 및 개선)
# ==========================================
with tab1:
    st.subheader("📍 아파트 실거래가 조회")
    col1, col2 = st.columns(2)
    with col1:
        lawd_cd = st.selectbox(
            "지역 선택",
            options=["11680", "11710", "41135", "26350"],
            format_func=lambda x: {"11680":"서울 강남구", "11710":"서울 송파구", "41135":"경기 성남 분당구", "26350":"부산 해운대구"}[x]
        )
    with col2:
        deal_ym = st.text_input("계약 연월 (YYYYMM)", value="202312")

    if st.button("지도에 아파트 띄우기", key="apt_btn"):
        with st.spinner("국토교통부 데이터를 불러오는 중입니다..."):
            url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
            params = {
                "serviceKey": DATA_GO_KR_KEY,
                "pageNo": "1", "numOfRows": "30",
                "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ym
            }
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.content)
                    items = root.findall('.//item')
                    map_data = []
                    
                    for item in items:
                        apt_name = item.findtext('aptNm')
                        price = item.findtext('dealAmount').strip()
                        dong = item.findtext('umdNm')
                        jibun = item.findtext('jibun')
                        full_address = f"{dong} {jibun}"
                        
                        # 주소 -> 좌표 변환
                        addr_url = "https://dapi.kakao.com/v2/local/search/address.json"
                        addr_res = requests.get(addr_url, headers={"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}, params={"query": full_address}).json()
                        
                        if addr_res['documents']:
                            lat = float(addr_res['documents'][0]['y'])
                            lng = float(addr_res['documents'][0]['x'])
                            map_data.append({"apt_name": apt_name, "price": price, "lat": lat, "lng": lng})
                    
                    if map_data:
                        map_html = f"""
                        <!DOCTYPE html>
                        <html><head><meta charset="utf-8"></head><body>
                        <div id="map" style="width:100%;height:500px;border-radius:10px;"></div>
                        <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}"></script>
                        <script>
                            var mapContainer = document.getElementById('map'),
                                mapOption = {{ center: new kakao.maps.LatLng({map_data[0]['lat']}, {map_data[0]['lng']}), level: 5 }};
                            var map = new kakao.maps.Map(mapContainer, mapOption);
                            var data = {json.dumps(map_data)};
                            var bounds = new kakao.maps.LatLngBounds();
                            
                            for (var i = 0; i < data.length; i ++) {{
                                var position = new kakao.maps.LatLng(data[i].lat, data[i].lng);
                                var marker = new kakao.maps.Marker({{ map: map, position: position }});
                                bounds.extend(position);
                                
                                var content = '<div style="padding:10px;font-size:14px;"><b>' + data[i].apt_name + '</b><br>💰 ' + data[i].price + '만원</div>';
                                var infowindow = new kakao.maps.InfoWindow({{ content: content, removable: true }});
                                
                                (function(marker, infowindow) {{
                                    kakao.maps.event.addListener(marker, 'click', function() {{ infowindow.open(map, marker); }});
                                }})(marker, infowindow);
                            }}
                            map.setBounds(bounds);
                        </script>
                        </body></html>
                        """
                        components.html(map_html, height=520)
                    else:
                        st.warning("데이터가 없습니다.")
                except Exception as e:
                    st.error("데이터 파싱 오류가 발생했습니다.")
            else:
                st.error("공공데이터포털 서버 오류입니다.")

# ==========================================
# 탭 2: 만다라트 맛집 찾기 (카테고리별 검색)
# ==========================================
with tab2:
    st.subheader("🍽️ 동네 찐 맛집 탐색기")
    st.write("원하는 지역을 입력하고, 당기는 메뉴를 클릭하세요!")
    
    food_address = st.text_input("검색할 동네 입력 (예: 강남역, 판교동, 해운대)", value="강남역")
    
    # 만다라트 느낌의 버튼 UI 구성
    st.markdown("### 🎯 메뉴를 선택하세요")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    selected_category = None
    if c1.button("🍚 든든한 한식", use_container_width=True): selected_category = "한식"
    if c2.button("🍜 불맛 중식", use_container_width=True): selected_category = "중식"
    if c3.button("🍣 깔끔한 일식", use_container_width=True): selected_category = "일식"
    if c4.button("🍝 분위기 양식", use_container_width=True): selected_category = "양식"
    if c5.button("☕ 감성 카페", use_container_width=True): selected_category = "카페"

    if selected_category and food_address:
        search_query = f"{food_address} {selected_category} 맛집"
        st.markdown(f"**'{search_query}'** 검색 결과입니다. (카카오맵 리뷰를 확인해보세요!)")
        
        places = search_kakao_keyword(search_query)
        
        if places:
            for place in places:
                with st.container():
                    st.markdown(f"""
                    <div style='padding:15px; border:1px solid #ddd; border-radius:10px; margin-bottom:10px;'>
                        <h4 style='margin:0; color:#0052A4;'>{place['place_name']} <span style='font-size:14px; color:gray;'>({place['category_group_name']})</span></h4>
                        <p style='margin:5px 0;'>📍 {place['road_address_name'] or place['address_name']}</p>
                        <p style='margin:5px 0;'>📞 {place['phone'] or '전화번호 없음'}</p>
                        <a href='{place['place_url']}' target='_blank' style='text-decoration:none; background-color:#FEE500; color:black; padding:5px 10px; border-radius:5px; font-weight:bold; font-size:14px;'>⭐ 카카오맵에서 별점/리뷰 보기</a>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("검색 결과가 없습니다.")

# ==========================================
# 탭 3: 주변 힐링 캠핑장 찾기
# ==========================================
with tab3:
    st.subheader("🏕️ 주말엔 자연으로! 캠핑장 찾기")
    camp_address = st.text_input("캠핑장을 찾고 싶은 지역 (예: 가평, 포천, 양평)", value="가평")
    
    if st.button("캠핑장 검색하기", key="camp_btn"):
        search_query = f"{camp_address} 캠핑장"
        places = search_kakao_keyword(search_query)
        
        if places:
            # 데이터를 표(DataFrame) 형태로 깔끔하게 보여주기
            camp_list = []
            for p in places:
                camp_list.append({
                    "캠핑장 이름": p['place_name'],
                    "주소": p['road_address_name'] or p['address_name'],
                    "전화번호": p['phone'],
                    "상세보기": p['place_url']
                })
            
            df = pd.DataFrame(camp_list)
            
            # Streamlit의 dataframe 기능을 사용하여 링크 클릭이 가능하게 설정
            st.dataframe(
                df,
                column_config={
                    "상세보기": st.column_config.LinkColumn("카카오맵 링크", display_text="지도 보기")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("해당 지역에 검색된 캠핑장이 없습니다.")
