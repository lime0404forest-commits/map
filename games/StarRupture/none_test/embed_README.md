# none_test（テスト用）— 埋め込み・反映方法

`map.js` は **スクリプトのURLのディレクトリを `baseUrl` として**、同じ階層の `master_data.csv` / `pins_export.json`（任意）/ `areas.json` を読みます。

---

## おすすめ: 即時反映（ファイルマネージャー・GitHub不要）

サーバーの **同一ディレクトリ** に次を置きます（名前はそのまま）。

| ファイル | 必須 |
|----------|------|
| `embed.html` | iframe 用ページにする場合 |
| `map.js` | 必須 |
| `master_data.csv` | ピンをCSVから読む場合（どちらか） |
| `pins_export.json` | ピンをJSONから読む場合（どちらか） |
| `areas.json` | エリア表示（無くても動く） |

- **`embed.html` は `<script src="map.js">` で相対読み込み** になっています。  
  アップロード後、ブラウザで  
  `https://あなたのドメイン/…/embed.html`  
  を開けば、**上書き保存した内容がそのまま反映**されます（CDNキャッシュなし）。

### iframe でブログに載せる例

`embed.html` を置いた **実際のURL** を `src` にします。

```html
<iframe
  src="https://YOUR-DOMAIN/path/to/embed.html"
  title="StarRupture マップ（テスト）"
  width="100%"
  height="640"
  style="border:1px solid #333;display:block;max-width:100%;min-height:480px;"
  loading="lazy"
  allowfullscreen
></iframe>
```

### カスタムHTMLブロックに直接貼る場合

`blog_embed_snippet_selfhost.html` を使い、コメントのとおり **`YOUR_BASE_URL` を自サーバーのディレクトリURL（末尾 `/`）** に置き換えてください。  
`map.js` と同じ場所に `master_data.csv` / `areas.json` を置けば即反映です。

---

## GitHub / raw.githack 経由（反映が遅れがち）

push と CDN キャッシュの都合で遅延します。バックアップ・共有用として利用。

- `blog_embed_snippet.html` などは **githack の `none_test/map.js`** を参照。
- iframe 用の githack URL は `embed_README` 旧版や [raw.githack.com](https://raw.githack.com/) を参照。

---

## ローカル確認

- `index.html` — 同階層の `map.js` を相対読み込み（開発用）

---

## タイル画像について

`map.js` 内の `tileUrl` は外部CDNのままです。タイルも自サーバーにしたい場合は `map.js` の `tileUrl` を書き換えてからアップロードしてください。
