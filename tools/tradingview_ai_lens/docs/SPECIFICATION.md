# AI Agent Lens: Specification

Version 1.0 · Pine Script v6 · Packet schema `ai-agent-lens/v1`

This document describes exactly what the indicator calculates, so a person or an AI agent can verify every number it produces.

---

## 1. Design principles

| Principle | How it is enforced |
|---|---|
| No repainting | Setups, trade tracking and alert packets are evaluated only when `barstate.isconfirmed` is true, i.e. on closed bars. |
| No lookahead | Daily and higher-timeframe values are requested as `expr[1]` with `lookahead = barmerge.lookahead_on`, so only already-closed higher-timeframe bars are used. |
| Agent-first output | Every value is emitted as structured JSON with fixed field names and enum values. Nothing has to be read from colors or shapes. |
| Transparent scoring | Each score is the sum of five published factors worth 20 points each. The factors are included in every packet. |
| Human-readable too | The same values are shown in the Agent Readout panel and in the TradingView Data Window. |

---

## 2. Inputs and defaults

| Group | Input | Default |
|---|---|---|
| Signals | Setup score threshold | 70 |
| Signals | Block setups in HIGH_VOLATILITY | true |
| Signals | Higher timeframe | 240 (4h) |
| Signals | Higher timeframe EMA length | 50 |
| Trend and momentum | Fast / mid / slow EMA | 20 / 50 / 200 |
| Trend and momentum | Slow EMA slope lookback | 5 bars |
| Trend and momentum | RSI length, overbought, oversold | 14, 75, 25 |
| Trend and momentum | ADX / DMI length, trend threshold | 14, 20 |
| Volume and volatility | Volume average length | 20 |
| Volume and volatility | ATR length | 14 |
| Volume and volatility | ATR percentile lookback, HIGH_VOLATILITY level | 100, 90 |
| Structure and levels | Swing pivot strength | 5 bars each side |
| Risk map | Stop distance | 1.5 x ATR |
| Risk map | Target 1 / Target 2 | 1.5R / 3R |
| AI agent packet | Send JSON packet | Every bar close |
| AI agent packet | Recent candles in packet | 5 |

---

## 3. Indicators used

| Name | Calculation |
|---|---|
| EMA fast / mid / slow | `ta.ema(close, 20 / 50 / 200)` |
| RSI | `ta.rsi(close, 14)` |
| MACD histogram | `ta.macd(close, 12, 26, 9)` |
| DI+ / DI- / ADX | `ta.dmi(14, 14)` |
| ATR | `ta.atr(14)` |
| ATR percentile | `ta.percentrank(ATR, 100)`, 0 to 100 |
| Relative volume | `volume / ta.sma(volume, 20)` |
| VWAP | `ta.vwap(hlc3)`, session anchored |
| Previous day high / low | daily `high[1]`, `low[1]` |
| Higher-timeframe bias | HTF `close[1]` versus HTF `EMA(50)[1]`: UP if above, DOWN if below, FLAT if equal, N/A if the chosen HTF is not higher than the chart |

---

## 4. Regime

Evaluated in this order; the first match wins.

| Regime | Condition |
|---|---|
| `HIGH_VOLATILITY` | ATR percentile >= 90 |
| `TREND_UP` | close > EMA slow AND EMA slow rising over 5 bars AND ADX >= 20 |
| `TREND_DOWN` | close < EMA slow AND EMA slow falling over 5 bars AND ADX >= 20 |
| `RANGE` | anything else |

---

## 5. Confluence scores

Two independent scores, `long` and `short`, each from 0 to 100. Five factors, 20 points each.

### Long score

| Factor | Points |
|---|---|
| Trend | +7 if EMA fast > EMA mid, +7 if EMA mid > EMA slow, +6 if close > EMA fast |
| Momentum | +10 if RSI > 50 (only +4 if RSI >= 75, overbought), +5 if MACD histogram > 0, +5 if MACD histogram rising |
| Strength | +10 if DI+ > DI-, +10 more if also ADX >= 20 |
| Volume | 20 if bullish candle and relative volume >= 1.5, 12 if bullish and >= 1.0, 6 if bullish below average, 0 otherwise |
| Higher timeframe | 20 if HTF bias UP, 10 if FLAT or N/A, 0 if DOWN |

### Short score

Exact mirror: EMAs reversed, RSI < 50 (only +4 if <= 25), MACD histogram < 0 and falling, DI- > DI+, bearish candle volume, HTF bias DOWN.

---

## 6. Setups

A setup fires on a closed bar when:

| Setup | Condition |
|---|---|
| `LONG_SETUP` | long score crosses up through the threshold (this bar >= 70, previous bar < 70) AND regime is not TREND_DOWN AND (regime is not HIGH_VOLATILITY, if blocking is on) |
| `SHORT_SETUP` | short score crosses up through the threshold AND regime is not TREND_UP AND (regime is not HIGH_VOLATILITY, if blocking is on) |

If both fire on the same bar, neither is taken. A setup in the same direction as a trade that is still open is ignored, so one move produces one signal. An opposite setup replaces the open trade.

---

## 7. Risk map and trade tracking

When a setup fires, the indicator opens a tracked trade at the close of the signal bar:

| Field | Long | Short |
|---|---|---|
| Entry | close | close |
| Stop | entry - 1.5 x ATR | entry + 1.5 x ATR |
| Risk (R) | entry - stop | stop - entry |
| Target 1 | entry + 1.5R | entry - 1.5R |
| Target 2 | entry + 3R | entry - 3R |

On every following closed bar the trade status is updated with that bar's high and low. **The stop is checked first** (conservative when one bar touches both).

| Status | Meaning |
|---|---|
| `ACTIVE` | open, no level touched |
| `TARGET_1_HIT` | target 1 touched, trade still tracked toward target 2 |
| `TARGET_2_HIT` | target 2 touched, trade closed |
| `STOPPED` | stop touched before target 1, trade closed |
| `STOPPED_AFTER_T1` | stop touched after target 1, trade closed |
| `NONE` | no trade yet |

An opposite setup replaces an open trade; a same-direction setup is ignored while a trade is open. The tracking is a reference for the agent, not a backtest: it ignores fees, slippage and partial exits.

---

## 8. Candle anatomy

| Field | Definition |
|---|---|
| direction | bull if close > open, bear if close < open, flat otherwise |
| body_pct | abs(close - open) / (high - low) x 100 |
| upper_wick_pct | (high - max(open, close)) / range x 100 |
| lower_wick_pct | (min(open, close) - low) / range x 100 |
| range_atr | (high - low) / ATR |
| close_position_pct | (close - low) / range x 100: 100 = closed at the high |
| gap_pct | (open - previous close) / previous close x 100 |

### Patterns

Shape only. The first match in this order is reported:

| Pattern | Rule |
|---|---|
| `FLAT` | high equals low |
| `BULLISH_ENGULFING` | bullish candle, previous bearish, close >= previous open, open <= previous close |
| `BEARISH_ENGULFING` | mirror of the above |
| `DOJI` | body <= 10% of range |
| `HAMMER` | lower wick >= 2 x body and upper wick <= 15% of range |
| `SHOOTING_STAR` | upper wick >= 2 x body and lower wick <= 15% of range |
| `BULLISH_MARUBOZU` / `BEARISH_MARUBOZU` | body >= 90% of range |
| `INSIDE_BAR` | high < previous high and low > previous low |
| `OUTSIDE_BAR` | high > previous high and low < previous low |
| `WIDE_RANGE_BULL` / `WIDE_RANGE_BEAR` | range >= 1.8 x ATR |
| `NONE` | none of the above |

---

## 9. Market structure

Swing highs and lows are confirmed pivots with 5 bars on each side (`ta.pivothigh` / `ta.pivotlow`). They appear 5 bars after the pivot and never move afterwards.

| Field | Rule |
|---|---|
| bias `BULLISH` | last swing high > previous swing high AND last swing low > previous swing low |
| bias `BEARISH` | last swing high < previous AND last swing low < previous |
| bias `MIXED` | anything else |
| event `BREAK_UP` | close crosses above the last swing high |
| event `BREAK_DOWN` | close crosses below the last swing low |

---

## 10. Outputs

| Output | Where |
|---|---|
| JSON packet | `alert()` once per bar close. Schema in [PACKET_SCHEMA.md](PACKET_SCHEMA.md) |
| Static alerts | "AI Lens: LONG setup" and "AI Lens: SHORT setup" alert conditions |
| Agent Readout panel | Signal card on the chart: LONG / SHORT / WAIT, status, regime, scores, factors aligned (12+ of 20 points), open trade with live R multiple, context, candle and structure (Full or Compact mode) |
| Data Window | Long score, short score, regime code, HTF bias, RSI, ADX, relative volume, ATR percentile, trade side |
| Chart drawings | EMA ribbon and EMA 200, previous day high/low, VWAP, swing points, structure breaks, LONG/SHORT score labels with factor tooltips, risk and reward position boxes with price tags |

---

## 11. Known limitations

- Scores and patterns are rule-based. They describe the chart; they do not predict it.
- The trade tracker is a reference only (no fees, no slippage, no partial fills).
- Symbols without volume data (some indices, some forex feeds) get `null` volume fields and zero volume points.
- VWAP and previous-day levels are most meaningful on intraday charts.
- Webhook alerts require a paid TradingView plan with two-factor authentication enabled.
