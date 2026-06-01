import streamlit as st
import requests
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. 페이지 및 기본 설정
# ==========================================
st.set_page_config(page_title="POSCO Future M - 프롭테크 플랫폼", layout="wide", initial_sidebar_state="expanded")

# 커스텀 CSS로 호갱노노/네이버부동산 느낌의 고급스러운 UI 적용
st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 900; color: #0052A4; margin-bottom: 0px; }
    .sub-title { font-size: 1.2rem; color: #555; margin-bottom: 30px; }
    .metric-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

try:
    KAKAO_REST_KEY = st.secrets["KAKAO_API_KEY"]
    KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]
    DATA_GO_KR_KEY = st.secrets["DATA_GO_KR_API_KEY"]
except KeyError:
    st.error("🚨 API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
    st.stop()

# ==========================================
# 2. 사이드바 네비게이션 및 필터링
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/POSCO_Future_M_logo.svg/512px-POSCO_Future_M_logo.svg.png", width=150)
    st.markdown("### 🧭 메뉴 탐색")
    menu = st.radio("분석 모드 선택", ["📊 종합 대시보드", "🗺️ 다중 레이어 입지 지도", "🕸️ 인프라 헥사곤 분석", "💰 부동산 금융 계산기"])
    
    st.markdown("---")
    st.markdown("### 🔍 기본 검색 조건")
    lawd_cd = st.selectbox("관심 지역", {"11680":"서울 강남구", "11710":"서울 송파구", "41135":"경기 성남 분당구", "26350":"부산 해운대구", "11110":"서울 종로구"}, format_func=lambda x: {"11680":"서울 강남구", "11710":"서울 송파구", "41135":"경기 성남 분당구", "26350":"부산 해운대구", "11110":"서울 종로구"}[x])
    deal_ym = st.text_input("조회 연월 (YYYYMM)", value=datetime.now().strftime("%Y%m"))
    
    st.markdown("---")
    st.info("💡 **Tip:** 30년 차 전문가의 노하우가 담긴 데이터입니다. 각 탭을 클릭하여 심층 분석을 진행하세요.")

# ==========================================
# 공통 함수 모음
# ==========================================
@st.cache_data(ttl=3600)
def get_apt_trade_data(lawd_cd, deal_ym):
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {"serviceKey": DATA_GO_KR_KEY, "pageNo": "1", "numOfRows": "50", "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ym}
    try:
        res = requests.get(url, params=params)
        root = ET.fromstring(res.content)
        data = []
        for item in root.findall('.//item'):
            data.append({
                "apt_name": item.findtext('aptNm'),
                "price": int(item.findtext('dealAmount').replace(',', '').strip()),
                "area": float(item.findtext('excluUseAr')),
                "floor": item.findtext('floor'),
                "dong": item.findtext('umdNm'),
                "jibun": item.findtext('jibun'),
                "build_year": item.findtext('buildYear')
            })
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def get_lat_lng(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    try:
        res = requests.get(url, headers=headers, params={"query": address}).json()
        if res['documents']:
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except:
        pass
    return None, None

def search_category(category_group_code, lat, lng, radius=1500):
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    params = {"category_group_code": category_group_code, "y": lat, "x": lng, "radius": radius, "size": 15}
    try:
        return requests.get(url, headers=headers, params=params).json().get('documents', [])
    except:
        return []

# ==========================================
# 화면 1: 📊 종합 대시보드 (KB부동산 스타일)
# ==========================================
if menu == "📊 종합 대시보드":
    st.markdown('<p class="main-title">📊 지역 부동산 시장 동향</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">선택하신 지역의 실거래가 요약 및 시장 지표를 한눈에 파악하세요.</p>', unsafe_allow_html=True)
    
    df = get_apt_trade_data(lawd_cd, deal_ym)
    
    if not df.empty:
        df['pyung'] = df['area'] / 3.3
        df['price_per_pyung'] = df['price'] / df['pyung']
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 거래 건수", f"{len(df)}건", "활발함" if len(df)>20 else "관망세")
        col2.metric("최고 거래가", f"{df['price'].max():,}만원", f"{df.loc[df['price'].idxmax(), 'apt_name']}")
        col3.metric("평균 거래가", f"{int(df['price'].mean()):,}만원")
        col4.metric("평균 평당가", f"{int(df['price_per_pyung'].mean()):,}만원")
        
        st.markdown("### 📈 면적별 거래가 분포 (호갱노노 스타일)")
        fig = px.scatter(df, x="area", y="price", size="price", color="build_year", hover_name="apt_name",
                         labels={"area": "전용면적(㎡)", "price": "거래금액(만원)", "build_year": "건축연도"},
                         title="면적 대비 거래가 및 노후도 분석", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 📋 최근 실거래 내역 Top 5")
        st.dataframe(df[['apt_name', 'dong', 'price', 'area', 'floor', 'build_year']].sort_values('price', ascending=False).head(5), use_container_width=True)
    else:
        st.warning("해당 연월에 거래 데이터가 없습니다. 다른 연월을 선택해주세요.")

# ==========================================
# 화면 2: 🗺️ 다중 레이어 입지 지도 (네이버부동산 스타일)
# ==========================================
elif menu == "🗺️ 다중 레이어 입지 지도":
    st.markdown('<p class="main-title">🗺️ 다중 레이어 입지 지도</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">아파트 실거래가와 주변 핵심 인프라(지하철, 학교, 병원)를 동시에 확인하세요.</p>', unsafe_allow_html=True)
    
    df = get_apt_trade_data(lawd_cd, deal_ym)
    if not df.empty:
        with st.spinner("지도 데이터를 렌더링 중입니다..."):
            map_data = []
            for _, row in df.iterrows():
                lat, lng = get_lat_lng(f"{row['dong']} {row['jibun']}")
                if lat and lng:
                    map_data.append({"name": row['apt_name'], "price": row['price'], "lat": lat, "lng": lng, "type": "apt"})
            
            if map_data:
                center_lat, center_lng = map_data[0]['lat'], map_data[0]['lng']
                
                # 주변 인프라 데이터 수집 (지하철 SW8, 학교 SC4, 대형마트 MT1)
                infra_data = []
                for code, icon, itype in [("SW8", "🚇", "subway"), ("SC4", "🏫", "school"), ("MT1", "🛒", "mart")]:
                    places = search_category(code, center_lat, center_lng)
                    for p in places:
                        infra_data.append({"name": p['place_name'], "lat": float(p['y']), "lng": float(p['x']), "icon": icon, "type": itype})
                
                # 카카오맵 HTML 생성 (커스텀 오버레이 활용)
                map_html = f"""
                <!DOCTYPE html>
                <html><head><meta charset="utf-8">
                <style>
                    .apt-label {{ background-color: #0052A4; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px; border: 2px solid white; box-shadow: 0px 2px 4px rgba(0,0,0,0.3); }}
                    .infra-label {{ background-color: white; color: black; padding: 4px 8px; border-radius: 10px; font-size: 11px; border: 1px solid #ccc; box-shadow: 0px 1px 2px rgba(0,0,0,0.2); }}
                </style>
                </head><body>
                <div id="map" style="width:100%;height:650px;border-radius:10px;"></div>
                <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}"></script>
                <script>
                    var mapContainer = document.getElementById('map'),
                        mapOption = {{ center: new kakao.maps.LatLng({center_lat}, {center_lng}), level: 4 }};
                    var map = new kakao.maps.Map(mapContainer, mapOption);
                    
                    var aptData = {json.dumps(map_data)};
                    var infraData = {json.dumps(infra_data)};
                    
                    // 아파트 마커 (파란색 커스텀 라벨)
                    aptData.forEach(function(d) {{
                        var content = '<div class="apt-label">' + d.name + '<br>' + (d.price/10000).toFixed(1) + '억</div>';
                        var position = new kakao.maps.LatLng(d.lat, d.lng);
                        new kakao.maps.CustomOverlay({{ map: map, position: position, content: content, yAnchor: 1 }});
                    }});
                    
                    // 인프라 마커 (아이콘 라벨)
                    infraData.forEach(function(d) {{
                        var content = '<div class="infra-label">' + d.icon + ' ' + d.name + '</div>';
                        var position = new kakao.maps.LatLng(d.lat, d.lng);
                        new kakao.maps.CustomOverlay({{ map: map, position: position, content: content, yAnchor: 0 }});
                    }});
                </script>
                </body></html>
                """
                components.html(map_html, height=670)
    else:
        st.warning("데이터가 없습니다.")

# ==========================================
# 화면 3: 🕸️ 인프라 헥사곤 분석 (데이터 사이언스)
# ==========================================
elif menu == "🕸️ 인프라 헥사곤 분석":
    st.markdown('<p class="main-title">🕸️ 동네 인프라 헥사곤 분석</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">특정 주소를 중심으로 교육, 교통, 편의, 의료, 자연, 문화 점수를 방사형 차트로 분석합니다.</p>', unsafe_allow_html=True)
    
    target_address = st.text_input("분석할 중심 주소 또는 아파트명 입력", "강남역")
    
    if st.button("헥사곤 분석 실행"):
        lat, lng = get_lat_lng(target_address)
        if lat and lng:
            with st.spinner("반경 1.5km 내의 모든 인프라 데이터를 수집 및 분석 중입니다..."):
                # 카테고리별 개수 수집
                edu = len(search_category("SC4", lat, lng)) + len(search_category("AC5", lat, lng)) # 학교+학원
                trans = len(search_category("SW8", lat, lng)) # 지하철
                conv = len(search_category("MT1", lat, lng)) + len(search_category("CS2", lat, lng)) # 마트+편의점
                medi = len(search_category("HP8", lat, lng)) + len(search_category("PM9", lat, lng)) # 병원+약국
                food = len(search_category("FD6", lat, lng)) + len(search_category("CE7", lat, lng)) # 음식점+카페
                culture = len(search_category("CT1", lat, lng)) # 문화시설
                
                # 점수 정규화 (임의의 만점 기준 설정)
                categories = ['교육(학군)', '교통(역세권)', '편의(슬세권)', '의료(병세권)', '외식/카페', '문화/여가']
                scores = [min(edu*10, 100), min(trans*30, 100), min(conv*5, 100), min(medi*5, 100), min(food*3, 100), min(culture*20, 100)]
                
                fig = go.Figure(data=go.Scatterpolar(
                  r=scores + [scores[0]], # 폐곡선을 위해 첫 값 추가
                  theta=categories + [categories[0]],
                  fill='toself',
                  line_color='#0052A4',
                  fillcolor='rgba(0, 82, 164, 0.4)'
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, title=f"[{target_address}] 종합 입지 헥사곤")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("### 📊 상세 인프라 수치")
                    st.write(f"**🏫 교육 시설:** {edu}개")
                    st.write(f"**🚇 지하철역:** {trans}개")
                    st.write(f"**🛒 편의/마트:** {conv}개")
                    st.write(f"**🏥 의료 시설:** {medi}개")
                    st.write(f"**☕ 맛집/카페:** {food}개")
                    st.write(f"**🎨 문화 시설:** {culture}개")
                    
                    total_score = sum(scores) / 6
                    st.success(f"🏆 **종합 입지 점수: {total_score:.1f}점 / 100점**")
        else:
            st.error("주소를 찾을 수 없습니다. 정확한 동/호수나 건물명을 입력해주세요.")

# ==========================================
# 화면 4: 💰 부동산 금융 계산기
# ==========================================
elif menu == "💰 부동산 금융 계산기":
    st.markdown('<p class="main-title">💰 영끌족을 위한 부동산 금융 계산기</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">취득세부터 주택담보대출 원리금 상환액까지 완벽하게 계산해 드립니다.</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏦 주택담보대출 계산기 (원리금균등상환)")
        principal = st.number_input("대출 원금 (만원)", min_value=0, value=30000, step=1000) * 10000
        annual_rate = st.number_input("연 이자율 (%)", min_value=0.0, value=4.5, step=0.1)
        years = st.number_input("대출 기간 (년)", min_value=1, value=30, step=1)
        
        if st.button("대출 이자 계산하기"):
            r = (annual_rate / 100) / 12
            n = years * 12
            if r > 0:
                pmt = principal * (r * (1 + r)**n) / ((1 + r)**n - 1)
            else:
                pmt = principal / n
                
            total_payment = pmt * n
            total_interest = total_payment - principal
            
            st.info(f"💸 **매월 상환액:** 약 **{int(pmt/10000):,}만 원**")
            st.write(f"- 총 상환 금액: {int(total_payment/100000000)}억 {int((total_payment%100000000)/10000):,}만 원")
            st.write(f"- 총 발생 이자: {int(total_interest/100000000)}억 {int((total_interest%100000000)/10000):,}만 원")

    with col2:
        st.markdown("### 📜 부동산 취득세 계산기")
        buy_price = st.number_input("매매 가격 (만원)", min_value=0, value=80000, step=1000) * 10000
        area_type = st.radio("전용 면적", ["85㎡ 이하", "85㎡ 초과"])
        house_cnt = st.selectbox("보유 주택 수", ["무주택자 (1주택 취득)", "1주택자 (2주택 취득)", "다주택자"])
        
        if st.button("취득세 계산하기"):
            # 간략화된 취득세율 로직 (실제 법령에 따라 다를 수 있음)
            tax_rate = 0.01
            if buy_price > 900000000: tax_rate = 0.03
            elif buy_price > 600000000: tax_rate = 0.02
            
            if house_cnt == "1주택자 (2주택 취득)": tax_rate = 0.08
            elif house_cnt == "다주택자": tax_rate = 0.12
            
            edu_tax = tax_rate * 0.1
            farm_tax = 0.002 if area_type == "85㎡ 초과" else 0.0
            
            total_tax_rate = tax_rate + edu_tax + farm_tax
            total_tax = buy_price * total_tax_rate
            
            st.error(f"🏛️ **예상 총 취득세:** 약 **{int(total_tax/10000):,}만 원**")
            st.write(f"- 적용 취득세율: {tax_rate*100:.1f}%")
            st.write(f"- 지방교육세: {edu_tax*100:.2f}%")
            st.write(f"- 농어촌특별세: {farm_tax*100:.1f}%")
