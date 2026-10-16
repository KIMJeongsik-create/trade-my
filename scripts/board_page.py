"""실습 D — 바이어 리스크 한눈에(v1) 페이지를 계산해서 쓴다.

입력: labs/day3/lab-d/buyer_board.csv (읽기만)
토큰: workbench/day3/outputs/design.md 의 토큰 표 — 아래 TOKENS 한 곳에 옮겨 둔다
출력: workbench/day3/outputs/buyer_board.html (손으로 고치지 않는다 — 같은 입력이면 같은 페이지)
구역: 머리 · KPI 4 · 신호등 등급 분포 + 위험 선 슬라이더 · 위험 상위 10 · 지역별 채권 · 바닥글
실행: uv run python scripts/board_page.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "labs/day3/lab-d/buyer_board.csv"
OUT = ROOT / "workbench/day3/outputs/buyer_board.html"

AS_OF = "2026-09-30"
LINE0 = 17  # 처음 위험 선(%) — 사람이 정한 값
LINE_MIN, LINE_MAX = 5, 30
TOP_N = 10
GRADES = ["S", "A", "B", "C"]

# design.md 토큰 표와 같은 값만 쓴다(바꾸면 두 곳을 함께 고친다)
TOKENS = {
    "bg": "#f6f7f9",
    "surface": "#ffffff",
    "border": "#dfe3e8",
    "text": "#1b1f24",
    "muted": "#5b6470",
    "accent": "#1d5fd1",
    "grade-s": "#2e7d4f",
    "grade-a": "#557214",
    "grade-b": "#8a6408",
    "grade-c": "#c0392b",
    "font": "'Noto Sans KR', sans-serif",
    "fs-1": "12px",
    "fs-2": "14px",
    "fs-3": "16px",
    "fs-4": "20px",
    "fs-5": "28px",
    "fs-6": "36px",
    "sp-1": "4px",
    "sp-2": "8px",
    "sp-3": "12px",
    "sp-4": "16px",
    "sp-5": "24px",
    "sp-6": "32px",
    "radius": "6px",
    "shadow": "none",
}

COUNTRY_KO = {
    "ARE": "아랍에미리트", "BRA": "브라질", "CHN": "중국", "DEU": "독일", "EGY": "이집트",
    "GBR": "영국", "IDN": "인도네시아", "IND": "인도", "JPN": "일본", "MEX": "멕시코",
    "MYS": "말레이시아", "NGA": "나이지리아", "NLD": "네덜란드", "POL": "폴란드",
    "SAU": "사우디아라비아", "THA": "태국", "TUR": "튀르키예", "TWN": "대만",
    "USA": "미국", "VNM": "베트남",
}


# ---------- 계산 ----------

def load():
    df = pd.read_csv(CSV, encoding="utf-8-sig")
    df["pd_bp"] = (df["pd_30d"] * 10000).round().astype(int)  # 정수 만분율 — 경계값 비교를 정확하게
    return df


def grade_of(pd_bp, line_pct):
    """C부터 검사: 선 이상 C · 선의 1/2 이상 B · 선의 1/4 이상 A · 나머지 S."""
    t = line_pct * 100  # % → 만분율
    if pd_bp >= t:
        return "C"
    if 2 * pd_bp >= t:
        return "B"
    if 4 * pd_bp >= t:
        return "A"
    return "S"


def compute(df):
    regraded = df["pd_bp"].map(lambda b: grade_of(b, LINE0))
    match = int((regraded == df["grade"]).sum())
    unknown = sorted(set(df["country_code"]) - set(COUNTRY_KO))
    if unknown:
        raise SystemExit(f"한글 이름이 없는 country_code: {unknown}")

    total_ar = int(df["open_ar_usd"].sum())
    c = df[df["grade"] == "C"]
    by_grade = {g: {"n": int((df["grade"] == g).sum()),
                    "ar": int(df.loc[df["grade"] == g, "open_ar_usd"].sum())} for g in GRADES}
    rows = []
    for r in df.sort_values(["pd_bp", "buyer_id"], ascending=[False, True]).itertuples():
        rows.append({
            "id": r.buyer_id, "name": r.buyer_name, "country": COUNTRY_KO[r.country_code],
            "region": r.region, "ar": int(r.open_ar_usd), "od": int(r.overdue_usd),
            "bp": int(r.pd_bp), "signal": None if pd.isna(r.signal_1) else r.signal_1,
        })
    return {
        "rows": rows, "match": match, "total_ar": total_ar, "by_grade": by_grade,
        "c_n": int(len(c)), "c_ar": int(c["open_ar_usd"].sum()),
        "od_n": int((df["overdue_usd"] > 0).sum()), "od_sum": int(df["overdue_usd"].sum()),
    }


def luminance(hex_color):
    h = hex_color.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(fg, bg):
    a, b = sorted([luminance(fg), luminance(bg)], reverse=True)
    return (a + 0.05) / (b + 0.05)


def contrast_table():
    pairs = [("text", "surface"), ("text", "bg"), ("muted", "surface"), ("muted", "bg"),
             ("accent", "surface")] + [(f"grade-{g.lower()}", s) for g in GRADES for s in ("surface", "bg")]
    return [(fg, bg, round(contrast(TOKENS[fg], TOKENS[bg]), 2)) for fg, bg in pairs]


# ---------- 화면 ----------

CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:var(--fs-3);
  line-height:1.5;word-break:keep-all;font-variant-numeric:tabular-nums}
.wrap{max-width:1200px;margin:0 auto;padding:var(--sp-6) var(--sp-5)}
header h1{margin:0;font-size:var(--fs-5);font-weight:700;color:var(--text)}
header p{margin:var(--sp-1) 0 0;font-size:var(--fs-2);color:var(--muted)}
section{margin-top:var(--sp-5)}
h2{margin:0 0 var(--sp-3);font-size:var(--fs-4);font-weight:700;color:var(--text)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:var(--sp-4);box-shadow:var(--shadow)}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--sp-3)}
.kpi .label{font-size:var(--fs-2);color:var(--muted)}
.kpi .num{font-size:var(--fs-6);font-weight:700;color:var(--text);white-space:nowrap;overflow:hidden;line-height:1.25}
.kpi .num.risk{color:var(--grade-c)}
.kpi .sub{font-size:var(--fs-2);color:var(--muted);white-space:nowrap}
.dist{display:grid;grid-template-columns:2fr 1fr;gap:var(--sp-3)}
.bar{display:block;width:100%;height:var(--sp-6);border-radius:var(--radius)}
.legend{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--sp-2);margin:var(--sp-3) 0 0;padding:0;list-style:none}
.legend li{font-size:var(--fs-2);color:var(--muted)}
.legend b{display:block;font-size:var(--fs-3)}
.legend .money{white-space:nowrap}
.g-S{color:var(--grade-s)} .g-A{color:var(--grade-a)} .g-B{color:var(--grade-b)} .g-C{color:var(--grade-c)}
.slider label{display:block;font-size:var(--fs-2);color:var(--muted)}
.slider .now{font-size:var(--fs-5);font-weight:700;color:var(--text)}
.slider input{width:100%;accent-color:var(--accent);margin:var(--sp-2) 0}
.slider .ends{display:flex;justify-content:space-between;font-size:var(--fs-1);color:var(--muted)}
.slider .delta{margin-top:var(--sp-3);font-size:var(--fs-2);color:var(--text)}
.slider .rule{margin-top:var(--sp-2);font-size:var(--fs-1);color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:var(--fs-2);color:var(--text)}
th{text-align:left;font-weight:400;color:var(--muted);padding:var(--sp-2);border-bottom:1px solid var(--border)}
td{padding:var(--sp-2);border-bottom:1px solid var(--border);vertical-align:top}
th.n,td.n{text-align:right;white-space:nowrap}
td.grade{font-weight:700;white-space:nowrap}
.regions .row{display:grid;grid-template-columns:minmax(0,9em) minmax(0,1fr) auto;grid-template-areas:'name bar val';
  gap:var(--sp-1) var(--sp-3);align-items:center;margin-bottom:var(--sp-2)}
.regions .name{grid-area:name;font-size:var(--fs-2);color:var(--text)}
.regions svg{grid-area:bar;display:block;width:100%;height:var(--sp-4)}
.regions .val{grid-area:val;font-size:var(--fs-2);color:var(--text);text-align:right;white-space:nowrap}
.regions .val span{color:var(--grade-c)}
.note{margin:var(--sp-3) 0 0;font-size:var(--fs-1);color:var(--muted)}
footer{margin-top:var(--sp-6);padding-top:var(--sp-4);border-top:1px solid var(--border);font-size:var(--fs-1);color:var(--muted)}
@media (max-width:640px){
  .wrap{padding:var(--sp-5) var(--sp-4)}
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--sp-2)}
  .card{padding:var(--sp-3)}
  .dist{grid-template-columns:minmax(0,1fr)}
  .legend{grid-template-columns:repeat(2,minmax(0,1fr))}
  .regions .row{grid-template-columns:minmax(0,1fr) auto;grid-template-areas:'name val' 'bar bar'}
  table.top thead{display:none}
  table.top,table.top tbody,table.top tr,table.top td{display:block;width:100%}
  table.top tr{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
    padding:var(--sp-2) var(--sp-3);margin-bottom:var(--sp-2)}
  table.top td{display:flex;justify-content:space-between;gap:var(--sp-3);border:0;padding:var(--sp-1) 0;text-align:right}
  table.top td::before{content:attr(data-label);color:var(--muted);text-align:left;white-space:nowrap}
  table.top td.name{display:block;text-align:left;font-weight:700;font-size:var(--fs-3)}
  table.top td.name::before{content:none}
  table.top td.sig{white-space:normal}
  .topwrap{background:transparent;border:0;padding:0}
}
"""

JS = """
const D = JSON.parse(document.getElementById('data').textContent);
const LINE0 = D.line0, ROWS = D.rows, TOTAL = D.total_ar;
const GR = ['S','A','B','C'];
const COLOR = {S:'var(--grade-s)',A:'var(--grade-a)',B:'var(--grade-b)',C:'var(--grade-c)'};
const money = n => '$' + n.toLocaleString('en-US');
const pct = (a,b) => (b ? a/b*100 : 0).toFixed(1) + '%';
const score = bp => (bp/100).toFixed(1) + '%';
const sign = n => (n < 0 ? '\\u2212' : '+');
function gradeOf(bp, line){ const t = line*100;
  if (bp >= t) return 'C'; if (2*bp >= t) return 'B'; if (4*bp >= t) return 'A'; return 'S'; }
function summary(line){
  const g = {S:{n:0,ar:0},A:{n:0,ar:0},B:{n:0,ar:0},C:{n:0,ar:0}}; const reg = {};
  for (const r of ROWS){ const k = gradeOf(r.bp, line); r.g = k; g[k].n++; g[k].ar += r.ar;
    reg[r.region] = reg[r.region] || {ar:0,c:0}; reg[r.region].ar += r.ar; if (k==='C') reg[r.region].c += r.ar; }
  return {g, reg};
}
const BASE = summary(LINE0).g.C;
const SVGNS = 'http://www.w3.org/2000/svg';
function rect(svg, x, w, fill){ const e = document.createElementNS(SVGNS,'rect');
  e.setAttribute('x',x); e.setAttribute('y',0); e.setAttribute('width',w); e.setAttribute('height',10);
  e.setAttribute('fill',fill); svg.appendChild(e); }
function el(tag, cls, text){ const e = document.createElement(tag); if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text; return e; }

function render(line){
  const s = summary(line), C = s.g.C;
  document.getElementById('line-now').textContent = line + '%';
  // 2. KPI
  document.getElementById('k-c-n').textContent = C.n + '곳';
  document.getElementById('k-c-ar').textContent = money(C.ar);
  document.getElementById('k-c-pct').textContent = '전체 채권의 ' + pct(C.ar, TOTAL);
  // 3. 등급 분포 — 채권 금액 비율로 나눈 막대 하나
  const bar = document.getElementById('grade-bar'); bar.replaceChildren(); let x = 0;
  for (const k of GR){ const w = s.g[k].ar / TOTAL * 1000; rect(bar, x, w, COLOR[k]); x += w; }
  const lg = document.getElementById('legend'); lg.replaceChildren();
  for (const k of GR){ const li = el('li'); const b = el('b', 'g-'+k, k + '등급 ' + s.g[k].n + '곳');
    li.append(b, el('span','money', money(s.g[k].ar) + ' · ' + pct(s.g[k].ar, TOTAL))); lg.appendChild(li); }
  // 4. 처음 17%와 견준 한 줄
  const dn = C.n - BASE.n, da = C.ar - BASE.ar;
  document.getElementById('delta').textContent = line === LINE0
    ? '처음 ' + LINE0 + '% 기준입니다. 선을 움직이면 C등급이 몇 곳 · 얼마 바뀌는지 보입니다.'
    : '처음 ' + LINE0 + '%보다 C등급 ' + sign(dn) + Math.abs(dn) + '곳 · ' + sign(da) + money(Math.abs(da));
  // 5. 위험 상위 10 — 등급 칸만 선에 따라 바뀐다
  for (const td of document.querySelectorAll('td.grade')){ const k = ROWS[+td.dataset.i].g;
    td.textContent = k; td.className = 'grade g-' + k; }
  // 6. 지역별 채권 — 큰 순서(순서는 고정), 지금 C 몫을 진하게
  const max = D.regions[0].ar;
  for (const r of D.regions){ const v = s.reg[r.name], svg = document.getElementById('rb-' + r.key);
    svg.replaceChildren(); rect(svg, 0, v.ar / max * 1000, 'var(--muted)'); rect(svg, 0, v.c / max * 1000, 'var(--grade-c)');
    document.getElementById('rc-' + r.key).textContent = 'C ' + money(v.c); }
  fitNumbers();
}
// 숫자는 한 줄 — 칸보다 길면 글자를 한 단계씩 줄인다(토큰 크기만)
const STEPS = ['var(--fs-6)','var(--fs-5)','var(--fs-4)'];
function fitNumbers(){ for (const n of document.querySelectorAll('.kpi .num')){
  for (const fs of STEPS){ n.style.fontSize = fs; if (n.scrollWidth <= n.clientWidth) break; } } }
const slider = document.getElementById('line');
slider.addEventListener('input', () => render(+slider.value));
window.addEventListener('resize', fitNumbers);
render(LINE0);
"""


def money(n):
    return f"${n:,}"


def render(res):
    root = ":root{" + ";".join(f"--{k}:{v}" for k, v in TOKENS.items()) + "}"
    top = res["rows"][:TOP_N]
    trs = []
    for i, r in enumerate(top):
        trs.append(
            "<tr>"
            f'<td class="name">{esc(r["name"])}</td>'
            f'<td data-label="나라">{esc(r["country"])}</td>'
            f'<td class="grade" data-label="등급" data-i="{i}"></td>'
            f'<td class="n" data-label="위험 점수">{r["bp"] / 100:.1f}%</td>'
            f'<td class="n" data-label="채권">{money(r["ar"])}</td>'
            f'<td class="n" data-label="연체">{money(r["od"])}</td>'
            f'<td class="sig" data-label="위험 신호">{esc(r["signal"] or "–")}</td>'
            "</tr>")
    reg = (pd.DataFrame(res["rows"]).groupby("region")["ar"].sum()
           .sort_values(ascending=False, kind="stable"))
    regions = [{"name": k, "key": f"r{i}", "ar": int(v)} for i, (k, v) in enumerate(reg.items())]
    reg_html = "".join(
        f'<div class="row"><div class="name">{esc(r["name"])}</div>'
        f'<svg id="rb-{r["key"]}" viewBox="0 0 1000 10" preserveAspectRatio="none" role="img" '
        f'aria-label="{esc(r["name"])} 채권 막대"></svg>'
        f'<div class="val">{money(r["ar"])} · <span id="rc-{r["key"]}"></span></div></div>'
        for r in regions)
    data = {"line0": LINE0, "total_ar": res["total_ar"], "regions": regions,
            "rows": [{k: r[k] for k in ("region", "ar", "bp")} for r in res["rows"]]}
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    n_all = len(res["rows"])
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>바이어 리스크 한눈에</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
<style>{root}{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>바이어 리스크 한눈에</h1>
  <p>기준일 {AS_OF}</p>
  <p>(가상) 한빛정밀(주) 바이어 {n_all}곳 · 합성 데이터</p>
</header>

<section aria-label="핵심 숫자">
<div class="kpis">
  <div class="card kpi"><div class="label">위험 바이어(C등급)</div><div class="num risk" id="k-c-n"></div><div class="sub">위험 선 이상</div></div>
  <div class="card kpi"><div class="label">C등급 채권</div><div class="num" id="k-c-ar"></div><div class="sub" id="k-c-pct"></div></div>
  <div class="card kpi"><div class="label">전체 채권</div><div class="num">{money(res["total_ar"])}</div><div class="sub">{n_all}곳</div></div>
  <div class="card kpi"><div class="label">연체 금액</div><div class="num">{money(res["od_sum"])}</div><div class="sub">연체 있는 곳 {res["od_n"]}곳</div></div>
</div>
</section>

<section class="dist">
  <div class="card">
    <h2>신호등 등급 분포</h2>
    <svg class="bar" id="grade-bar" viewBox="0 0 1000 10" preserveAspectRatio="none" role="img" aria-label="등급별 채권 금액 비율 막대"></svg>
    <ul class="legend" id="legend"></ul>
    <p class="note">막대 길이는 채권 금액 비율입니다.</p>
  </div>
  <div class="card slider">
    <h2>위험 선</h2>
    <label for="line">위험 점수가 이 선 이상이면 C등급</label>
    <div class="now" id="line-now"></div>
    <input type="range" id="line" min="{LINE_MIN}" max="{LINE_MAX}" step="1" value="{LINE0}">
    <div class="ends"><span>{LINE_MIN}%</span><span>{LINE_MAX}%</span></div>
    <div class="delta" id="delta"></div>
    <div class="rule">선의 절반 이상 B · 4분의 1 이상 A · 나머지 S</div>
  </div>
</section>

<section>
  <h2>위험 상위 {TOP_N} — 이번 주에 전화할 곳</h2>
  <div class="card topwrap">
  <table class="top">
    <thead><tr><th>바이어</th><th>나라</th><th>등급</th><th class="n">위험 점수</th><th class="n">채권</th><th class="n">연체</th><th>위험 신호</th></tr></thead>
    <tbody>{"".join(trs)}</tbody>
  </table>
  </div>
  <p class="note">위험 점수(30일 안 연체 가능성)가 높은 순입니다. 위험 신호는 확인해 볼 이유이고, 원인이라는 뜻은 아닙니다.</p>
</section>

<section>
  <h2>지역별 채권</h2>
  <div class="card"><div class="regions">{reg_html}</div>
  <p class="note">회색 막대는 지역 채권 전체, 빨간 몫은 지금 선에서 C등급인 채권입니다.</p></div>
</section>

<footer>(가상) 합성 데이터 · 기준일 {AS_OF} · 위험 점수는 판단을 돕는 값이고 결정은 사람이 합니다</footer>
</div>
<script type="application/json" id="data">{data_json}</script>
<script>{JS}</script>
</body>
</html>
"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def main():
    df = load()
    res = compute(df)
    OUT.write_text(render(res), encoding="utf-8", newline="\n")

    print(f"쓴 파일: {OUT.relative_to(ROOT)}")
    print("등급별 곳 수(grade 열):", {g: res["by_grade"][g]["n"] for g in GRADES})
    print(f"C등급 채권 {money(res['c_ar'])} / 전체 채권 {money(res['total_ar'])}"
          f" = {res['c_ar'] / res['total_ar'] * 100:.1f}%")
    print(f"연체: {res['od_n']}곳 · {money(res['od_sum'])}")
    print(f"grade 열 = 17% 규칙: {res['match']}/{len(df)}")
    print("대비(글자 : 바탕)")
    for fg, bg, r in contrast_table():
        print(f"  {fg:8} on {bg:8} {r:5.2f} {'OK' if r >= 4.5 else '미달'}")


if __name__ == "__main__":
    main()
