# Results layout

| Path | Contents | Git |
|------|----------|-----|
| `raw/` | Generation JSONL + **private** `blind_mapping_*.csv` | ignored |
| `blinded/` | Blinded response CSVs for raters | ignored by default |
| `ratings/` | Filled human rating sheets | add reviewed files intentionally |
| `analysis/` | Summary CSVs + `figures/` | aggregated outputs may be published after review |

Never commit AWS secrets or blind mappings.
