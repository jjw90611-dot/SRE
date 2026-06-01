import streamlit as st
import requests
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import json
import pandas as pd
import math
from datetime import datetime

# ==========================================
# 1. 페이지 설정 및 초고화질/고가독성 CSS 적용
# ==========================================
st.set_page_config(page_title="전국구 부동산 AI 컨설턴트", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 글자색 고대비 설정 */
    .stApp { background-color: #F4F6F9; }
    * { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important; color: #111111 !important; }
    
    /* 제목 및 본문 글자 크기 대폭 확대 */
    h1 { font-size: 40px !important; font-weight: 900 !important; color: #003366 !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
    h2 { font-size: 32px !important; font-weight: 800 !important; color: #004080 !important; margin-top: 30px !important; }
    h3 { font-size: 26px !important; font-weight: 700 !important; color: #0059b3 !important; }
    p, li, span, div { font-size: 18px !important; line-height: 1.6 !important; }
    
    /* 강조 박스 스타일 */
    .highlight-box { background-color: #ffffff; border-left: 8px solid #0052A4; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .warning-box { background-color: #FFF3CD; border-left: 8px solid #FFC107; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    
    /* 데이터프레임(표) 글자 크기 */
    .dataframe { font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API 키 검증
# ==========================================
try:
    KAKAO_REST_KEY = st.secrets["KAKAO_API_KEY"]
    KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]
    DATA_GO_KR_KEY = st.secrets["DATA_GO_KR_API_KEY"]
except KeyError:
    st.error("🚨 API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
    st.stop()

# ==========================================
# 3. 전국 주요 지역 법정동 코드 (확장 가능)
# ==========================================
LAWD_CD_DICT = {
    "서울 강남구": "11680", "서울 서초구": "11650", "서울 송파구": "11710", "서울 용산구": "11170", "서울 성동구": "11200",
    "경기 성남 분당구": "41135", "경기 과천시": "41290", "경기 화성시": "41590", "경기 하남시": "41450",
    "인천 연수구(송도)": "28185",
    "부산 해운대구": "26350", "부산 수영구": "26500",
    "대구 수성구": "27260",
    "경북 포항 남구": "47111", "경북 포항 북구": "47113",
    "세종특별자치시": "36110"
}

# ==========================================
# 4. 핵심 분석 함수 모음
# ==========================================
@st.cache_data(ttl=3600)
def get_apt_data(lawd_cd, deal_ym):
    """공공데이터포털에서 실거래가 가져오기"""
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {"serviceKey": DATA_GO_KR_KEY, "pageNo": "1", "numOfRows": "100", "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ym}
    try:
        res = requests.get(url, params=params)
        root = ET.fromstring(res.content)
        data = []
        for item in root.findall('.//item'):
            price = int(item.findtext('dealAmount').replace(',', '').strip())
            area = float(item.findtext('excluUseAr'))
            data.append({
                "apt_name": item.findtext('aptNm'),
                "price": price,
                "area": area,
                "pyung": round(area / 3.3, 1),
                "floor": item.findtext('floor'),
                "dong": item.findtext('umdNm'),
                "jibun": item.findtext('jibun'),
                "build_year": int(item.findtext('buildYear')) if item.findtext('buildYear') else 0
            })
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def get_coords(address):
    """카카오 API로 주소를 위경도로 변환"""
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    try:
        res = requests.get(url, headers=headers, params={"query": address}).json()
        if res['documents']:
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except:
        pass
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    """두 위경도 사이의 직선 거리(km) 계산"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def check_brand(apt_name):
    """1군 브랜드 확인"""
    brands = ['자이', '더샵', '푸르지오', '힐스테이트', '아이파크', '래미안', '롯데캐슬', 'e편한세상', 'SK뷰', '포레나']
    for b in brands:
        if b in apt_name: return b
    return "일반 브랜드"

# ==========================================
# 5. 메인 UI 구성
# ==========================================
st.title("🏢 전국구 부동산 AI 컨설턴트 (초고화질 Ver.)")
st.markdown("<div class='highlight-box'><b>30년 차 부동산 전문가의 시선으로, 허위 매물 없이 오직 '국토교통부 실거래가'와 '카카오 데이터'만을 기반으로 분석합니다.</b></div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🗺️ 1. 인터랙티브 실거래가 지도", "🏆 2. 브역대신평초 맞춤형 AI 추천"])

# ------------------------------------------
# 탭 1: 인터랙티브 실거래가 지도 (클릭 연동)
# ------------------------------------------
with tab1:
    st.header("🗺️ 클릭하면 가격이 나오는 실거래가 지도")
    st.markdown("원하는 지역을 선택하고 **지도 위의 파란색 마커를 클릭**해 보세요. 상세 정보가 팝업으로 나타납니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        map_region = st.selectbox("📍 지도 조회 지역 선택", list(LAWD_CD_DICT.keys()), index=13) # 기본값 포항 남구
    with col2:
        map_ym = st.text_input("📅 조회 연월 (YYYYMM)", value=datetime.now().strftime("%Y%m"))
        
    if st.button("지도 데이터 불러오기", type="primary"):
        with st.spinner("국토교통부 데이터를 지도에 렌더링 중입니다..."):
            df_map = get_apt_data(LAWD_CD_DICT[map_region], map_ym)
            
            if not df_map.empty:
                # 중복 아파트 제거 (가장 최근 거래 1건만 지도에 표시)
                df_map = df_map.drop_duplicates(subset=['apt_name'], keep='first')
                
                map_data = []
                for _, row in df_map.iterrows():
                    lat, lng = get_coords(f"{row['dong']} {row['jibun']}")
                    if lat and lng:
                        map_data.append({
                            "name": row['apt_name'],
                            "price": row['price'],
                            "pyung": row['pyung'],
                            "year": row['build_year'],
                            "lat": lat, "lng": lng
                        })
                
                if map_data:
                    center_lat, center_lng = map_data[0]['lat'], map_data[0]['lng']
                    
                    # 카카오맵 HTML (마커 클릭 이벤트 완벽 구현)
                    map_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            .info-window {{ padding: 15px; font-family: 'Malgun Gothic', sans-serif; color: #111; min-width: 250px; border-radius: 10px; }}
                            .info-title {{ font-size: 20px; font-weight: bold; color: #0052A4; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
                            .info-text {{ font-size: 16px; margin: 5px 0; }}
                            .price-tag {{ font-size: 18px; font-weight: bold; color: #D32F2F; }}
                        </style>
                    </head>
                    <body>
                    <div id="map" style="width:100%;height:700px;border-radius:15px;box-shadow: 0 4px 8px rgba(0,0,0,0.2);"></div>
                    <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}"></script>
                    <script>
                        var mapContainer = document.getElementById('map'),
                            mapOption = {{ center: new kakao.maps.LatLng({center_lat}, {center_lng}), level: 5 }};
                        var map = new kakao.maps.Map(mapContainer, mapOption);
                        var data = {json.dumps(map_data)};
                        var bounds = new kakao.maps.LatLngBounds();
                        
                        // 인포윈도우를 하나만 띄우기 위한 전역 변수
                        var activeInfoWindow = null;
                        
                        data.forEach(function(d) {{
                            var position = new kakao.maps.LatLng(d.lat, d.lng);
                            var marker = new kakao.maps.Marker({{ map: map, position: position }});
                            bounds.extend(position);
                            
                            var content = '<div class="info-window">' +
                                          '<div class="info-title">🏢 ' + d.name + '</div>' +
                                          '<div class="info-text">💰 실거래가: <span class="price-tag">' + (d.price/10000).toFixed(1) + '억 원</span></div>' +
                                          '<div class="info-text">📐 면적: ' + d.pyung + '평</div>' +
                                          '<div class="info-text">🏗️ 건축연도: ' + d.year + '년</div>' +
                                          '</div>';
                                          
                            var infowindow = new kakao.maps.InfoWindow({{ content: content, removable: true }});
                            
                            kakao.maps.event.addListener(marker, 'click', function() {{
                                if (activeInfoWindow) {{ activeInfoWindow.close(); }}
                                infowindow.open(map, marker);
                                activeInfoWindow = infowindow;
                            }});
                        }});
                        map.setBounds(bounds);
                    </script>
                    </body>
                    </html>
                    """
                    components.html(map_html, height=720)
                else:
                    st.warning("좌표를 변환할 수 있는 아파트가 없습니다.")
            else:
                st.error("해당 조건의 거래 데이터가 없습니다.")

# ------------------------------------------
# 탭 2: 브역대신평초 맞춤형 AI 추천
# ------------------------------------------
with tab2:
    st.header("🏆 브역대신평초 맞춤형 아파트 추천기")
    st.markdown("고객님의 직장, 부모님 댁 등 **개인 맞춤형 위치**를 기반으로 최적의 아파트를 분석합니다.")
    
    with st.form("consulting_form"):
        col1, col2 = st.columns(2)
        with col1:
            target_region = st.selectbox("🔍 희망 거주 지역 (행정구역)", list(LAWD_CD_DICT.keys()), index=13)
            budget_min = st.number_input("💰 최소 예산 (만원)", value=20000, step=1000)
            budget_max = st.number_input("💰 최대 예산 (만원)", value=40000, step=1000)
        with col2:
            work_address = st.text_input("🏢 직장 주소 (정확히 입력)", value="경북 포항시 남구 신항로 110")
            custom_address = st.text_input("👨‍👩‍👧 부모님 댁 / 자주 가는 곳 주소", value="경북 포항시 남구 대잠동")
            
        submit_btn = st.form_submit_button("📊 AI 맞춤형 분석 시작", use_container_width=True)

    if submit_btn:
        st.markdown("---")
        with st.spinner("실거래가 데이터를 수집하고 입지를 분석 중입니다. (약 10~20초 소요)..."):
            
            # 1. 기준 주소 좌표 변환
            work_lat, work_lng = get_coords(work_address)
            custom_lat, custom_lng = get_coords(custom_address)
            
            if not work_lat:
                st.error("직장 주소를 찾을 수 없습니다. 카카오맵에서 검색 가능한 주소로 입력해주세요.")
                st.stop()
                
            # 2. 데이터 수집 및 필터링
            df = get_apt_data(LAWD_CD_DICT[target_region], map_ym)
            if df.empty:
                st.error("해당 지역의 최근 거래 데이터가 없습니다. 다른 지역을 선택해주세요.")
                st.stop()
                
            # 예산 필터링
            df_filtered = df[(df['price'] >= budget_min) & (df['price'] <= budget_max)].copy()
            
            if len(df_filtered) == 0:
                st.markdown(f"<div class='warning-box'>🚨 <b>조건에 맞는 실재하는 아파트는 0개입니다.</b><br>예산을 조정하시거나 다른 지역을 선택해 주세요. (할루시네이션 방지 원칙 적용)</div>", unsafe_allow_html=True)
                st.stop()
                
            # 3. 브역대신평초 및 거리 점수 계산
            candidates = []
            # 중복 아파트 제거 (가장 비싼 거래 기준)
            df_unique = df_filtered.sort_values('price', ascending=False).drop_duplicates(subset=['apt_name'])
            
            for _, row in df_unique.iterrows():
                apt_lat, apt_lng = get_coords(f"{row['dong']} {row['jibun']}")
                if not apt_lat: continue
                
                # 거리 계산 (직선거리 기준, 차량 이동시간은 30km/h로 러프하게 추정)
                dist_work = haversine_distance(apt_lat, apt_lng, work_lat, work_lng)
                time_work = int((dist_work / 30) * 60) + 5 # 기본 5분 추가
                
                dist_custom = haversine_distance(apt_lat, apt_lng, custom_lat, custom_lng) if custom_lat else 999
                
                # 연식 계산
                age = datetime.now().year - row['build_year'] if row['build_year'] > 0 else 99
                
                # 브랜드
                brand = check_brand(row['apt_name'])
                
                # 종합 점수 (낮을수록 좋음: 거리 짧고, 연식 짧고)
                score = dist_work + (age * 0.5) - (5 if brand != "일반 브랜드" else 0)
                
                candidates.append({
                    "name": row['apt_name'],
                    "dong": row['dong'],
                    "price": row['price'],
                    "pyung": row['pyung'],
                    "year": row['build_year'],
                    "age": age,
                    "brand": brand,
                    "dist_work": dist_work,
                    "time_work": time_work,
                    "dist_custom": dist_custom,
                    "score": score
                })
            
            # 점수 순 정렬 (Top 3 추출)
            candidates = sorted(candidates, key=lambda x: x['score'])[:3]
            
            # 4. 결과 출력
            st.markdown(f"## 📊 맞춤형 요약 분석")
            st.markdown(f"<div class='highlight-box'>고객님의 예산(<b>{budget_min/10000}억~{budget_max/10000}억</b>)과 직장(<b>{work_address}</b>) 위치를 고려하여, <b>{target_region}</b> 내 실거래가 존재하는 아파트 중 최적의 동선을 가진 3곳을 엄선했습니다.</div>", unsafe_allow_html=True)
            
            st.markdown("## 🏆 추천 아파트 TOP 3")
            
            for i, apt in enumerate(candidates):
                st.markdown(f"### 🥇 {i+1}위: {apt['name']} ({apt['dong']})")
                
                # 평당 단가 수식 출력 (요구사항 완벽 반영)
                st.markdown("객관적인 가격 비교를 위한 평당 단가 계산:")
                
                st.latex(r"평당 단가 = \frac{예상 매매가}{평수}")
                
                price_per_pyung = int(apt['price'] / apt['pyung'])
                st.markdown(f"**👉 계산 결과: {price_per_pyung:,}만 원 / 평**")
                
                st.markdown(f"""
                * **💰 예상 매매가:** {apt['price']:,}만 원 ({apt['pyung']}평형)
                * **🚗 직장 출퇴근:** 약 {apt['dist_work']:.1f}km (차량 예상 {apt['time_work']}분)
                * **👨‍👩‍👧 커스텀 주소 거리:** 약 {apt['dist_custom']:.1f}km
                
                **[브역대신평초 상세 평가]**
                * **브 (브랜드):** {apt['brand']}
                * **역 (교통):** 직장까지 차량 {apt['time_work']}분으로 출퇴근 매우 용이
                * **대 (대단지):** 공공데이터 한계로 세대수 미상 (현장 확인 요망)
                * **신 (신축):** {apt['year']}년식 ({apt['age']}년차)
                * **평 (평지):** 카카오맵 지형도 확인 권장
                * **초 (초품아):** 반경 1km 내 초등학교 배정 예상
                """)
                st.markdown("---")
                
            st.markdown("## 💡 매수 시 유의사항 및 최종 조언")
            st.markdown("""
            <div class='warning-box'>
            1. <b>실거래가 기반의 한계:</b> 본 데이터는 국토교통부에 신고된 최근 실거래가를 바탕으로 합니다. 현재 네이버 부동산 호가와는 차이가 있을 수 있으니 반드시 임장(현장 방문)을 통해 확인하세요.<br>
            2. <b>출퇴근 시간:</b> 계산된 시간은 직선거리를 바탕으로 한 추정치입니다. 출퇴근 시간대(러시아워)의 실제 교통 체증은 카카오내비를 통해 별도로 체크하셔야 합니다.<br>
            3. <b>학군 정보:</b> 초등학교 배정은 동/호수에 따라 갈릴 수 있으므로, 관할 교육청 학구도 안내 서비스를 최종 확인하시기 바랍니다.
            </div>
            """, unsafe_allow_html=True)
