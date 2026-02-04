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

# 3. 입력
col1, col2 = st.columns(2)
with col1:
    task_name = st.text_input("작업명", placeholder="예: 지하 피트층 배관 용접 작업")
    location = st.text_input("작업 장소", placeholder="예: 밀폐된 지하 공간")
with col2:
    tools = st.text_input("사용 장비/도구", placeholder="예: TIG 용접기, 그라인더, 환기팬")

generate_btn = st.button("🚀 위험성평가표 자동 생성하기")

# 4. 로직
if generate_btn:
    if not api_key:
        st.error("설정(Secrets)에 API 키가 없습니다.")
    else:
        with st.spinner("분석 중... 🧠"):
            try:
                genai.configure(api_key=api_key)
                
                # 모델명: 'models/' 빼고 깔끔하게
                model = genai.GenerativeModel(
                    'gemini-1.5-flash', 
                    generation_config={"response_mime_type": "application/json"}
                )

                prompt = f"""
                건설 안전 기술사로서 '{task_name}'(장소:{location}, 장비:{tools})에 대한 위험성평가표를 작성하세요.
                
                [규칙]
                1. '작업준비'->'본작업'->'정리정돈' 단계별 위험요인과 대책 작성.
                2. 빈도(1~5)와 강도(1~4) 평가 (곱 8 이하).
                3. 반드시 JSON 리스트로 출력.
                
                [JSON 예시]
                [
                    {{"단계": "본작업", "위험요인": "...", "대책": "...", "빈도": 2, "강도": 3}}
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

if 'result_df' in st.session_state:
    st.divider()
    st.data_editor(st.session_state.result_df, use_container_width=True)
