"""
Bronze Goods EDA — Plotly 인터랙티브 리포트
실행: conda run -n final-project python scripts/eda_goods.py
출력: output/eda/goods_eda.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, "scripts")
from config import CATEGORIES

OUTPUT_DIR = Path("output/eda")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT = "output/checkpoint_detail_images.json"
PARQUET    = "output/bronze/goods/20260309_goods.parquet"

# ── 데이터 로드 및 전처리 ─────────────────────────────────
df = pd.read_parquet(PARQUET)

df["price"]          = pd.to_numeric(df["price_raw"],          errors="coerce")
df["discount_price"] = pd.to_numeric(df["discount_price_raw"], errors="coerce")
df["rating"]         = pd.to_numeric(df["rating_raw"],         errors="coerce") / 2
df["review_count"]   = pd.to_numeric(df["review_count_raw"],   errors="coerce")
df["soldout"]        = df["sold_out_yn"] == "Y"
df["species"]        = df["cate_cd_l"].map({"12564": "강아지", "12565": "고양이"})
df["discount_rate"]  = ((df["price"] - df["discount_price"]) / df["price"] * 100).clip(0, 100)

with open(CHECKPOINT) as f:
    ckpt = json.load(f)
df["has_detail_img"] = df["goods_id"].map(lambda x: bool(ckpt.get(x)))
df["detail_img_cnt"] = df["goods_id"].map(lambda x: len(ckpt.get(x, [])))

cate_map = {disp: name for _, _, disp, name in CATEGORIES}
df["subcate_name"]  = df["disp_clsf_no"].map(cate_map)
df["midcate_name"]  = df["subcate_name"].str.split("_").str[1]

df_u = df.drop_duplicates(subset="goods_id").copy()
df_u["prefix"] = df_u["goods_id"].str[:2]

PREFIX_LABEL = {
    "GI": "GI (단품)",
    "GP": "GP (용량묶음)",
    "GO": "GO (옵션선택)",
    "GS": "GS (세트/번들)",
    "PI": "PI (플랜)",
}
df_u["prefix_label"] = df_u["prefix"].map(PREFIX_LABEL)

PREFIX_COLOR = {
    "GI (단품)":    "#4C72B0",
    "GP (용량묶음)": "#DD8452",
    "GO (옵션선택)": "#55A868",
    "GS (세트/번들)":"#C44E52",
    "PI (플랜)":    "#8172B3",
}
SPECIES_COLOR = {"강아지": "#4C72B0", "고양이": "#DD8452"}
TEMPLATE = "plotly_white"

print(f"전체 행: {len(df):,}  |  고유 상품: {len(df_u):,}")

figs: list[tuple[str, go.Figure]] = []  # (제목, fig)


# ═══════════════════════════════════════════════════════════
# SECTION 1 — 전체 개요
# ═══════════════════════════════════════════════════════════

# 1. 대분류별 고유 상품 수
cnt = df_u["species"].value_counts().reset_index()
cnt.columns = ["species", "count"]
fig = px.bar(cnt, x="species", y="count", color="species",
             color_discrete_map=SPECIES_COLOR, text="count",
             title="대분류별 고유 상품 수", template=TEMPLATE,
             labels={"species": "", "count": "상품 수"})
fig.update_traces(textposition="outside")
fig.update_layout(showlegend=False)
figs.append(("대분류별 고유 상품 수", fig))

# 2. 소분류별 상품 수 TOP 20
top20 = df_u["subcate_name"].value_counts().head(20).reset_index()
top20.columns = ["subcate_name", "count"]
top20["species"] = top20["subcate_name"].str.split("_").str[0]
fig = px.bar(top20, x="count", y="subcate_name", color="species",
             color_discrete_map=SPECIES_COLOR, orientation="h",
             title="소분류별 고유 상품 수 TOP 20", template=TEMPLATE,
             labels={"subcate_name": "", "count": "상품 수"}, text="count")
fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=560)
figs.append(("소분류별 상품 수 TOP 20", fig))

# 3. 브랜드 TOP 20
top_b = df_u["brand_name"].value_counts().head(20).reset_index()
top_b.columns = ["brand_name", "count"]
fig = px.bar(top_b, x="count", y="brand_name", orientation="h",
             title="브랜드별 상품 수 TOP 20", template=TEMPLATE,
             labels={"brand_name": "", "count": "상품 수"},
             text="count", color_discrete_sequence=["#2ca02c"])
fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=560)
figs.append(("브랜드 TOP 20", fig))


# ═══════════════════════════════════════════════════════════
# SECTION 2 — 접두사(상품 유형) 분석
# ═══════════════════════════════════════════════════════════

# 4. 접두사별 상품 수
prefix_cnt = df_u["prefix_label"].value_counts().reset_index()
prefix_cnt.columns = ["prefix_label", "count"]
fig = px.bar(prefix_cnt, x="prefix_label", y="count", color="prefix_label",
             color_discrete_map=PREFIX_COLOR, text="count",
             title="접두사(상품 유형)별 고유 상품 수", template=TEMPLATE,
             labels={"prefix_label": "", "count": "상품 수"})
fig.update_traces(textposition="outside")
fig.update_layout(showlegend=False)
figs.append(("접두사별 상품 수", fig))

# 5. 접두사별 평균 리뷰 수 / 품절률 / 상세이미지 보유율
prefix_stats = df_u.groupby("prefix_label").agg(
    avg_review   =("review_count", lambda x: x[x > 0].mean()),
    soldout_rate =("soldout",       "mean"),
    img_rate     =("has_detail_img","mean"),
    count        =("goods_id",      "count"),
).reset_index()
prefix_stats["soldout_pct"] = prefix_stats["soldout_rate"] * 100
prefix_stats["img_pct"]     = prefix_stats["img_rate"] * 100

fig = make_subplots(rows=1, cols=3,
                    subplot_titles=["평균 리뷰 수", "품절률 (%)", "상세이미지 보유율 (%)"])

for col_i, (y_col, fmt) in enumerate([("avg_review", ".0f"), ("soldout_pct", ".1f"), ("img_pct", ".1f")], 1):
    for _, row in prefix_stats.iterrows():
        fig.add_trace(go.Bar(
            x=[row["prefix_label"]], y=[row[y_col]],
            name=row["prefix_label"],
            marker_color=PREFIX_COLOR[row["prefix_label"]],
            text=[f"{row[y_col]:{fmt}}"],
            textposition="outside",
            showlegend=(col_i == 1),
            hovertemplate=f"{row['prefix_label']}<br>{y_col}: %{{y:{fmt}}}<extra></extra>",
        ), row=1, col=col_i)

fig.update_layout(title="접두사별 핵심 지표 비교", template=TEMPLATE,
                  height=420, barmode="group", legend_title="상품 유형")
figs.append(("접두사별 핵심 지표 비교", fig))

# 6. 접두사별 중분류 분포 (stacked bar)
cross = df_u.groupby(["prefix_label", "midcate_name"]).size().reset_index(name="count")
fig = px.bar(cross, x="prefix_label", y="count", color="midcate_name",
             title="접두사별 중분류 분포", template=TEMPLATE,
             labels={"prefix_label": "상품 유형", "count": "상품 수", "midcate_name": "중분류"},
             barmode="stack")
fig.update_layout(height=450)
figs.append(("접두사별 중분류 분포", fig))

# 7. 접두사별 가격 분포 (box)
price_valid = df_u[df_u["discount_price"] > 0].copy()
fig = px.box(price_valid, x="prefix_label", y="discount_price",
             color="prefix_label", color_discrete_map=PREFIX_COLOR,
             title="접두사별 할인가 분포", template=TEMPLATE,
             labels={"prefix_label": "상품 유형", "discount_price": "할인가 (원)"},
             points=False)
fig.update_yaxes(range=[0, 150000])
fig.update_layout(showlegend=False, height=420)
figs.append(("접두사별 할인가 분포", fig))

# 8. 접두사별 평점 분포 (box, 리뷰 있는 상품만)
rating_valid = df_u[df_u["rating"] > 0].copy()
fig = px.box(rating_valid, x="prefix_label", y="rating",
             color="prefix_label", color_discrete_map=PREFIX_COLOR,
             title="접두사별 평점 분포 (리뷰 있는 상품)", template=TEMPLATE,
             labels={"prefix_label": "상품 유형", "rating": "평점 (5점)"},
             points=False)
fig.update_layout(showlegend=False, height=420)
figs.append(("접두사별 평점 분포", fig))


# ═══════════════════════════════════════════════════════════
# SECTION 3 — 가격 / 평점 / 리뷰
# ═══════════════════════════════════════════════════════════

# 9. 가격 분포
fig = make_subplots(rows=1, cols=2,
                    subplot_titles=["할인가 분포 (10만원 이하)", "할인율 분포 (할인 있는 상품)"])
fig.add_trace(go.Histogram(
    x=df_u["discount_price"].dropna().clip(upper=100000),
    nbinsx=50, name="할인가", marker_color="#4C72B0",
    hovertemplate="가격: %{x}원<br>상품 수: %{y}"), row=1, col=1)
disc = df_u["discount_rate"].dropna()
fig.add_trace(go.Histogram(
    x=disc[disc > 0], nbinsx=30, name="할인율", marker_color="#DD8452",
    hovertemplate="할인율: %{x:.1f}%<br>상품 수: %{y}"), row=1, col=2)
fig.update_layout(title="가격 분포", template=TEMPLATE, showlegend=False, height=400)
fig.update_xaxes(title_text="원", row=1, col=1)
fig.update_xaxes(title_text="%", row=1, col=2)
figs.append(("가격 분포", fig))

# 10. 평점 분포
rating_v = df_u["rating"].dropna()
rating_v = rating_v[rating_v > 0]
avg_r = rating_v.mean()
fig = px.histogram(rating_v, nbins=25, template=TEMPLATE,
                   title=f"평점 분포 (5점 만점 · 리뷰 있는 상품 {len(rating_v):,}개)",
                   labels={"value": "평점"}, color_discrete_sequence=["#55A868"])
fig.add_vline(x=avg_r, line_dash="dash", line_color="red",
              annotation_text=f"평균 {avg_r:.2f}", annotation_position="top right")
fig.update_layout(xaxis_title="평점", yaxis_title="상품 수", showlegend=False)
figs.append(("평점 분포", fig))

# 11. 리뷰 수 분포
fig = make_subplots(rows=1, cols=2,
                    subplot_titles=["리뷰 수 분포 (500개 이하)", "리뷰 수 분포 (log10)"])
rv = df_u["review_count"].dropna()
fig.add_trace(go.Histogram(x=rv[rv <= 500], nbinsx=50, marker_color="#C44E52",
                           hovertemplate="리뷰 수: %{x}<br>상품 수: %{y}"), row=1, col=1)
rv_log = rv[rv > 0].apply(math.log10)
fig.add_trace(go.Histogram(x=rv_log, nbinsx=30, marker_color="#8172B3",
                           hovertemplate="log10: %{x:.2f}<br>상품 수: %{y}"), row=1, col=2)
fig.update_layout(title="리뷰 수 분포", template=TEMPLATE, showlegend=False, height=400)
figs.append(("리뷰 수 분포", fig))

# 12. 평점 × 리뷰 수 산점도
sample = df_u[(df_u["rating"] > 0) & (df_u["review_count"] > 0)].copy()
sample["review_cap"] = sample["review_count"].clip(upper=2000)
fig = px.scatter(sample, x="review_cap", y="rating", color="prefix_label",
                 color_discrete_map=PREFIX_COLOR, opacity=0.45,
                 hover_data={"goods_id": True, "product_name": True,
                             "brand_name": True, "review_count": True,
                             "review_cap": False},
                 title="평점 × 리뷰 수 산점도 (리뷰 수 2000 cap)",
                 template=TEMPLATE,
                 labels={"review_cap": "리뷰 수", "rating": "평점", "prefix_label": "상품 유형"})
figs.append(("평점 × 리뷰 수 산점도", fig))

# 13. 중분류별 평균 평점
midcate_r = (
    df_u[df_u["rating"] > 0]
    .groupby(["species", "midcate_name"])["rating"]
    .agg(mean="mean", count="count")
    .reset_index()
)
fig = px.bar(midcate_r, x="midcate_name", y="mean", color="species",
             barmode="group", color_discrete_map=SPECIES_COLOR,
             hover_data={"count": True, "mean": ":.2f"},
             title="중분류별 평균 평점", template=TEMPLATE,
             labels={"midcate_name": "중분류", "mean": "평균 평점", "count": "상품 수"})
figs.append(("중분류별 평균 평점", fig))


# ═══════════════════════════════════════════════════════════
# SECTION 4 — 품절 / 상세 이미지
# ═══════════════════════════════════════════════════════════

# 14. 품절 현황
fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "bar"}]],
                    subplot_titles=["전체 품절 비율", "대분류별 품절률 (%)"])
soldout_cnt = df_u["soldout"].value_counts()
fig.add_trace(go.Pie(
    labels=["판매중", "품절"], values=soldout_cnt.values,
    marker_colors=["#4C72B0", "#C44E52"],
    hovertemplate="%{label}: %{value}개 (%{percent})<extra></extra>"), row=1, col=1)
sp_soldout = df_u.groupby("species")["soldout"].mean() * 100
fig.add_trace(go.Bar(
    x=sp_soldout.index, y=sp_soldout.values,
    marker_color=["#4C72B0", "#DD8452"],
    text=[f"{v:.1f}%" for v in sp_soldout.values], textposition="outside",
    hovertemplate="%{x}: %{y:.1f}%<extra></extra>"), row=1, col=2)
fig.update_layout(title="품절 현황", template=TEMPLATE, showlegend=False, height=400)
fig.update_yaxes(title_text="%", row=1, col=2)
figs.append(("품절 현황", fig))

# 15. 상세 이미지 보유 현황
fig = make_subplots(rows=1, cols=2,
                    specs=[[{"type": "pie"}, {"type": "histogram"}]],
                    subplot_titles=["상세 이미지 보유 비율", "이미지 수 분포 (보유 상품)"])
img_cnt = df_u["has_detail_img"].value_counts()
fig.add_trace(go.Pie(
    labels=["이미지 있음", "이미지 없음"], values=img_cnt.values,
    marker_colors=["#55A868", "#aaaaaa"],
    hovertemplate="%{label}: %{value}개 (%{percent})<extra></extra>"), row=1, col=1)
img_has = df_u[df_u["detail_img_cnt"] > 0]["detail_img_cnt"]
fig.add_trace(go.Histogram(x=img_has, nbinsx=30, marker_color="#55A868",
                           hovertemplate="이미지 수: %{x}<br>상품 수: %{y}"), row=1, col=2)
fig.update_layout(title="상세 이미지 보유 현황", template=TEMPLATE, showlegend=False, height=400)
figs.append(("상세 이미지 보유 현황", fig))


# ═══════════════════════════════════════════════════════════
# SECTION 5 — 데이터 품질 이슈
# ═══════════════════════════════════════════════════════════

# 16. 접두사별 품절률 — GO 0% 이슈
prefix_soldout = df_u.groupby("prefix_label").agg(
    total   =("goods_id", "count"),
    soldout =("soldout",  "sum"),
).reset_index()
prefix_soldout["soldout_pct"] = prefix_soldout["soldout"] / prefix_soldout["total"] * 100
fig = px.bar(prefix_soldout, x="prefix_label", y="soldout_pct",
             color="prefix_label", color_discrete_map=PREFIX_COLOR,
             text=prefix_soldout.apply(lambda r: f"{r['soldout_pct']:.1f}%<br>({int(r['soldout'])}/{int(r['total'])})", axis=1),
             title="⚠️ 접두사별 품절률 — GO는 품절 0% (soldout_yn 신뢰 불가)",
             template=TEMPLATE,
             labels={"prefix_label": "상품 유형", "soldout_pct": "품절률 (%)"})
fig.update_traces(textposition="outside")
fig.update_layout(showlegend=False, height=420, yaxis_range=[0, 20])
figs.append(("접두사별 품절률 (GO 이슈)", fig))

# 17. GP 리뷰 뻥튀기 — 접두사별 리뷰 수 박스플롯 (log)
rv_valid = df_u[df_u["review_count"] > 0].copy()
rv_valid["review_log"] = rv_valid["review_count"].apply(math.log10)
fig = px.box(rv_valid, x="prefix_label", y="review_log",
             color="prefix_label", color_discrete_map=PREFIX_COLOR,
             points="outliers",
             hover_data={"goods_id": True, "product_name": True, "review_count": True},
             title="⚠️ 접두사별 리뷰 수 분포 (log10) — GP/PI 극단값 주의",
             template=TEMPLATE,
             labels={"prefix_label": "상품 유형", "review_log": "log10(리뷰 수)"})
fig.update_layout(showlegend=False, height=450)
figs.append(("접두사별 리뷰 수 분포 (GP 뻥튀기)", fig))

# 18. 동일 상품명 GI/GP 중복
dup_names = df_u[df_u.duplicated(subset="product_name", keep=False)].copy()
dup_summary = (
    dup_names.groupby("product_name")
    .agg(goods_ids=("goods_id", list), prefixes=("prefix", list), count=("goods_id", "count"))
    .reset_index()
    .sort_values("count", ascending=False)
)
dup_summary["prefix_combo"] = dup_summary["prefixes"].apply(lambda x: "+".join(sorted(set(x))))
combo_cnt = dup_summary["prefix_combo"].value_counts().reset_index()
combo_cnt.columns = ["prefix_combo", "count"]
fig = px.bar(combo_cnt, x="prefix_combo", y="count",
             text="count", color_discrete_sequence=["#C44E52"],
             title=f"⚠️ 동일 상품명 중복 — {len(dup_summary)}개 상품명, {len(dup_names)}개 상품 (추천 시 중복 노출 위험)",
             template=TEMPLATE,
             labels={"prefix_combo": "접두사 조합", "count": "중복 상품명 수"})
fig.update_traces(textposition="outside")
fig.update_layout(showlegend=False, height=400)
figs.append(("동일 상품명 GI/GP 중복", fig))

# 19. 상세 이미지 수 분포 — 50개 초과 구간 강조
img_df = df_u[df_u["detail_img_cnt"] > 0].copy()
img_df["img_group"] = pd.cut(
    img_df["detail_img_cnt"],
    bins=[0, 10, 20, 30, 50, 200],
    labels=["1~10", "11~20", "21~30", "31~50", "51+"]
)
img_group_cnt = img_df["img_group"].value_counts().sort_index().reset_index()
img_group_cnt.columns = ["img_group", "count"]
img_group_cnt["color"] = img_group_cnt["img_group"].apply(lambda x: "#C44E52" if x == "51+" else "#55A868")
fig = px.bar(img_group_cnt, x="img_group", y="count",
             color="img_group",
             color_discrete_map={"1~10": "#55A868", "11~20": "#55A868",
                                  "21~30": "#DD8452", "31~50": "#DD8452", "51+": "#C44E52"},
             text="count",
             title="⚠️ 상세 이미지 수 분포 — 51개 이상은 OCR 비용 과다 (샘플링 고려)",
             template=TEMPLATE,
             labels={"img_group": "이미지 수 구간", "count": "상품 수"})
fig.update_traces(textposition="outside")
fig.update_layout(showlegend=False, height=400)
figs.append(("상세 이미지 수 구간별 분포", fig))

# 20. 중분류별 상세 이미지 보유율 — 용품도 높음
midcate_img = df_u.groupby("midcate_name").agg(
    total   =("goods_id",      "count"),
    has_img =("has_detail_img","sum"),
).reset_index()
midcate_img["img_pct"] = midcate_img["has_img"] / midcate_img["total"] * 100
midcate_img = midcate_img.sort_values("img_pct", ascending=True)
fig = px.bar(midcate_img, x="img_pct", y="midcate_name", orientation="h",
             text=midcate_img.apply(lambda r: f"{r['img_pct']:.0f}% ({int(r['has_img'])}/{int(r['total'])})", axis=1),
             title="⚠️ 중분류별 상세 이미지 보유율 — '식품류만' 가정 틀림, 용품도 높음",
             template=TEMPLATE,
             labels={"img_pct": "이미지 보유율 (%)", "midcate_name": "중분류"},
             color_discrete_sequence=["#4C72B0"])
fig.update_traces(textposition="outside")
fig.update_layout(showlegend=False, height=420, xaxis_range=[0, 115])
figs.append(("중분류별 상세 이미지 보유율", fig))

# ── HTML 리포트 생성 ──────────────────────────────────────
n_unique   = len(df_u)
n_brands   = df_u["brand_name"].nunique()
avg_rating = df_u[df_u["rating"] > 0]["rating"].mean()
avg_review = df_u["review_count"].dropna().mean()
n_soldout  = df_u["soldout"].sum()
n_img      = df_u["has_detail_img"].sum()

stats_html = f"""
<div class="stats">
  <div class="stat"><div class="val">{n_unique:,}</div><div class="lbl">고유 상품 수</div></div>
  <div class="stat"><div class="val">{n_brands:,}</div><div class="lbl">브랜드 수</div></div>
  <div class="stat"><div class="val">{avg_rating:.2f}</div><div class="lbl">평균 평점 (5점)</div></div>
  <div class="stat"><div class="val">{avg_review:.0f}</div><div class="lbl">평균 리뷰 수</div></div>
  <div class="stat"><div class="val">{n_soldout:,}</div><div class="lbl">품절 상품</div></div>
  <div class="stat"><div class="val">{n_img:,}</div><div class="lbl">상세 이미지 보유</div></div>
</div>
"""

SECTIONS = {
    "SECTION 1 — 전체 개요":              [1, 2, 3],
    "SECTION 2 — 접두사(상품 유형) 분석":  [4, 5, 6, 7, 8],
    "SECTION 3 — 가격 / 평점 / 리뷰":     [9, 10, 11, 12, 13],
    "SECTION 4 — 품절 / 상세 이미지":     [14, 15],
    "SECTION 5 — ⚠️ 데이터 품질 이슈":   [16, 17, 18, 19, 20],
}
FULL_WIDTH = {2, 3, 5, 6, 12, 17}

grid_html = ""
fig_map = {i: (title, fig) for i, (title, fig) in enumerate(figs, 1)}

for sec_title, idxs in SECTIONS.items():
    grid_html += f'<h2 class="section">{sec_title}</h2>\n<div class="grid">\n'
    for i in idxs:
        title, fig = fig_map[i]
        cls     = "card full" if i in FULL_WIDTH else "card"
        inc_js  = "inline" if i == 1 else False
        inner   = fig.to_html(full_html=False, include_plotlyjs=inc_js,
                              config={"displayModeBar": False})
        grid_html += f'<div class="{cls}"><h3>{i}. {title}</h3>{inner}</div>\n'
    grid_html += "</div>\n"

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Goods EDA Report</title>
<style>
  body  {{ font-family: -apple-system, sans-serif; max-width: 1400px; margin: 40px auto; padding: 0 24px; background: #f5f6fa; }}
  h1    {{ color: #222; border-bottom: 3px solid #4C72B0; padding-bottom: 10px; }}
  h2.section {{ color: #4C72B0; margin: 48px 0 16px; font-size: 1.15em; border-left: 4px solid #4C72B0; padding-left: 12px; }}
  h3    {{ color: #444; font-size: 1em; margin: 0 0 8px; }}
  .stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 24px 0; }}
  .stat  {{ background: white; border-radius: 10px; padding: 16px 28px; box-shadow: 0 1px 6px rgba(0,0,0,.08); text-align: center; min-width: 120px; }}
  .stat .val {{ font-size: 2em; font-weight: 700; color: #4C72B0; }}
  .stat .lbl {{ color: #888; font-size: .85em; margin-top: 4px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 1px 6px rgba(0,0,0,.08); }}
  .card.full {{ grid-column: 1 / -1; }}
</style>
</head>
<body>
<h1>Bronze Goods EDA Report</h1>
{stats_html}
{grid_html}
</body>
</html>"""

html_path = OUTPUT_DIR / "goods_eda.html"
html_path.write_text(html, encoding="utf-8")
print(f"EDA 완료 → {html_path}")
