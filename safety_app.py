import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re # JSON 추출을 위한 도구 추가

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
# 버전 확인용
st.caption(f"시스템: {genai.__version__} / 엔진: Gemini Pro (Safe Mode)")

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
        with st.spinner("분석 중... (Gemini Pro) 🧠"):
            try:
                genai.configure(api_key=api_key)
                
                # [핵심 변경] 1.5 Flash -> gemini-pro (가장 안정적인 모델)
                # JSON 강제 모드 삭제 (Pro 모델은 지원 안 함)
                model = genai.GenerativeModel('gemini-pro')

                prompt = f"""
                건설 안전 기술사로서 '{task_name}'(장소:{location}, 장비:{tools})에 대한 위험성평가표를 작성하세요.
                
                [규칙]
                1. '작업준비'->'본작업'->'정리정돈' 단계별 위험요인과 대책 작성.
                2. 빈도(1~5)와 강도(1~4) 평가.
                3. 반드시 아래 JSON 형식으로만 출력하세요. (코드블록 없이 순수 JSON만)
                
                [
                    {{"단계": "본작업", "위험요인": "...", "대책": "...", "빈도": 2, "강도": 3}}
                ]
                """
                
                response = model.generate_content(prompt)
                
                # [추가] JSON 파싱 강화 (Pro 모델은 잡담을 섞을 수 있어서 정제 필요)
                text = response.text
                # JSON 부분만 쏙 뽑아내는 정규식
                match = re.search(r'\[.*\]', text, re.DOTALL)
                
                if match:
                    json_str = match.group(0)
                    data = json.loads(json_str)
                    df = pd.DataFrame(data)
                    df["위험성"] = df["빈도"] * df["강도"]
                    df["등급"] = df["위험성"].apply(lambda x: "🔴 상" if x>=6 else ("🟡 중" if x>=3 else "🟢 하"))
                    
                    st.session_state.result_df = df
                    st.success("생성 완료!")
                else:
                    st.error("AI가 JSON 형식을 잘못 만들었습니다. 다시 시도해주세요.")
                    st.write(text) # 디버깅용

            except Exception as e:
                st.error(f"에러 상세: {e}")

if 'result_df' in st.session_state:
    st.divider()
    st.data_editor(st.session_state.result_df, use_container_width=True)
