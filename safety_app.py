import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# 1. 화면 디자인 (다크모드 & 기본설정)
st.set_page_config(page_title="스마트 위험성평가", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    /* 전체 배경 다크모드 및 글씨체 설정 */
    .stApp { background-color: #1a1a1a; color: #ffffff; }
    h1, h2, h3, p, div { font-family: 'Noto Sans KR', sans-serif; }
    
    /* 입력창 스타일 */
    .stTextInput input { background-color: #333333 !important; color: white !important; }
    
    /* 버튼 스타일 */
    div.stButton > button {
        background-color: #0085ff; color: white; border: none;
        border-radius: 5px; padding: 10px 20px; font-weight: bold; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ AI 건설 위험성평가 생성기")
st.caption("작업 내용만 입력하면 AI가 위험요인과 안전대책을 자동으로 작성해줍니다.")

# 2. API 키 가져오기 (Streamlit Secrets에서 가져옴)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    # 로컬 테스트용 (배포 후엔 안 보임)
    api_key = st.text_input("API 키 입력 (테스트용)", type="password")

# 3. 입력 받는 곳
col1, col2 = st.columns(2)
with col1:
    task_name = st.text_input("작업명", placeholder="예: 지하 피트층 배관 용접 작업")
    location = st.text_input("작업 장소", placeholder="예: 밀폐된 지하 공간")
with col2:
    tools = st.text_input("사용 장비/도구", placeholder="예: TIG 용접기, 그라인더, 환기팬")

generate_btn = st.button("🚀 위험성평가표 자동 생성하기")

# 4. AI 생성 로직
if generate_btn:
    if not api_key:
        st.error("설정(Secrets)에 API 키가 없습니다.")
    elif not task_name:
        st.warning("작업명을 입력해주세요!")
    else:
        with st.spinner("AI 안전팀장이 분석 중입니다... 🧠"):
            try:
                # 모델 설정 (Gemini 1.5 Flash + JSON 모드)
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    'models/gemini-1.5-flash',
                    generation_config={"response_mime_type": "application/json"}
                )

                # 프롬프트 (작업 지시서)
                prompt = f"""
                당신은 건설 안전 기술사입니다. 아래 작업에 대한 위험성평가표를 작성하세요.
                
                [입력 정보]
                - 작업: {task_name}
                - 장소: {location}
                - 장비: {tools}

                [작성 규칙]
                1. '작업준비' -> '본작업' -> '정리정돈' 3단계로 구분할 것.
                2. 각 단계별 핵심 위험요인을 도출하고 구체적인 대책을 쓸 것.
                3. 빈도(1~5)와 강도(1~4)를 평가하되, 곱(위험성)이 8을 넘지 않도록 할 것.
                
                [출력 형식: JSON List]
                [
                    {{
                        "단계": "본작업",
                        "위험요인": "용접 불티에 의한 화재",
                        "대책": "불티비산방지포 설치 및 소화기 비치",
                        "빈도": 2, "강도": 3
                    }}
                ]
                """
                
                # AI 호출
                response = model.generate_content(prompt)
                
                # 데이터 가공
                data = json.loads(response.text)
                df = pd.DataFrame(data)
                
                # 위험성 계산 및 등급 판정
                df["위험성"] = df["빈도"] * df["강도"]
                df["등급"] = df["위험성"].apply(lambda x: "🔴 상" if x>=6 else ("🟡 중" if x>=3 else "🟢 하"))
                
                st.session_state.result_df = df
                st.success("생성 완료!")

            except Exception as e:
                st.error(f"에러 발생: {e}")

# 5. 결과 보여주기 및 수정/다운로드
if 'result_df' in st.session_state:
    st.divider()
    st.subheader("📝 결과 확인 및 수정")
    
    # 수정 가능한 표
    edited_df = st.data_editor(
        st.session_state.result_df,
        use_container_width=True,
        num_rows="dynamic"
    )
    
    # 엑셀(CSV) 다운로드
    csv = edited_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("💾 엑셀(CSV)로 다운로드", csv, "risk_assessment.csv")