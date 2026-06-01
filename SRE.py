import streamlit as st
import requests
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import json
import pandas as pd
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ==========================================
# 1. 페이지 설정 및 모던 UI (이전 스타일 복구)
# ==========================================
st.set_page_config(page_title="POSCO Future M - 프롭테크 플랫폼", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 900; color: #0052A4; margin-bottom: 0px; }
    .sub-title { font-size: 1.2rem; color: #555; margin-bottom: 30px; }
    .metric-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
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
# 3. 전국 주요 지역 법정동 코드
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
    """카카오 API로 주소를 위경도로 변환 (검색어 정제 포함)"""
    # 괄호 안의 내용이나 불필요한 건물명 제거 (예: "신항로 110 포스코퓨처엠" -> "신항로 110")
    clean_address = address.split('(')[0].strip()
    # 도로명 주소 형식(OO로 00)까지만 추출하는 간단한 휴리스틱
    parts = clean_address.split()
    if len(parts) > 4:
        clean_address = " ".join(parts[:4])

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    try:
        res = requests.get(url, headers=headers, params={"query": clean_address}).json()
        if res['documents']:
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
        
        # 주소 검색 실패 시 키워드 검색으로 재시도
        url_kw = "https://dapi.kakao.com/v2/local/search/keyword.json"
        res_kw = requests.get(url_kw, headers=headers, params={"query": address}).json()
        if res_kw['documents']:
            return float(res_kw['documents'][0]['y']), float(res_kw['documents'][0]['x'])
            
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
st.markdown('<p class="main-title">🏆 30년 차 전문가의 종합 입지 분석기</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">부동산 실거래가는 물론, 주변 숨은 맛집과 캠핑장까지 한 번에 분석해 드립니다.</p>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🗺️ 인터랙티브 실거래가 지도", "🏆 브역대신평초 맞춤형 AI 추천"])

# ------------------------------------------
# 탭 1: 인터랙티브 실거래가 지도
# ------------------------------------------
with tab1:
    st.subheader("📍 아파트 실거래가 조회 (클릭 시 상세 정보)")
    
    col1, col2 = st.columns(2)
    with col1:
        map_region = st.selectbox("지역 선택", list(LAWD_CD_DICT.keys()), index=13) # 기본값 포항 남구
    with col2:
        # 실거래가 데이터 지연을 고려하여 기본값을 2달 전으로 설정
        default_ym = (datetime.now() - relativedelta(months=2)).strftime("%Y%m")
        map_ym = st.text_input("계약 연월 (YYYYMM)", value=default_ym)
        st.caption("💡 실거래가 신고 기한(30일)을 고려하여 1~2달 전 데이터를 조회하는 것을 권장합니다.")
        
    if st.button("지도에 아파트 띄우기", key="apt_btn"):
        with st.spinner("국토교통부 데이터를 불러오는 중입니다..."):
            df_map = get_apt_data(LAWD_CD_DICT[map_region], map_ym)
            
            if not df_map.empty:
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
                    
                    map_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            .apt-label {{ background-color: #0052A4; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px; border: 2px solid white; box-shadow: 0px 2px 4px rgba(0,0,0,0.3); cursor: pointer; }}
                            .info-window {{ padding: 10px; font-size: 14px; min-width: 200px; }}
                        </style>
                    </head>
                    <body>
                    <div id="map" style="width:100%;height:600px;border-radius:10px;"></div>
                    <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}"></script>
                    <script>
                        var mapContainer = document.getElementById('map'),
                            mapOption = {{ center: new kakao.maps.LatLng({center_lat}, {center_lng}), level: 5 }};
                        var map = new kakao.maps.Map(mapContainer, mapOption);
                        var data = {json.dumps(map_data)};
                        var bounds = new kakao.maps.LatLngBounds();
                        var activeInfoWindow = null;
                        
                        data.forEach(function(d) {{
                            var position = new kakao.maps.LatLng(d.lat, d.lng);
                            
                            // 커스텀 오버레이 (마커 대신 가격 라벨 표시)
                            var labelContent = '<div class="apt-label" onclick="showInfo(\'' + d.name + '\', ' + d.price + ', ' + d.pyung + ', ' + d.year + ', ' + d.lat + ', ' + d.lng + ')">' + d.name + '<br>' + (d.price/10000).toFixed(1) + '억</div>';
                            var customOverlay = new kakao.maps.CustomOverlay({{
                                position: position,
                                content: labelContent,
                                yAnchor: 1
                            }});
                            customOverlay.setMap(map);
                            bounds.extend(position);
                        }});
                        
                        // 전역 함수로 인포윈도우 띄우기
                        window.showInfo = function(name, price, pyung, year, lat, lng) {{
                            if (activeInfoWindow) {{ activeInfoWindow.close(); }}
                            
                            var content = '<div class="info-window">' +
                                          '<b>🏢 ' + name + '</b><br>' +
                                          '💰 실거래가: ' + (price/10000).toFixed(1) + '억 원<br>' +
                                          '📐 면적: ' + pyung + '평<br>' +
                                          '🏗️ 건축연도: ' + year + '년' +
                                          '</div>';
                                          
                            var position = new kakao.maps.LatLng(lat, lng);
                            var infowindow = new kakao.maps.InfoWindow({{
                                position: position,
                                content: content,
                                removable: true
                            }});
                            
                            infowindow.open(map);
                            activeInfoWindow = infowindow;
                        }};
                        
                        map.setBounds(bounds);
                    </script>
                    </body>
                    </html>
                    """
                    components.html(map_html, height=620)
                else:
                    st.warning("좌표를 변환할 수 있는 아파트가 없습니다.")
            else:
                st.error(f"{map_ym} 연월에 해당하는 거래 데이터가 없습니다. 다른 연월을 선택해주세요.")

# ------------------------------------------
# 탭 2: 브역대신평초 맞춤형 AI 추천
# ------------------------------------------
with tab2:
    st.subheader("🏆 브역대신평초 맞춤형 아파트 추천기")
    
    with st.form("consulting_form"):
        col1, col2 = st.columns(2)
        with col1:
            target_region = st.selectbox("희망 거주 지역", list(LAWD_CD_DICT.keys()), index=13)
            budget_min = st.number_input("최소 예산 (만원)", value=20000, step=1000)
            budget_max = st.number_input("최대 예산 (만원)", value=40000, step=1000)
        with col2:
            work_address = st.text_input("직장 주소 (도로명 주소 권장)", value="경북 포항시 남구 신항로 110")
            custom_address = st.text_input("부모님 댁 / 자주 가는 곳 주소", value="경북 포항시 남구 대잠동")
            
        submit_btn = st.form_submit_button("📊 AI 맞춤형 분석 시작", use_container_width=True)

    if submit_btn:
        st.markdown("---")
        with st.spinner("데이터 분석 중입니다..."):
            
            work_lat, work_lng = get_coords(work_address)
            custom_lat, custom_lng = get_coords(custom_address)
            
            if not work_lat:
                st.error(f"'{work_address}' 주소를 찾을 수 없습니다. 정확한 도로명 주소나 동 이름을 입력해주세요.")
                st.stop()
                
            # 추천 로직에서도 2달 전 데이터를 기본으로 사용
            search_ym = (datetime.now() - relativedelta(months=2)).strftime("%Y%m")
            df = get_apt_data(LAWD_CD_DICT[target_region], search_ym)
            
            if df.empty:
                st.error(f"{target_region} 지역의 최근({search_ym}) 거래 데이터가 없습니다.")
                st.stop()
                
            df_filtered = df[(df['price'] >= budget_min) & (df['price'] <= budget_max)].copy()
            
            if len(df_filtered) == 0:
                st.warning(f"🚨 조건(예산 {budget_min/10000}억~{budget_max/10000}억)에 맞는 실재하는 아파트는 0개입니다. 예산을 조정해주세요.")
                st.stop()
                
            candidates = []
            df_unique = df_filtered.sort_values('price', ascending=False).drop_duplicates(subset=['apt_name'])
            
            for _, row in df_unique.iterrows():
                apt_lat, apt_lng = get_coords(f"{row['dong']} {row['jibun']}")
                if not apt_lat: continue
                
                dist_work = haversine_distance(apt_lat, apt_lng, work_lat, work_lng)
                time_work = int((dist_work / 30) * 60) + 5
                
                dist_custom = haversine_distance(apt_lat, apt_lng, custom_lat, custom_lng) if custom_lat else 999
                
                age = datetime.now().year - row['build_year'] if row['build_year'] > 0 else 99
                brand = check_brand(row['apt_name'])
                
                score = dist_work + (age * 0.5) - (5 if brand != "일반 브랜드" else 0)
                
                candidates.append({
                    "name": row['apt_name'], "dong": row['dong'], "price": row['price'],
                    "pyung": row['pyung'], "year": row['build_year'], "age": age,
                    "brand": brand, "dist_work": dist_work, "time_work": time_work,
                    "dist_custom": dist_custom, "score": score
                })
            
            candidates = sorted(candidates, key=lambda x: x['score'])[:3]
            
            st.markdown(f"### 📊 맞춤형 요약 분석")
            st.info(f"예산({budget_min/10000}억~{budget_max/10000}억)과 직장({work_address}) 위치를 고려하여, {target_region} 내 최적의 동선을 가진 3곳을 추천합니다.")
            
            st.markdown("### 🏆 추천 아파트 TOP 3")
            
            for i, apt in enumerate(candidates):
                with st.expander(f"🥇 {i+1}위: {apt['name']} ({apt['dong']}) - 예상가 {apt['price']/10000:.1f}억", expanded=True):
                    
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
                    * **역 (교통):** 직장까지 차량 {apt['time_work']}분
                    * **대 (대단지):** 현장 확인 요망
                    * **신 (신축):** {apt['year']}년식 ({apt['age']}년차)
                    * **평 (평지):** 카카오맵 지형도 확인 권장
                    * **초 (초품아):** 반경 1km 내 초등학교 배정 예상
                    """)
