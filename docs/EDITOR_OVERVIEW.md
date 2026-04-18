# マップエディター仕様（ざっくり概要）

この文書は **Strategy Map Portal / MapEditor** の役割とデータの流れを短くまとめたものです。細部は `src/editor.py` 等の実装を参照してください。

---

## 全体像

| 要素 | 説明 |
|------|------|
| **入口** | `main.py` → `Portal`（ゲーム選択 → 地域選択 → エディタ起動） |
| **メイン** | `MapEditor`（CustomTkinter）。左サイドバーでピン／エリア編集、中央に地図キャンバス、右にサイト相当のピンプレビュー |
| **データ置き場** | `games/<ゲーム>/<地域>/`（`GAMES_ROOT` 配下） |

新規地域はポータルから画像を選ぶとタイル生成などの初期化が走り、そのフォルダがマップ単位のワークスペースになる。

---

## ゲームフォルダに置く主なファイル

| ファイル | 役割 |
|----------|------|
| `config.json` | マップ画像パス、解像度、マスタ（オブジェクト・カテゴリ・アイテム等）、`save_file`、任意で `wp_rest_guide_sources` や `guide_page_links_file` など |
| `master_data.csv`（既定名。`config` で変更可） | **ピン1行1レコード**。座標・オブジェクト・カテゴリJSON・メモ・リンク列など |
| `areas.json` | エリア（多角形等）の編集データ |
| `tiles/` | ズーム用タイル画像（ポータルで地域作成時に生成） |
| `guide_page_links.json`（任意） | ガイド記事候補（slug / タイトル日英 / URL 日英など）。REST とマージしてピン編集の候補に使う |
| `templates.json`（任意） | ピン定型（オブジェクト・カテゴリ・リンク等のプリセット） |
| `view-presets.json`（任意） | サイト表示プリセット |

---

## ピン編集（サイドバー中心）

- **オブジェクト（必須）**: `attr_mapping` に基づくマーカー種別。属性スロットはオブジェクト定義に応じて動的。
- **カテゴリ／中身**: 複数スロット。JSON（`categories` 列）として保存。定型から一括作成も可。
- **表示名**: 地点名の JP / EN 上書き（空ならマスタ側の名前が使われる想定）。
- **重要度・メモ**: JP / EN メモは `<br>` 保存など HTML 寄りの扱い。
- **リンク設定（折りたたみ）**  
  - JP: 検索 → ページ候補コンボ（`url_jp` がある行のみ）→ URL 入力  
  - EN: 同様（`url_en` のみ）  
  - **アンカー（共通）**: `#` なしで入力。CSV の `link_anchor` に保存し、ベース URL 列はフラグメントなし。エクスポート時に日英両方へ `#アンカー` を付与（`export_utils.resolve_pin_for_display`）。
- **親ピン**: `parent_uid` / `parent_type`（inside / near / in_area など）。
- **マーカー表示**: `marker_display_style`（map.js 側の表示モードと連携）。
- **特記事項**: カテゴリルールに応じた補足 UI（`category_special_notes` 等）。

保存は **CSV 書き出し**（列は `editor.py` の `write_files` の `flds` に準拠）。未保存の切り替え時は確認ダイアログ。

---

## エリア編集

- 多角形・円・矩形の作成／編集モードと、`areas.json` への保存。
- ピン編集とモードが干渉しないよう切り替え時に確認がある。

---

## 環境設定ウィンドウ（`SettingsWindow`）

マスタの CRUD に近い操作を別ウィンドウで行う。

- オブジェクト（属性マッピング）
- ルート参照（分割モード時）
- カテゴリ・アイテム
- EN 未設定の確認用タブ
- 旧 `type` 系の互換タブ

保存すると `config.json` が更新され、エディタ側マスタが再読込される。

---

## WordPress / ガイドリンク連携

- **`wp_rest_guide.py`**: REST の投稿一覧から日英ペア行を組み立て。`lang` が無い場合はパーマリンクの `/en/` 有無で言語を推論する処理あり。
- **`config.json` の `wp_rest_guide_sources`**: 取得元 REST のリスト（無ければモジュール既定）。
- **ピン側**: `guide_page_links.json` と REST 結果をマージし、ピン編集のコンボ候補に。別途 **WP 候補ピッカー**（`WpRestGuidePickerWindow`）から一覧選択で URL を埋めることも可能。

---

## エクスポート・プレビュー

| モジュール | 役割 |
|------------|------|
| `export_utils.py` | CSV のピンを表示用に解決し、`pins_export.json` 等へ。リンクはベース + `link_anchor` を結合した URL を出力 |
| `pin_site_preview.py` | map.js に近いルールでツールチップ／ポップアップ文言を組み立て、右ペインに表示 |

---

## その他 UI・操作

- **ピンフィルタ**（`PinFilterWindow`）: マップ上の表示絞り込み。
- **サイト表示プリセット**（`ViewPresetWindow`）: `view-presets.json` 管理。
- **地図**: ズーム・パン、タイル／オリジナル画像の表示。クロップ保存など（`utils` 利用）。
- **メニュー**: 設定・エクスポート・マスタ CSV 出力など（メニュー定義は `editor.py` 内）。

---

## 技術スタック（ざっくり）

- Python 3、**CustomTkinter** + **tkinter Canvas**（地図・ピン描画）
- **Pillow**（画像・タイル）
- ピン・エリアデータは **CSV / JSON** が主。埋め込みサイト用は **map.js**（各ゲームの `world map` 等）が別途 CSV または `pins_export.json` を読む想定

---

## 関連ソース（読む順の目安）

1. `src/portal.py` — 起動とフォルダ作成  
2. `src/editor.py` — `MapEditor` と各ダイアログ（ファイルが大きいので検索で追う）  
3. `src/export_utils.py` — ブログ／JSON エクスポート  
4. `src/wp_rest_guide.py` — REST ガイド行の収集  
5. `src/pin_site_preview.py` — プレビュー文言  
6. `games/<game>/<region>/config.json` — そのマップの真実の設定

---

*このファイルは仕様の要約であり、挙動の正はソースコードに従います。*
