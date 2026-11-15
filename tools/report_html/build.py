import html
OUT="final_report.html"   # 出力先（実行したフォルダ）。Artifact への公開は、クラウドのセッションで行っていた

def esc(s): return html.escape(str(s))

def hbars(rows, series, fmt, vmin, vmax, label_w=170, w=680, bar_h=18, gap=6, title="", signed_colors=None, unit=""):
    """rows: [(label,[v...])]; series: [(name,cssclass)]; signed_colors=(pos,neg) css classes for single-series diverging."""
    n=len(series); rh=n*(bar_h+2)+gap+8
    H=len(rows)*rh+34
    x0=label_w; x1=w-60
    def X(v): return x0+(v-vmin)/(vmax-vmin)*(x1-x0)
    z=X(0)
    out=[f'<svg class="chart" viewBox="0 0 {w} {H}" role="img" aria-label="{esc(title)}">']
    # grid ticks
    import math
    span=vmax-vmin
    step=10**math.floor(math.log10(span/4)); 
    for m in (1,2,5):
        if span/(step*m)<=6: step*=m; break
    t=math.ceil(vmin/step)*step
    while t<=vmax+1e-12:
        out.append(f'<line class="grid" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="6" y2="{H-24}"/><text class="tick" x="{X(t):.1f}" y="{H-8}" text-anchor="middle">{fmt(t)}</text>')
        t+=step
    out.append(f'<line class="axis" x1="{z:.1f}" x2="{z:.1f}" y1="6" y2="{H-24}"/>')
    y=10
    for label,vals in rows:
        out.append(f'<text class="lab" x="{label_w-8}" y="{y+ (n*(bar_h+2))/2+4:.1f}" text-anchor="end">{esc(label)}</text>')
        for k,v in enumerate(vals):
            if v is None: continue
            cls=series[k][1]
            if signed_colors: cls=signed_colors[0] if v>=0 else signed_colors[1]
            xa,xb=sorted((z,X(v)))
            out.append(f'<rect class="{cls}" x="{xa:.1f}" y="{y+k*(bar_h+2)}" width="{max(xb-xa,1):.1f}" height="{bar_h}" rx="3"><title>{esc(label)} {esc(series[k][0])}: {fmt(v)}</title></rect>')
            anchor="start" if v>=0 else "end"; tx=xb+4 if v>=0 else xa-4
            out.append(f'<text class="val" x="{tx:.1f}" y="{y+k*(bar_h+2)+bar_h/2+4}" text-anchor="{anchor}">{fmt(v)}</text>')
        y+=rh
    out.append('</svg>')
    return "".join(out)

def legend(series):
    return '<div class="legend">'+"".join(f'<span><i class="sw {c}"></i>{esc(n)}</span>' for n,c in series)+'</div>'

def table(head, rows, cls=""):
    h="".join(f"<th>{esc(x)}</th>" for x in head)
    b="".join("<tr>"+"".join(f"<td>{x}</td>" for x in r)+"</tr>" for r in rows)
    return f'<div class="scroll {cls}"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'

pct=lambda v: f"{v*100:+.1f}%" if abs(v)>=0.0005 else "0.0%"
pct2=lambda v: f"{v*100:+.2f}%"
pl=lambda v: f"{v*100:.1f}%"
ic=lambda v: f"{v:+.3f}"

S_OLD=[("旧区分期","s-old"),("新区分期","s-new")]
c1=hbars([("SEL-A チャートのみ",[0.042,0.064]),("SEL-B 財務",[0.010,0.048]),("SEL-C1 線形結合",[0.044,0.068]),("SEL-C2 LightGBM",[0.040,0.062])],S_OLD,ic,0,0.08,title="順位相関IC")
feat=[("予想益利回り(割安)",0.0400),("簿価利回り(割安)",0.0340),("ROE",0.0185),("純利益予想の上方修正",0.0160),("52週高値への近さ",0.0152),("営業利益予想の修正",0.0095),("ボラ収縮",0.0105),("配当予想の変更",0.0060),("売買代金の傾き",0.0011),("過去21日リターン",-0.0305),("過去63日リターン",-0.0184),("過去126日リターン",-0.0274),("TOPIX下落日の耐性",-0.0283),("60日ボラ(高いほど不利)",-0.0370),("過去5日リターン",-0.0399)]
feat.sort(key=lambda x:-x[1])
c2=hbars([(a,[b]) for a,b in feat],[("IC","s-new")],ic,-0.05,0.05,label_w=190,signed_colors=("s-pos","s-neg"),title="特徴量ごとのIC")
# H0 stacked
def stacked(rows,w=680,label_w=120):
    H=len(rows)*40+40; x0=label_w; x1=w-70; vmax=0.20
    X=lambda v:x0+v/vmax*(x1-x0)
    o=[f'<svg class="chart" viewBox="0 0 {w} {H}" role="img" aria-label="理想から実現までの目減り">']
    for t in (0,0.05,0.10,0.15,0.20):
        o.append(f'<line class="grid" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="4" y2="{H-24}"/><text class="tick" x="{X(t):.1f}" y="{H-8}" text-anchor="middle">{t*100:.0f}%</text>')
    ux=X(0.1153); o.append(f'<line class="ref" x1="{ux:.1f}" x2="{ux:.1f}" y1="4" y2="{H-24}"/><text class="reftxt" x="{ux+4:.1f}" y="14">母集団平均 11.5%</text>')
    y=22
    for name,real,cost,lot in rows:
        o.append(f'<text class="lab" x="{label_w-8}" y="{y+16}" text-anchor="end">{esc(name)}</text>')
        segs=[("実現(コスト後)",real,"s-new"),("コスト",cost,"s-cost"),("100株単位・約定制約",lot,"s-lot")]
        a=0
        for lab,v,cl in segs:
            o.append(f'<rect class="{cl}" x="{X(a):.1f}" y="{y}" width="{max(X(a+v)-X(a)-2,1):.1f}" height="24" rx="3"><title>{name} {lab}: {v*100:.1f}pt</title></rect>')
            if X(a+v)-X(a)>36: o.append(f'<text class="seg" x="{(X(a)+X(a+v))/2-1:.1f}" y="{y+16}" text-anchor="middle">{v*100:.1f}</text>')
            a+=v
        o.append(f'<text class="val" x="{X(a)+4:.1f}" y="{y+16}">{a*100:.1f}%</text>')
        y+=40
    o.append('</svg>'); return "".join(o)
c3=stacked([("SEL-A",.0550,.0360,.0412),("SEL-B",.1086,.0363,.0420),("SEL-C1",.0715,.0349,.0373),("SEL-C2",.0819,.0378,.0370)])
leg3=legend([("実現(コスト後)","s-new"),("コスト(片道15bps)","s-cost"),("100株単位・約定制約","s-lot")])
c4=hbars([("理想(連続・コストなし)",[0.1869]),("1株単位・1,000万円",[0.1423]),("100株・5,000万円",[0.1363]),("100株・1,000万円(現行)",[0.1086])],[("SEL-B","s-new")],pl,0,0.20,label_w=190,title="SEL-Bの資金・単位別(コスト後)")
c5=hbars([("SEL-A",[-0.0603,-0.0611]),("SEL-B",[-0.0068,0.0151]),("SEL-C1",[-0.0438,-0.0423]),("SEL-C2",[-0.0334,-0.0273])],[("全売却→再購入","s-old"),("差分売買","s-new")],pct,-0.08,0.03,label_w=100,title="対母集団平均(年率)")
c6=hbars([("上位1/5",[0.0184,0.0144]),("上位1/10",[0.0268,0.0180])],[("発見期間 51窓","s-old"),("確認期間 54窓","s-new")],pct2,0,0.03,label_w=100,title="S2 超過")
c7=hbars([("Q1(利回り低)",[-0.0038,-0.0176]),("Q2",[0.0039,-0.0082]),("Q3",[0.0087,-0.0160]),("Q4",[0.0116,-0.0035]),("Q5(利回り高)",[0.0184,0.0144])],[("発見期間","s-old"),("確認期間","s-new")],pct2,-0.025,0.025,label_w=120,title="S2 利回り5段階")
c8=hbars([("A 5億円以上",[0.0163,0.0006]),("B 5,000万〜5億円",[0.0084,0.0101]),("C 2,000万〜5,000万円",[0.0078,-0.0034])],[("発見期間(往復コスト後)","s-old"),("確認期間(往復コスト後)","s-new")],pct2,-0.01,0.02,label_w=150,title="S2 段階別")
c9=hbars([("買い20営業日前",[0.0091,0.0006]),("買い40営業日前(採用)",[0.0184,0.0144]),("買い60営業日前",[0.0322,0.0243])],[("発見期間","s-old"),("確認期間","s-new")],pct2,0,0.04,label_w=150,title="S2 買う時期(最終日の始値で売り)")
fam=table(["検証の家族","計画","検定できた","補正後に有意","確認で再現"],[
 ["段階1: 49のチャート規則","98","90","0","—"],["段階3: 3つの型(押し目・ブレイクアウト・反発)","8","8","0","—"],
 ["決算起因の急落(探索的)","24","20","0","—"],["底打ち・上昇しやすい局面","12","9","0","—"],["下がり方の特徴(探索的)","22","19","0","—"],
 ["市場の内部指標","20","14","0","—"],["信用残・空売り比率","10","9","1(K5)","<b>0</b>(再現せず)"],
 ["季節性(S1・S2・S3)","5","5","2(S2)","<b>2</b>(S2の2検定とも再現)"],["パターン図鑑(v2: 6,344通りから45個を確認。買える日を修正して再計算)","6,344","6,344","0","<b>0</b>(前の「2」は撤回)"],
 ["<b>合計(図鑑を除く)</b>","<b>199</b>","<b>174</b>","<b>3</b>","<b>2</b>"]])
trials=table(["モデル(等ウエイト)","全売却: 対TOPIX","全売却: 対母集団","差分売買: 対TOPIX","差分売買: 対母集団","入れ替え率(全売却→差分)"],[
 ["SEL-A","−8.2%","−6.0%","−8.3%","−6.1%","0.77 → 0.73"],["SEL-B","−2.9%","−0.7%","−0.7%","+1.5%","0.86 → 0.45"],
 ["SEL-C1","−6.6%","−4.4%","−6.4%","−4.2%","0.78 → 0.71"],["SEL-C2","−5.5%","−3.3%","−4.9%","−2.7%","0.77 → 0.65"]])
drops=table(["下がり方の特徴(下げ状態の銘柄)","21日後の超過(あり)","21日後の超過(なし)","差の検定"],[
 ["深い下落(20日で−25%以下)","−1.96%","−0.16%","p=0.16"],["市場全体の連れ安","+1.38%(68日)","−0.56%","計算不能(同じ日に比較できず)"],
 ["売り枯れ(出来高が半分以下)","+6.2%(69日)","−0.06%","計算不能(事例が少ない)"],["投げ売りの出来高","−0.10%","−0.23%","p=0.87"],
 ["急落(5日で−10%以下)","−0.47%","−0.33%","p=0.96"],["低位株(500円未満)","−0.19%","−0.09%","p=0.88"]])
margins=table(["信用残・空売り比率の目印","5日の差","21日の差","結果"],[
 ["K1 買い残の急減","−0.35%","計算不能","予測と逆、有意でない"],["K2 信用倍率が低い","−0.30%","−1.52%","予測と逆、有意でない"],["K3 売り残の急増","−0.05%","−0.92%","有意でない"],
 ["K4 業種の空売り比率が高い","−0.10%","−0.63%","有意でない"],["K5 業種の空売り比率が低下","−0.45%","<b>−0.66%(補正後q=0.024)</b>","発見期間で有意だったが、確認期間で再現せず(−0.45%、p=0.75)"]])
data=table(["データ","内容","件数"],[["銘柄日足","2016-11-14〜2026-11-12、廃止銘柄を含む、5,392銘柄","10,145,608行"],["上場銘柄表","営業日ごとのスナップショット(有効区間に圧縮)","2,441回 → 15,698区間"],["財務サマリー","開示日時つき(15:30以降は翌営業日から使う)","189,622行"],["信用取引週末残高","週次・全銘柄(公表日つき。古い週は公表日なし)","2,182,310行"],["業種別空売り比率","日次・34業種","82,960行"],["投資部門別売買状況","週次","2,369行"],["指数・TOPIX","","187,925行 / 2,442行"]])

CSS=r'''
:root{--bg:#f7f8f8;--surface:#ffffff;--fg:#1d2527;--muted:#5b6b6e;--line:#d8e0e1;--accent:#0f6b73;--accent-soft:#e1f0f1;--head-bg:#eef3f3;
--s-new:#2a78d6;--s-old:#9ec5f4;--s-cost:#eb6834;--s-lot:#9a9a95;--s-pos:#2a78d6;--s-neg:#eb6834;--ref:#1d2527;
--font-body:"Noto Sans JP","Hiragino Sans","Yu Gothic",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#10181a;--surface:#161f21;--fg:#e3ecec;--muted:#93a6a8;--line:#2a3a3d;--accent:#5cc3cc;--accent-soft:#16363a;--head-bg:#1c2a2d;
--s-new:#3987e5;--s-old:#1c5cab;--s-cost:#d95926;--s-lot:#6f6f6a;--s-pos:#3987e5;--s-neg:#d95926;--ref:#e3ecec;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#10181a;--surface:#161f21;--fg:#e3ecec;--muted:#93a6a8;--line:#2a3a3d;--accent:#5cc3cc;--accent-soft:#16363a;--head-bg:#1c2a2d;
--s-new:#3987e5;--s-old:#1c5cab;--s-cost:#d95926;--s-lot:#6f6f6a;--s-pos:#3987e5;--s-neg:#d95926;--ref:#e3ecec;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--font-body);line-height:1.8;padding-block:32px 72px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
main{max-width:860px;margin:0 auto;min-width:0}
header{padding-block:8px 20px;border-bottom:1px solid var(--line)}
.kicker{margin:0;font-size:13px;letter-spacing:.14em;color:var(--accent);font-weight:700}
h1{font-size:clamp(26px,5vw,38px);line-height:1.3;margin:6px 0 10px;text-wrap:balance}
.meta{margin:0;color:var(--muted);font-size:14px}
h2{font-size:22px;margin:48px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--accent);text-wrap:balance}
h3{font-size:16px;margin:28px 0 6px}
p,li{max-width:46em}
.lead{background:var(--accent-soft);border-radius:8px;padding:6px 20px 6px 40px;margin:24px 0}
.note{color:var(--muted);font-size:14px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px 16px 8px;margin:14px 0 22px}
.card h3{margin:0 0 4px}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--muted);margin:2px 0 6px}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
svg.chart{width:100%;height:auto;display:block;font-family:var(--font-body)}
.grid{stroke:var(--line);stroke-width:1}.axis{stroke:var(--muted);stroke-width:1.2}
.ref{stroke:var(--ref);stroke-width:1.2;stroke-dasharray:4 3}.reftxt{fill:var(--muted);font-size:11px}
.tick{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}.lab{fill:var(--fg);font-size:12.5px}.val{fill:var(--fg);font-size:12px;font-variant-numeric:tabular-nums}.seg{fill:#fff;font-size:11.5px;font-weight:700}
.s-new{fill:var(--s-new);background:var(--s-new)}.s-old{fill:var(--s-old);background:var(--s-old)}.s-cost{fill:var(--s-cost);background:var(--s-cost)}.s-lot{fill:var(--s-lot);background:var(--s-lot)}.s-pos{fill:var(--s-pos)}.s-neg{fill:var(--s-neg)}
.scroll{overflow-x:auto;margin:10px 0 18px;border:1px solid var(--line);border-radius:6px;background:var(--surface)}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:14px;line-height:1.6;font-variant-numeric:tabular-nums}
th{background:var(--head-bg);text-align:left;font-weight:700}th,td{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:0}
details{margin:2px 0 10px;font-size:13px}summary{cursor:pointer;color:var(--accent)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:0 18px}
.pending li{margin:4px 0}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88em;background:var(--head-bg);padding:1px 6px;border-radius:4px}
'''
def card(title,body,note=""):
    return f'<div class="card"><h3>{title}</h3>{body}{f"<p class=note>{note}</p>" if note else ""}</div>'

BODY=f'''
<header><p class="kicker">J-QUANTS 10年データの検証</p><h1>どんな分析をして、何が分かったか</h1>
<p class="meta">2026-11-14 時点。対象: 2016-11-14〜2026-11-12(2,441営業日)。J-Quants Standard のデータだけを使用。投資助言ではない。</p></header>

<ol class="lead">
<li><b>チャートの「買う合図」は、確認期間で再現したものがありません。</b>約200件の検定のうち、確認期間でも再現したのは、季節性の配当の権利取り(S2)の2件だけです。</li>
<li><b>S2(配当の権利取り)が、初めて再現した候補です。</b>予想配当利回りの上位1/5が、権利付き最終日の40営業日前から最終日にかけて、市場平均を上回りました(発見期間 +1.84%、確認期間 +1.44%)。確認期間で残ったのは、売買代金5,000万〜5億円の銘柄です。</li>
<li><b>信用残(売り残・信用倍率)の「避ける」フィルターは、確認期間で再現しませんでした。</b>探索を打ち切り、前向きの記録で待ちます。</li>
<li><b>銘柄を順位づける力はあります</b>(順位相関 0.04〜0.06)。源泉は、割安・低ボラ・過去の値上がりが小さいという傾向です。</li>
<li><b>1,000万円・100株単位では、その力の大半が目減りします。</b>制約が年約4pt、コストが約3.6pt。資金5,000万円なら、制約は約1.4ptに縮みます。</li>
</ol>

<h2>1. 使ったデータ</h2>
{data}
<p class="note">配当金情報と売買内訳データは、契約(Standard)では使えません。比較は価格リターンです。品質検証: OHLCの矛盾0件、調整係数の突合は丸め(0.1円)を超える不一致0件、取得は全件成功(要調査0件)。</p>

<h2>2. 銘柄を順位づける力</h2>
<p>毎月、各銘柄のスコアと、その後21営業日の超過リターンの順位相関(IC)を測りました。ICが正なら、スコアの高い銘柄が、その後、相対的に上がっています。評価は77期(旧区分24期、新区分53期)です。</p>
{card("モデルごとの順位相関(IC)",legend(S_OLD)+c1,"全期間のICは、SEL-A 0.057(t=3.5)、SEL-B 0.036(2.3)、SEL-C1 0.061(3.7)、SEL-C2 0.055(3.7)。4モデルを比べた上の値なので、割り引いて見る。")}
{card("効いている特徴量(90期、全期間の順位相関)",c2,"割安(予想益利回り・簿価利回り)は新区分期(2022-04以降)に集中: 予想益利回りは新区分 +0.057、旧区分 +0.016。東証の改革と重なる局所的な現象の可能性があり、恒久的な効果とは断定できない。買われすぎ・高ボラを避けるほうが有利。")}

<h2>3. 売買にすると、どれだけ目減りするか</h2>
<p>毎月、スコア上位15銘柄を等ウエイトで買い、21営業日後に売る売買を再現しました(翌日始値で約定、100株単位、現物のみ)。「理想」(連続・コストなし)から、実現まで、年率でどれだけ失うかを分けました。</p>
{card("理想から実現までの目減り(年率)",leg3+c3,"制約(100株単位の切り捨て・買えなかった銘柄)が3.7〜4.2pt、コストが3.5〜3.8pt。買った直後の現金が資産の14〜22%を占めていた。")}
{card("資金額と売買単位を変えた場合(SEL-B、コスト後、年率)",c4,"母集団平均は11.5%。5,000万円なら100株単位のままでも、母集団平均を約2pt上回る(診断で、統計的な有意性はない)。単元未満株は、仕様として認めない方針。")}
<h3>全売却→再購入と、差分売買(コスト15bps、年率の対母集団平均)</h3>
{card("差分売買の効果",legend([("全売却→再購入","s-old"),("差分売買","s-new")])+c5,"SEL-Bだけが大きく改善(入れ替え率 0.86→0.45、コスト 321万→178万円)。チャート系は毎期の順位が大きく入れ替わるので、効果が小さい。")}
{trials}
<p class="note">24試行すべてが、採用ゲート(TOPIXと母集団平均の両方に正)を通らなかった。高ボラ時に現金へ避ける方式は、全モデルで4〜8pt悪化させた。</p>

<h2>4. チャートの規則・状態の検証</h2>
<p>資料から起こした規則や状態を、全銘柄・10年で検証しました。日 t の引け後に点灯、t+1 始値で買い、5営業日後と21営業日後の始値で売り、同じ日の母集団平均との差を見ました。発見期間(〜2022-03)で探し、確認期間(2022-04〜)は、通過したものだけを一度読みます。</p>
{fam}
<p><b>見えたこと</b></p>
<ul>
<li>トレンドが強い・買われすぎ・新高値の状態は、5日で0.2〜0.35%負ける傾向(上位20件のうち17件が負)。ただし補正後は有意でない。</li>
<li>下げ状態(20日で−15%以上)の銘柄は、母集団に対して5日 +0.02%、21日 −0.37%。<b>「売られすぎは戻る」という傾向は、この母集団にはない。</b></li>
<li>決算起因の急落の差(決算なし−あり)は +0.35〜0.39% で予測と同じ向きだが、有意でない。</li>
<li>市場の投げの割合(M4)が極端な日の5日後は、TOPIXが +1.35%(18回、p=0.035、補正後q=0.50)。向きは予測どおりだが、補正後は偶然と区別できない。</li>
</ul>
<h3>どんな下がり方が戻りやすいか(探索的、記述)</h3>
{drops}
<p class="note">向きは、市場連れ安・売り枯れが戻りやすく、深い下落は戻りにくい、という事前の予測と一致。ただし、事例が少なく、有意ではない。</p>
<h3>信用残・空売り比率による「投げ売り」「売り枯れ」の目印</h3>
{margins}

<h2>5. 季節性: 毎年同じ時期の上げ下げ</h2>
<p>広い母集団(全市場、売買代金60日平均2,000万円以上、約2,450銘柄/日)で、3つの型を検証しました。S1 同じ月の持続(発見期間14か月、効果なし)、S3 決算発表前の上昇(平均 +0.37%、p=0.28、コスト後は負)、そして<b>S2 配当の権利取り</b>です。</p>
<p><b>S2:</b> 決算期末の月と6か月後の月を権利月とし、権利付き最終日の40営業日前の始値で買い、最終日の始値で売る(権利落ち前に売る)。予想配当利回りの上位1/5を持つ。</p>
<div class="two">
{card("上位の超過(権利付き最終日まで)",legend([("発見期間 51窓","s-old"),("確認期間 54窓","s-new")])+c6,"上位1/5: 発見 +1.84%(t=3.3)、確認 +1.44%(t=3.4)。")}
{card("買う時期を変えた場合(記述)",legend([("発見期間","s-old"),("確認期間","s-new")])+c9,"早く買うほど大きい: 権利付き最終日の約3か月前から、上がり続ける形。選ぶための表ではない。")}
</div>
{card("利回りの5段階(権利月の銘柄を、予想配当利回りで5等分)",legend([("発見期間","s-old"),("確認期間","s-new")])+c7,"発見期間は、利回りが高いほど順に上がっている。確認期間は、Q5だけが正で、他は負(単調ではない)。")}
{card("流動性の段階別(上位1/5、往復コスト後)",legend([("発見期間","s-old"),("確認期間","s-new")])+c8,"コストの想定: 往復 A 0.30%、B 0.60%、C 1.20%。<b>確認期間で残ったのは B(5,000万〜5億円)だけ</b>(+1.0%、t=2.8)。A は +0.06% に縮み(窓24、t=0.5)、C はコストで負。")}
<ul>
<li><b>権利落ちの後は、大きく下がる。</b>最終日の始値から10営業日後までの超過は、発見 −3.1%、確認 −3.7%(t=−13〜−17)。配当を受け取らずに売る設計は、この下落を避けている。</li>
<li><b>年別:</b> 2018〜2026年のすべての年で、上位1/5の超過は正(0.04〜3.3%)。2022年と2025年は、ほぼゼロ。</li>
<li><b>権利月別:</b> 窓が4〜5個しかなく、検定できない。12か月のうち、発見で9か月、確認で10か月が正。6月・8月は弱い。</li>
<li><b>実行できる形(段階Aの利回り上位15銘柄、片道15bps):</b> 1窓あたり、発見 +1.46%、確認 +1.16%(コスト後、t=1.7〜2.0、窓26〜27、正の窓は73%・63%)。ただし、段階Aで20銘柄以上の権利月は、約半分の月しかない。年率換算の目安(+7〜9%)は、約半分(+3.5〜4.5%)に割り引いて見るべき。</li>
</ul>
<p class="note">S2は、発見期間で補正後に有意(q=0.004)、確認期間でも同じ向き・同じ大きさで再現。結果を見る前に「S2は正」と予測していた。約200件の中の初めての再現であり、前向きの記録で確認する。前回の報告で「A と B まで使える」と書いたが、確認期間では B のみ。訂正する。</p>

<h2>5-2. パターン図鑑: 条件の組み合わせの網羅(v2、買える日を修正して再計算)</h2>
<p>流動性・株価・下落・リターン・ボラ・割安・修正・ROE・信用残・トレンド・業種・市場・月の条件を、最大3つ組み合わせた<b>6,344通り</b>を、発見期間で数えました。上位45個(買い側30・避ける側15)だけを、確認期間で読みました。</p>
<ul>
<li>補正後(q&lt;0.10)に有意な組み合わせは、発見期間で<b>0件</b>。確認期間で規則どおり「再現」したものも<b>0件</b>です。</li>
<li><b>訂正:</b> 前の版では、避ける側の2つが「再現」と出ていました。「買える日」の判定の欠陥(寄り付き後にストップ高になった銘柄まで除いていた)を直して再計算すると、その2つは上位45に入らず、再現は0になりました。上位を選ぶ方式は、小さな定義の変更で顔ぶれが入れ替わり、再現の判定は頑健ではありませんでした。<b>前の「再現2」は撤回します。</b></li>
<li>避ける側15個は、確認期間で全部、同じ向き(負)でした(前の版も同じ)。買い側で同じ向きだったのは、約半数です。ただし、避ける側の最良でも p=0.0195(q=0.37)で、1つずつは有意になりません。</li>
</ul>
<div class="scroll"><table><thead><tr><th>パターン</th><th>発見 21日</th><th>確認 21日</th><th>見方</th></tr></thead><tbody>
<tr><td>21日で+15%超 ＆ 修正なし ＆ 信用買い残が軽い(避ける)</td><td>−1.93%(6/6年)</td><td>−1.49%(p=0.0195)</td><td>向きと大きさが一致。q=0.37で基準に届かず</td></tr>
<tr><td>21日で+15%超 ＆ 信用買い残が軽い(避ける)</td><td>−1.71%(6/6年)</td><td>−1.09%(p=0.088)</td><td>向きは一致</td></tr>
<tr><td>52週高値から−10%以内 ＆ 信用買い残が重い(買い)</td><td>+1.17%(6/6年)</td><td>+0.54%(p=0.016)</td><td>向きは一致。q=0.37で基準に届かず</td></tr>
</tbody></table></div>
<p class="note">確認期間は、v1・v2・今回の再計算で、複数回読んでいます。この表は、新しい証拠ではありません。</p>

<h2>5-3. 探索マップ: 発見期間だけの、記述</h2>
<p><b>「買える日」を修正して再計算しても、主要な結果はほぼ同じでした</b>(売り残の重さ上位1/5の21日 −0.74%・t=−4.2、63日 −1.39%・t=−4.0 など)。特徴量ごとの順位相関を、保有期間5・21・63・126営業日で測り、上位1/5と下位1/5の超過、決算発表後の値動き、夜間と日中、暦、業種を、発見期間(〜2022-03)だけで眺めました。検定ではなく記述で、数十の数字を並べているので、t値が±4でも割り引いて見ます。確認期間には触れていません。</p>
<ul>
<li><b>信用の売り残が重い銘柄は、その後に弱い。</b>最も強い結果でした。売り残が売買代金の何日分か、の上位1/5は、母集団より21日で−0.73%(t=−4.2)、63日で−1.39%(t=−4.0)。信用倍率(買い残÷売り残)の下位1/5は、63日で−1.83%(t=−4.6)。売り方に情報がある、という見方と整合しますが、K3(売り残の急増)の検証では有意でなかったので、「変化」ではなく「水準」です。</li>
<li><b>過去5日リターンが高い銘柄の反落は、半年続く。</b>順位相関は、21日で−0.055(t=−2.4)、126日で−0.041(t=−3.6)。</li>
<li><b>純利益予想の上方修正は、時間をかけて効く。</b>順位相関は、5日で−0.007、63日で+0.027(t=2.6)、126日で+0.031(t=2.6)。短期では効きません。</li>
<li><b>高ROEの上位1/5</b>は、21日で+1.8%(t=2.3。18期のみ)。</li>
<li><b>決算発表後の継続(PEAD)は、見えません。</b>開示直後の値動きの5段階で、後の21日・63日の超過に、一貫した向きはありません。</li>
<li><b>夜間と日中:</b> 過去5日の勝ち組は、翌日の夜間に+0.034%(t=3.1)、日中に−0.062%(t=−3.8)。負け組は逆。1日の幅は3〜6bpsで、実際に使える大きさではありません。</li>
<li><b>暦(曜日・月末月初)と、業種の勢い:</b> 有意なものは、ありません。</li>
</ul>
<h3>除外フィルターの検証: 確認期間で再現しなかった</h3>
<p>探索マップの信用残の結果(売り残が重い・信用倍率が低い)を、順位予測の上位15から除くフィルターとして、事前固定して検証しました(確認期間は1度だけ読みました)。</p>
<div class="scroll"><table><thead><tr><th>フィルター</th><th>掛かった銘柄の21日超過<br>発見期間</th><th>確認期間</th><th>上位15から除いた効果<br>(確認期間、対の差)</th></tr></thead><tbody>
<tr><td>X1 売り残が売買代金の何日分か、上位1/5</td><td>−0.75%(t=−4.2)</td><td>−0.11%(p=0.55)</td><td>+0.13%(p=0.38)</td></tr>
<tr><td>X2 信用倍率の下位1/5</td><td>−0.51%(t=−1.9)</td><td>−0.26%(p=0.36)</td><td>−0.16%(p=0.24)</td></tr>
<tr><td>U12(X1 または X2)</td><td>−0.60%(t=−3.8)</td><td>−0.22%(p=0.21)</td><td>−0.09%(p=0.62)</td></tr>
</tbody></table></div>
<ul>
<li>向きは確認期間でも負でしたが、大きさは発見期間の2〜15%に縮み、有意ではありません(BH q 0.53〜0.55)。「効く」「使える」は0件です。</li>
<li>探索マップで最も強かった結果(t=−4.2)は、ほぼ発見期間だけの現象でした。数十の数字から最強のものを選んだ形で、勝者の呪いと見るのが妥当です。</li>
<li>X3・X4(パターン図鑑由来)は、掛かる銘柄が2〜6%と少なく、確認期間でも有意ではありませんでした。</li>
<li><b>判断: フィルターは採用しない。モデルの既定は変えない。信用残(Standard限定データ)を、モデル・規則に入れる根拠はない。</b></li>
</ul>
<p class="note">未検証の仮説: 図鑑の再現は広い母集団(売買代金2,000万円以上)、順位予測は5億円以上で、効果の出る銘柄が対象外かもしれない。既存の特徴量(ボラ・過去リターン)と重なっている可能性もある。</p>

<h2>6. まだ分かっていないこと</h2>
<ul class="pending">
<li><b>探索は、ここで打ち切る。</b>確認済みで残るのは、S2(段階B)と、避ける側の弱い傾向だけ。確認期間を何度も読むほど偽の発見が増えるため、以後は前向きの記録を貯めて結論を待つ。</li>
<li><b>S2の前向きの記録:</b> 実装済み。データを更新するたびに記録し、権利月の後に採点します。12か月以上たまるまで結論を出しません。</li>
<li><b>順位予測の前向きの記録:</b> 2026-11-12に開始。12期(約1年)たまるまで結論を出さない。</li>
<li><b>予測モデル側の未完了:</b> 標本内残差の過小評価(FIX-09の2)、リッジ罰則のパネルでの検証(同3)。</li>
</ul>

<h2>7. 検証の限界</h2>
<ul>
<li>母集団は、流動性の高い銘柄の等ウエイト。TOPIXは時価総額加重で、性質が違う。</li>
<li>評価期間は約6.4年。リターンでの有意性は、原理的に出にくい。</li>
<li>約200件の検定を家族ごとに補正した。補正は家族の中だけで、全体の偽発見の期待数は、家族ごとの q の合計に近い。</li>
<li>発見と確認の境界は2022-04で、東証の市場再編と重なる。</li>
<li>「結果を見てから追加した検証」(決算起因の急落、下がり方の特徴)は探索的。確認は前向きの記録で行う。</li>
</ul>
<p class="note">事前固定の仕様と、検証の全記録は、リポジトリの <code>docs/</code>(<code>w5_protocol.md</code>、<code>final_report.md</code>)にある。試行台帳は追記専用のハッシュ連鎖で、改ざんを検出できる。</p>
'''
html_doc=f'''<title>J-Quants 10年検証報告</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap">
<style>{CSS}</style>
<main>{BODY}</main>
'''
open(OUT,"w",encoding="utf-8").write(html_doc)
print(len(html_doc))
