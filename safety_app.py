import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# 1. 화면 디자인
def parse_to_list(text_data):
    if isinstance(text_data, list):
        return text_data
    if not text_data:
        return []
    return [item.strip() for item in text_data.split(',') if item.strip()]

st.set_page_config(page_title="스마트 위험성평가", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1a1a1a; color: #ffffff; }
    h1, h2, h3, p, div { font-family: 'Noto Sans KR', sans-serif; }
    .stTextInput input { background-color: #333333 !important; color: white !important; }
    .stTextInput label, .stMultiSelect label, .stTextInput label p, .stMultiSelect label p { color: #ffffff !important; }
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

# 3. 작업 정보 입력 (1단계)
st.markdown("### 1. 작업 개요 및 위험 특성")
col1, col2 = st.columns(2)
with col1:
    task_name = st.text_input("작업명", placeholder="예: 외부 비계 해체 작업")
    # 주요 위험 요인 선택 (체크박스 대신 멀티셀렉트로 깔끔하게 구현)
    risk_factors = st.multiselect(
        "해당되는 위험 작업 특성을 모두 선택하세요 (자동 추천에 반영)",
        ["일반작업 (해당 없음)", "고소작업 (추락 위험)", "화기작업 (화재 발생)", "밀폐공간 (질식 위험)", 
         "전기작업 (감전 위험)", "중량물 취급 (근골격계/낙하)", "화학물질 취급", 
         "건설기계 사용", "해체/철거 작업"]
    )

with col2:
    location = st.text_input("작업 위치", placeholder="예: 105동 외부 지상 3층~5층")
    risk_context_manual = st.text_input("기타 위험 특성 (직접 입력)", placeholder="예: 강풍 예상, 야간 작업, 인접 장비 동시 작업 등")

# 초안 생성 버튼
if "draft_generated" not in st.session_state:
    st.session_state.draft_generated = False

analyze_btn = st.button("📋 작업 정보 분석 및 장비 추천받기 (1단계)", use_container_width=True)

if analyze_btn:
    if not api_key:
        st.error("API 키를 먼저 입력해주세요.")
    else:
        with st.spinner("작업 특성을 분석하여 안전 장비를 추천 중입니다... 🤖"):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-flash-latest', generation_config={"response_mime_type": "application/json"})
                
                req_prompt = f"""
                건설 안전 전문가로서 다음 작업에 필요한 장비와 준비물을 제안하세요.
                
                [작업 정보]
                - 작업명: {task_name}
                - 장소: {location}
                - 위험 특성: {', '.join(risk_factors)}
                - 기타: {risk_context_manual}
                
                [요청 사항]
                아래 항목에 대해 현장에 꼭 필요한 실질적인 리스트를 작성해서 JSON으로 반환하세요.
                1. 보호구 (필수 및 권장)
                2. 안전장비 (시설물 포함)
                3. 사용 공구/장비
                4. 준비자료 (허가서 등)
                
                [JSON 포맷]
                {{
                    "protectors": "안전모, 안전화, ...",
                    "safety_equip": "소화기, ...",
                    "tools": "...",
                    "docs": "..."
                }}
                """
                
                response = model.generate_content(req_prompt)
                draft_data = json.loads(response.text)
                
                # 세션에 저장
                st.session_state.draft_data = draft_data
                st.session_state.draft_generated = True
                
            except Exception as e:
                st.error(f"분석 실패: {e}")

# 2단계: 추천 결과 확인 및 수정
if st.session_state.draft_generated:
    st.markdown("### 2. 추천 장비 및 준비물 확인 (수정 가능)")
    st.info("AI가 추천한 내용입니다. 현장 상황에 맞게 수정하세요.")
    
    draft = st.session_state.draft_data
    
    col3, col4 = st.columns(2)
    with col3:
        protectors_list = parse_to_list(draft.get("protectors", ""))
        protectors = st.multiselect("보호구", options=protectors_list, default=protectors_list)

        tools_list = parse_to_list(draft.get("tools", ""))
        tools = st.multiselect("사용 공구/장비", options=tools_list, default=tools_list)
    
    with col4:
        safety_equip_list = parse_to_list(draft.get("safety_equip", ""))
        safety_equip = st.multiselect("안전장비/시설", options=safety_equip_list, default=safety_equip_list)

        materials_list = parse_to_list(draft.get("docs", ""))
        materials = st.multiselect("준비자료/허가서", options=materials_list, default=materials_list)

    st.markdown("---")
    generate_final_btn = st.button("🚀 위험성평가표 최종 생성하기 (2단계)", use_container_width=True)

    if generate_final_btn:
        with st.spinner("최종 위험성평가표를 생성하고 있습니다... 🛡️"):
            try:
                genai.configure(api_key=api_key)
                # 모델명: 'gemini-flash-latest' 사용
                model = genai.GenerativeModel(
                    'gemini-flash-latest', 
                    generation_config={"response_mime_type": "application/json"}
                )

                prompt = f"""
                건설 안전 기술사로서 아래 작업에 대한 위험성평가표(JSA)를 작성하세요.
                
                [작업 정보]
                - 작업명: {task_name}
                - 작업 위치: {location}
                - 위험 특성: {', '.join(risk_factors)} / {risk_context_manual}
                - 보호구: {', '.join(protectors)}
                - 안전장비: {', '.join(safety_equip)}
                - 사용장비: {', '.join(tools)}
                - 준비자료: {', '.join(materials)}
                
                [작업 규칙]
                [작업 규칙]
                1. '작업준비' -> '본작업' -> '작업종료/정리' 3단계를 기본으로 하되, **'본작업'은 반드시 구체적인 단위 작업명으로 세분화해서 작성하세요.** (예: '본작업: 펌프카 설치', '본작업: 타설 진행')
                2. '작업준비' 단계의 맨 첫 번째 행은 반드시 '작업자 개인 보호구 및 복장 상태 확인'에 대한 내용이어야 합니다.
                3. 각 위험요인별 '대책'은 실질적인 내용으로 반드시 2개~5개 사이로 다르게 작성하세요. (줄바꿈은 반드시 '\\n' 문자를 사용하세요. 실제 엔터키 사용 금지)
                4. [중요] 위험성은 빈도(1~5)와 강도(1~4)의 곱으로 계산하되, 계산된 '위험성' 수치가 절대 8을 초과하지 않도록 빈도와 강도를 조절하세요. (위험성 <= 8)
                5. 반드시 JSON 포맷으로만 출력하세요. (Markdown 코드 블록 없이 순수 JSON만 출력)
                
                [JSON 예시]
                [
                    {{"단계": "작업준비", "위험요인": "작업자 복장 불량으로 인한 끼임 사고 위험", "대책": "- 안전모, 안전화, 각반 착용 상태 확인\\n- 작업복 소매 및 옷단 정리 정돈\\n- 보안경 착용 확인", "빈도": 2, "강도": 3}},
                    {{"단계": "본작업: 펌프카 설치", "위험요인": "...", "대책": "- 대책1 ...\\n- 대책2 ...", "빈도": 2, "강도": 3}}
                ]
                """
                
                response = model.generate_content(prompt)
                
                # JSON 파싱 전처리
                text = response.text
                if "```json" in text:
                    text = text.replace("```json", "").replace("```", "")
                text = text.strip()
                
                data = json.loads(text, strict=False)
                df = pd.DataFrame(data)
                df["위험성"] = df["빈도"] * df["강도"]
                df["등급"] = df["위험성"].apply(lambda x: "🔴 상" if x>=6 else ("🟡 중" if x>=3 else "🟢 하"))
                
                st.session_state.result_df = df
                st.success("최종 생성 완료! 아래 결과를 확인하세요.")

            except Exception as e:
                st.error(f"생성 중 오류 발생: {e}")

if 'result_df' in st.session_state:
    st.divider()
    
    # 보기 모드 선택 (PC 표 / 모바일 카드)
    view_mode = st.radio("보기 모드 선택", ["📄 표준 보고서형 (PC)", "📱 카드형 리스트 (Mobile)"], horizontal=True)

    if "PC" in view_mode:
        # 정적 테이블로 출력 (줄바꿈 지원을 위해 st.table 사용)
        st.markdown("### 📋 위험성평가 결과표")
        
        # 1. 기본 설정: 줄바꿈, 상단 정렬, 배경색
        styled_df = st.session_state.result_df.style.set_properties(**{
            'white-space': 'pre-wrap',
            'vertical-align': 'middle',
            'text-align': 'center',
            'background-color': '#ffffff',
            'color': '#000000',
            'border-color': '#dddddd'
        })
        
        # 3. '대책' 컬럼만 좌측 정렬로 덮어쓰기
        styled_df.set_properties(subset=['대책'], **{
            'text-align': 'left'
        })

        # 4-1. 숫자 컬럼 및 단계 컬럼 스타일링 (가운데 정렬, 줄바꿈 방지 등)
        styled_df.set_properties(subset=['빈도', '강도', '위험성', '등급'], **{
             'text-align': 'center'
        })
        styled_df.set_properties(subset=['단계'], **{
             'text-align': 'center',
             'white-space': 'nowrap' 
        })
        
        # 4. 헤더 스타일
        styled_df.set_table_styles([
            dict(selector='th', props=[
                ('text-align', 'center'), 
                ('background-color', '#e6e9ef'), 
                ('color', '#000000'),
                ('font-weight', 'bold'),
                ('border-bottom', '2px solid #555'),
                ('vertical-align', 'middle')
            ])
        ])
        
        # 5. 인덱스 숨기기 및 출력
        st.table(styled_df.hide(axis="index"))
    
    else:
        # 모바일 카드 뷰 구현
        st.markdown("### 📱 위험성평가 카드 리스트")
        for index, row in st.session_state.result_df.iterrows():
            # 등급에 따른 색상/아이콘 설정
            grade = row['등급']
            border_color = "#ff6c6c" if "상" in grade else ("#f1c40f" if "중" in grade else "#2ecc71")
            
            # HTML 카드 디자인
            card_html = f"""
            <div style="
                background-color: white; 
                padding: 15px; 
                border-radius: 10px; 
                border-left: 6px solid {border_color}; 
                margin-bottom: 15px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                color: black;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-weight: bold; color: #555; font-size: 0.9em;">Step {index+1} [{row['단계']}]</span>
                    <span style="font-weight: bold; color: {border_color}; border: 1px solid {border_color}; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{grade} ({row['위험성']})</span>
                </div>
                <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 8px; color: #333;">
                    ⚠️ {row['위험요인']}
                </div>
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 6px; font-size: 0.95em; color: #444; line-height: 1.5; white-space: pre-wrap;">
                    {row['대책']}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
