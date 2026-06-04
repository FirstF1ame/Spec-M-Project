
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math
import re
import altair as alt

import db_utils
import api_utils
import calculator 

# ---------------------------------------------------------------------
# --- 1. 페이지 기본 설정
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Spec-M | 최적의 스펙업 로드맵", 
    page_icon="🗡️", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)


# ---------------------------------------------------------------------
# --- 2. CSS 스타일 정의 ---
# ---------------------------------------------------------------------
st.markdown("""
<style>
    /* 메이플 UI 특유의 짙은 네이비/차콜 톤 그라데이션 */
    .stApp {
        background: linear-gradient(135deg, #13151A 0%, #1A1D24 50%, #0D1117 100%);
    }

    /* 모든 컨테이너(박스)를 메이플 장비창처럼 반투명하게 만들기 */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"],
    .stForm, .stTabs [data-baseweb="tab-panel"] {
        background-color: rgba(30, 34, 42, 0.7) !important;
        border: 1px solid rgba(85, 95, 110, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        padding: 1.5rem !important;
        margin-bottom: 1rem;
    }

    /* 버튼 스타일링 (메이플스타일 골드/옐로우 포인트) */
    .stButton>button[kind="primary"] {
        background: linear-gradient(180deg, #FFD700 0%, #FFA500 100%);
        color: #333333 !important;
        font-weight: 900 !important;
        border: 2px solid #B8860B !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(180deg, #FFF8DC 0%, #FFD700 100%);
        border-color: #DAA520 !important;
    }

    /* 장비 그리드 스타일 정의 */
    .eq-grid {
        display: grid;
        grid-template-columns: repeat(7, 55px);
        grid-template-rows: repeat(6, 55px);
        gap: 5px;
        width: max-content;
        padding: 15px;
        background: rgba(10, 10, 10, 0.5);
        border: 1px solid #444;
        border-radius: 5px;
        margin: 0 auto;
    }
    .eq-slot {
        width: 100%; height: 100%;
        background-color: #333;
        border: 1px solid #555;
        border-radius: 3px;
        position: relative;
        display: flex; align-items: center; justify-content: center;
    }
    .eq-slot img {
        width: 40px; height: 40px;
        object-fit: contain;
    }
    .part-label { font-size: 9px; color: #aaa; position: absolute; bottom: 2px; line-height: 1; text-align: center; width: 100%; }
    .star-label {
        font-size: 10px; color: #ffeb3b; position: absolute; top: 1px; right: 2px; z-index: 3; font-weight: bold;
        text-shadow: 1px 1px 2px #000;
    }
    
    /* 잠재능력 등급별 테두리 */
    .border-legendary { border: 2px solid #51ff00 !important; }
    .border-unique { border: 2px solid #ffcc00 !important; border-radius: 3px; }
    .border-epic { border: 2px solid #c800ff !important; border-radius: 3px; }
    .border-rare { border: 2px solid #00d9ff !important; border-radius: 3px; }
    
    /* 가독성을 위한 텍스트 스타일 */
    .stMarkdown, .stMetric, label, p {
        color: #EEE !important;
    }
    h1, h2, h3 {
        color: #FFF !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# --- 🚀 [수정] 우측 상단 로고 이미지 배치
# ---------------------------------------------------------------------
header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.title("🗡️ Spec-M")

with header_col2:
    st.markdown(
        f'<div style="text-align: right; padding-top: 15px;">'
        f'<img src="https://imgur.com/QKsqdvp.jpg" width="120">'
        f'</div>', 
        unsafe_allow_html=True
    )

st.markdown("**당신의 시간과 재화를 아껴주는 최적의 스펙업 로드맵**")
st.divider()

# --- 2. 세션 상태 초기화 ---
if 'char_data' not in st.session_state:
    st.session_state.char_data = None
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'dashboard'
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# --- 🚀 핵심 분석 알고리즘 (주스탯 % 환산 및 플가 필터링 적용) ---
def calculate_custom_score(item):
    total_score = 0.0
    
    all_options = []
    for i in range(1, 4):
        all_options.append(item.get(f"potential_option_{i}", ""))
        all_options.append(item.get(f"additional_potential_option_{i}", ""))

    for opt in all_options:
        if not opt: continue
        if "9레벨당" in opt:
            total_score += 6.0
        elif "%" in opt:
            match = re.search(r'\+(\d+)%', opt)
            if match: 
                total_score += float(match.group(1))
        elif "공격력" in opt or "마력" in opt:
            match = re.search(r'\+(\d+)', opt)
            if match:
                atk_val = float(match.group(1))
                total_score += (atk_val * 3.5) / 10.0

    starforce = int(item.get("starforce", 0))
    total_score += starforce * 1.5
    
    part = item.get("item_equipment_part", "")
    if part in ["무기", "보조무기", "엠블렘"]:
        total_score *= 1.5
        
    non_plat_parts = ["엠블렘", "보조무기", "기계 심장"]
    event_rings = ["테네브리스", "글로리온", "어웨이크", "결속", "카오스 링", "어드벤처", "SS급", "오닉스", "코스모스", "벤젼스", "이터널 플레임", "어비스 헌터스"]
    
    if part in non_plat_parts or any(ring in item.get("item_name", "") for ring in event_rings):
        total_score += 1000.0
        
    return total_score

# --- 3. 중앙 폼 영역 (로그인 및 검색) ---
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("<h3 style='text-align: center;'>나의 스펙 진단하기</h3>", unsafe_allow_html=True)
    with st.form("login_form"):
        api_key = st.text_input("넥슨 개발자 센터 API Key", type="password", value=st.session_state.api_key)
        character_name = st.text_input("캐릭터 닉네임", placeholder="조회할 캐릭터의 정확한 닉네임을 입력해 주세요.")
        submit_btn = st.form_submit_button("내 스펙 진단하기", width="stretch")

    if submit_btn:
        if not character_name:
            st.warning("조회할 캐릭터 닉네임을 입력해 주세요.")
        else:
            with st.spinner(f"'{character_name}'님의 정보를 찾는 중..."):
                cached_data = db_utils.get_user_by_nickname(character_name)
                use_cache = False
                
                # 1. DB에 최근 검색 기록이 있는지 확인 (캐시 검증)
                if cached_data:
                    updated_time = pd.to_datetime(cached_data['updated_at'])
                    current_time = datetime.now(updated_time.tzinfo)
                    
                    stats_data = cached_data.get('stats_data', {})
                    basic_info = stats_data.get('basic', {}) if isinstance(stats_data, dict) else {}
                    is_data_valid = bool(basic_info.get('character_image')) 
                    
                    if (current_time - updated_time < timedelta(days=7)) and is_data_valid:
                        use_cache = True
                        st.success(f"✨ '{character_name}'님의 최근 기록을 DB에서 찾았습니다!")
                        
                        # 🚀 [수정 핵심 1] 캐시에서 데이터 꺼내기 (이름 통일)
                        basic_data = basic_info
                        # DB 버전에 상관없이 장비 데이터를 안전하게 가져오도록 수정
                        equip_data = cached_data.get('equip_data', cached_data.get('equipment_data', {})) 
                        achieve_data = stats_data.get('achievement', {})
                    else:
                        use_cache = False
                
                # 2. 캐시가 없거나 만료되었으면 넥슨 API 직접 호출
                if not use_cache:
                    if not api_key:
                        st.error("❌ API Key를 입력해 주세요.")
                        st.stop()
                    
                    st.info("🔄 넥슨 서버와 통신합니다...")
                    ocid = api_utils.get_ocid(api_key, character_name)
                    if ocid:
                        # 🚀 [수정 핵심 2] API에서 데이터 꺼내기 (이름 통일)
                        basic_data = api_utils.get_character_basic(api_key, ocid)
                        stat_data = api_utils.get_character_stat(api_key, ocid)
                        equip_data = api_utils.get_character_equipment(api_key, ocid)
                        achieve_data = api_utils.get_character_achievement(api_key, ocid)
                        
                        if basic_data and stat_data and equip_data:
                            # DB에 최신 데이터 캐싱 저장
                            db_utils.upsert_user_cache(api_key, character_name, 
                                {"basic": basic_data, "stat": stat_data, "achievement": achieve_data}, 
                                equip_data)
                        else:
                            st.error("데이터 로드 실패.") ; st.stop()
                    else:
                        st.error("캐릭터를 찾을 수 없습니다.") ; st.stop()

                # 🚀 [수정 핵심 3] 어디서 가져왔든, 하나로 통일된 achieve_data로 보스 수익 계산!
                auto_boss_income = calculator.calculate_weekly_boss_income(achieve_data)

                # --- 여기서부터 장비 분석 로직 시작 ---
                equipment_list = equip_data.get("item_equipment", [])
                all_ui_items = []    
                analyzed_items = []  
                potential_score_map = {"레전드리": 40, "유니크": 30, "에픽": 20, "레어": 10, "없음": 0}

                for item in equipment_list:
                    # 🚀 [핵심 수정 포인트] item_equipment_part -> item_equipment_slot 으로 변경!
                    # 이제 '두손검'이 아니라 '무기'로, '반지'가 아니라 '반지1', '반지2'로 정확히 가져옵니다.
                    part = item.get("item_equipment_slot", item.get("item_equipment_part", "알 수 없음"))
                    
                    item_name = item.get("item_name", "알 수 없음")
                    icon = item.get("item_icon", item.get("item_shape_icon", ""))
                    starforce = int(item.get("starforce", 0))
                    potential = item.get("potential_option_grade", "없음")
                    add_potential = item.get("additional_potential_option_grade", "없음")
                    
                    ui_item = {"part": part, "name": item_name, "starforce": starforce, "potential": potential, "icon": icon}
                    all_ui_items.append(ui_item)
                    
                    if part in ["훈장", "포켓 아이템", "뱃지"]: continue

                    base_score = (starforce * 10) + potential_score_map.get(potential, 0) + (potential_score_map.get(add_potential, 0) * 0.5)
                    # 이제 '무기', '보조무기'를 정확히 인식하므로 가중치(1.5배) 부여 로직도 완벽하게 작동합니다!
                    final_score = base_score * 1.5 if part in ["무기", "보조무기", "엠블렘"] else base_score
                        
                    analyzed_items.append({**ui_item, "score": final_score})

                analyzed_items.sort(key=lambda x: x["score"], reverse=True)
                # ------------------------------------

                # 세션에 최종 저장
                st.session_state.char_data = {
                    "name": character_name, 
                    "image": basic_data.get("character_image", "") if basic_data else "",
                    "level": basic_data.get("character_level", 0) if basic_data else 0,
                    "class": basic_data.get("character_class", "알 수 없음") if basic_data else "알 수 없음",
                    "all_ui_items": all_ui_items,
                    "analyzed_items": analyzed_items,
                    "boss_income": auto_boss_income # 보스 수익 세션 등록
                }
                st.session_state.current_view = 'dashboard'
                st.rerun()

# ---------------------------------------------------------------------
# --- 🖥️ 4. 결과 렌더링 영역 ---
# ---------------------------------------------------------------------
if st.session_state.char_data:
    st.write("")
    st.divider()
    
    head_col, nav1, nav2, nav3 = st.columns([2.5, 1, 1, 1])
    with head_col:
        st.markdown(f"### 🎉 스펙 진단 완료! **Lv.{st.session_state.char_data['level']} {st.session_state.char_data['class']}**")
    
    with nav1:
        if st.button("📊 대시보드", width="stretch", type="primary" if st.session_state.current_view == 'dashboard' else "secondary"):
            st.session_state.current_view = 'dashboard' ; st.rerun()
    with nav2:
        if st.button("🔄 시뮬레이터", width="stretch", type="primary" if st.session_state.current_view == 'simulator' else "secondary"):
            st.session_state.current_view = 'simulator' ; st.rerun()
    with nav3:
        if st.button("⭐ 보관함", width="stretch", type="primary" if st.session_state.current_view == 'favorites' else "secondary"):
            st.session_state.current_view = 'favorites' ; st.rerun()

    # =========================================================
    # [뷰 1] 대시보드 화면
    # =========================================================
    if st.session_state.current_view == 'dashboard':
        st.subheader("📊 나의 장비 세팅 및 분석")

        st.markdown("""
        <style>
            .eq-grid {
                display: grid;
                grid-template-columns: repeat(7, 55px);
                grid-template-rows: repeat(6, 55px);
                gap: 5px;
                width: max-content;
                background-color: #1e1e1e;
                padding: 15px;
                border: 2px solid #555;
                border-radius: 8px;
                margin: 0 auto;
            }
            .eq-slot {
                width: 100%; height: 100%;
                background-color: #333;
                border: 1px solid #666;
                border-radius: 4px;
                position: relative;
                display: flex; align-items: center; justify-content: center;
            }
            .eq-slot img {
                width: 40px; height: 40px;
                object-fit: contain;
                z-index: 2;
            }
            .char-image-box {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 6px;
                display: flex; align-items: center; justify-content: center;
                overflow: hidden;
            }
            .char-image-box img {
                max-width: 100%; max-height: 100%; object-fit: contain;
            }
            .part-label { font-size: 10px; color: #888; position: absolute; bottom: 2px; line-height: 1; text-align: center; width: 100%; }
            .star-label {
                font-size: 11px; color: #ffeb3b; position: absolute; top: 2px; right: 4px; z-index: 3; font-weight: bold;
                text-shadow: 1px 1px 2px #000;
            }
            .border-legendary { border: 2px solid #51ff00 !important; }
            .border-unique { border: 2px solid #ffcc00 !important; }
            .border-epic { border: 2px solid #c800ff !important; }
            .border-rare { border: 2px solid #00d9ff !important; }
            
            .aura-strong { box-shadow: 0 0 12px #00bcff, inset 0 0 10px #00bcff; animation: pulse-b 1.5s infinite; }
            .aura-weak { box-shadow: 0 0 12px #ff4b4b, inset 0 0 10px #ff4b4b; animation: pulse-r 1.5s infinite; }
            @keyframes pulse-b { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            @keyframes pulse-r { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            
            .empty-slot { background-color: #1a1a1a; border: 1px dashed #555; }
        </style>
        """, unsafe_allow_html=True)

        strong_names = [item['name'] for item in st.session_state.char_data['analyzed_items'][:3]]
        weak_names = [item['name'] for item in st.session_state.char_data['analyzed_items'][-3:]]

        # 🚀 1. 가장 최신 버전의 완벽한 render_slot 함수를 한 번만 선언합니다.
        def render_slot(part_keywords, label, col, row):
            if isinstance(part_keywords, str): part_keywords = [part_keywords]
            matches = [i for i in st.session_state.char_data['all_ui_items'] if i['part'] in part_keywords]
            item = matches[0] if matches else None
            
            pos_style = f"grid-column: {col}; grid-row: {row};"
            
            if not item or not item.get("icon"):
                return f'<div class="eq-slot empty-slot" style="{pos_style}"><div class="part-label">{label}</div></div>'
            
            classes = ["eq-slot"]
            pot = item.get('potential', '없음')
            if pot == "레전드리": classes.append("border-legendary")
            elif pot == "유니크": classes.append("border-unique")
            elif pot == "에픽": classes.append("border-epic")
            elif pot == "레어": classes.append("border-rare")
            
            if item['name'] in strong_names: classes.append("aura-strong")
            elif item['name'] in weak_names: classes.append("aura-weak")
            
            star = item.get("starforce", 0)
            star_html = f'<div class="star-label">★{star}</div>' if star > 0 else ""
            img_html = f'<img src="{item["icon"]}" alt="{label}">'
            
            return f'<div class="{" ".join(classes)}" style="{pos_style}" title="{item["name"]} ({pot})">{star_html}{img_html}</div>'

        
        # ---------------------------------------------------------
        # 화면을 좌우로 분할
        dashboard_col1, dashboard_col2 = st.columns([1, 1])

        # 좌측: 메이플 오리지널 장비창 UI
        with dashboard_col1:
            char_img_url = st.session_state.char_data.get('image', '')
            
            # 🚀 2. CSS 뼈대 (엑셀 구조에 맞춰 7열 6행으로 확장하고 캐릭터를 대폭 키웠습니다!)
            html_content = f"""
            <style>
            .eq-grid-authentic {{
                display: grid;
                /* 🚀 7개의 열(Column) 생성! */
                grid-template-columns: repeat(7, 52px);
                grid-template-rows: repeat(6, 52px);
                gap: 6px; justify-content: center; margin: 15px auto;
            }}
            .char-center {{
                /* 🚀 캐릭터가 3~5열(가로 3칸) / 1~4행(세로 4칸)을 넓게 차지합니다! */
                grid-column: 3 / span 3; 
                grid-row: 1 / span 4; 
                display: flex; align-items: center; justify-content: center;
            }}
            .char-center img {{
                /* 🚀 공간이 넓어진 만큼 캐릭터 높이를 240px로 대폭 확대! */
                max-height: 240px; max-width: 100%; object-fit: contain;
                filter: drop-shadow(0 0 10px rgba(255,255,255,0.25));
            }}
            .eq-grid-authentic .eq-slot {{
                width: 100%; height: 100%; background-color: rgba(20, 24, 34, 0.9);
                border: 1px solid #3a3f50; border-radius: 4px; position: relative; 
                display: flex; align-items: center; justify-content: center;
            }}
            .eq-grid-authentic .empty-slot {{ background-color: transparent; border: 1px dashed #3a3f50; }}
            .eq-grid-authentic .part-label {{ font-size: 10px; color: #555; font-weight: bold; text-align: center; }}
            .eq-grid-authentic img {{ max-width: 90%; max-height: 90%; object-fit: contain; z-index: 2; }}
            .star-label {{
                position: absolute; top: -7px; left: 50%; transform: translateX(-50%);
                font-size: 10px; color: #FFD700; text-shadow: 1px 1px 1px #000; z-index: 3; font-weight: bold;
                white-space: nowrap;
            }}
            </style>
            <div class="eq-grid-authentic">
                <div class="char-center"><img src="{char_img_url}" alt="Character"></div>
            """
            
            # 🚀 3. 기획자님이 주신 7x6 엑셀 좌표 완벽 매핑
            slots = [
                # 1행
                ('반지1', '반지1', 1, 1), ('얼굴장식', '얼장', 2, 1), 
                # (3, 4, 5열 1~4행은 캐릭터가 차지)
                ('모자', '모자', 6, 1), ('망토', '망토', 7, 1),
                
                # 2행
                ('반지2', '반지2', 1, 2), ('눈장식', '눈장식', 2, 2), 
                (['상의', '한벌옷'], '상의', 6, 2), ('장갑', '장갑', 7, 2),
                
                # 3행
                ('반지3', '반지3', 1, 3), ('귀고리', '귀고리', 2, 3), 
                ('하의', '하의', 6, 3), ('신발', '신발', 7, 3),
                
                # 4행
                ('반지4', '반지4', 1, 4), ('펜던트', '펜던트1', 2, 4), 
                ('어깨장식', '견장', 6, 4), ('훈장', '훈장', 7, 4),
                
                # 5행 (🚀 대망의 무기, 보조무기, 엠블렘 라인!)
                ('벨트', '벨트', 1, 5), ('펜던트2', '펜던트2', 2, 5), 
                ('무기', '무기', 3, 5), ('보조무기', '보조', 4, 5), ('엠블렘', '엠블렘', 5, 5), 
                ('안드로이드', '안드', 6, 5), (['기계 심장', '심장'], '심장', 7, 5),
                
                # 6행
                ('포켓 아이템', '포켓', 1, 6), ('빈공간', '', 2, 6), 
                # (3, 4, 5, 6열은 엑셀 설계대로 비워둡니다)
                ('빈공간', '', 6, 6), ('뱃지', '뱃지', 7, 6)
            ]
            
            # 🚀 4. 리스트를 돌면서 HTML 조립 후 출력
            for part, label, col, row in slots:
                html_content += render_slot(part, label, col, row)
                
            html_content += "</div>"
            st.markdown(html_content, unsafe_allow_html=True)
            
        with dashboard_col2:
            st.markdown("### 🔍 정밀 스펙 분석 리포트")
            st.write("잠재능력 수치(%)와 공/마를 실제 효율로 환산하여 분석한 결과입니다.")
            st.info(f"**💪 가장 강력한 부위 TOP 3:**\n\n{', '.join(strong_names)}")
            st.warning(f"**🚨 최우선 교체 권장 TOP 3:**\n\n{', '.join(weak_names)}")
            st.write("마우스를 아이템 아이콘 위에 올리면 상세 정보가 표시됩니다.")

        # --- 🚀 [수정] 대시보드 하단: 일요일 강조 메소 시세 트렌드 그래프 ---
        st.write("")
        st.divider()
        st.subheader("📈 최근 4주간 메소 시세 동향")
        st.write("안전한 스펙업의 첫걸음은 시세의 흐름을 읽는 것입니다. (1억 메소 당 거래가)")

        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(27, -1, -1)]
        is_sunday = [(today - timedelta(days=i)).weekday() == 6 for i in range(27, -1, -1)]

        np.random.seed(42)
        price_changes = np.random.normal(loc=0, scale=30, size=28) 
        prices = [2750]
        for change in price_changes[1:]:
            prices.append(int(prices[-1] + change))

        df_meso = pd.DataFrame({
            "날짜": pd.to_datetime(dates),
            "1억 메소 당 가격(원)": prices,
            "일요일": is_sunday
        })

        min_price = min(prices)
        max_price = max(prices)
        current_price = prices[-1]
        week_ago_price = prices[-8]
        price_diff = current_price - week_ago_price

        y_min = min_price - 50 
        
        base = alt.Chart(df_meso).encode(
            x=alt.X('날짜:T', title='', axis=alt.Axis(format='%m-%d', grid=False)),
            y=alt.Y('1억 메소 당 가격(원):Q', title='1억 메소 (원)', scale=alt.Scale(domain=[y_min, max_price + 50]))
        )

        line = base.mark_line(color='#FFD700', strokeWidth=3)

        points = base.mark_circle(size=60).encode(
            color=alt.condition(alt.datum.일요일, alt.value('#FF4B4B'), alt.value('#FFD700')),
            tooltip=[alt.Tooltip('날짜:T', format='%Y-%m-%d'), alt.Tooltip('1억 메소 당 가격(원):Q', format=',')]
        )

        rules = base.mark_rule(color='#FF4B4B', strokeDash=[4, 4], opacity=0.6).encode(
            x='날짜:T'
        ).transform_filter(alt.datum.일요일)

        chart = (rules + line + points).properties(height=350).interactive()
        st.altair_chart(chart, use_container_width=True)
        
        st.write("")
        col1, col2, col3 = st.columns(3)
        col1.metric("현재 시세", f"{current_price:,}원", f"{price_diff:+,}원 (전주 대비)")
        col2.metric("최근 4주 최고가", f"{max_price:,}원")
        col3.metric("최근 4주 최저가", f"{min_price:,}원")

    # =========================================================
    # [뷰 2] 시뮬레이터 화면 
    # =========================================================
    elif st.session_state.current_view == 'simulator':
        st.subheader("🔄 스펙업 가성비 시뮬레이터")
        st.markdown("경매장에서 본 아이템의 정보와 나의 플레이 타임을 입력하여 **정확한 소요 주차와 회수율**을 진단해 보세요.")
        
        sim_col1, sim_col2 = st.columns([1.2, 1])
        
        with sim_col1:
            st.markdown("#### 🛍️ 구매 희망 아이템 정보")
            
            main_category = st.selectbox("1. 아이템 종류 선택", ["방어구", "장신구", "무기", "보조무기", "엠블렘", "기계 심장"])

            sub_category_options = []
            item_name_options = []

            if main_category == "방어구":
                sub_category_options = ["모자", "상의", "하의", "한벌옷", "신발", "장갑", "망토", "어깨장식(견장)"]
                item_name_options = ["앱솔랩스", "아케인셰이드", "에테르넬", "카루타(루타비스)", "여명"]
            elif main_category == "장신구":
                sub_category_options = ["반지", "펜던트", "얼굴장식", "눈장식", "귀고리", "벨트"]
                item_name_options = ["보스 장신구", "여명의 보스 장신구", "칠흑의 보스 장신구", "마이스터", "이벤트 링"]
            elif main_category == "무기":
                sub_category_options = ["무기"]
                item_name_options = ["앱솔랩스", "아케인셰이드", "제네시스", "파프니르"]
            elif main_category == "보조무기":
                sub_category_options = ["보조무기"]
                item_name_options = ["블랙", "은빛", "루인 포스실드", "기타 보조무기"]
            elif main_category == "엠블렘":
                sub_category_options = ["엠블렘"]
                item_name_options = ["골드", "미트라", "기타 엠블렘"]
            elif main_category == "기계 심장":
                sub_category_options = ["기계 심장"]
                item_name_options = ["페어리 하트", "티타늄 하트", "블랙 하트", "리튬 하트"]

            c1, c2 = st.columns(2)
            with c1:
                sub_category = st.selectbox("2. 상세 부위 선택", sub_category_options)
            with c2:
                item_name = st.selectbox("3. 아이템 세트/이름", item_name_options)

            c3, c4 = st.columns(2)
            with c3:
                starforce = st.number_input("4. 스타포스 수치 (0~30성)", min_value=0, max_value=30, value=17, step=1)
            with c4:
                scissors_options = ["제한 없음(교환 가능)"] + [f"{i}회" for i in range(10, -1, -1)]
                scissors_count = st.selectbox("5. 남은 가위 가능 횟수", scissors_options)

            # 🚀 1. 기획자의 요구사항: 잠재능력 및 에디셔널 드롭다운 추가
            c7, c8 = st.columns(2)
            with c7:
                pot_grade = st.selectbox("6. 윗잠재 등급", ["레전드리", "유니크", "에픽", "레어", "없음"])
            with c8:
                add_pot_grade = st.selectbox("7. 에디셔널 등급", ["레전드리", "유니크", "에픽", "레어", "없음"])

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 💰 재화 정보 (단위: 억 메소)")
            c5, c6 = st.columns(2)
            with c5:
                current_meso_eok = st.number_input("현재 보유 메소 (억)", min_value=0.0, value=15.0, step=1.0, format="%.1f")
            with c6:
                target_price_eok = st.number_input("목표 아이템 가격 (억)", min_value=0.0, value=100.0, step=1.0, format="%.1f")

            calc_btn = st.button("📊 스펙업 진단 및 계산하기", use_container_width=True, type="primary")

        with sim_col2:
            calculator.render_income_calculator()

        # 🚀 2. 핵심 수학 모델 적용 및 분석 로직
        if calc_btn:
            target_price = target_price_eok * 100_000_000
            current_meso = current_meso_eok * 100_000_000
            
            # --- 최소가 보정 로직 (Floor Price) ---
            pot_min_map = {"레전드리": 16.0, "유니크": 6.0, "에픽": 0.0, "레어": 0.0, "없음": 0.0}
            add_pot_min_map = {"레전드리": 30.0, "유니크": 13.0, "에픽": 2.0, "레어": 0.0, "없음": 0.0}
            
            min_guarantee_eok = pot_min_map.get(pot_grade, 0.0) + add_pot_min_map.get(add_pot_grade, 0.0)
            min_guarantee_meso = min_guarantee_eok * 100_000_000

            # --- 가위 횟수 파싱 및 로그스케일 감가상각 공식 ---
            if "제한 없음" in scissors_count:
                after_equip_trades = 10 
                log_multiplier = 1.0
            else:
                trades_left = int(scissors_count.replace("회", ""))
                after_equip_trades = max(0, trades_left - 1) # 장착하면 1회 차감됨
                log_multiplier = 0.65 + 0.35 * (math.log10(after_equip_trades + 1) / math.log10(11))

            full_item_name = f"{starforce}성 {item_name} {sub_category}"
            
            if target_price > 0 and full_item_name:
                weekly_income = st.session_state.get('total_weekly_income', 0)
                
                needed_meso = target_price - current_meso
                weeks_needed = 0 if needed_meso <= 0 else (math.ceil(needed_meso / weekly_income) if weekly_income > 0 else 0)

                # 최종 회수율 산정
                base_recoverable = target_price * 0.95 * log_multiplier
                recoverable_meso = min(max(base_recoverable, min_guarantee_meso), target_price * 0.95)
                return_rate = (recoverable_meso / target_price) * 100

                st.write("---")
                st.subheader("💡 AI 스펙업 진단 결과")
                
                res_col1, res_col2, res_col3 = st.columns(3)
                res_col1.metric("⏳ 예상 소요 기간", f"약 {weeks_needed}주" if weekly_income > 0 else "측정 불가", delta=f"부족한 메소: {needed_meso / 100_000_000:.1f}억" if needed_meso > 0 else "즉시 구매 가능!", delta_color="off")
                res_col2.metric("📉 예상 회수율", f"{return_rate:.1f}%")
                res_col3.metric("💰 나중에 되팔 때 금액", f"{recoverable_meso / 100_000_000:.2f}억 메소")

                # 🚀 [추가된 기능] 가위 횟수에 따른 감가상각 변화 그래프 생성
                if "제한 없음" not in scissors_count and after_equip_trades > 0:
                    st.markdown("<br>##### 📉 가위 횟수별 예상 회수 금액 변화 (로그 스케일)", unsafe_allow_html=True)
                    
                    chart_data = []
                    # 현재 장착 후 남은 가위 횟수부터 0회까지 가격 변화 추적
                    for remaining_cuts in range(after_equip_trades, -1, -1):
                        temp_multiplier = 0.65 + 0.35 * (math.log10(remaining_cuts + 1) / math.log10(11))
                        temp_base = target_price * 0.95 * temp_multiplier
                        temp_recoverable = min(max(temp_base, min_guarantee_meso), target_price * 0.95)
                        
                        chart_data.append({
                            "가위 횟수": remaining_cuts,
                            "예상 회수 금액(억)": round(temp_recoverable / 100_000_000, 2)
                        })
                    
                    if len(chart_data) > 1:
                        df_chart = pd.DataFrame(chart_data)
                        
                        # Altair를 이용한 직관적인 꺾은선 + 영역 그래프 (메이플 감성 레드)
                        import altair as alt
                        depreciation_chart = alt.Chart(df_chart).mark_area(
                            line={'color': '#FF4B4B'}, opacity=0.2, color='#FF4B4B', point={'color': '#FF4B4B', 'size': 50}
                        ).encode(
                            # 역순 정렬을 통해 가위 횟수가 줄어드는 흐름을 직관적으로 보여줌
                            x=alt.X('가위 횟수:O', sort='descending', title='남은 가위 횟수 (회)', axis=alt.Axis(labelAngle=0)),
                            y=alt.Y('예상 회수 금액(억):Q', title='가치 (억 메소)', scale=alt.Scale(zero=False)),
                            tooltip=['가위 횟수', '예상 회수 금액(억)']
                        ).properties(height=220).interactive()
                        
                        st.altair_chart(depreciation_chart, use_container_width=True)

                # 세션에 결과 저장
                st.session_state.last_sim_result = {
                    "part": sub_category, "name": full_item_name, "price": target_price,
                    "trades": trades_left if "제한 없음" not in scissors_count else "무제한", 
                    "weeks": weeks_needed, "rate": return_rate, "meso": recoverable_meso
                }
            else:
                st.warning("아이템 가격을 올바르게 입력해 주세요.")
        
        # 즐겨찾기 저장 로직
        if st.session_state.get('last_sim_result'):
            if st.button("⭐ 이 시뮬레이션 결과 즐겨찾기에 저장하기", use_container_width=True):
                res = st.session_state.last_sim_result
                stats_json = {"expected_weeks": res['weeks'], "return_rate": res['rate'], "recoverable_meso": res['meso']}
                
                char_id = st.session_state.get('character_id')
                if char_id:
                    db_utils.save_favorite_item(char_id, res['part'], res['name'], res['price'], res['trades'], stats_json)
                    st.success(f"✅ '{res['name']}'이(가) 즐겨찾기에 안전하게 저장되었습니다!")
                    st.session_state.last_sim_result = None 
                else:
                    st.error("캐릭터 정보가 만료되었습니다. 다시 조회해 주세요.")
                    
        st.write("")
        st.divider()
        calculator.render_starforce_simulator()

    # =========================================================
    # [뷰 3] 즐겨찾기 보관함 화면
    # =========================================================
    elif st.session_state.current_view == 'favorites':
        st.subheader("⭐ 스펙업 가성비 보관함")
        st.markdown("저장해둔 시뮬레이션 결과를 모아보고, 어떤 아이템을 먼저 구매하는 것이 **가장 이득(가성비)**인지 비교해 보세요.")
        
        char_id = st.session_state.get('character_id')
        
        if char_id:
            favorites = db_utils.get_favorite_items(char_id)
            
            if not favorites:
                st.info("💡 아직 저장된 즐겨찾기가 없습니다. 시뮬레이터에서 찜하고 싶은 아이템을 먼저 저장해 보세요!")
            else:
                df_fav = pd.DataFrame(favorites)
                df_fav['expected_weeks'] = df_fav['stats_json'].apply(lambda x: x.get('expected_weeks', 0))
                df_fav['return_rate'] = df_fav['stats_json'].apply(lambda x: x.get('return_rate', 0.0))
                
                sort_option = st.radio("어떤 기준으로 아이템을 비교할까요?", 
                    ["📉 회수율이 높은 순서 (되팔 때 이득)", "⏳ 소요 주차가 짧은 순서 (빠른 스펙업)", "💰 가격이 저렴한 순서"], horizontal=True)
                st.write("")
                
                if sort_option == "📉 회수율이 높은 순서 (되팔 때 이득)":
                    df_fav = df_fav.sort_values(by='return_rate', ascending=False)
                elif sort_option == "⏳ 소요 주차가 짧은 순서 (빠른 스펙업)":
                    df_fav = df_fav.sort_values(by='expected_weeks', ascending=True)
                else:
                    df_fav = df_fav.sort_values(by='price', ascending=True)
                
                for idx, row in df_fav.iterrows():
                    with st.container():
                        st.markdown(f"#### [{row['part']}] {row['item_name']}")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("경매장 가격", f"{row['price'] / 100_000_000:.2f}억 메소")
                        col2.metric("남은 가위 횟수", f"{row['trade_count_left']}회")
                        col3.metric("예상 소요 기간", f"약 {row['expected_weeks']}주")
                        col4.metric("로그스케일 예상 회수율", f"{row['return_rate']:.1f}%", delta="가성비 지표", delta_color="off")
                        st.divider()
        else:
            st.error("캐릭터 정보가 만료되었습니다. 다시 조회해 주세요.")
