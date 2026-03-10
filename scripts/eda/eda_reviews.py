"""
Bronze Reviews EDA
- 입력: output/bronze/reviews/20260310_reviews.parquet
- 출력: output/eda/reviews_eda.html (Plotly 인터랙티브)

실행:
  conda run -n final-project python scripts/eda/eda_reviews.py
  conda run -n final-project python scripts/eda/eda_reviews.py \
      --input output/bronze/reviews/20260310_reviews.parquet
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SILVER_GOODS = "output/silver/goods/20260310_goods_silver.parquet"
CHECKPOINT   = "output/checkpoint_reviews.json"
OUTPUT_PATH  = "output/eda/reviews_eda.html"


# ── 데이터 로드 및 전처리 ────────────────────────────────────────────────────────

def load_data(input_path: str):
    df = pd.read_parquet(input_path)
    df["written_at"] = pd.to_datetime(df["written_at_raw"], format="%Y.%m.%d", errors="coerce")
    df["content_len"] = df["content"].str.len()
    df["prefix"] = df["goods_id"].str[:2]
    df["year"]  = df["written_at"].dt.year
    df["month"] = df["written_at"].dt.to_period("M").astype(str)

    # pet_age → 개월 수 변환
    def to_months(val):
        if pd.isna(val):
            return None
        val = str(val).strip()
        if "개월" in val:
            try: return int(val.replace("개월", "").strip())
            except: return None
        elif "살" in val:
            try: return int(val.replace("살", "").strip()) * 12
            except: return None
        return None

    df["pet_age_months"] = df["pet_age_raw"].apply(to_months)

    # pet_weight → float
    def to_weight(val):
        if pd.isna(val):
            return None
        try:
            return float(str(val).replace("kg", "").strip())
        except:
            return None

    df["pet_weight_kg"] = df["pet_weight_raw"].apply(to_weight)

    return df


def load_silver_goods():
    sg = pd.read_parquet(SILVER_GOODS)
    canonical = sg[sg["is_canonical"] == True]
    non_gp = canonical[~canonical["goods_id"].str.startswith("GP")]
    return non_gp[["goods_id", "product_name", "prefix"]].set_index("goods_id")


# ── 색상 팔레트 ──────────────────────────────────────────────────────────────────

COLORS = {
    "GI": "#4C72B0", "GO": "#DD8452", "GS": "#55A868",
    "PI": "#C44E52", "GP": "#8172B2",
}
SCORE_COLORS = ["#d73027","#fc8d59","#fee090","#91bfdb","#4575b4"]


# ── 섹션별 차트 ──────────────────────────────────────────────────────────────────

def fig_collection_overview(df, sg):
    """SECTION 1: 수집 현황"""
    has_review = set(df["goods_id"].unique())
    no_review  = [g for g in sg.index if g not in has_review]

    figs = []

    # 1-1. 리뷰 있는/없는 상품 비율
    fig = go.Figure(go.Pie(
        labels=["리뷰 있음", "리뷰 없음"],
        values=[len(has_review), len(no_review)],
        marker_colors=["#4C72B0", "#cccccc"],
        hole=0.4,
        textinfo="label+percent+value",
    ))
    fig.update_layout(title="수집 상품 중 리뷰 보유 비율 (GP 제외)")
    figs.append(fig)

    # 1-2. prefix별 리뷰 수
    prefix_cnt = df["prefix"].value_counts().sort_index()
    fig = go.Figure(go.Bar(
        x=prefix_cnt.index.tolist(),
        y=prefix_cnt.values.tolist(),
        marker_color=[COLORS.get(p, "#999") for p in prefix_cnt.index],
        text=[f"{v:,}" for v in prefix_cnt.values],
        textposition="outside",
    ))
    fig.update_layout(title="prefix별 리뷰 수", xaxis_title="prefix", yaxis_title="리뷰 수")
    figs.append(fig)

    # 1-3. 상품별 리뷰 수 분포 (log scale histogram)
    per_goods = df.groupby("goods_id").size()
    fig = go.Figure(go.Histogram(
        x=per_goods.values,
        nbinsx=50,
        marker_color="#4C72B0",
        name="상품",
    ))
    fig.update_layout(
        title="상품별 리뷰 수 분포",
        xaxis_title="리뷰 수", yaxis_title="상품 수",
        xaxis_type="log",
    )
    figs.append(fig)

    # 1-4. 리뷰 수 Top 15 상품
    top15 = df.groupby("goods_id").size().sort_values(ascending=False).head(15)
    names = [sg["product_name"].get(gid, gid)[:25] + f" ({gid})" for gid in top15.index]
    fig = go.Figure(go.Bar(
        x=top15.values.tolist()[::-1],
        y=names[::-1],
        orientation="h",
        marker_color="#4C72B0",
        text=[f"{v:,}" for v in top15.values.tolist()[::-1]],
        textposition="outside",
    ))
    fig.update_layout(
        title="리뷰 수 Top 15 상품",
        xaxis_title="리뷰 수", height=500,
    )
    figs.append(fig)

    return figs


def fig_score(df):
    """SECTION 2: 점수 분포"""
    figs = []

    # 2-1. 전체 점수 분포
    score_cnt = df["score_raw"].value_counts().sort_index()
    total = score_cnt.sum()
    fig = go.Figure(go.Bar(
        x=[str(s) for s in score_cnt.index],
        y=score_cnt.values.tolist(),
        marker_color=["#d73027","#f46d43","#fdae61","#abd9e9","#74add1","#4575b4","#313695","#313695","#313695","#313695"],
        text=[f"{v:,}<br>({v/total*100:.1f}%)" for v in score_cnt.values],
        textposition="outside",
    ))
    fig.update_layout(title="전체 점수(score_raw) 분포", xaxis_title="점수", yaxis_title="리뷰 수")
    figs.append(fig)

    # 2-2. prefix별 평균 점수
    prefix_score = df.groupby("prefix")["score_raw"].agg(["mean","count"]).reset_index()
    fig = go.Figure(go.Bar(
        x=prefix_score["prefix"].tolist(),
        y=prefix_score["mean"].round(2).tolist(),
        marker_color=[COLORS.get(p,"#999") for p in prefix_score["prefix"]],
        text=[f"{v:.2f}" for v in prefix_score["mean"]],
        textposition="outside",
        error_y=dict(
            type="data",
            array=df.groupby("prefix")["score_raw"].std().reindex(prefix_score["prefix"]).tolist(),
            visible=True,
        ),
    ))
    fig.update_layout(
        title="prefix별 평균 점수 (±1σ)",
        xaxis_title="prefix", yaxis_title="평균 점수",
        yaxis_range=[0, 6],
    )
    figs.append(fig)

    # 2-3. 점수별 purchase_label 비율
    score_label = df.groupby(["score_raw","purchase_label"]).size().unstack(fill_value=0)
    for col in ["first","repeat"]:
        if col not in score_label.columns:
            score_label[col] = 0
    score_pct = score_label.div(score_label.sum(axis=1), axis=0) * 100
    fig = go.Figure()
    for label, color in [("first","#4C72B0"),("repeat","#DD8452")]:
        fig.add_trace(go.Bar(
            name=label,
            x=[str(s) for s in score_pct.index],
            y=score_pct[label].round(1).tolist(),
            marker_color=color,
        ))
    fig.update_layout(
        barmode="stack",
        title="점수별 구매 유형 비율 (first vs repeat)",
        xaxis_title="점수", yaxis_title="%",
    )
    figs.append(fig)

    return figs


def fig_timeline(df):
    """SECTION 3: 시계열"""
    figs = []

    # 3-1. 연도별 리뷰 수
    year_cnt = df["year"].value_counts().sort_index().dropna()
    fig = go.Figure(go.Bar(
        x=[str(int(y)) for y in year_cnt.index],
        y=year_cnt.values.tolist(),
        marker_color="#4C72B0",
        text=[f"{v:,}" for v in year_cnt.values],
        textposition="outside",
    ))
    fig.update_layout(title="연도별 리뷰 수", xaxis_title="연도", yaxis_title="리뷰 수")
    figs.append(fig)

    # 3-2. 최근 24개월 월별 추이
    recent = df[df["written_at"] >= "2024-01-01"].copy()
    month_cnt = recent.groupby("month").size().reset_index(name="count").sort_values("month")
    fig = go.Figure(go.Scatter(
        x=month_cnt["month"].tolist(),
        y=month_cnt["count"].tolist(),
        mode="lines+markers",
        line_color="#4C72B0",
        fill="tozeroy",
        fillcolor="rgba(76,114,176,0.15)",
        text=[f"{v:,}" for v in month_cnt["count"]],
    ))
    fig.update_layout(
        title="월별 리뷰 수 (2024년 이후)",
        xaxis_title="월", yaxis_title="리뷰 수",
    )
    figs.append(fig)

    return figs


def fig_content(df):
    """SECTION 4: 리뷰 텍스트"""
    figs = []

    # 4-1. 텍스트 길이 분포
    bins   = [0, 1, 10, 30, 50, 100, 200, 10000]
    labels = ["0", "1~9", "10~29", "30~49", "50~99", "100~199", "200+"]
    df["len_bin"] = pd.cut(df["content_len"], bins=bins, labels=labels, right=False)
    bin_cnt = df["len_bin"].value_counts().sort_index()
    total = bin_cnt.sum()
    fig = go.Figure(go.Bar(
        x=labels,
        y=[bin_cnt.get(l, 0) for l in labels],
        marker_color="#55A868",
        text=[f"{bin_cnt.get(l,0):,}<br>({bin_cnt.get(l,0)/total*100:.1f}%)" for l in labels],
        textposition="outside",
    ))
    fig.update_layout(title="리뷰 텍스트 길이 분포 (글자 수)", xaxis_title="글자 수 구간", yaxis_title="리뷰 수")
    figs.append(fig)

    # 4-2. prefix별 텍스트 길이 box
    fig = go.Figure()
    for prefix in sorted(df["prefix"].unique()):
        sub = df[df["prefix"] == prefix]["content_len"]
        fig.add_trace(go.Box(
            y=sub.tolist(),
            name=prefix,
            marker_color=COLORS.get(prefix, "#999"),
            boxmean=True,
        ))
    fig.update_layout(
        title="prefix별 리뷰 텍스트 길이 분포",
        yaxis_title="글자 수",
        yaxis_range=[0, 200],
    )
    figs.append(fig)

    return figs


def fig_pet_profile(df):
    """SECTION 5: 펫 프로필"""
    figs = []

    # 5-1. 프로필 필드 보유율
    fields = ["pet_name","pet_gender","pet_age_raw","pet_weight_raw","pet_breed","review_info"]
    labels = ["이름","성별","나이","체중","품종","review_info"]
    rates  = [df[f].notna().mean() * 100 for f in fields]
    counts = [df[f].notna().sum() for f in fields]
    fig = go.Figure(go.Bar(
        x=labels, y=rates,
        marker_color="#4C72B0",
        text=[f"{r:.1f}%<br>({c:,})" for r, c in zip(rates, counts)],
        textposition="outside",
    ))
    fig.update_layout(
        title="펫 프로필 필드 보유율 (%)",
        xaxis_title="필드", yaxis_title="%",
        yaxis_range=[0, 65],
    )
    figs.append(fig)

    # 5-2. 성별 분포
    gender = df["pet_gender"].str.replace(r"[()]", "", regex=True).str.strip()
    gender_cnt = gender.value_counts(dropna=False).head(5)
    fig = go.Figure(go.Bar(
        x=gender_cnt.index.fillna("미등록").tolist(),
        y=gender_cnt.values.tolist(),
        marker_color=["#4C72B0","#DD8452","#cccccc","#cccccc","#cccccc"],
        text=[f"{v:,}" for v in gender_cnt.values],
        textposition="outside",
    ))
    fig.update_layout(title="펫 성별 분포", xaxis_title="성별", yaxis_title="리뷰 수")
    figs.append(fig)

    # 5-3. 나이 분포 (개월 수, 프로필 있는 것만)
    age = df["pet_age_months"].dropna()
    fig = go.Figure(go.Histogram(
        x=age.tolist(),
        nbinsx=30,
        marker_color="#55A868",
        name="나이",
    ))
    fig.update_layout(
        title="펫 나이 분포 (개월 수, 프로필 보유 리뷰)",
        xaxis_title="개월 수", yaxis_title="리뷰 수",
    )
    figs.append(fig)

    # 5-4. 품종 Top 20
    breed = df["pet_breed"].dropna()
    breed_cnt = breed.value_counts().head(20)
    fig = go.Figure(go.Bar(
        x=breed_cnt.values.tolist()[::-1],
        y=breed_cnt.index.tolist()[::-1],
        orientation="h",
        marker_color="#C44E52",
        text=[f"{v:,}" for v in breed_cnt.values.tolist()[::-1]],
        textposition="outside",
    ))
    fig.update_layout(
        title="품종 Top 20", xaxis_title="리뷰 수", height=600,
    )
    figs.append(fig)

    # 5-5. 체중 분포
    weight = df["pet_weight_kg"].dropna()
    weight = weight[weight <= 80]  # 이상치 제거
    fig = go.Figure(go.Histogram(
        x=weight.tolist(),
        nbinsx=40,
        marker_color="#8172B2",
    ))
    fig.update_layout(
        title="펫 체중 분포 (kg, ≤80kg, 프로필 보유 리뷰)",
        xaxis_title="체중 (kg)", yaxis_title="리뷰 수",
    )
    figs.append(fig)

    return figs


def fig_purchase(df):
    """SECTION 6: 구매 유형"""
    figs = []

    # 6-1. 전체 purchase_label 분포
    pl = df["purchase_label"].value_counts(dropna=False)
    fig = go.Figure(go.Pie(
        labels=pl.index.fillna("미표기").tolist(),
        values=pl.values.tolist(),
        marker_colors=["#4C72B0","#DD8452","#cccccc"],
        hole=0.4,
        textinfo="label+percent+value",
    ))
    fig.update_layout(title="구매 유형 (first vs repeat)")
    figs.append(fig)

    # 6-2. prefix별 first/repeat 비율
    pl_prefix = df.groupby(["prefix","purchase_label"]).size().unstack(fill_value=0)
    for col in ["first","repeat"]:
        if col not in pl_prefix.columns:
            pl_prefix[col] = 0
    pl_pct = pl_prefix.div(pl_prefix.sum(axis=1), axis=0) * 100
    fig = go.Figure()
    for label, color in [("first","#4C72B0"),("repeat","#DD8452")]:
        fig.add_trace(go.Bar(
            name=label,
            x=pl_pct.index.tolist(),
            y=pl_pct[label].round(1).tolist(),
            marker_color=color,
            text=[f"{v:.1f}%" for v in pl_pct[label]],
            textposition="inside",
        ))
    fig.update_layout(
        barmode="stack",
        title="prefix별 구매 유형 비율",
        xaxis_title="prefix", yaxis_title="%",
    )
    figs.append(fig)

    # 6-3. 구매 유형별 평균 점수
    score_by_pl = df.groupby("purchase_label")["score_raw"].agg(["mean","count"]).reset_index()
    fig = go.Figure(go.Bar(
        x=score_by_pl["purchase_label"].tolist(),
        y=score_by_pl["mean"].round(3).tolist(),
        marker_color=["#4C72B0","#DD8452"],
        text=[f"{v:.3f}<br>(n={c:,})" for v, c in zip(score_by_pl["mean"], score_by_pl["count"])],
        textposition="outside",
    ))
    fig.update_layout(
        title="구매 유형별 평균 점수",
        xaxis_title="구매 유형", yaxis_title="평균 점수",
        yaxis_range=[4.5, 5.2],
    )
    figs.append(fig)

    return figs


def fig_review_info(df):
    """SECTION 7: review_info (용품 리뷰 만족도)"""
    figs = []

    # review_info 있는 것만
    ri = df["review_info"].dropna()

    # 7-1. 키별 등장 빈도
    keys = []
    for v in ri:
        try:
            keys.extend(json.loads(v).keys())
        except:
            pass
    key_cnt = Counter(keys).most_common(15)
    k_labels = [k for k, _ in key_cnt]
    k_vals   = [v for _, v in key_cnt]
    fig = go.Figure(go.Bar(
        x=k_vals[::-1], y=k_labels[::-1],
        orientation="h",
        marker_color="#55A868",
        text=[f"{v:,}" for v in k_vals[::-1]],
        textposition="outside",
    ))
    fig.update_layout(
        title="review_info 항목별 등장 빈도 Top 15",
        xaxis_title="등장 횟수", height=450,
    )
    figs.append(fig)

    # 7-2. prefix별 review_info 보유율
    ri_rate = df.groupby("prefix").apply(lambda g: g["review_info"].notna().mean() * 100).reset_index()
    ri_rate.columns = ["prefix", "rate"]
    fig = go.Figure(go.Bar(
        x=ri_rate["prefix"].tolist(),
        y=ri_rate["rate"].round(1).tolist(),
        marker_color=[COLORS.get(p,"#999") for p in ri_rate["prefix"]],
        text=[f"{v:.1f}%" for v in ri_rate["rate"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="prefix별 review_info 보유율",
        xaxis_title="prefix", yaxis_title="%", yaxis_range=[0, 100],
    )
    figs.append(fig)

    return figs


# ── HTML 렌더링 ──────────────────────────────────────────────────────────────────

SECTION_TITLES = {
    1: "수집 현황",
    2: "점수 분포",
    3: "시계열 트렌드",
    4: "리뷰 텍스트",
    5: "펫 프로필",
    6: "구매 유형 (purchase_label)",
    7: "review_info (용품 리뷰)",
}

ISSUES_HTML = """
<h2 style="margin:32px 0 8px;padding:8px 16px;background:#c0392b;color:#fff;border-radius:6px">
  데이터 품질 이슈 (docs/data/05_reviews_eda_issues.md)
</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">

  <div style="background:#fff;border-radius:10px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:5px solid #e74c3c">
    <div style="font-weight:700;font-size:1rem;margin-bottom:8px">
      🔴 이슈 1 — GO 리뷰 수집 실패 235개 <span style="font-size:.8rem;font-weight:400;color:#888">[P2]</span>
    </div>
    <p style="margin:0;font-size:.9rem;color:#444;line-height:1.6">
      goods API에 <code>review_count &gt; 0</code>이지만 수집 결과 0건인 상품 235개.
      GO(옵션 선택형) 상품이 집중적으로 포함됨.<br>
      <b>추정 원인</b>: <code>goodsCstrtTpCd="ITEM"</code>이 GO에 미적용되거나
      <code>optGoodsId</code> 지정 필요.<br>
      <b>대응</b>: Silver에 <code>review_collected=False</code> 플래그 추가, Phase 2 재수집.
    </p>
  </div>

  <div style="background:#fff;border-radius:10px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:5px solid #e67e22">
    <div style="font-weight:700;font-size:1rem;margin-bottom:8px">
      🟠 이슈 2 — 5점 리뷰 77% 극단 편향 <span style="font-size:.8rem;font-weight:400;color:#888">[P0]</span>
    </div>
    <p style="margin:0;font-size:.9rem;color:#444;line-height:1.6">
      전체 131,147건 중 5점이 101,046건(77%). 4점 이상 93%.<br>
      <b>원인</b>: 자기선택 편향 + 포인트 지급 구조.<br>
      <b>대응</b>: <code>score_raw</code> 단독 랭킹 사용 금지.
      <code>popularity_score</code>에 텍스트 기반 <code>sentiment_score</code> 가중치 사용.
      감성 분석 모델 학습 시 클래스 가중치 조정 필요.
    </p>
  </div>

  <div style="background:#fff;border-radius:10px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:5px solid #f39c12">
    <div style="font-weight:700;font-size:1rem;margin-bottom:8px">
      🟡 이슈 3 — pet_gender 빈 문자열 3,275건 <span style="font-size:.8rem;font-weight:400;color:#888">[P1]</span>
    </div>
    <p style="margin:0;font-size:.9rem;color:#444;line-height:1.6">
      <code>pet_gender</code>에 <code>None</code> 대신 <code>""</code>(빈 문자열) 저장된 레코드 3,275건.
      <code>pet_name</code>, <code>pet_age_raw</code>는 정상.<br>
      <b>원인</b>: 파서에서 <code>gender_el</code> 없을 때 <code>get_text()</code>가 빈 문자열 반환.<br>
      <b>대응</b>: Silver ETL에서 <code>"" → NULL</code> 변환.
      파서도 <code>or None</code> 추가.
    </p>
  </div>

  <div style="background:#fff;border-radius:10px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:5px solid #27ae60">
    <div style="font-weight:700;font-size:1rem;margin-bottom:8px">
      ✅ 이슈 4 — PI 리뷰 과다 집계 의심 → 정상 확인 <span style="font-size:.8rem;font-weight:400;color:#888">[이슈 없음]</span>
    </div>
    <p style="margin:0;font-size:.9rem;color:#444;line-height:1.6">
      PI 상품당 평균 229.2건으로 GI(39.7건) 대비 5.8배. GP 집계 과다와 유사해 의심했으나,
      <b>수집 수 ≈ goods API <code>review_count</code></b>로 일치 확인.<br>
      PI는 단품 구독 상품으로 리뷰가 실제로 많은 인기 상품. <code>review_count_source=direct</code> 유지.
    </p>
  </div>

</div>
"""


def render_html(all_figs: list[tuple[int, go.Figure]], output_path: str, summary: dict) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    blocks = []
    include_plotlyjs = True

    # 요약 카드
    blocks.append(f"""
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin:24px 0">
      <div class="card"><div class="val">{summary['total_reviews']:,}</div><div class="lbl">전체 리뷰</div></div>
      <div class="card"><div class="val">{summary['unique_goods']:,}</div><div class="lbl">리뷰 보유 상품</div></div>
      <div class="card"><div class="val">{summary['unique_authors']:,}</div><div class="lbl">고유 작성자</div></div>
      <div class="card"><div class="val">{summary['coverage_pct']:.1f}%</div><div class="lbl">수집 대상 커버율</div></div>
      <div class="card"><div class="val">{summary['avg_score']:.2f}</div><div class="lbl">평균 점수</div></div>
      <div class="card"><div class="val">{summary['pet_profile_pct']:.1f}%</div><div class="lbl">펫 프로필 보유율</div></div>
    </div>
    """)

    # 데이터 품질 이슈
    blocks.append(ISSUES_HTML)

    cur_section = 0
    for section, fig in all_figs:
        if section != cur_section:
            if cur_section != 0:
                blocks.append("</div>")
            cur_section = section
            blocks.append(f"""
            <h2 style="margin:32px 0 8px;padding:8px 16px;
                       background:#2c3e50;color:#fff;border-radius:6px">
              SECTION {section} — {SECTION_TITLES[section]}
            </h2>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
            """)

        div_html = fig.to_html(
            full_html=False,
            include_plotlyjs="cdn" if not include_plotlyjs else True,
            div_id=f"fig_{len(blocks)}",
            default_width="700px",
            default_height="420px",
        )
        include_plotlyjs = False
        blocks.append(f'<div style="flex:0 0 auto">{div_html}</div>')

    if cur_section != 0:
        blocks.append("</div>")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Bronze Reviews EDA</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 24px; background: #f5f5f5; }}
  h1   {{ color: #2c3e50; border-bottom: 3px solid #2c3e50; padding-bottom: 8px; }}
  .card {{
    background: #fff; border-radius: 10px; padding: 20px 28px;
    box-shadow: 0 2px 8px rgba(0,0,0,.08); text-align: center; min-width: 130px;
  }}
  .val {{ font-size: 2rem; font-weight: 700; color: #2c3e50; }}
  .lbl {{ font-size: .85rem; color: #888; margin-top: 4px; }}
</style>
</head>
<body>
<h1>Bronze Reviews EDA</h1>
<p style="color:#666">수집일: 2026-03-10 &nbsp;|&nbsp; GP 제외 (GI/GO/GS/PI)</p>
{''.join(blocks)}
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"저장 완료: {output_path}")


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(input_path: str) -> None:
    print(f"[eda_reviews] 데이터 로드 중: {input_path}")
    df = load_data(input_path)
    sg = load_silver_goods()

    print(f"  리뷰: {len(df):,}건 / 상품: {df['goods_id'].nunique():,}개 / 작성자: {df['author_nickname'].nunique():,}명")

    has_review = df["goods_id"].nunique()
    total_target = len(sg[~sg.index.str.startswith("GP")])

    summary = {
        "total_reviews":   len(df),
        "unique_goods":    has_review,
        "unique_authors":  df["author_nickname"].nunique(),
        "coverage_pct":    has_review / total_target * 100,
        "avg_score":       df["score_raw"].mean(),
        "pet_profile_pct": df["pet_name"].notna().mean() * 100,
    }

    print("  차트 생성 중...")
    all_figs: list[tuple[int, go.Figure]] = []

    for fig in fig_collection_overview(df, sg): all_figs.append((1, fig))
    for fig in fig_score(df):                   all_figs.append((2, fig))
    for fig in fig_timeline(df):                all_figs.append((3, fig))
    for fig in fig_content(df):                 all_figs.append((4, fig))
    for fig in fig_pet_profile(df):             all_figs.append((5, fig))
    for fig in fig_purchase(df):                all_figs.append((6, fig))
    for fig in fig_review_info(df):             all_figs.append((7, fig))

    render_html(all_figs, OUTPUT_PATH, summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="output/bronze/reviews/20260310_reviews.parquet",
        help="Bronze reviews parquet 경로",
    )
    args = parser.parse_args()
    main(args.input)
