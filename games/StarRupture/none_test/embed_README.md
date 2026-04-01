# none_test（テスト用）— ブログ埋め込み

このフォルダは **本番 `None` とデータを分けて試す** ためのセットです。  
`map.js` は **スクリプトURLのディレクトリを `baseUrl` として** `master_data.csv` / `pins_export.json` / `areas.json` を読みます。

## 読み込む map.js のURL（共通）

`none_test` 完結用:

`https://raw.githack.com/lime0404forest-commits/map/main/games/StarRupture/none_test/map.js?v=20260218_none_test`

更新したら **`?v=` の日付やサフィックスを変えて** キャッシュを避けてください。

## カスタムHTMLブロック

- `blog_embed_snippet.html` — 全部用
- `blueprint_embed_snippet.html` — 設計図用
- `lem_embed_snippet.html` — LEM用  

いずれも上記 **none_test の map.js** を参照するようになっています。

## iframe で `embed.html` を載せる場合

`raw.githubusercontent.com` のURLは **X-Frame-Options 等で iframe から弾かれる**ことが多いです。  
次のように **[raw.githack.com](https://raw.githack.com/) のURL** を `src` に使ってください。

**開発用（コミット直後に近い内容が見える・キャッシュ弱め）**

```html
<iframe
  src="https://raw.githack.com/lime0404forest-commits/map/main/games/StarRupture/none_test/embed.html"
  title="StarRupture マップ（テスト）"
  width="100%"
  height="640"
  style="border:1px solid #333;display:block;max-width:100%;min-height:480px;"
  loading="lazy"
  allowfullscreen
></iframe>
```

**本番キャッシュ用（raw.githack の画面で表示される Production URL）**  
サイトに貼る最終版は、必要に応じて [raw.githack.com](https://raw.githack.com/) で生成した **Production** の `embed.html` URL に差し替えてください。

## 単体プレビュー

- ローカル: `index.html`（同階層の `map.js` を相対読み込み）
- 完全HTML: `embed.html`（上記 githack URL で開く）

## 反映手順

1. このリポジトリの `games/StarRupture/none_test/` を **lime0404forest-commits/map** に push  
2. 埋め込み側の `?v=` を更新  
3. githack Production を使う場合は、初回や更新後にキャッシュが効くまで少し時間がかかることがあります
