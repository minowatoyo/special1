"""合成データで chartlib の指標を描画するデモ（実市場データではない）。

    python examples/demo_chart.py [--out-dir examples]

出力:
  demo_chart_basic.png    ローソク足 + SMA25/75 + ボリンジャー(20,2) + 出来高 + RSI(14) + MACD(12,26,9)
  demo_chart_ichimoku.png ローソク足 + 一目均衡表（転換線・基準線・雲・遅行スパン）
配色は日本の慣行（陽線=赤、陰線=青）。ラベルは CJK フォント非依存にするため英語。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import mplfinance as mpf  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from chartlib import indicators as ind  # noqa: E402
from conftest import make_ohlcv  # noqa: E402


def style():
    mc = mpf.make_marketcolors(up="#d32f2f", down="#1976d2", edge="inherit", wick="inherit", volume="inherit")
    return mpf.make_mpf_style(base_mpf_style="yahoo", marketcolors=mc, gridstyle=":", gridcolor="#cccccc")


def basic(df: pd.DataFrame, shown: int, out: Path) -> None:
    d = df
    bb = ind.bollinger(d.close, 20, 2.0)
    r = ind.rsi(d.close, 14)
    m = ind.macd(d.close)
    tail = slice(-shown, None)
    plot_df = d.rename(columns=str.capitalize).iloc[tail]
    hist = m["hist"].iloc[tail]
    aps = [
        mpf.make_addplot(ind.sma(d.close, 25).iloc[tail], color="#fb8c00", width=1.0),
        mpf.make_addplot(ind.sma(d.close, 75).iloc[tail], color="#388e3c", width=1.0),
        mpf.make_addplot(bb["upper"].iloc[tail], color="#757575", linestyle="--", width=0.7),
        mpf.make_addplot(bb["lower"].iloc[tail], color="#757575", linestyle="--", width=0.7),
        mpf.make_addplot(r.iloc[tail], panel=2, color="#6a1b9a", ylabel="RSI(14)", ylim=(0, 100), secondary_y=False),
        mpf.make_addplot(pd.Series(70.0, index=plot_df.index), panel=2, color="#616161", linestyle="--", width=0.8, secondary_y=False),
        mpf.make_addplot(pd.Series(30.0, index=plot_df.index), panel=2, color="#616161", linestyle="--", width=0.8, secondary_y=False),
        mpf.make_addplot(m["macd"].iloc[tail], panel=3, color="#1976d2", ylabel="MACD", secondary_y=False),
        mpf.make_addplot(m["signal"].iloc[tail], panel=3, color="#fb8c00", secondary_y=False),
        mpf.make_addplot(hist, panel=3, type="bar", color=np.where(hist >= 0, "#ef9a9a", "#90caf9"), secondary_y=False),
    ]
    mpf.plot(plot_df, type="candle", style=style(), volume=True, addplot=aps, panel_ratios=(5, 1.4, 2, 2),
             figsize=(12, 9), title="SYNTHETIC DATA: SMA25/75, Bollinger(20,2), RSI(14), MACD(12,26,9)",
             savefig=dict(fname=str(out), dpi=110, bbox_inches="tight"))


def ichimoku_chart(df: pd.DataFrame, shown: int, out: Path) -> None:
    d = df
    ich = ind.ichimoku(d.high, d.low, d.close)
    tail = slice(-shown, None)
    plot_df = d.rename(columns=str.capitalize).iloc[tail]
    sa, sb = ich["senkou_a"].iloc[tail], ich["senkou_b"].iloc[tail]
    valid = (sa.notna() & sb.notna()).to_numpy()
    aps = [
        mpf.make_addplot(ich["tenkan"].iloc[tail], color="#1976d2", width=1.0),
        mpf.make_addplot(ich["kijun"].iloc[tail], color="#d32f2f", width=1.0),
        mpf.make_addplot(sa, color="#ef9a9a", width=0.6),
        mpf.make_addplot(sb, color="#90caf9", width=0.6),
        mpf.make_addplot(ich["chikou"].iloc[tail], color="#7b1fa2", width=0.9),
    ]
    fills = [
        dict(y1=sa.fillna(0).to_numpy(), y2=sb.fillna(0).to_numpy(), where=valid & (sa >= sb).to_numpy(),
             alpha=0.25, color="#ef5350"),
        dict(y1=sa.fillna(0).to_numpy(), y2=sb.fillna(0).to_numpy(), where=valid & (sa < sb).to_numpy(),
             alpha=0.25, color="#42a5f5"),
    ]
    mpf.plot(plot_df, type="candle", style=style(), volume=False, addplot=aps, fill_between=fills,
             figsize=(12, 6.5), title="SYNTHETIC DATA: Ichimoku (9,26,52) — tenkan blue, kijun red, chikou purple",
             savefig=dict(fname=str(out), dpi=110, bbox_inches="tight"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--shown", type=int, default=170)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = make_ohlcv(n=600, seed=58)   # 上昇も下落も含む経路（見本向き）
    basic(df, args.shown, out_dir / "demo_chart_basic.png")
    ichimoku_chart(df, args.shown, out_dir / "demo_chart_ichimoku.png")
    print("wrote", out_dir / "demo_chart_basic.png", "and", out_dir / "demo_chart_ichimoku.png")


if __name__ == "__main__":
    main()
