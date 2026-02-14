# ブログ埋め込み用スニペット（3種類）

| ファイル | 用途 | #game-map の主な属性 |
|----------|------|----------------------|
| **blog_embed_snippet.html** | **全部用** — 全ピン表示 | `data-zoom="2"` のみ |
| **blueprint_embed_snippet.html** | **設計図用** — 設計図ピンのみ + 常時ラベル | `data-filter="blueprint"` `data-show-labels="true"` |
| **lem_embed_snippet.html** | **LEM用** — LEMピンのみ + 常時ラベル | `data-filter="lem"` `data-show-labels="true"` |

- いずれも `data-csv` は指定しない（map.js と同階層の `master_data.csv` を参照）。
- map.js は `raw.githack.com/lime0404forest-commits/map/main/games/StarRupture/None/map.js` を読み込む想定。

**ブログで不具合が直らない場合**
- ブログは上記 URL の map.js を参照しています。このリポジトリ（map-editor）で map.js を修正しただけでは、ブログには反映されません。
- **修正を反映するには**：map.js（と必要なら master_data.csv）を、埋め込み URL が指すリポジトリ（例: lime0404forest-commits/map）の同じパスにプッシュしてください。
- 反映後、キャッシュを避けるため埋め込みの `?v=20260215` を `?v=20260216` のように更新してください。map.js 先頭コメントのバージョン（例: v20260216）で読み込まれているか確認できます。

- 単体プレビュー用の完全なHTMLは **embed.html**（全部用と同じ構成）。
