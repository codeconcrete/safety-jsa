import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# 1. 화면 디자인
st.set_page_config(page_title="스마트 위험성평가", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1a1a1a; color: #ffffff; }
    h1, h2, h3, p, div { font-family: 'Noto Sans KR', sans-serif; }
    .stTextInput input { background-color: #333333 !important; color: white !important; }
    div.stButton > button {
        background-color: #0085ff; color: white; border: none;
        border-radius: 5px; padding: 10px 20px; font-weight: bold; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ AI 건설 위험성평가 생성기")

# [중요] 버전 확인용 (성공하면 0.8.3 이상이 찍혀야 함)
st.caption(f"시스템 버전: {genai.__version__} (Gemini 1.5 Flash 엔진)")

# 2. API 키 가져오기
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.text_input("API 키 입력", type="password")

# 3. 작업 정보 입력
st.markdown("### 1. 작업 개요")
col1, col2 = st.columns(2)
with col1:
    task_name = st.text_input("작업명", placeholder="예: 배관 용접 작업")
    worker_count = st.number_input("투입 인원 (명)", min_value=1, value=2, step=1)
with col2:
    materials = st.text_input("사용 자재", placeholder="예: 배관 파이프, 용접봉")
    tools = st.text_input("사용 장비/도구", placeholder="예: TIG 용접기, 그라인더, 연장선")

st.markdown("### 2. 장소 및 환경")
col3, col4 = st.columns(2)
with col3:
    location_main = st.text_input("주요 장소 (시설/건물)", placeholder="예: 지하 2층 기계실")
with col4:
    location_detail = st.text_input("세부 위치", placeholder="예: 공조기 배관 하부")

location_env = st.text_input("주변 환경 특이사항", placeholder="예: 조명이 어둡고 환기가 불충분함, 바닥 물기 있음")
protectors = st.text_input("착용 보호구", placeholder="예: 안전모, 안전화, 보안면, 가죽장갑, 방진마스크, 각반")

generate_btn = st.button("🚀 위험성평가표 자동 생성하기")

# 4. 로직
if generate_btn:
    if not api_key:
        st.error("설정(Secrets)에 API 키가 없습니다.")
    else:
        with st.spinner("분석 중... 🧠"):
            try:
                genai.configure(api_key=api_key)
                
                # 모델명 변경: 쿼터 제한 회피를 위해 'gemini-flash-latest' 사용
                model = genai.GenerativeModel(
                    'gemini-flash-latest', 
                    generation_config={"response_mime_type": "application/json"}
                )

                prompt = f"""
                건설 안전 기술사로서 아래 작업에 대한 위험성평가표(JSA)를 작성하세요.
                
                [작업 정보]
                - 작업명: {task_name} (투입인원: {worker_count}명)
                - 사용 자재: {materials}
                - 사용 장비: {tools}
                - 작업 장소: {location_main} ({location_detail})
                - 환경 특성: {location_env}
                - 보호구: {protectors}
                
                [작업 규칙]
                1. '작업준비' -> '본작업' -> '작업종료/정리' 3단계로 구분하여 작성하세요.
                2. '작업준비' 단계의 맨 첫 번째 행은 반드시 '작업자 개인 보호구 및 복장 상태 확인'에 대한 내용이어야 합니다.
                3. 각 위험요인별 '대책'은 실질적인 내용으로 반드시 2개~5개 사이로 다르게 작성하세요. (줄바꿈 '-' 기호 사용)
                4. [중요] 위험성은 빈도(1~5)와 강도(1~4)의 곱으로 계산하되, 계산된 '위험성' 수치가 절대 8을 초과하지 않도록 빈도와 강도를 조절하세요. (위험성 <= 8)
                5. 반드시 JSON 포맷으로만 출력하세요.
                
                [JSON 예시]
                [
                    {{"단계": "작업준비", "위험요인": "작업자 복장 불량으로 인한 끼임 사고 위험", "대책": "- 안전모, 안전화, 각반 착용 상태 확인\n- 작업복 소매 및 옷단 정리 정돈\n- 보안경 착용 확인", "빈도": 2, "강도": 3}},
                    {{"단계": "본작업", "위험요인": "...", "대책": "- 대책1 ...\n- 대책2 ...", "빈도": 2, "강도": 3}}
                ]
                """
                
                response = model.generate_content(prompt)
                data = json.loads(response.text)
                df = pd.DataFrame(data)
                df["위험성"] = df["빈도"] * df["강도"]
                df["등급"] = df["위험성"].apply(lambda x: "🔴 상" if x>=6 else ("🟡 중" if x>=3 else "🟢 하"))
                
                st.session_state.result_df = df
                st.success("생성 완료!")

            except Exception as e:
                st.error(f"에러 상세: {e}")
                st.warning("⚠️ 사용 가능한 모델 목록 (API 키 권한 확인용):")
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            st.write(f"- {m.name}")
                except Exception as list_e:
                    st.error(f"모델 목록 조회 실패: {list_e}")

if 'result_df' in st.session_state:
    st.divider()
    # HTML로 변환하여 출력 (줄바꿈 강제 적용)
    st.markdown("### 📋 위험성평가 결과표")
    
    # \n을 <br>로 변환
    display_df = st.session_state.result_df.copy()
    display_df['대책'] = display_df['대책'].str.replace('\n', '<br>')
    
    # 스타일 적용
    table_css = """
    <style>
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { background-color: #262730; color: white; padding: 12px; text-align: left; border-bottom: 2px solid #edaf12; }
        td { padding: 10px; border-bottom: 1px solid #444; vertical-align: top; color: #ddd; }
        .col-risk { font-weight: bold; color: #ff6c6c; }
        .col-measure { white-space: pre-wrap; line-height: 1.6; }
    </style>
    """
    
    # Pandas HTML 변환 (escape=False로 설정하여 <br> 태그 허용)
    html = display_df.to_html(classes='dataframe', escape=False, index=False)
    
    # 최종 렌더링
    st.markdown(table_css + html, unsafe_allow_html=True)
