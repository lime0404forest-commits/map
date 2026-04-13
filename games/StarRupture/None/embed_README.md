# ブログ埋め込み用スニペット（3種類）

| ファイル | 用途 | #game-map の主な属性 |
|----------|------|----------------------|
| **blog_embed_snippet.html** | **全部用** — 全ピン表示 | `data-zoom="2"` のみ |
| **blueprint_embed_snippet.html** | **設計図用** — 設計図ピンのみ + 常時ラベル | `data-filter="blueprint"` `data-show-labels="true"` |
| **lem_embed_snippet.html** | **LEM用** — LEMピンのみ + 常時ラベル | `data-filter="lem"` `data-show-labels="true"` |

- 既定では `data-csv` なしで GitHub 上の `master_data.csv`（jsDelivr）を参照します。別 URL にしたい場合のみ `#game-map` に `data-csv="https://..."` を付けます。
- タイルだけ自サイトにある場合は `data-tiles="https://あなたのドメイン/.../tiles/{z}/{x}/{y}.webp"` で上書きできます（`{z}/{x}/{y}` はそのまま）。
- map.js は次を推奨（キャッシュに強い）:  
  `https://cdn.jsdelivr.net/gh/lime0404forest-commits/map@main/games/StarRupture/None/map.js?v=20260410`

**CSV 形式**
- エディタが書き出す列（`name_jp`, `category`, `categories` の JSON, `memo_jp` / `memo_en`, `attribute` など）に対応しています。旧形式（`ITEM_WEAPON` 等のみの列）もヘッダーで判別して読みます。

**ブログで不具合が直らない場合**
- 埋め込みは上記 URL の map.js / CSV を参照します。map-editor 側で直しただけではブログに出ません。**map リポジトリに同じパスでプッシュ**してください。
- 反映後は `?v=20260410` のようにクエリを更新し、ブラウザの開発者ツールのコンソールで `StarRupture map.js v20260410` が出るか確認してください。

- 単体プレビュー用の完全なHTMLは **embed.html**（全部用と同じ構成）。
