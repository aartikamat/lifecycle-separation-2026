# SCHEMA — LIFECYCLE-SEPARATION-2026-v1

Field-level documentation for the three data files.

## `sniper_cohorts_intra_v2.jsonl`

JSON Lines format. One row per cohort detection event.

| Field | Type | Description |
|---|---|---|
| `mint` | string | Solana base-58 token mint address |
| `detected_at` | number (epoch seconds) | UTC timestamp when the cohort was detected |
| `wallets` | array of strings | Solana base-58 wallet addresses in the detected cohort |
| `n_wallets` | integer | Cohort size (length of `wallets`) |
| `window_sec` | integer | Detection window duration in seconds |
| `avg_sol` | number | Mean SOL committed per wallet during the first-buyer window |
| `first_rank` | integer | Median first-buyer rank across cohort wallets |
| `tx_sigs` | array of strings | Transaction signatures for cohort buy events |

**File size:** 428 KB
**Row count:** 623
**Time range:** 2026-06-29T02:20:58Z to 2026-07-16T15:09:23Z (17.5 days)
**Unique mints:** 623

## `rejection_outcomes_v1_window.jsonl.gz` and `rejection_outcomes_v2_window.jsonl.gz`

JSON Lines format (gzip-compressed). One row per post-rejection outcome sample. A single mint can appear multiple times (one row per sample time after rejection).

| Field | Type | Description |
|---|---|---|
| `mint` | string | Solana base-58 token mint address |
| `symbol` | string | Token ticker symbol |
| `rejectReason` | string | Filter-specific rejection reason code |
| `rejectTs` | string (ISO-8601 UTC) | Timestamp of the rejection event |
| `sampleTs` | string (ISO-8601 UTC) | Timestamp of this post-rejection sample |
| `ageMin` | integer | Token age in minutes at sample time |
| `priceUsd` | number | Token price in USD at sample time |
| `liquidity` | number | Pool liquidity in USD at sample time |
| `volume24h` | number | Trailing 24-hour trading volume in USD |
| `priceChange5m` | number | Percent price change over the trailing 5 minutes |
| `priceChange1h` | number | Percent price change over the trailing 1 hour |
| `priceChange24h` | number | Percent price change over the trailing 24 hours |
| `dexId` | string | DEX identifier where the token trades (pumpswap, raydium, meteora, pumpfun, metadao) |
| `pairAddress` | string | Trading pair address on the DEX |

### File summaries

| File | Size (compressed) | Size (uncompressed) | Rows | Unique mints |
|---|---|---|---|---|
| `rejection_outcomes_v1_window.jsonl.gz` | 1.17 MB | 8.21 MB | 12,688 | 83 |
| `rejection_outcomes_v2_window.jsonl.gz` | 30.2 MB | 154 MB | 238,722 | 1,743 |

## Common reject-reason vocabulary

The `rejectReason` field takes values including but not limited to:

- `timeSlot_not_strong` — time-of-day filter
- `downtrend_24h` — trailing 24h price-drop filter
- `marketcap_out_of_range` — market-cap threshold filter
- `multi_tf_fade` — multi-timeframe fade filter
- `dormant_d7_trades_lt_3` — dormancy filter
- `insufficient_liquidity` — liquidity threshold filter
- (additional filter-specific codes may appear)

The precise mapping between reason codes and filter logic is documented in Kamat (2026a) and Kamat (2026c).

## Data provenance summary

- Cohort detections are produced by the author's cohort-detection process (Python 3), which consumes raw pump.fun program events via a Helius WebSocket.
- Rejection outcomes are produced by the author's post-rejection tracker (Node.js), which reads an algorithmic trading system's filter-rejection log and samples post-rejection price/liquidity via DexScreener.
- Both streams are the same measurement pipelines used across the RED-2400, RED-COHORT-2026, and RED-PUMP-2026-v1 dataset series.

## Notes on time windows

The windowed rejection subsets are extracted from the live rejection-outcomes corpus by restricting `rejectTs` OR `sampleTs` to fall within the target cohort observation window:

- **v1 window:** 2026-06-11T21:47:47Z to 2026-06-26T00:00:00Z (approximately 13.4 days)
- **v2 window:** 2026-06-29T02:20:58Z to 2026-07-17T00:00:00Z (approximately 17.5 days)

The extraction preserves all fields of the original rejection rows.
