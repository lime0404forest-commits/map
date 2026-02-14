# ブログ埋め込み用スニペット（3種類）

| ファイル | 用途 | #game-map の主な属性 |
|----------|------|----------------------|
| **blog_embed_snippet.html** | **全部用** — 全ピン表示 | `data-zoom="2"` のみ |
| **blueprint_embed_snippet.html** | **設計図用** — 設計図ピンのみ + 常時ラベル | `data-filter="blueprint"` `data-show-labels="true"` |
| **lem_embed_snippet.html** | **LEM用** — LEMピンのみ + 常時ラベル | `data-filter="lem"` `data-show-labels="true"` |

- いずれも `data-csv` は指定しない（map.js と同階層の `master_data.csv` を参照）。
- map.js は `raw.githack.com/lime0404forest-commits/map/main/games/StarRupture/None/map.js` を読み込む想定。
- 単体プレビュー用の完全なHTMLは **embed.html**（全部用と同じ構成）。
