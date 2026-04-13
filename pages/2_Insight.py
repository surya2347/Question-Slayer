import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from collections import Counter

from core.utils import BLOOM_LEVELS

st.set_page_config(
    page_title="Insight - Question-Slayer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 사이드바 — 읽기 전용 설정 표시
with st.sidebar:
    st.markdown("### 📊 Insight")
    st.markdown("---")

    if "subject_label" not in st.session_state:
        st.session_state.subject_label = None

    if st.session_state.get("subject_label"):
        st.info(f"✅ {st.session_state.subject_label}")
    else:
        st.warning("⚙️ 과목 미설정")

    if st.session_state.get("interests"):
        st.caption(f"관심사: {', '.join(st.session_state.interests)}")


# ============================================================================
# 데이터 준비 — session_state.messages 에서 집계
# ============================================================================

def _collect_stats(messages: list) -> dict:
    """메시지 목록에서 Bloom 통계를 집계합니다."""
    assistant_msgs = [m for m in messages if m.get("role") == "assistant"]

    bloom_levels   = [m.get("bloom_level", 1) for m in assistant_msgs]
    # 관점 집계: graph가 확정한 assistant 메시지 기준
    perspectives   = [
        m.get("perspective")
        for m in assistant_msgs
        if m.get("perspective") is not None
    ]
    times          = [m.get("time", "") for m in assistant_msgs]

    return {
        "total": len(assistant_msgs),
        "bloom_levels": bloom_levels,
        "perspectives": perspectives,
        "times": times,
        "avg_bloom": round(sum(bloom_levels) / len(bloom_levels), 2) if bloom_levels else 0,
    }


# 세션 메시지 없으면 더미 데이터 사용
if "messages" not in st.session_state:
    st.session_state.messages = []

stats = _collect_stats(st.session_state.messages)
has_data = stats["total"] > 0

# ============================================================================
# 페이지 헤더
# ============================================================================

st.markdown("## 📊 학습 Insight")
st.markdown("질문 이력을 분석해 학습 수준 변화를 시각화합니다.")
st.markdown("---")

# ============================================================================
# 요약 통계 카드 (상단 3열)
# ============================================================================

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        label="총 질문 수",
        value=stats["total"] if has_data else 0,
    )

with c2:
    avg = stats["avg_bloom"] if has_data else 0
    avg_name = BLOOM_LEVELS.get(round(avg) or 1, {}).get("name_ko", "-")
    st.metric(
        label="평균 Bloom 레벨",
        value=f"Lv{avg:.1f}" if has_data else "-",
        help=avg_name,
    )

with c3:
    if has_data and stats["perspectives"]:
        top_p = Counter(stats["perspectives"]).most_common(1)[0][0]
        # 한국어 라벨 매핑
        p_label_map = {
            "concept": "💡 개념", "principle": "⚙️ 원리",
            "analogy": "🎭 비유", "relation": "🔗 관계",
            "usage": "🛠️ 활용", "caution": "⚠️ 주의사항",
        }
        top_p_label = p_label_map.get(top_p, top_p)
    else:
        top_p_label = "-"
    st.metric(label="가장 많이 사용한 관점", value=top_p_label)

st.markdown("---")

# ============================================================================
# 차트 영역 (2열)
# ============================================================================

col_left, col_right = st.columns(2, gap="large")

# ── 왼쪽: Bloom 단계 분포 막대 차트 ─────────────────────────
with col_left:
    st.markdown("#### Bloom 단계 분포")

    if has_data:
        # 1~6 전 단계 집계 (0인 단계도 표시)
        count_map = Counter(stats["bloom_levels"])
        levels = list(range(1, 7))
        counts = [count_map.get(lv, 0) for lv in levels]
        labels = [f"Lv{lv} {BLOOM_LEVELS[lv]['name_ko']}" for lv in levels]
        colors = ["#1e88e5", "#43a047", "#fb8c00", "#e53935", "#8e24aa", "#00897b"]

        fig_bar = go.Figure(go.Bar(
            x=labels,
            y=counts,
            marker_color=colors,
            text=counts,
            textposition="outside",
        ))
        fig_bar.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis=dict(title="질문 수", dtick=1),
            xaxis=dict(tickangle=-20),
            showlegend=False,
            plot_bgcolor="white",
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("💡 Chat 페이지에서 질문하면 Bloom 단계 분포가 표시됩니다.", icon=None)

# ── 오른쪽: 질문 수준 성장 곡선 ─────────────────────────────
with col_right:
    st.markdown("#### 질문 수준 성장 곡선")

    if has_data and len(stats["bloom_levels"]) >= 2:
        x_vals = list(range(1, len(stats["bloom_levels"]) + 1))
        y_vals = stats["bloom_levels"]
        level_names = [BLOOM_LEVELS[lv]["name_ko"] for lv in y_vals]

        fig_line = go.Figure(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines+markers",
            line=dict(color="#4f46e5", width=2),
            marker=dict(size=8, color="#4f46e5"),
            text=level_names,
            hovertemplate="%{x}번째 질문<br>Lv%{y} %{text}<extra></extra>",
        ))
        fig_line.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis=dict(
                title="Bloom 레벨",
                range=[0.5, 6.5],
                dtick=1,
                tickvals=list(range(1, 7)),
                ticktext=[f"Lv{i} {BLOOM_LEVELS[i]['name_ko']}" for i in range(1, 7)],
            ),
            xaxis=dict(title="질문 순서", dtick=1),
            plot_bgcolor="white",
        )
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
    elif has_data:
        # 질문이 정확히 1개인 경우 — 현재 레벨만 단일 포인트로 표시
        lv = stats["bloom_levels"][0]
        lv_name = BLOOM_LEVELS[lv]["name_ko"]
        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;align-items:center;
                        justify-content:center;height:180px;border:1.5px dashed #c7d2fe;
                        border-radius:12px;background:#f8f9ff;">
                <div style="font-size:2rem;font-weight:700;color:#4f46e5;">Lv{lv}</div>
                <div style="font-size:1rem;color:#6d28d9;margin-top:4px;">{lv_name}</div>
                <div style="font-size:0.85rem;color:#999;margin-top:10px;">
                    질문이 2개 이상 쌓이면 성장 곡선이 표시됩니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("💡 Chat 페이지에서 질문하면 성장 곡선이 표시됩니다.", icon=None)

# ============================================================================
# 최근 질문 이력
# ============================================================================

st.markdown("---")
st.markdown("#### 최근 질문 이력")

p_label_map = {
    "concept": "💡 개념", "principle": "⚙️ 원리",
    "analogy": "🎭 비유", "relation": "🔗 관계",
    "usage": "🛠️ 활용", "caution": "⚠️ 주의사항",
}
bloom_colors = {
    1: "#1e88e5", 2: "#43a047", 3: "#fb8c00",
    4: "#e53935", 5: "#8e24aa", 6: "#00897b",
}

# 사용자 질문 + 해당 AI 응답의 bloom 레벨 쌍으로 구성
pairs = []
msgs = st.session_state.messages
for i, msg in enumerate(msgs):
    if msg.get("role") == "user":
        # 다음 assistant 메시지 찾기
        bloom_lv = 1
        for j in range(i + 1, len(msgs)):
            if msgs[j].get("role") == "assistant":
                bloom_lv = msgs[j].get("bloom_level", 1)
                break
        pairs.append({
            "질문": msg["content"],
            "관점": p_label_map.get(msg.get("perspective", "concept"), "-"),
            "Bloom": bloom_lv,
            "시간": msg.get("time", ""),
        })

if pairs:
    # 최근 10개 역순 표시
    for p in reversed(pairs[-10:]):
        b_color = bloom_colors.get(p["Bloom"], "#333")
        badge = (
            f'<span style="background:#f5f5f5;color:{b_color};'
            f'border:1px solid {b_color};border-radius:6px;'
            f'padding:2px 8px;font-size:0.75rem;font-weight:bold;">'
            f'Lv{p["Bloom"]} {BLOOM_LEVELS[p["Bloom"]]["name_ko"]}</span>'
        )
        st.markdown(
            f'<div style="padding:8px 0;border-bottom:1px solid #eee;">'
            f'<span style="color:#666;font-size:0.8rem;">{p["시간"]} · {p["관점"]}</span> '
            f'{badge}<br>'
            f'<span style="font-size:0.95rem;">{p["질문"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("Chat 페이지에서 질문하면 이력이 여기에 표시됩니다.")
