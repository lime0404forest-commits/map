(function() {
    'use strict';
    // VEIN world map — フィルターは Star Rupture 向けではなく config.json の attr_mapping（オブジェクト種）基準
    // ピン: marker_display_style (icon_only) / CSV ヘッダー対応 / JSON ピンは config でスタイル補完（要アップロード同期）

    var maxZoom = 5;
    var imgW = 5878;
    var imgH = 5886;
    var mapPadding = 1500;

    var mapDiv = document.getElementById('game-map');
    if (!mapDiv) {
        console.error('map.js: #game-map element not found');
        return;
    }

    (function ensureLeafletShellStyle() {
        if (document.getElementById('map-pin-leaflet-shell-style')) return;
        var st = document.createElement('style');
        st.id = 'map-pin-leaflet-shell-style';
        st.textContent = [
            '.map-pin-leaflet-shell{background:transparent!important;border:none!important;}',
            '.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-1 .map-pin-svg-composite,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-1 .map-pin-icon-only,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-1.emoji-icon div{transform:scale(0.92);}',
            '.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-2 .map-pin-svg-composite,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-2 .map-pin-icon-only,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-2.emoji-icon div{transform:scale(0.97);}',
            '.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-3 .map-pin-svg-composite,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-3 .map-pin-icon-only,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-3.emoji-icon div{transform:scale(1);}',
            '.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-4 .map-pin-svg-composite,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-4 .map-pin-icon-only,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-4.emoji-icon div{transform:scale(1.08);}',
            '.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-5 .map-pin-svg-composite,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-5 .map-pin-icon-only,.leaflet-marker-icon.map-pin-importance--on.map-pin-imp-5.emoji-icon div{transform:scale(1.16);}',
            '.leaflet-marker-icon.map-pin-importance--on.map-pin-importance-glow.map-pin-imp-4 .map-pin-svg-composite,.leaflet-marker-icon.map-pin-importance--on.map-pin-importance-glow.map-pin-imp-4 .map-pin-icon-only,.leaflet-marker-icon.map-pin-importance--on.map-pin-importance-glow.map-pin-imp-4.emoji-icon div{',
            '-webkit-filter:drop-shadow(0 0 6px rgba(255,210,120,0.45));filter:drop-shadow(0 0 6px rgba(255,210,120,0.45));}',
            '.leaflet-marker-icon.map-pin-importance--on.map-pin-importance-glow.map-pin-imp-5 .map-pin-svg-composite,.leaflet-marker-icon.map-pin-importance--on.map-pin-importance-glow.map-pin-imp-5 .map-pin-icon-only,.leaflet-marker-icon.map-pin-importance--on.map-pin-importance-glow.map-pin-imp-5.emoji-icon div{',
            '-webkit-filter:drop-shadow(0 0 9px rgba(255,220,140,0.56));filter:drop-shadow(0 0 9px rgba(255,220,140,0.56));}',
            '.leaflet-marker-icon.map-pin-active{z-index:1200!important;}',
            '.leaflet-marker-icon.map-pin-active .map-pin-svg-composite,.leaflet-marker-icon.map-pin-active .map-pin-icon-only,.leaflet-marker-icon.map-pin-active.emoji-icon div{',
            'transform:scale(1.12);transform-origin:50% 50%;',
            '-webkit-filter:drop-shadow(0 0 10px rgba(255,220,140,0.55));',
            'filter:drop-shadow(0 0 10px rgba(255,220,140,0.55));',
            'transition:transform 0.12s ease,filter 0.12s ease;}'
        ].join('');
        document.head.appendChild(st);
    })();

    /** 左ドロワー型フィルター UI（L.control.layers 置き換え）— 落ち着いたトーン・SVG アイコン */
    (function ensureVeinFilterDrawerStyles() {
        if (document.getElementById('vein-filter-drawer-style')) return;
        var st = document.createElement('style');
        st.id = 'vein-filter-drawer-style';
        st.textContent = [
            '#map-container.vein-map-with-filter{display:flex!important;flex-direction:row!important;align-items:stretch!important;width:100%!important;box-sizing:border-box!important;',
            'min-height:560px!important;height:88vh!important;max-height:100%!important;position:relative!important;overflow:hidden!important;}',
            '#map-container.vein-map-with-filter #game-map{flex:1 1 auto!important;min-width:0!important;min-height:400px!important;',
            'align-self:stretch!important;max-height:100%!important;overflow:hidden!important;}',
            '.vein-filter-drawer{flex:0 0 auto;width:286px;max-width:88vw;box-sizing:border-box;',
            'background:#121214;border-right:1px solid rgba(255,255,255,0.045);',
            'display:flex;flex-direction:column;z-index:700;color:#b8b5b0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans JP",sans-serif;',
            'min-height:0!important;height:100%!important;max-height:100%!important;',
            'transition:width 0.2s ease,min-width 0.2s ease;overflow:hidden;font-size:13px;}',
            '.vein-filter-drawer.vein-filter-drawer--collapsed{width:48px;min-width:48px;}',
            '.vein-filter-drawer__head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 12px 8px;border-bottom:1px solid rgba(255,255,255,0.04);flex-shrink:0;}',
            '.vein-filter-drawer__title{font-size:10px;font-weight:500;letter-spacing:0.2em;text-transform:uppercase;color:#5a5855;}',
            '.vein-filter-drawer__toggle{width:30px;height:30px;border-radius:6px;border:1px solid rgba(255,255,255,0.06);background:transparent;',
            'color:#8e8c88;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:15px;line-height:1;transition:background 0.15s,color 0.15s;}',
            '.vein-filter-drawer__toggle:hover{background:rgba(255,255,255,0.05);color:#c9c6c1;}',
            '.vein-filter-drawer__scroll{flex:1 1 auto!important;min-height:0!important;overflow-y:auto;overflow-x:hidden;padding:6px 8px 12px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,0.12) transparent;}',
            '.vein-filter-drawer__scroll::-webkit-scrollbar{width:5px;}',
            '.vein-filter-drawer__scroll::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px;}',
            '.vein-filter-section{margin-bottom:14px;}',
            '.vein-filter-section:last-child{margin-bottom:4px;}',
            '.vein-filter-section__label{font-size:9px;font-weight:500;letter-spacing:0.18em;text-transform:uppercase;color:#4a4846;padding:8px 8px 6px;margin:0;}',
            '.vein-filter-group{margin-bottom:10px;}',
            '.vein-filter-group__head{display:flex;align-items:center;gap:10px;padding:8px 10px 6px;margin-bottom:0;border-bottom:1px solid rgba(255,255,255,0.035);border-radius:6px 6px 0 0;}',
            '.vein-filter-group__head.vein-filter-row{margin-bottom:0;}',
            '.vein-filter-group__title{flex:1;font-size:11px;font-weight:500;color:#8f8b85;letter-spacing:0.06em;}',
            '.vein-filter-group__body{padding:2px 0 6px 0;}',
            '.vein-filter-row--nested{margin-left:10px;padding-left:10px;border-left:1px solid rgba(255,255,255,0.05);}',
            '.vein-filter-row--nested-deep{margin-left:20px;padding-left:10px;border-left:1px solid rgba(255,255,255,0.045);}',
            '.vein-filter-subgroup-title{margin:6px 0 2px 12px;padding:4px 8px 3px;border-left:1px solid rgba(255,255,255,0.07);font-size:10px;letter-spacing:0.05em;color:#6f6c67;}',
            '.vein-filter-group--collapsed .vein-filter-group__body{display:none;}',
            '.vein-filter-group__collapse{flex:0 0 auto;min-width:52px;height:22px;border-radius:999px;border:1px solid rgba(255,255,255,0.09);background:rgba(255,255,255,0.03);',
            'color:#9b978f;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:4px;padding:0 8px;font-size:10px;line-height:1;}',
            '.vein-filter-group__collapse:hover{background:rgba(255,255,255,0.08);color:#d2cec8;}',
            '.vein-filter-group__collapse-arrow{display:inline-block;font-size:11px;line-height:1;transform:rotate(0deg);transition:transform 0.14s ease;}',
            '.vein-filter-group--collapsed .vein-filter-group__collapse-arrow{transform:rotate(-90deg);}',
            '.vein-filter-group__collapse-label{letter-spacing:0.04em;}',
            '.vein-filter-drawer--collapsed .vein-filter-group__collapse{display:none;}',
            '.vein-filter-drawer--collapsed .vein-filter-group__head,.vein-filter-drawer--collapsed .vein-filter-group__title{display:none;}',
            '.vein-filter-drawer--collapsed .vein-filter-row--nested{margin-left:0;border-left:none;padding-left:6px;}',
            '.vein-filter-row{display:flex;align-items:center;gap:10px;padding:8px 10px;margin-bottom:2px;border-radius:6px;cursor:pointer;',
            'border:1px solid transparent;border-left:2px solid transparent;transition:background 0.14s,border-color 0.14s;user-select:none;}',
            '.vein-filter-row:hover{background:rgba(255,255,255,0.03);}',
            '.vein-filter-row--on{background:rgba(255,255,255,0.045);border-left-color:rgba(180,175,168,0.35);}',
            '.vein-filter-row input{position:absolute;opacity:0;width:0;height:0;}',
            '.vein-filter-icon-svg{flex-shrink:0;color:#6e6b66;opacity:0.92;display:block;}',
            '.vein-filter-row--on .vein-filter-icon-svg{color:#9c9892;}',
            '.vein-filter-icon-svg--muted{color:#555350;opacity:0.85;}',
            '.vein-filter-label{flex:1;font-size:12.5px;font-weight:400;color:#a9a6a1;line-height:1.3;}',
            '.vein-filter-row--on .vein-filter-label{color:#d4d1cc;}',
            '.vein-filter-drawer--collapsed .vein-filter-drawer__title,.vein-filter-drawer--collapsed .vein-filter-label,.vein-filter-drawer--collapsed .vein-filter-section__label,.vein-filter-drawer--collapsed .vein-filter-none-label{display:none;}',
            '.vein-filter-drawer--collapsed .vein-filter-row{justify-content:center;padding:7px 4px;}',
            '.vein-filter-drawer--collapsed .vein-filter-icon-svg{margin:0;}',
            '.vein-filter-toggle-ui{flex-shrink:0;width:34px;height:18px;border-radius:999px;background:#1e1e21;position:relative;transition:background 0.16s;border:1px solid rgba(255,255,255,0.06);}',
            '.vein-filter-toggle-ui::after{content:"";position:absolute;width:14px;height:14px;border-radius:50%;background:#5c5a57;top:1px;left:2px;transition:transform 0.16s,background 0.16s;}',
            '.vein-filter-row--on .vein-filter-toggle-ui{background:#2c2c30;border-color:rgba(255,255,255,0.08);}',
            '.vein-filter-row--on .vein-filter-toggle-ui::after{transform:translateX(14px);background:#c8c4be;}',
            '.vein-filter-drawer--collapsed .vein-filter-toggle-ui{display:none;}',
            '.leaflet-top.leaflet-right .leaflet-control-zoom a{background:#161618!important;border:1px solid rgba(255,255,255,0.07)!important;color:#b5b2ad!important;}',
            '.leaflet-top.leaflet-right .leaflet-control-zoom a:hover{background:#1e1e21!important;}',
            '.leaflet-top.leaflet-right .leaflet-bar{box-shadow:0 2px 12px rgba(0,0,0,0.4);border-radius:8px;overflow:hidden;border:none!important;}',
            '.vein-fullscreen-btn{background:#161618!important;border:1px solid rgba(255,255,255,0.07)!important;color:#b5b2ad!important;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:14px;line-height:1;cursor:pointer;}',
            '.vein-fullscreen-btn:hover{background:#1e1e21!important;color:#d0ccc6!important;}',
            '.leaflet-control.vein-fullscreen-control{margin-top:8px;}',
            '.vein-filter-adv{margin-top:10px;border-top:1px solid rgba(255,255,255,0.06);padding-top:6px;}',
            '.vein-filter-adv__summary{cursor:pointer;font-size:10px;font-weight:500;letter-spacing:0.14em;color:#6a6865;padding:8px 6px 6px;list-style:none;user-select:none;}',
            '.vein-filter-adv__summary::-webkit-details-marker{display:none;}',
            '.vein-filter-adv__inner{padding:0 2px 10px;}',
            '.vein-filter-adv__search{width:100%;box-sizing:border-box;margin-bottom:8px;padding:7px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.08);background:#1a1a1d;color:#c9c6c1;font-size:12px;}',
            '.vein-filter-adv__search::placeholder{color:#5c5a57;}',
            '.vein-filter-adv__list{max-height:240px;overflow-y:auto;scrollbar-width:thin;}',
            '.vein-filter-adv .vein-filter-row--nested{margin-left:0;padding-left:6px;border-left:none;}',
            '.vein-filter-drawer--collapsed .vein-filter-adv{display:none;}'
        ].join('');
        document.head.appendChild(st);
    })();

    // 設定読み込み
    var showLabels = mapDiv.getAttribute('data-show-labels') === 'true';
    var htmlZoom = parseInt(mapDiv.getAttribute('data-zoom'), 10);
    // 既定は 1 段階寄り（2 -> 3）
    var defaultZoom = (!isNaN(htmlZoom)) ? htmlZoom : 3;
    var centerXRaw = parseFloat(mapDiv.getAttribute('data-center-x'));
    var centerYRaw = parseFloat(mapDiv.getAttribute('data-center-y'));
    var defaultCenterX = !isNaN(centerXRaw) ? centerXRaw : 2200;
    var defaultCenterY = !isNaN(centerYRaw) ? centerYRaw : 3300;
    var importanceVisualParam = (new URLSearchParams(window.location.search).get('importance_visual') || '').trim().toLowerCase();
    var importanceVisualRaw = (importanceVisualParam || mapDiv.getAttribute('data-importance-visual') || 'off').trim().toLowerCase();
    var importanceVisualVariant = 'size';
    if (importanceVisualRaw === 'size+glow' || importanceVisualRaw === 'size_glow' || importanceVisualRaw === 'glow') {
        importanceVisualVariant = 'size+glow';
    } else if (importanceVisualRaw === 'size') {
        importanceVisualVariant = 'size';
    }
    var importanceVisualEnabled = importanceVisualRaw !== 'off' && importanceVisualRaw !== 'false' && importanceVisualRaw !== '0';
    var filterMode = mapDiv.getAttribute('data-filter');
    var customCsv = mapDiv.getAttribute('data-csv');
    var customPins = mapDiv.getAttribute('data-pins');  // pins_export.json 用
    // テスト用: 未指定時は「その他」等も表示（本番 embed では付けない想定）
    var showAllPins = mapDiv.getAttribute('data-show-all-pins') === 'true';
    // 表示プリセット（embed から指定）: ?preset=weapons / data-view-preset="weapons"
    // 互換: ?subset=weapons / data-subset も preset として受け付ける
    var presetMode = (
        new URLSearchParams(window.location.search).get('preset') ||
        mapDiv.getAttribute('data-view-preset') ||
        new URLSearchParams(window.location.search).get('subset') ||
        mapDiv.getAttribute('data-subset') ||
        ''
    ).trim().toLowerCase();
    var subsetAllowedCategoryIds = null;
    var subsetAllowedObjectIds = null;
    var subsetAllowedItemIds = null;
    var presetDefaultOnObjectIds = null;
    var presetDefaultOffObjectIds = null;
    var presetDefaultOnCategoryIds = null;
    var presetDefaultOnItemIds = null;
    var presetCollapsedObjectIds = null;

    function setFromIdArray(arr) {
        if (!Array.isArray(arr) || arr.length === 0) return null;
        var s = new Set();
        arr.forEach(function (x) {
            var v = String(x || '').trim().toUpperCase();
            if (v) s.add(v);
        });
        return s.size > 0 ? s : null;
    }

    function builtinPresetRule(name) {
        var n = String(name || '').trim().toLowerCase();
        if (n === 'weapons' || n === 'weapon') {
            return {
                allowed_category_ids: ['LOOT_CONTAINER', 'WEAPON'],
                allowed_object_ids: ['POI', 'DEPLOYABLES'],
                allowed_item_ids: [],
                default_on_object_ids: ['DEPLOYABLES'],
                default_off_object_ids: ['POI'],
                default_on_category_ids: [],
                default_on_item_ids: [],
                collapsed_object_ids: ['POI']
            };
        }
        return null;
    }

    function applyViewPresetRule(rule) {
        subsetAllowedCategoryIds = null;
        subsetAllowedObjectIds = null;
        subsetAllowedItemIds = null;
        presetDefaultOnObjectIds = null;
        presetDefaultOffObjectIds = null;
        presetDefaultOnCategoryIds = null;
        presetDefaultOnItemIds = null;
        presetCollapsedObjectIds = null;
        if (!rule || typeof rule !== 'object') return;
        subsetAllowedCategoryIds = setFromIdArray(rule.allowed_category_ids);
        subsetAllowedObjectIds = setFromIdArray(rule.allowed_object_ids);
        subsetAllowedItemIds = setFromIdArray(rule.allowed_item_ids);
        presetDefaultOnObjectIds = setFromIdArray(rule.default_on_object_ids);
        presetDefaultOffObjectIds = setFromIdArray(rule.default_off_object_ids);
        presetDefaultOnCategoryIds = setFromIdArray(rule.default_on_category_ids);
        presetDefaultOnItemIds = setFromIdArray(rule.default_on_item_ids);
        presetCollapsedObjectIds = setFromIdArray(rule.collapsed_object_ids);
    }

    function isSubsetActive() {
        return !!subsetAllowedCategoryIds || !!subsetAllowedObjectIds || !!subsetAllowedItemIds ||
            !!presetDefaultOnObjectIds || !!presetDefaultOffObjectIds ||
            !!presetDefaultOnCategoryIds || !!presetDefaultOnItemIds ||
            !!presetCollapsedObjectIds;
    }
    function normalizeCatId(cid) {
        return String(cid || '').trim().toUpperCase();
    }
    function isCategoryAllowedBySubset(cid) {
        if (!subsetAllowedCategoryIds) return true;
        var c = normalizeCatId(cid);
        if (!c) return false;
        return subsetAllowedCategoryIds.has(c);
    }
    function hasAnySubsetAllowedCategory(catIds) {
        if (!subsetAllowedCategoryIds) return true;
        var arr = Array.isArray(catIds) ? catIds : [];
        for (var i = 0; i < arr.length; i++) {
            if (isCategoryAllowedBySubset(arr[i])) return true;
        }
        return false;
    }
    function isItemAllowedBySubset(itemId) {
        if (!subsetAllowedItemIds) return true;
        var i = String(itemId || '').trim().toUpperCase();
        if (!i) return false;
        return subsetAllowedItemIds.has(i);
    }
    function hasAnySubsetAllowedItem(itemIds) {
        if (!subsetAllowedItemIds) return true;
        var arr = Array.isArray(itemIds) ? itemIds : [];
        for (var i = 0; i < arr.length; i++) {
            if (isItemAllowedBySubset(arr[i])) return true;
        }
        return false;
    }
    function isObjectAllowedBySubset(objId) {
        if (!subsetAllowedObjectIds) return true;
        var o = String(objId || '').trim().toUpperCase();
        if (!o) return false;
        return subsetAllowedObjectIds.has(o);
    }
    function subsetAllowsMarker(primaryObj, catIds, itemIds) {
        if (!isSubsetActive()) return true;
        if (!isObjectAllowedBySubset(primaryObj)) return false;
        if (isPoiObjectKey(primaryObj)) return hasAnySubsetAllowedItem(itemIds);
        return hasAnySubsetAllowedCategory(catIds) && hasAnySubsetAllowedItem(itemIds);
    }

    // map.js の配置ディレクトリを baseUrl にする（currentScript が null の環境向けフォールバック付き）
    function resolveMapJsBaseUrl() {
        var s = document.currentScript && document.currentScript.src;
        if (s) {
            var idx = s.lastIndexOf('/');
            if (idx >= 0) return s.substring(0, idx + 1);
        }
        var scripts = document.getElementsByTagName('script');
        for (var i = scripts.length - 1; i >= 0; i--) {
            var src = scripts[i].src || '';
            if (!src || src.indexOf('leaflet') >= 0) continue;
            if (src.indexOf('map.js') >= 0) {
                var j = src.lastIndexOf('/');
                if (j >= 0) return src.substring(0, j + 1);
            }
        }
        // embed.html と csv を同じフォルダに置いた場合の最終手段
        var loc = window.location.href.split('#')[0];
        var k = loc.lastIndexOf('/');
        if (k >= 0) return loc.substring(0, k + 1);
        return '';
    }

    var baseUrl = resolveMapJsBaseUrl();
    // 共通 SVG: プロジェクトルートの assets/icons/ をホストするベースURL（末尾スラッシュ可）
    var svgIconsCommonBase = (mapDiv.getAttribute('data-svg-icons-common-base') || '').trim();

    var csvUrl = customCsv || (baseUrl + 'master_data.csv');
    var pinsJsonUrl = customPins || (baseUrl + 'pins_export.json');
    var tileUrl = baseUrl + 'tiles/{z}/{x}/{y}.webp';

    /**
     * 表示言語の解決順:
     * 1) URL クエリ (?lang=ja|en)
     * 2) #game-map data-lang
     * 3) embed 側 html[lang]
     * 4) ブラウザ言語
     */
    function resolveMapUiLang() {
        var qLang = (new URLSearchParams(window.location.search).get('lang') || '').trim().toLowerCase();
        var dLang = (mapDiv.getAttribute('data-lang') || '').trim().toLowerCase();
        var hLang = (document.documentElement.lang || '').trim().toLowerCase();
        var nLang = (navigator.language || '').trim().toLowerCase();
        var raw = qLang || dLang || hLang || nLang || 'ja';
        if (raw.indexOf('ja') === 0) return 'ja';
        if (raw.indexOf('en') === 0) return 'en';
        return 'ja';
    }
    var mapUiLang = resolveMapUiLang();
    var isJa = mapUiLang === 'ja';
    var isDebug = new URLSearchParams(window.location.search).get('debug') === 'true';

    // レイヤーフィルター用（config.attr_mapping から再構築）
    var styles = {};
    var attrToStyle = {};
    /** VEIN: オブジェクト(attribute)フィルター + category_master 由来の cat_id フィルター */
    var catIdToStyle = {};
    var categoryMasterGlobal = {};
    var activeCategoryFilters = new Set();
    /** config.category_list の順（マスタ保存時のカテゴリ行順＝category_master のキー順） */
    var categoryListOrderGlobal = [];
    /** config.item_master — 詳細フィルター用 */
    var itemMasterGlobal = {};
    var activeItemFilters = new Set();
    /** メイン階層UI: POI 配下のアイテムフィルター（カテゴリではなく item_id で絞る） */
    var activePoiItemFilters = new Set();
    /** config の map_object_attr_ids 順でオブジェクトグループを並べる（無ければ styles のキー順） */
    var mapObjectAttrIdsOrder = null;

    var TYPE_EMOJI = { landmark: '🏛️', loot: '📦', colony: '🌿', other: '📍' };

    function emojiForObjectType(typeId) {
        var t = String(typeId || 'loot').toLowerCase();
        return TYPE_EMOJI[t] || TYPE_EMOJI.other;
    }

    function initActiveCategoriesForVein() {
        activeCategories.clear();
        var fm = filterMode ? String(filterMode).trim() : '';
        Object.keys(styles).forEach(function (key) {
            if (key === 'trash' && !isDebug) return;
            if (key === 'other') return;
            if (!isObjectAllowedBySubset(key)) return;
            if (fm) {
                if (key.toUpperCase() === fm.toUpperCase()) activeCategories.add(key);
                return;
            }
            var ku = String(key || '').trim().toUpperCase();
            if (presetDefaultOnObjectIds) {
                if (presetDefaultOnObjectIds.has(ku)) activeCategories.add(key);
                return;
            }
            if (presetDefaultOffObjectIds && presetDefaultOffObjectIds.has(String(key || '').trim().toUpperCase())) {
                return;
            }
            activeCategories.add(key);
        });
    }

    function firstObjectStyleKey() {
        var keys = Object.keys(styles).filter(function (k) {
            return k !== 'trash' && k !== 'other';
        });
        return keys[0] || '';
    }

    function initActiveCategoryFilters() {
        activeCategoryFilters.clear();
        if (!presetDefaultOnCategoryIds) return;
        presetDefaultOnCategoryIds.forEach(function (cid) {
            if (isCategoryAllowedBySubset(cid)) activeCategoryFilters.add(String(cid));
        });
    }

    /** config.json 読込後: オブジェクトマスタ1件 = フィルター1項目（マーカー用 emoji・色は type に応じた既定） */
    function rebuildVeinFilterFromAttrMapping() {
        styles = {};
        attrToStyle = {};
        catIdToStyle = {};
        var am = attrMappingGlobal && typeof attrMappingGlobal === 'object' ? attrMappingGlobal : {};
        Object.keys(am).forEach(function (attrId) {
            var ent = am[attrId];
            if (!ent || typeof ent !== 'object') return;
            var labelJa = String(ent.name_jp || attrId).trim() || attrId;
            var labelEn = String(ent.name_en || labelJa).trim();
            var typ = String(ent.type || 'loot').toLowerCase();
            var color = defaultMarkerBgByType[typ] || defaultMarkerBgByType.other;
            styles[attrId] = {
                emoji: emojiForObjectType(typ),
                color: color,
                label: isJa ? labelJa : labelEn,
                objType: typ
            };
            attrToStyle[attrId] = attrId;
            attrToStyle[String(attrId).toUpperCase()] = attrId;
        });
        if (isDebug) {
            styles.trash = { emoji: '❌', color: '#555555', label: isJa ? '調査済み(空)' : 'Checked(Empty)', objType: 'other' };
        }
        initActiveCategoriesForVein();
        initActiveCategoryFilters();
        initActiveItemFilters();
        initActivePoiItemFilters();
    }

    function initActiveItemFilters() {
        activeItemFilters.clear();
    }

    function initActivePoiItemFilters() {
        activePoiItemFilters.clear();
        if (!presetDefaultOnItemIds) return;
        presetDefaultOnItemIds.forEach(function (iid) {
            if (isItemAllowedBySubset(iid)) activePoiItemFilters.add(String(iid));
        });
    }

    function resolveFilterStyleKey(rawAttr) {
        var a = String(rawAttr || '').trim();
        var fb = firstObjectStyleKey();
        if (!a) return fb || a;
        if (styles[a]) return a;
        var u = a.toUpperCase();
        if (attrToStyle[u]) return attrToStyle[u];
        if (attrToStyle[a]) return attrToStyle[a];
        return fb || a;
    }

    function pickVisualStyle(styleKey) {
        var st = styles[styleKey];
        if (st) return st;
        var fb = firstObjectStyleKey();
        if (fb && styles[fb]) return styles[fb];
        return { emoji: TYPE_EMOJI.other, color: '#4a4a4c', label: '', objType: 'loot' };
    }

    window.map = L.map('game-map', {
        crs: L.CRS.Simple,
        minZoom: 0,
        maxZoom: maxZoom,
        zoom: defaultZoom,
        maxBoundsViscosity: 0.8,
        preferCanvas: true,
        zoomControl: false
    });
    L.control.zoom({ position: 'topright' }).addTo(map);

    function addFullscreenControl() {
        var target = document.getElementById('map-container') || mapDiv.parentElement || mapDiv;
        var FullscreenControl = L.Control.extend({
            options: { position: 'topright' },
            onAdd: function () {
                var btn = L.DomUtil.create('button', 'vein-fullscreen-btn');
                btn.type = 'button';
                btn.title = isJa ? '全画面表示' : 'Fullscreen';
                btn.setAttribute('aria-label', btn.title);
                btn.innerHTML = '&#x26F6;';

                function syncUi() {
                    var fsOn = !!document.fullscreenElement;
                    btn.innerHTML = fsOn ? '&#x2715;' : '&#x26F6;';
                    btn.title = fsOn ? (isJa ? '全画面を終了' : 'Exit fullscreen') : (isJa ? '全画面表示' : 'Fullscreen');
                    btn.setAttribute('aria-label', btn.title);
                }

                L.DomEvent.disableClickPropagation(btn);
                L.DomEvent.on(btn, 'click', function (ev) {
                    L.DomEvent.stop(ev);
                    if (!document.fullscreenElement) {
                        var req = target.requestFullscreen || target.webkitRequestFullscreen || target.msRequestFullscreen;
                        if (req) {
                            Promise.resolve(req.call(target)).then(function () {
                                syncUi();
                                invalidateMapSizeSoon();
                            }).catch(function () { /* ignore */ });
                        }
                    } else {
                        var ex = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
                        if (ex) {
                            Promise.resolve(ex.call(document)).then(function () {
                                syncUi();
                                invalidateMapSizeSoon();
                            }).catch(function () { /* ignore */ });
                        }
                    }
                });
                document.addEventListener('fullscreenchange', function () {
                    syncUi();
                    invalidateMapSizeSoon();
                });
                syncUi();
                return btn;
            }
        });
        map.addControl(new FullscreenControl());
    }
    addFullscreenControl();

    var imageBounds = new L.LatLngBounds(
        map.unproject([0, imgH], maxZoom),
        map.unproject([imgW, 0], maxZoom)
    );
    var paddedBounds = new L.LatLngBounds(
        map.unproject([-mapPadding, imgH + mapPadding], maxZoom),
        map.unproject([imgW + mapPadding, -mapPadding], maxZoom)
    );

    map.setMaxBounds(paddedBounds);
    map.fitBounds(imageBounds);
    map.setView(map.unproject([defaultCenterX, defaultCenterY], maxZoom), defaultZoom);

    L.tileLayer(tileUrl, {
        minZoom: 0,
        maxZoom: maxZoom,
        tileSize: 256,
        noWrap: true,
        bounds: imageBounds,
        tms: false
    }).addTo(map);

    function updateZoomClass() {
        var c = document.getElementById('game-map');
        if (c) {
            c.className = c.className.replace(/zoom-level-\d+/g, '').trim();
            c.classList.add('zoom-level-' + map.getZoom());
        }
    }
    map.on('zoomend', updateZoomClass);
    updateZoomClass();

    // 親レイアウト後のリサイズ（WordPress 等で高さが後から決まる／フィルター挿入後の再計算）
    window.addEventListener('resize', function () {
        try {
            map.invalidateSize();
        } catch (eR) { /* ignore */ }
    });
    setTimeout(function () {
        try {
            map.invalidateSize();
        } catch (eR2) { /* ignore */ }
    }, 0);

    // デモ用ピン: 内蔵レイヤー + 別ファイルのアイコン（例: frame1.svg）
    // data-demo-svg-href: 省略 / embedded / - → 内蔵ベース＋アイコン別fetch。それ以外 → 従来どおり SVG 丸ごと fetch
    // data-demo-svg-icon-href: アイコン用 SVG（既定 frame1.svg）
    // 既定は fetch 成功後「HTML img で重ね表示」（表示が安定）。インラインSVG+currentColor は data-demo-svg-icon-inline="true"
    function escapeHtmlAttr(s) {
        return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
    }
    function isSafeSvgIconColor(v) {
        return typeof v === 'string' && /^#[0-9a-fA-F]{3,8}$/.test(v.trim());
    }
    function extractSvgInner(svgText) {
        svgText = String(svgText).replace(/^\uFEFF/, '');
        svgText = svgText.replace(/<script[\s\S]*?<\/script>/gi, '');
        svgText = svgText.replace(/<\?xml[\s\S]*?\?>/gi, '').trim();
        var m = svgText.match(/<svg\b[^>]*>([\s\S]*)<\/svg>/i);
        return m ? m[1].trim() : '';
    }
    function normalizeBaseUrl(b) {
        if (!b || typeof b !== 'string') return '';
        b = b.trim();
        if (!b) return '';
        return b.slice(-1) === '/' ? b : b + '/';
    }
    function buildIconFetchUrlList(iconFname) {
        var list = [];
        var abs = (mapDiv.getAttribute('data-demo-svg-icon-url') || '').trim();
        if (abs) list.push(abs);
        var assetBase = normalizeBaseUrl(mapDiv.getAttribute('data-demo-svg-base-url') || '');
        if (assetBase) {
            list.push(assetBase + encodeURIComponent(iconFname));
            try {
                list.push(new URL(encodeURIComponent(iconFname), assetBase).href);
            } catch (e1) { /* ignore */ }
        }
        var bu = normalizeBaseUrl(baseUrl);
        if (bu) {
            list.push(bu + encodeURIComponent(iconFname));
            try {
                list.push(new URL(encodeURIComponent(iconFname), bu).href);
            } catch (e2) { /* ignore */ }
        }
        var out = [];
        var seen = {};
        list.forEach(function (u) {
            if (u && !seen[u]) {
                seen[u] = true;
                out.push(u);
            }
        });
        return out;
    }
    function fetchIconSvgText(urlList, bust) {
        function attempt(i) {
            if (i >= urlList.length) {
                return Promise.reject(new Error('icon: all URLs failed'));
            }
            var u = urlList[i];
            var uu = u + (u.indexOf('?') >= 0 ? '&' : '?') + bust;
            return fetch(uu)
                .then(function (r) {
                    if (!r.ok) return attempt(i + 1);
                    return r.text().then(function (text) {
                        return { text: text, url: u };
                    });
                })
                .catch(function () {
                    return attempt(i + 1);
                });
        }
        return attempt(0);
    }
    // 下→上: 白枠(円r17+尻尾) → 背景円r15 currentColor → シンボル → 外部SVG(img)を最上層
    // マーカー枠はアイコン(24px)より大きく見せる（既定56px）。#game-map data-demo-pin-marker-size="52"〜"72" で調整可
    var PIN_SVG_HEAD = '<svg width="100%" height="100%" viewBox="0 0 48 48" preserveAspectRatio="xMidYMid meet" fill="none" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">';
    var PIN_SVG_LAYERS =
        '<g id="pin-frame" fill="white">' +
        '<circle cx="24" cy="24" r="17"/>' +
        '<path d="M24 47L29.1962 38.75H18.8038L24 47Z"/>' +
        '</g>' +
        '<g id="pin-inner-bg"><circle cx="24" cy="24" r="15" fill="currentColor"/></g>';
    var PIN_SVG_TAIL = '</svg>';
    function buildPinStackSvg(iconInnerMarkup, symColor) {
        var sc = isSafeSvgIconColor(String(symColor || '').trim()) ? String(symColor).trim() : '#1e1e1e';
        var sym = iconInnerMarkup
            ? '<g id="pin-symbol-overlay" style="color:' + escapeHtmlAttr(sc) + '"' +
                ' transform="translate(24,24) scale(0.42) translate(-24,-24)">' + iconInnerMarkup + '</g>'
            : '<g id="pin-symbol-overlay"></g>';
        return PIN_SVG_HEAD + PIN_SVG_LAYERS + sym + PIN_SVG_TAIL;
    }
    /** 外部SVGを HTML img で重ねる（SVG内 <image> より表示が安定） */
    function wrapPinBasePlusImgIcon(pinBgColor, iconSrcWithBust, symColor, markerPx) {
        var mp = markerPx || 32;
        var baseOnly = buildPinStackSvg('', symColor);
        var href = escapeHtmlAttr(iconSrcWithBust);
        return '<div class="demo-pin-composite" style="position:relative;width:' + mp + 'px;height:' + mp + 'px;display:block;">' +
            '<div class="demo-svg-inner" style="' +
            'color:' + escapeHtmlAttr(pinBgColor) + ';' +
            'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;' +
            'line-height:0;background:transparent;">' + baseOnly + '</div>' +
            '<img src="' + href + '" alt="" decoding="async" draggable="false" ' +
            'class="demo-pin-icon-img" ' +
            'style="position:absolute;left:50%;top:50%;width:14px;height:14px;max-width:14px;max-height:14px;' +
            'transform:translate(-50%,-50%);object-fit:contain;box-sizing:border-box;pointer-events:none;z-index:2;"/>' +
            '</div>';
    }

    /** Leaflet が .leaflet-marker-icon に transform: translate3d を直指定するため、embed の scale は子要素に掛ける */
    var MAP_PIN_LEAFLET_SHELL = 'map-pin-leaflet-shell';
    function wrapDivIconZoomScale(innerHtml, zoomSurfaceClass, transformOrigin) {
        var o = transformOrigin || '50% 50%';
        return '<div class="' + zoomSurfaceClass + '" style="width:100%;height:100%;box-sizing:border-box;transform-origin:' + o + ';">' +
            innerHtml + '</div>';
    }

    /** Leaflet iconAnchor: マップ座標を viewBox (24,47) の尻尾先に合わせる（48×48 ピンSVG） */
    function leafletPinAnchorAtTail(markerPx) {
        var mp = markerPx || 32;
        return [Math.round(mp / 2), Math.round((47 * mp) / 48)];
    }

    function addDemoSvgIconMarker() {
        if (mapDiv.getAttribute('data-demo-svg-icon') !== 'true') return;
        var fname = (mapDiv.getAttribute('data-demo-svg-href') || '').trim();
        var useEmbedded = !fname || fname.toLowerCase() === 'embedded' || fname === '-';
        var svgUrl = useEmbedded ? '' : (baseUrl + encodeURIComponent(fname));
        var rawBg = (mapDiv.getAttribute('data-demo-svg-color') || '#e53935').trim();
        var pinBgColor = isSafeSvgIconColor(rawBg) ? rawBg : '#e53935';
        var rawSym = (mapDiv.getAttribute('data-demo-svg-icon-color') || '#1e1e1e').trim();
        var iconSymColor = isSafeSvgIconColor(rawSym) ? rawSym : '#1e1e1e';
        var iconFname = (mapDiv.getAttribute('data-demo-svg-icon-href') || 'frame1.svg').trim();
        var iconUrlCandidates = buildIconFetchUrlList(iconFname);
        var markerPxRaw = parseInt(mapDiv.getAttribute('data-demo-pin-marker-size'), 10);
        var demoPinMarkerPx = (!isNaN(markerPxRaw) && markerPxRaw >= 44 && markerPxRaw <= 80) ? markerPxRaw : 56;
        var demoPinAnchor = leafletPinAnchorAtTail(demoPinMarkerPx);
        var px = parseFloat(mapDiv.getAttribute('data-demo-svg-x'), 10);
        var py = parseFloat(mapDiv.getAttribute('data-demo-svg-y'), 10);
        if (isNaN(px)) px = Math.round(imgW * 0.48);
        if (isNaN(py)) py = Math.round(imgH * 0.42);
        var latLng = map.unproject([px, py], maxZoom);

        function placeDemoMarker(html) {
            var demoIcon = L.divIcon({
                html: wrapDivIconZoomScale(html, 'demo-svg-icon', '50% 50%'),
                className: MAP_PIN_LEAFLET_SHELL,
                iconSize: [demoPinMarkerPx, demoPinMarkerPx],
                iconAnchor: demoPinAnchor
            });
            var m = L.marker(latLng, { icon: demoIcon, zIndexOffset: 500 });
            m.addTo(map);
            m.bindPopup(isJa ? 'デモ: 尻尾→白枠→背景色→frame1.svg' : 'Demo: pin + frame1.svg');
        }

        // ラッパー color = 小円の currentColor（アイコン層は内側 g で別 color を指定）
        function wrapPinSvg(svgText) {
            return '<div class="demo-svg-inner" style="' +
                'color:' + escapeHtmlAttr(pinBgColor) + ';' +
                'width:100%;height:100%;display:flex;align-items:center;justify-content:center;' +
                'line-height:0;background:transparent;">' + svgText + '</div>';
        }

        if (useEmbedded) {
            var svgBust = 't=' + Date.now();
            if (!iconUrlCandidates.length) {
                console.warn('[map.js] アイコンSVGのURLが決められません。data-demo-svg-base-url または data-demo-svg-icon-url を #game-map に指定してください。baseUrl=', baseUrl);
                placeDemoMarker(wrapPinSvg(buildPinStackSvg('', iconSymColor)));
                return;
            }
            fetchIconSvgText(iconUrlCandidates, svgBust)
                .then(function (res) {
                    var txt = res.text;
                    var usedUrl = res.url;
                    var inner = extractSvgInner(txt);
                    var imgBust = usedUrl + (usedUrl.indexOf('?') >= 0 ? '&' : '?') + svgBust;
                    var wantInline = mapDiv.getAttribute('data-demo-svg-icon-inline') === 'true';
                    if (wantInline && inner.length > 0) {
                        placeDemoMarker(wrapPinSvg(buildPinStackSvg(inner, iconSymColor)));
                    } else {
                        placeDemoMarker(wrapPinBasePlusImgIcon(pinBgColor, imgBust, iconSymColor, demoPinMarkerPx));
                    }
                    if (isDebug) console.log('map.js: demo pin+icon OK', usedUrl, 'mode=', wantInline && inner.length > 0 ? 'inline' : 'img', 'bg=', pinBgColor, 'markerPx=', demoPinMarkerPx);
                })
                .catch(function (e) {
                    console.warn('[map.js] アイコンSVGの取得に失敗しました（404・別ドメイン・ファイル名のスペース等）。試したURL:', iconUrlCandidates.join(' | '), e);
                    placeDemoMarker(wrapPinSvg(buildPinStackSvg('', iconSymColor)));
                });
            return;
        }

        var bust = 't=' + Date.now();
        fetch(svgUrl + (svgUrl.indexOf('?') >= 0 ? '&' : '?') + bust)
            .then(function (r) {
                if (!r.ok) throw new Error('svg fetch ' + r.status);
                return r.text();
            })
            .then(function (svgText) {
                svgText = String(svgText).replace(/<script[\s\S]*?<\/script>/gi, '');
                placeDemoMarker(wrapPinSvg(svgText));
                if (isDebug) console.log('map.js: demo SVG (full file) at', px, py, 'url=', svgUrl);
            })
            .catch(function (e) {
                if (isDebug) console.warn('map.js: full SVG fetch failed', e);
                if (!iconUrlCandidates.length) {
                    placeDemoMarker(wrapPinSvg(buildPinStackSvg('', iconSymColor)));
                    return;
                }
                fetchIconSvgText(iconUrlCandidates, bust)
                    .then(function (res) {
                        var inner = extractSvgInner(res.text);
                        var imgBust = res.url + (res.url.indexOf('?') >= 0 ? '&' : '?') + bust;
                        var wantInline = mapDiv.getAttribute('data-demo-svg-icon-inline') === 'true';
                        if (wantInline && inner.length > 0) {
                            placeDemoMarker(wrapPinSvg(buildPinStackSvg(inner, iconSymColor)));
                        } else {
                            placeDemoMarker(wrapPinBasePlusImgIcon(pinBgColor, imgBust, iconSymColor, demoPinMarkerPx));
                        }
                    })
                    .catch(function () {
                        placeDemoMarker(wrapPinSvg(buildPinStackSvg('', iconSymColor)));
                    });
            });
    }
    addDemoSvgIconMarker();

    var allMarkers = [];
    var activeCategories = new Set();
    /** CSV 読み込み時、config.json の pin_marker_by_attribute で SVG／色を補う */
    var pinMarkerByAttribute = {};
    var pinMarkerByCategoryId = {};
    var pinMarkerByItemId = {};
    var categorySpecialRules = {};
    /** config.json skill_name_master: { id: { name_jp, name_en } } */
    var skillNameMaster = {};
    var attrMappingGlobal = {};
    var defaultMarkerBgByType = { loot: '#2ecc71', landmark: '#3498db', colony: '#e67e22', other: '#7f8c8d' };

    function normalizeImportanceLevel(value) {
        var n = parseInt(String(value == null ? '' : value).trim(), 10);
        if (isNaN(n)) return 0;
        if (n < 1) return 0;
        if (n > 5) return 5;
        return n;
    }

    function syncMarkerImportanceVisual(marker) {
        if (!marker) return;
        var el = marker.getElement ? marker.getElement() : marker._icon;
        if (!el || !el.classList) return;
        el.classList.remove('map-pin-importance--on', 'map-pin-importance-glow');
        el.classList.remove('map-pin-imp-1', 'map-pin-imp-2', 'map-pin-imp-3', 'map-pin-imp-4', 'map-pin-imp-5');
        var lv = marker.__importanceLevel || 0;
        if (lv <= 0) return;
        el.classList.add('map-pin-imp-' + lv);
        if (!importanceVisualEnabled) return;
        el.classList.add('map-pin-importance--on');
        if (importanceVisualVariant === 'size+glow') {
            el.classList.add('map-pin-importance-glow');
        }
    }

    function bindMarkerImportanceVisual(marker, importanceValue) {
        if (!marker) return;
        marker.__importanceLevel = normalizeImportanceLevel(importanceValue);
        if (!marker.__importanceVisualHooked && marker.on) {
            marker.on('add', function () {
                syncMarkerImportanceVisual(marker);
            });
            marker.__importanceVisualHooked = true;
        }
        syncMarkerImportanceVisual(marker);
    }

    function refreshAllMarkerImportanceVisual() {
        var i;
        for (i = 0; i < allMarkers.length; i++) {
            if (allMarkers[i] && allMarkers[i].marker) {
                syncMarkerImportanceVisual(allMarkers[i].marker);
            }
        }
        for (i = 0; i < allAreaItems.length; i++) {
            var iconMarker = allAreaItems[i] && allAreaItems[i].iconMarker;
            if (iconMarker) syncMarkerImportanceVisual(iconMarker);
        }
    }

    function normalizeMarkerDisplayStyle(v) {
        var s = String(v || '').trim().toLowerCase().replace(/-/g, '_');
        if (s === 'icon_only' || s === 'icononly') return 'icon_only';
        return 'standard';
    }

    function applyPinMarkerPartial(pin, pm) {
        if (!pm || typeof pm !== 'object') return;
        var touched = false;
        var sid = (pm.svg_icon_id || '').trim();
        if (sid) { pin.svg_icon_id = sid; touched = true; }
        var scp = (pm.svg_icon_scope || '').trim();
        if (scp) pin.svg_icon_scope = scp;
        var ic = (pm.icon_color || '').trim();
        if (/^#[0-9a-fA-F]{6}$/.test(ic)) { pin.marker_icon_color = ic; touched = true; }
        var bg = (pm.background_color || '').trim();
        if (/^#[0-9a-fA-F]{6}$/.test(bg)) { pin.marker_bg_color = bg; touched = true; }
        var ds = (pm.display_style || '').trim();
        if (ds) pin.marker_display_style = normalizeMarkerDisplayStyle(ds);
        else if (touched) pin.marker_display_style = 'standard';
    }

    function pinMarkerEntryForAttribute(attrRaw) {
        var k = (attrRaw || '').trim();
        if (!k) return null;
        var pm = pinMarkerByAttribute[k];
        if (pm && typeof pm === 'object') return pm;
        var ku = k.toUpperCase();
        if (ku !== k) {
            pm = pinMarkerByAttribute[ku];
            if (pm && typeof pm === 'object') return pm;
        }
        return null;
    }

    /**
     * マーカー見た目: オブジェクト → カテゴリ → アイテムの順に apply（後勝ち）。
     * 複数スロット時: 配列順で「pinMarkerByCategoryId にある最初の cat_id」、
     * 続けて「pinMarkerByItemId にある最初の item_id」だけを採用（各レイヤー先頭一致で打ち切り）。
     * CSV の marker_display_style は呼び出し側でこの後に上書き。
     */
    function mergePinStyleFromConfig(pin, attributeKey, categoriesArr) {
        var attr = (attributeKey || '').trim();
        applyPinMarkerPartial(pin, pinMarkerEntryForAttribute(attr));
        if (categoriesArr && categoriesArr.length) {
            for (var ci = 0; ci < categoriesArr.length; ci++) {
                var cid = (categoriesArr[ci].cat_id || '').trim();
                if (!cid) continue;
                var ov = pinMarkerByCategoryId[cid];
                if (ov && typeof ov === 'object') {
                    applyPinMarkerPartial(pin, ov);
                    break;
                }
            }
            for (var ii = 0; ii < categoriesArr.length; ii++) {
                var iid = (categoriesArr[ii].item_id || '').trim();
                if (!iid) continue;
                var im = pinMarkerByItemId[iid];
                if (im && typeof im === 'object') {
                    applyPinMarkerPartial(pin, im);
                    break;
                }
            }
        }
        pin.marker_display_style = normalizeMarkerDisplayStyle(pin.marker_display_style);
        if (pin.marker_display_style !== 'icon_only') {
            if (!pin.marker_bg_color && attr && attrMappingGlobal[attr] && typeof attrMappingGlobal[attr] === 'object') {
                var typ = String(attrMappingGlobal[attr].type || 'other').toLowerCase();
                pin.marker_bg_color = defaultMarkerBgByType[typ] || defaultMarkerBgByType.other;
            }
        }
        if (!pin.marker_icon_color) pin.marker_icon_color = '#ffffff';
    }

    // activeCategories は config 読込後の rebuildVeinFilterFromAttrMapping() で初期化

    function categoryFilterMasterEnabled() {
        var n = 0;
        Object.keys(categoryMasterGlobal).forEach(function (jk) {
            var e = categoryMasterGlobal[jk];
            if (e && typeof e === 'object' && String(e.id || '').trim()) n++;
        });
        return n > 0;
    }

    function markerPrimaryObjectKey(itemLike) {
        var cats = (itemLike && itemLike.categories && itemLike.categories.length) ? itemLike.categories : [];
        return String(cats[0] || '').trim();
    }

    function isPoiObjectKey(k) {
        return String(k || '').trim().toUpperCase() === 'POI';
    }

    function isDefaultGroupCollapsed(key) {
        var k = String(key || '').trim().toUpperCase();
        if (presetCollapsedObjectIds) return presetCollapsedObjectIds.has(k);
        // 既定: POI は初期で閉じ、その他（コンテナ・アイテム等）は開き
        return isPoiObjectKey(key);
    }

    function updateVisibleMarkers() {
        var catMasterOn = categoryFilterMasterEnabled();
        allMarkers.forEach(function (item) {
            var objOk = item.categories.some(function (cat) {
                return activeCategories.has(cat);
            });
            if (!objOk) {
                if (map.hasLayer(item.marker)) map.removeLayer(item.marker);
                return;
            }
            var primaryObj = markerPrimaryObjectKey(item);
            var catOk = true;
            var poiItemOk = true;
            if (isPoiObjectKey(primaryObj)) {
                if (activePoiItemFilters.size > 0) {
                    var poiItemIds = item.pinItemIds || [];
                    poiItemOk = poiItemIds.some(function (iid) {
                        return activePoiItemFilters.has(iid);
                    });
                }
            } else if (catMasterOn && activeCategoryFilters.size > 0) {
                var pc = item.pinCategoryIds || [];
                if (pc.length === 0) {
                    catOk = activeCategoryFilters.has('__none__');
                } else {
                    catOk = pc.some(function (cid) {
                        return activeCategoryFilters.has(cid);
                    });
                }
            }
            var itemOk = true;
            if (activeItemFilters.size > 0) {
                var pItemIds = item.pinItemIds || [];
                itemOk = pItemIds.some(function (pid) {
                    return activeItemFilters.has(pid);
                });
            }
            if (objOk && catOk && poiItemOk && itemOk) {
                if (!map.hasLayer(item.marker)) {
                    item.marker.addTo(map);
                    if (showLabels && item.marker.openTooltip) item.marker.openTooltip();
                }
            } else {
                if (map.hasLayer(item.marker)) map.removeLayer(item.marker);
            }
        });
        updateVisibleAreas();
    }

    /** エリアをピンと同じ activeCategories / category / item フィルタで表示切替 */
    function updateVisibleAreas() {
        if (!allAreaItems || allAreaItems.length === 0) return;
        if (!areaLayer || !areaIconLayerGroup) return;
        var catMasterOn = categoryFilterMasterEnabled();
        allAreaItems.forEach(function (entry) {
            var poly = entry.poly;
            var iconMarker = entry.iconMarker;
            var objOk = entry.categories.some(function (cat) {
                return activeCategories.has(cat);
            });
            if (!objOk) {
                if (areaLayer.hasLayer(poly)) areaLayer.removeLayer(poly);
                if (iconMarker && areaIconLayerGroup.hasLayer(iconMarker)) areaIconLayerGroup.removeLayer(iconMarker);
                return;
            }
            var primaryObj = markerPrimaryObjectKey(entry);
            var catOk = true;
            var poiItemOk = true;
            if (isPoiObjectKey(primaryObj)) {
                if (activePoiItemFilters.size > 0) {
                    var poiItemIds = entry.pinItemIds || [];
                    poiItemOk = poiItemIds.some(function (iid) {
                        return activePoiItemFilters.has(iid);
                    });
                }
            } else if (catMasterOn && activeCategoryFilters.size > 0) {
                var pc = entry.pinCategoryIds || [];
                if (pc.length === 0) {
                    catOk = activeCategoryFilters.has('__none__');
                } else {
                    catOk = pc.some(function (cid) {
                        return activeCategoryFilters.has(cid);
                    });
                }
            }
            var itemOk = true;
            if (activeItemFilters.size > 0) {
                var pItemIds = entry.pinItemIds || [];
                itemOk = pItemIds.some(function (pid) {
                    return activeItemFilters.has(pid);
                });
            }
            var show = objOk && catOk && poiItemOk && itemOk;
            if (show) {
                if (!areaLayer.hasLayer(poly)) areaLayer.addLayer(poly);
                if (iconMarker && !areaIconLayerGroup.hasLayer(iconMarker)) areaIconLayerGroup.addLayer(iconMarker);
            } else {
                if (areaLayer.hasLayer(poly)) areaLayer.removeLayer(poly);
                if (iconMarker && areaIconLayerGroup.hasLayer(iconMarker)) areaIconLayerGroup.removeLayer(iconMarker);
            }
        });
    }

    /** エディター svg_icon_assets.normalize_svg_paints_to_current_color に相当（単色シルエット用） */
    function normalizeSvgPaintsToCurrentColor(svgText) {
        function skip(val) {
            var v = String(val || '').trim().toLowerCase();
            if (!v || v === 'none' || v === 'currentcolor' || v === 'transparent') return true;
            if (/^url\(/i.test(v) || /^var\(/i.test(v)) return true;
            return false;
        }
        function replAttr(m, pre, val, suf) {
            if (skip(val)) return m;
            return pre + 'currentColor' + suf;
        }
        var s = String(svgText);
        s = s.replace(/(fill\s*=\s*["'])([^"']+)(["'])/gi, function (m, a, b, c) { return replAttr(m, a, b, c); });
        s = s.replace(/(stroke\s*=\s*["'])([^"']+)(["'])/gi, function (m, a, b, c) { return replAttr(m, a, b, c); });
        s = s.replace(/(stop-color\s*=\s*["'])([^"']+)(["'])/gi, function (m, a, b, c) { return replAttr(m, a, b, c); });
        s = s.replace(/(flood-color\s*=\s*["'])([^"']+)(["'])/gi, function (m, a, b, c) { return replAttr(m, a, b, c); });
        function replStyle(m, pre, val) {
            if (skip(val)) return m;
            return pre + 'currentColor';
        }
        s = s.replace(/(fill\s*:\s*)([^;"']+)(?=[;"'\]])/gi, function (m, a, b) { return replStyle(m, a, b); });
        s = s.replace(/(stroke\s*:\s*)([^;"']+)(?=[;"'\]])/gi, function (m, a, b) { return replStyle(m, a, b); });
        s = s.replace(/(stop-color\s*:\s*)([^;"']+)(?=[;"'\]])/gi, function (m, a, b) { return replStyle(m, a, b); });
        s = s.replace(/(flood-color\s*:\s*)([^;"']+)(?=[;"'\]])/gi, function (m, a, b) { return replStyle(m, a, b); });
        if (!/currentColor/i.test(s)) {
            var rm = /<svg\b([^>]*)>/i.exec(s);
            if (rm && !/\bfill\s*=/i.test(rm[1] || '')) {
                var full = rm[0];
                var replaced = '<svg' + rm[1] + ' fill="currentColor"' + '>';
                s = s.slice(0, rm.index) + replaced + s.slice(rm.index + full.length);
            }
        }
        return s;
    }

    /** エディター svg_icon_assets.replace_current_color と同じ契約（currentColor → 指定色） */
    function replaceSvgCurrentColor(svgText, hex) {
        var h = String(hex || '#ffffff').trim();
        if (!/^#[0-9a-fA-F]{6}$/.test(h)) h = '#ffffff';
        return String(svgText).replace(/currentColor/gi, h);
    }

    var jsonMarkerPxRaw = parseInt(mapDiv.getAttribute('data-demo-pin-marker-size'), 10);
    var JSON_PIN_MARKER_PX = (!isNaN(jsonMarkerPxRaw) && jsonMarkerPxRaw >= 24 && jsonMarkerPxRaw <= 56) ? jsonMarkerPxRaw : 32;
    var JSON_PIN_ANCHOR = leafletPinAnchorAtTail(JSON_PIN_MARKER_PX);

    function svgIconUrlCandidates(pinSvgId) {
        var idPart = encodeURIComponent(pinSvgId) + '.svg';
        var commonU = svgIconsCommonBase ? svgIconsCommonBase.replace(/\/?$/, '/') + idPart : '';
        /** map.js と同じディレクトリ直下の assets/icons/（サイトルートの /assets/ とは別） */
        var gameU = baseUrl + 'assets/icons/' + idPart;
        var list = [];
        list.push(gameU);
        if (commonU && commonU !== gameU) {
            list.push(commonU);
        }
        return list;
    }

    /** ページ読み込み単位のバスト（ピンごとの Date.now だとキャッシュが効かずサーバ負荷・エラー表示が増える） */
    var svgFetchSessionBust = 'v=' + Date.now();
    /** 4xx/5xx やネットワーク失敗した URL は同一セッションで再 fetch しない（507 等の連打を防ぐ） */
    var svgUrlKnownBad = new Set();
    /** 同一 svg + 色の objectURL を再利用（同一アイコンのピンが大量にあるときの重複取得を防ぐ） */
    var svgObjectUrlCache = {};
    /** 同一キーで取得中の Promise（完了まで共有し、並行 fetch の嵐を防ぐ） */
    var svgFetchPromiseByKey = {};
    /** 全候補 URL が失敗したキー（再試行しない） */
    var svgFetchFailedKeys = new Set();

    function svgResolvedCacheKey(pinSvgId, scope, symHex) {
        return String(pinSvgId || '') + '\x00' + String(scope || '') + '\x00' + String(symHex || '');
    }

    function fetchFirstSvgAsObjectUrlAsync(urls, bust, symHex) {
        return new Promise(function (resolve, reject) {
            fetchFirstSvgAsObjectUrl(urls, 0, bust, symHex, resolve, reject);
        });
    }

    function fetchFirstSvgAsObjectUrl(urls, index, bust, symHex, done, fail) {
        if (index >= urls.length) {
            fail();
            return;
        }
        var u = urls[index];
        var baseKey = u.split('?')[0];
        if (svgUrlKnownBad.has(baseKey)) {
            fetchFirstSvgAsObjectUrl(urls, index + 1, bust, symHex, done, fail);
            return;
        }
        var sep = u.indexOf('?') >= 0 ? '&' : '?';
        fetch(u + sep + bust)
            .then(function (r) {
                if (!r.ok) {
                    svgUrlKnownBad.add(baseKey);
                    throw new Error('bad status');
                }
                return r.text();
            })
            .then(function (text) {
                text = String(text).replace(/<script[\s\S]*?<\/script>/gi, '');
                var patched = replaceSvgCurrentColor(normalizeSvgPaintsToCurrentColor(text), symHex);
                var blob = new Blob([patched], { type: 'image/svg+xml;charset=utf-8' });
                done(URL.createObjectURL(blob));
            })
            .catch(function () {
                svgUrlKnownBad.add(baseKey);
                fetchFirstSvgAsObjectUrl(urls, index + 1, bust, symHex, done, fail);
            });
    }

    function getOrFetchSvgObjectUrl(pinSvgId, scope, symHex, candidates, done, fail) {
        var ck = svgResolvedCacheKey(pinSvgId, scope, symHex);
        if (svgObjectUrlCache[ck]) {
            done(svgObjectUrlCache[ck]);
            return;
        }
        if (svgFetchFailedKeys.has(ck)) {
            fail();
            return;
        }
        if (svgFetchPromiseByKey[ck] === undefined) {
            svgFetchPromiseByKey[ck] = fetchFirstSvgAsObjectUrlAsync(candidates, svgFetchSessionBust, symHex);
        }
        svgFetchPromiseByKey[ck].then(
            function (u) {
                svgObjectUrlCache[ck] = u;
                done(u);
            },
            function () {
                svgFetchFailedKeys.add(ck);
                fail();
            }
        );
    }

    /** ピン／エリア共通: アイコンのみマーカー（Leaflet ルートは translate3d のため内側で scale） */
    function attachIconOnlySvgToMarker(marker, pinSvgId, scope, symHex) {
        var candidates = svgIconUrlCandidates(pinSvgId);
        var iconOnlyPx = 30;
        var iconOnlyImgPx = 24;
        var iconOnlyImgStyle =
            'position:absolute;left:50%;top:50%;width:' + iconOnlyImgPx + 'px;height:' + iconOnlyImgPx + 'px;' +
            'transform:translate(-50%,-50%);object-fit:contain;pointer-events:none;' +
            '-webkit-filter:drop-shadow(0 1px 2px rgba(0,0,0,0.9)) drop-shadow(0 0 6px rgba(0,0,0,0.4));' +
            'filter:drop-shadow(0 1px 2px rgba(0,0,0,0.9)) drop-shadow(0 0 6px rgba(0,0,0,0.4));';
        getOrFetchSvgObjectUrl(
            pinSvgId,
            scope,
            symHex,
            candidates,
            function (objUrl) {
                var href = escapeHtmlAttr(objUrl);
                var core = '<div class="map-pin-icon-only-wrap" style="position:relative;width:' + iconOnlyPx + 'px;height:' + iconOnlyPx + 'px;">' +
                    '<img class="map-pin-icon-only-img" src="' + href + '" alt="" draggable="false" decoding="async" style="' + iconOnlyImgStyle + '"/>' +
                    '</div>';
                var html = wrapDivIconZoomScale(core, 'map-pin-icon-only', '50% 50%');
                marker.setIcon(
                    L.divIcon({
                        html: html,
                        className: MAP_PIN_LEAFLET_SHELL,
                        iconSize: [iconOnlyPx, iconOnlyPx],
                        iconAnchor: [Math.round(iconOnlyPx / 2), Math.round(iconOnlyPx / 2)]
                    })
                );
                syncMarkerImportanceVisual(marker);
            },
            function () {
                if (isDebug) console.warn('[map.js] svg_icon fetch failed (icon_only)', pinSvgId, candidates);
            }
        );
    }

    /** ポップアップ見出し用（テキストノード） */
    function escapeHtmlPin(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function memoToSafePopupHtml(memo) {
        return String(memo || '').replace(/<script[\s\S]*?<\/script>/gi, '');
    }

    function plainMemoForTooltip(memo) {
        return String(memo || '').replace(/<br\s*\/?>/gi, '\n').trim();
    }

    /** contents（JSON）と旧 category 列からカテゴリ表示名を列挙 */
    function categoryLabelsFromContents(contents, isJa, legacyCategory) {
        var labels = [];
        if (contents && contents.length) {
            contents.forEach(function (c) {
                if (!c) return;
                var lab = isJa
                    ? (c.cat_jp || c.category || '').trim()
                    : (c.cat_en || c.cat_name_en || c.category || '').trim();
                if (lab && labels.indexOf(lab) < 0) labels.push(lab);
            });
        }
        if (labels.length === 0 && legacyCategory && String(legacyCategory).trim()) {
            labels.push(String(legacyCategory).trim());
        }
        return labels;
    }

    /** 1行目: オブジェクト名：カテゴリ名（複数カテゴリは ・ で連結） */
    function buildPinHeadline(pin, isJa, contents, legacyCategory) {
        var objPart = isJa ? (pin.obj_jp || pin.obj_en || '') : (pin.obj_en || pin.obj_jp || '');
        objPart = String(objPart).trim();
        var cats = categoryLabelsFromContents(contents, isJa, legacyCategory);
        var catPart = cats.join('・');
        if (objPart && catPart) {
            if (objPart === catPart) return objPart;
            return objPart + '：' + catPart;
        }
        if (objPart) return objPart;
        if (catPart) return catPart;
        return isJa ? '（無題）' : '(Untitled)';
    }

    /** 説明欄: メモのみ（言語切替） */
    function buildPinDescription(pin, isJa) {
        return isJa ? String(pin.memo_jp || '').trim() : String(pin.memo_en || pin.memo_jp || '').trim();
    }

    function categoryLabelFromEntry(c, isJa) {
        if (!c) return '';
        var v = isJa
            ? (c.cat_jp || c.category || c.cat_en || c.cat_name_en || '')
            : (c.cat_en || c.cat_name_en || c.category || c.cat_jp || '');
        return String(v || '').trim();
    }

    function itemNameFromEntry(c, isJa) {
        if (!c) return '';
        var v = isJa
            ? (c.item_name_jp || c.item_jp || c.item_name_en || c.item_en || '')
            : (c.item_name_en || c.item_en || c.item_name_jp || c.item_jp || '');
        return String(v || '').trim();
    }

    /** item_select: item_qty があれば優先、なければ qty。アイテムありで両方空なら 1。qty_only は qty。 */
    function itemQtyStringForEntry(c) {
        if (!c) return '';
        var hasItem = c.item_id && String(c.item_id).trim();
        if (hasItem) {
            var iq = c.item_qty;
            if (iq != null && String(iq).trim() !== '') return String(iq).trim();
            var q = c.qty;
            if (q != null && String(q).trim() !== '') return String(q).trim();
            return '1';
        }
        var q2 = c.qty;
        return (q2 != null && String(q2).trim() !== '') ? String(q2).trim() : '';
    }

    function itemQtyForHover(c) {
        return itemQtyStringForEntry(c);
    }

    /** 全角数字を半角に寄せてから数値化（pin_site_preview と同趣旨） */
    function qtyNumericEqualsOne(s) {
        if (s == null || String(s).trim() === '') return false;
        var t = String(s).trim().replace(/[０-９]/g, function(ch) {
            return String.fromCharCode(ch.charCodeAt(0) - 0xFF10 + 0x30);
        });
        var n = parseFloat(t, 10);
        return !isNaN(n) && n === 1;
    }

    /** ホバー・クリックポップアップ: 数量が 1 のときは × なし。2 以上のみ「×数」 */
    function hoverQtySuffix(qtyStr) {
        if (qtyStr == null || String(qtyStr).trim() === '') return '';
        var s = String(qtyStr).trim();
        if (qtyNumericEqualsOne(s)) return '';
        return ' ×' + s;
    }

    function lockpickReqSuffix(c, isJa) {
        if (!c || !c.attributes || typeof c.attributes !== 'object') return '';
        var a = c.attributes;
        var has25 = !!(a.req_lockpick_lv25 === true || String(a.req_lockpick_lv25 || '').toLowerCase() === 'true' || String(a.req_lockpick_lv25 || '') === '1');
        var has75 = !!(a.req_lockpick_lv75 === true || String(a.req_lockpick_lv75 || '').toLowerCase() === 'true' || String(a.req_lockpick_lv75 || '') === '1');
        if (!has25 && !has75) return '';
        var lv = [];
        if (has25) lv.push('25');
        if (has75) lv.push('75');
        if (isJa) return '（要ロックピック Lv.' + lv.join('/Lv.') + '）';
        return ' (Req. Lv.' + lv.join('/Lv.') + ')';
    }

    function categorySpecialRulesForEntry(c) {
        if (!c) return [];
        var cid = String(c.cat_id || '').trim();
        var cjp = String(c.category || c.cat_jp || '').trim();
        var v = null;
        if (cid && categorySpecialRules && typeof categorySpecialRules[cid] === 'object') v = categorySpecialRules[cid];
        if (!v && cjp && categorySpecialRules && typeof categorySpecialRules[cjp] === 'object') v = categorySpecialRules[cjp];
        if (!v || !Array.isArray(v.rules)) return [];
        return v.rules;
    }

    function skillDisplayNameForRule(skillId, isJa) {
        var sid = String(skillId || '').trim();
        if (!sid) return '';
        var inf = skillNameMaster && typeof skillNameMaster === 'object' ? skillNameMaster[sid] : null;
        if (!inf || typeof inf !== 'object') return sid;
        var jp = String(inf.name_jp || '').trim();
        var en = String(inf.name_en || '').trim();
        if (isJa) return jp || en || sid;
        return en || jp || sid;
    }

    function normalizeSkillNameMaster(raw) {
        if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
            return raw;
        }
        if (!Array.isArray(raw)) return {};
        var out = {};
        raw.forEach(function (it) {
            if (!it || typeof it !== 'object') return;
            var sid = String(it.id || '').trim();
            if (!sid) return;
            out[sid] = {
                name_jp: String(it.name_jp || '').trim(),
                name_en: String(it.name_en || '').trim()
            };
        });
        return out;
    }

    function specialRuleText(rule, isJa) {
        if (!rule || typeof rule !== 'object') return '';
        var nt = String(rule.note_type || '').trim();
        var rt = String(rule.req_type || '').trim();
        var app = String(rule.applicability || 'always').trim();
        var ntDisp = isJa ? nt : ({ '必要条件': 'Required', '推奨条件': 'Recommended', 'メモ': 'Memo' }[nt] || nt);
        // JP の「必要条件(緩め)」は "必要条件（必要な場合がある）" ではなく "必要な場合がある" を使う
        if (isJa && nt === '必要条件' && app === 'lenient') ntDisp = '必要な場合がある';
        // EN の「必要条件(緩め)」は "Required (May require)" ではなく "May require" を使う
        if (!isJa && nt === '必要条件' && app === 'lenient') ntDisp = 'May require';
        var maybeTag = app === 'sometimes' ? (isJa ? '（場合あり）' : ' (Sometimes)')
            : (app === 'lenient' ? (isJa ? '（必要な場合がある）' : ' (May require)') : '');
        if (isJa && nt === '必要条件' && app === 'lenient') maybeTag = '';
        if (!isJa && nt === '必要条件' && app === 'lenient') maybeTag = '';
        if (nt === 'メモ') {
            var mjp = String(rule.memo_jp || '').trim();
            var men = String(rule.memo_en || '').trim();
            var leg = String(rule.memo || '').trim();
            if (isJa) {
                var t = mjp || leg;
                return t ? ('メモ: ' + t) : '';
            }
            var t2 = men || leg || mjp;
            return t2 ? ('Memo: ' + t2) : '';
        }
        if (rt === '装備') {
            var legacy = String(rule.item_name || '').trim();
            var ij = String(rule.item_name_jp || '').trim();
            var ie = String(rule.item_name_en || '').trim();
            if (!ij && legacy) ij = legacy;
            if (!ie && legacy) ie = legacy;
            var iname = isJa ? (ij || ie) : (ie || ij);
            var icnt = String(rule.item_count || '').trim();
            if (!iname) return '';
            var body = icnt && !qtyNumericEqualsOne(icnt) ? (iname + ' ×' + icnt) : iname;
            return ntDisp + maybeTag + ': ' + body;
        }
        if (rt === 'スキルレベル') {
            var sid2 = String(rule.skill_id || '').trim();
            var slv = String(rule.skill_level || '').trim();
            if (!sid2 || !slv) return '';
            var nm2 = skillDisplayNameForRule(sid2, isJa);
            return ntDisp + maybeTag + ': ' + nm2 + ' Lv.' + slv;
        }
        if (rt === 'スキル') {
            var sid3 = String(rule.skill_id || '').trim();
            if (!sid3) return '';
            var nm3 = skillDisplayNameForRule(sid3, isJa);
            return ntDisp + maybeTag + ': ' + (isJa ? ('スキル ' + nm3) : ('Skill ' + nm3));
        }
        var lv = String(rule.level || '').trim();
        if (!lv) return '';
        return ntDisp + maybeTag + ': Lv.' + lv;
    }

    function specialTextForEntry(c, isJa) {
        var fr = specialFragmentsForEntry(c, isJa);
        return fr.length ? fr.join(' / ') : '';
    }

    /** スロット1つ分の特記（有効ルールごとの文字列）。ピン単位で集約・重複除去する。 */
    function specialFragmentsForEntry(c, isJa) {
        var rules = categorySpecialRulesForEntry(c);
        if (!rules.length) return [];
        var attrs = (c && c.attributes && typeof c.attributes === 'object') ? c.attributes : {};
        var parts = [];
        rules.forEach(function (r, idx) {
            var k = 'special_rule_enabled_' + (idx + 1);
            if (!attrs[k]) return;
            var t = specialRuleText(r, isJa);
            if (t) parts.push(t);
        });
        return parts;
    }

    function pinHasCategoryWithSpecialRulesMaster(contentsArr) {
        if (!contentsArr || !contentsArr.length) return false;
        for (var i = 0; i < contentsArr.length; i++) {
            if (categorySpecialRulesForEntry(contentsArr[i]).length) return true;
        }
        return false;
    }

    /** ピン内の全スロットの特記を1か所にまとめ、同一表示文は1回だけ（順序は先出し優先）。 */
    function aggregateSpecialFragmentsForPin(contentsArr, isJa) {
        var seen = {};
        var order = [];
        (contentsArr || []).forEach(function (c) {
            specialFragmentsForEntry(c, isJa).forEach(function (t) {
                var key = String(t).trim();
                if (!key || seen[key]) return;
                seen[key] = true;
                order.push(t);
            });
        });
        return order;
    }

    /** ポップアップ用: 特記ブロックHTML（無し／マスタのみで未選択は （なし）） */
    function aggregateSpecialHtmlForPin(contentsArr, isJa) {
        var fr = aggregateSpecialFragmentsForPin(contentsArr, isJa);
        var lab = isJa ? '特記' : 'Notes';
        if (fr.length) {
            var inner = fr.map(function (t) {
                return '<div style="margin-top:3px;">・' + escapeHtmlPin(t) + '</div>';
            }).join('');
            return '<div style="font-size:12px;color:#333;margin-top:10px;line-height:1.45;">' +
                '<div style="font-weight:bold;">' + lab + '</div>' + inner + '</div>';
        }
        if (pinHasCategoryWithSpecialRulesMaster(contentsArr)) {
            return '<div style="font-size:12px;color:#333;margin-top:10px;">' +
                '<span style="font-weight:bold;">' + lab + '</span>' +
                (isJa ? ': （なし）' : ': (None)') + '</div>';
        }
        return '';
    }

    function shortMemoForHover(pin, isJa) {
        var m = isJa ? (pin.memo_jp || '') : (pin.memo_en || pin.memo_jp || '');
        m = String(m || '').trim();
        if (!m) return '';
        // hover は概要のみ: 短い補足だけ許可
        return m.length <= 20 ? m : '';
    }

    function alwaysMemoForHover(pin, isJa) {
        // 要望: メモは常に表示（空のときだけ非表示）
        var raw = isJa ? (pin.memo_jp || '') : (pin.memo_en || pin.memo_jp || '');
        var m = plainMemoForTooltip(raw).replace(/\n+/g, ' ').trim();
        return m;
    }

    function exceptionMemoForHover(pin, isJa) {
        // 例外表示名のときは「表示名 + メモ」を優先。長すぎるメモは1行短縮。
        var m = alwaysMemoForHover(pin, isJa);
        if (!m) return '';
        if (m.length > 40) return m.slice(0, 40) + '...';
        return m;
    }

    /**
     * Hover/tooltip 専用の概要テキストを生成する。
     * クリック popup は従来どおり詳細（全件・全文）を維持する。
     */
    function buildHoverTooltipText(pin, isJa, contents, legacyCategory) {
        var lines = [];
        var objName = isJa ? (pin.obj_jp || pin.obj_en || '') : (pin.obj_en || pin.obj_jp || '');
        objName = String(objName || '').trim();
        var rows = [];
        if (Array.isArray(contents)) {
            contents.forEach(function(c) {
                if (!c) return;
                var itemName = itemNameFromEntry(c, isJa);
                var cat = categoryLabelFromEntry(c, isJa);
                var qty = itemQtyStringForEntry(c);
                var req = lockpickReqSuffix(c, isJa);
                // hover では特記事項（カテゴリ特記ルール）とメモは出さない（popup 側）
                var suffix = hoverQtySuffix(qty) + req;
                if (itemName) rows.push(itemName + suffix);
                else if (cat) rows.push(cat + suffix);
            });
        }
        if (rows.length > 0) return rows.join('\n');
        if (objName) return objName;
        return isJa ? '（無題）' : '(Untitled)';
    }

    function createMarkerFromPin(pin, visualStyle, myCategories, bpNum, headline, description, filterTooltipText) {
        var coords = pin.coords || [pin.x, pin.y];
        var x = coords[0], y = coords[1];
        if (typeof x !== 'number' || typeof y !== 'number') return null;

        var latLng = map.unproject([x, y], maxZoom);
        var displayStyle = normalizeMarkerDisplayStyle(pin.marker_display_style);
        var pinSvgId = (pin.svg_icon_id || '').trim();
        var symHex = (pin.marker_icon_color || '#ffffff').trim();
        if (!isSafeSvgIconColor(symHex)) symHex = '#ffffff';
        var pinBg = (pin.marker_bg_color || (visualStyle && visualStyle.color) || '#95a5a6').trim();
        if (!isSafeSvgIconColor(pinBg)) pinBg = '#95a5a6';

        var iconHtml = '<div style="position:relative;">' + (visualStyle.emoji || '📌');
        if (bpNum) {
            iconHtml += '<span style="position:absolute;bottom:-5px;right:-8px;background:#e74c3c;color:white;border-radius:50%;font-size:10px;min-width:16px;height:16px;text-align:center;line-height:16px;font-weight:bold;border:1px solid white;box-shadow:1px 1px 2px rgba(0,0,0,0.3);">' + bpNum + '</span>';
        }
        iconHtml += '</div>';

        var emojiIcon = L.divIcon({
            html: iconHtml,
            className: 'emoji-icon',
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });

        var marker = L.marker(latLng, { icon: emojiIcon });

        if (pinSvgId && typeof wrapPinBasePlusImgIcon === 'function') {
            var scope = (pin.svg_icon_scope || '').trim();
            var candidates = svgIconUrlCandidates(pinSvgId);
            if (displayStyle === 'icon_only') {
                attachIconOnlySvgToMarker(marker, pinSvgId, scope, symHex);
            } else {
                getOrFetchSvgObjectUrl(
                    pinSvgId,
                    scope,
                    symHex,
                    candidates,
                    function (objUrl) {
                        var innerHtml = wrapPinBasePlusImgIcon(pinBg, objUrl, symHex, JSON_PIN_MARKER_PX);
                        var html = wrapDivIconZoomScale(innerHtml, 'map-pin-svg-composite', '50% 100%');
                        marker.setIcon(
                            L.divIcon({
                                html: html,
                                className: MAP_PIN_LEAFLET_SHELL,
                                iconSize: [JSON_PIN_MARKER_PX, JSON_PIN_MARKER_PX],
                                iconAnchor: JSON_PIN_ANCHOR
                            })
                        );
                        syncMarkerImportanceVisual(marker);
                    },
                    function () {
                        if (isDebug) console.warn('[map.js] svg_icon fetch failed', pinSvgId, candidates);
                    }
                );
            }
        }

        var descHtml = memoToSafePopupHtml(description);
        var detailHtml = formatAllContentsForPopup(pin.contents || [], isJa);
        var specialHtml = aggregateSpecialHtmlForPin(pin.contents || [], isJa);
        var midHtml = '';
        if (detailHtml) {
            midHtml += '<div style="font-size:12px;color:#333;">' + detailHtml + '</div>';
        }
        if (specialHtml) midHtml += specialHtml;
        var popupHtml = '<div style="font-family:sans-serif;min-width:200px;line-height:1.4;">' +
            '<div style="font-size:14px;font-weight:bold;">' + escapeHtmlPin(headline) + '</div>' +
            '<div style="margin:6px 0 8px;border-top:1px solid #bbb;"></div>';
        if (midHtml) popupHtml += midHtml;
        if (descHtml) {
            popupHtml += '<div style="margin:6px 0 6px;border-top:1px solid #bbb;"></div>';
            popupHtml += '<div style="font-size:12px;color:#333;white-space:normal;">' + descHtml + '</div>';
        }
        popupHtml += '</div>';
        marker.bindPopup(popupHtml);

        // 通常: hover は概要のみ（詳細は popup 側）。フィルタモード時は従来ラベルを優先。
        var tooltipText;
        if (filterMode && filterTooltipText && String(filterTooltipText).trim()) {
            tooltipText = filterTooltipText;
        } else {
            tooltipText = String(pin.hover_tooltip || '').trim();
        }
        if (!tooltipText || String(tooltipText).trim() === '') {
            tooltipText = headline || (visualStyle && visualStyle.label) || '—';
        }
        // サイト側CSSが nowrap でも行分割を維持するため、\n は <br> に明示変換する
        var tooltipHtml = escapeHtmlPin(tooltipText).replace(/\n/g, '<br>');
        var tooltipOpts = showLabels ? {
            permanent: true, direction: 'top', className: 'item-tooltip-permanent',
            opacity: 0.9, offset: [0, -20]
        } : {
            direction: 'top', sticky: true, className: 'item-tooltip',
            opacity: 0.9, offset: [0, -10]
        };
        marker.bindTooltip(tooltipHtml, tooltipOpts);

        // ホバー中/ポップアップ表示中は対象ピンを視覚的に強調する
        var isHoveringPin = false;
        var isPopupOpenPin = false;
        function syncMarkerActiveState() {
            var active = isHoveringPin || isPopupOpenPin;
            var el = marker.getElement ? marker.getElement() : marker._icon;
            if (el && el.classList) {
                el.classList.toggle('map-pin-active', !!active);
            }
            if (marker.setZIndexOffset) {
                marker.setZIndexOffset(active ? 1200 : 0);
            }
        }
        marker.on('mouseover', function () {
            isHoveringPin = true;
            syncMarkerActiveState();
        });
        marker.on('mouseout', function () {
            isHoveringPin = false;
            syncMarkerActiveState();
        });
        marker.on('popupopen', function () {
            isPopupOpenPin = true;
            syncMarkerActiveState();
        });
        marker.on('popupclose', function () {
            isPopupOpenPin = false;
            syncMarkerActiveState();
        });

        bindMarkerImportanceVisual(marker, pin.importance);

        return marker;
    }

    function addMarkersFromPins(pins) {
        if (!Array.isArray(pins)) return;

        pins.forEach(function(pin) {
            var coords = pin.coords || [pin.x, pin.y];
            var x = parseFloat(coords[0]), y = parseFloat(coords[1]);
            if (isNaN(x) || isNaN(y)) return;

            var attrRaw = (pin.obj_id || pin.attribute || '').trim();
            var contents = [];
            if (Array.isArray(pin.contents)) {
                contents = pin.contents;
            } else if (Array.isArray(pin.categories)) {
                // 旧/互換形式: pins_export に categories 配列で入っているケース
                contents = pin.categories;
            } else if (typeof pin.categories === 'string' && pin.categories.trim()) {
                try {
                    var parsedCats = JSON.parse(pin.categories);
                    if (Array.isArray(parsedCats)) contents = parsedCats;
                } catch (eC) { /* ignore */ }
            }
            // popup 詳細は createMarkerFromPin が pin.contents を参照するため正規化しておく
            pin.contents = contents;

            var styleKey = resolveFilterStyleKey(attrRaw);
            var visualStyle = pickVisualStyle(styleKey);
            var myCategories = [styleKey];

            var pinCategoryIds = [];
            if (contents && contents.length) {
                contents.forEach(function (c) {
                    if (c && c.cat_id) {
                        var cid = String(c.cat_id).trim();
                        if (cid && pinCategoryIds.indexOf(cid) < 0) pinCategoryIds.push(cid);
                    }
                });
            }
            if (pinCategoryIds.length === 0 && pin.category) {
                var cidLegacy = legacyCategoryToCatId(pin.category);
                if (cidLegacy) pinCategoryIds.push(cidLegacy);
            }
            if (!subsetAllowsMarker(styleKey, pinCategoryIds, pinItemIds)) {
                return;
            }
            var pinItemIds = collectPinItemIdsFromContents(contents);

            var headline = buildPinHeadline(pin, isJa, contents, pin.category);
            var description = buildPinDescription(pin, isJa);
            var filterTT = '';
            pin.hover_tooltip = buildHoverTooltipText(pin, isJa, contents, pin.category);

            var categoriesArrForMerge = [];
            if (contents && contents.length) {
                contents.forEach(function(c) {
                    if (c && c.cat_id) categoriesArrForMerge.push(c);
                });
            }
            var attrKeyMerge = (pin.obj_id || pin.attribute || '').trim();
            var exportedMds = (pin.marker_display_style || '').trim();
            mergePinStyleFromConfig(pin, attrKeyMerge, categoriesArrForMerge);
            if (exportedMds) {
                pin.marker_display_style = normalizeMarkerDisplayStyle(exportedMds);
            }

            var marker = createMarkerFromPin(pin, visualStyle, myCategories, null, headline, description, filterTT);
            if (!marker) return;

            allMarkers.push({ marker: marker, categories: myCategories, pinCategoryIds: pinCategoryIds, pinItemIds: pinItemIds, rank: 'standard' });
        });

        addOverlayControls();
        updateVisibleMarkers();
    }

    function parseCSVRow(row) {
        var result = [];
        var current = '';
        var inQuotes = false;
        for (var i = 0; i < row.length; i++) {
            var char = row[i];
            if (char === '"') {
                if (inQuotes && row[i + 1] === '"') {
                    current += '"';
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (char === ',' && !inQuotes) {
                result.push(current);
                current = '';
            } else {
                current += char;
            }
        }
        result.push(current);
        return result;
    }

    function veinFilterObjectIconHtml(typ) {
        var t = String(typ || 'loot').toLowerCase();
        var d;
        if (t === 'landmark') {
            d = 'M4 21V11l8-5 8 5v10M9 21v-4h6v4';
        } else if (t === 'colony') {
            d = 'M6 20h12M8 16h8M10 12h4M12 4v6';
        } else {
            d = 'M5 10h14v9H5V10zm3-3a4 4 0 118 0v3';
        }
        return '<span class="vein-filter-icon-wrap"><svg class="vein-filter-icon-svg" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">' +
            '<path fill="none" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round" d="' + d + '"/></svg></span>';
    }

    function veinFilterCategoryIconHtml() {
        return '<span class="vein-filter-icon-wrap"><svg class="vein-filter-icon-svg vein-filter-icon-svg--muted" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">' +
            '<path fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h12M4 18h16"/></svg></span>';
    }

    function orderedObjectFilterKeys() {
        var keys = Object.keys(styles).filter(function (k) {
            if (k === 'other') return false;
            if (k === 'trash' && !isDebug) return false;
            if (!isObjectAllowedBySubset(k)) return false;
            return true;
        });
        if (mapObjectAttrIdsOrder && mapObjectAttrIdsOrder.length) {
            var out = [];
            mapObjectAttrIdsOrder.forEach(function (id) {
                if (styles[id] && out.indexOf(id) < 0) out.push(id);
            });
            keys.forEach(function (k) {
                if (out.indexOf(k) < 0) out.push(k);
            });
            return out;
        }
        return keys;
    }

    /** category_master 1件を、map_object_attr_ids 優先でどのオブジェクト配下に置くか決める */
    function primaryObjectIdForCategory(ent, orderArr) {
        var oids = (ent && ent.object_ids && Array.isArray(ent.object_ids)) ? ent.object_ids : [];
        if (oids.length === 0) return null;
        var i;
        for (i = 0; i < orderArr.length; i++) {
            var aid = orderArr[i];
            var hit = oids.some(function (x) {
                return String(x || '').trim().toUpperCase() === String(aid).toUpperCase();
            });
            if (hit) return aid;
        }
        return String(oids[0] || '').trim() || null;
    }

    /** category_list（マスタの行順）に合わせてカテゴリ行を並べ替え。無ければ表示名でソート。 */
    function sortCategoryRowsByConfigOrder(rows) {
        var ord = categoryListOrderGlobal;
        if (!ord || !ord.length) {
            rows.sort(function (a, b) {
                return String(a.label).localeCompare(String(b.label), isJa ? 'ja' : 'en');
            });
            return;
        }
        var idx = {};
        var oi;
        for (oi = 0; oi < ord.length; oi++) {
            idx[ord[oi]] = oi;
        }
        rows.sort(function (a, b) {
            var ja = a.jpKey;
            var jb = b.jpKey;
            var ia = Object.prototype.hasOwnProperty.call(idx, ja) ? idx[ja] : 100000;
            var ib = Object.prototype.hasOwnProperty.call(idx, jb) ? idx[jb] : 100000;
            if (ia !== ib) return ia - ib;
            return String(a.label).localeCompare(String(b.label), isJa ? 'ja' : 'en');
        });
    }

    /** オブジェクト → カテゴリ行の階層データ（未紐づけは __orphan__） */
    function collectCategoryRowsByPrimaryObject() {
        var orderArr = orderedObjectFilterKeys();
        var byObj = {};
        orderArr.forEach(function (a) {
            byObj[a] = [];
        });

        var seenCatIds = {};
        Object.keys(categoryMasterGlobal).forEach(function (jpKey) {
            var ent = categoryMasterGlobal[jpKey];
            if (!ent || typeof ent !== 'object') return;
            var cid = String(ent.id || '').trim();
            if (!cid) return;
            if (!isCategoryAllowedBySubset(cid)) return;
            if (seenCatIds[cid]) return;
            seenCatIds[cid] = true;
            var lab = isJa ? (ent.name_jp || jpKey) : (ent.name_en || ent.name_jp || jpKey);
            var row = { id: cid, label: lab, jpKey: jpKey };
            var primary = primaryObjectIdForCategory(ent, orderArr);
            if (primary && byObj[primary]) {
                byObj[primary].push(row);
            } else {
                if (!byObj.__orphan__) {
                    byObj.__orphan__ = [];
                }
                byObj.__orphan__.push(row);
            }
        });

        orderArr.forEach(function (k) {
            sortCategoryRowsByConfigOrder(byObj[k]);
        });
        if (byObj.__orphan__) {
            sortCategoryRowsByConfigOrder(byObj.__orphan__);
        }
        return { byObj: byObj, orderArr: orderArr };
    }

    function collectPinItemIdsFromContents(contentsArr) {
        var out = [];
        if (!contentsArr || !contentsArr.length) return out;
        contentsArr.forEach(function (c) {
            if (!c) return;
            var iid = String(c.item_id || '').trim();
            if (iid && out.indexOf(iid) < 0) out.push(iid);
        });
        return out;
    }

    function legacyCategoryToCatId(legacyCategory) {
        var lc = String(legacyCategory || '').trim();
        if (!lc) return '';
        var catMap = {
            '設計図': 'blueprint',
            'LEM': 'lem',
            '戦時債権': 'war_bonds',
            '交換アイテム': 'trade_item',
            'キーカード': 'keycard',
            '植物': 'plant',
            '武器コンテナ': 'LOOT_CONTAINER',
            '医療品コンテナ': 'MEDICAL_CONTAINER',
            'ツールコンテナ': 'TOOL_CONTAINER',
            '武器': 'WEAPON',
            'ツール': 'TOOL'
        };
        return catMap[lc] || lc;
    }

    /** item_master をフラット化（同一 item_id は先頭のみ） */
    function flattenItemMasterForFilter(im) {
        var rows = [];
        var seen = {};
        if (!im || typeof im !== 'object') return rows;
        Object.keys(im).forEach(function (grp) {
            if (isSubsetActive()) {
                var cmEnt = categoryMasterGlobal[grp];
                var cidGrp = cmEnt && typeof cmEnt === 'object' ? String(cmEnt.id || '').trim() : '';
                if (!isCategoryAllowedBySubset(cidGrp)) return;
            }
            var grpObj = im[grp];
            if (!grpObj || typeof grpObj !== 'object') return;
            Object.keys(grpObj).forEach(function (iidRaw) {
                var iid = String(iidRaw || '').trim();
                if (!iid || seen[iid]) return;
                if (!isItemAllowedBySubset(iid)) return;
                seen[iid] = true;
                var info = grpObj[iidRaw];
                if (!info || typeof info !== 'object') return;
                var lab = isJa
                    ? (String(info.name_jp || iid).trim() || iid)
                    : (String(info.name_en || info.name_jp || iid).trim() || iid);
                rows.push({ id: iid, label: lab, group: grp });
            });
        });
        return rows;
    }

    /**
     * 指定カテゴリ行（category_master.jpKey）配下の item_master を集約。
     * POI グループで「カテゴリではなくアイテム」で絞るために使う。
     */
    function collectItemRowsGroupedByCategoryRows(catRows) {
        var out = [];
        var seenGlobal = {};
        (catRows || []).forEach(function (ce) {
            var grp = String((ce && ce.jpKey) || '').trim();
            if (!grp) return;
            var grpObj = itemMasterGlobal[grp];
            if (!grpObj || typeof grpObj !== 'object') return;
            var rows = [];
            Object.keys(grpObj).forEach(function (iidRaw) {
                var iid = String(iidRaw || '').trim();
                if (!iid || seenGlobal[iid]) return;
                if (!isItemAllowedBySubset(iid)) return;
                seenGlobal[iid] = true;
                var info = grpObj[iidRaw];
                if (!info || typeof info !== 'object') return;
                var lab = isJa
                    ? (String(info.name_jp || iid).trim() || iid)
                    : (String(info.name_en || info.name_jp || iid).trim() || iid);
                rows.push({ id: iid, label: lab, group: grp });
            });
            rows.sort(function (a, b) {
                return String(a.label).localeCompare(String(b.label), isJa ? 'ja' : 'en');
            });
            if (rows.length > 0) {
                out.push({ title: ce.label, rows: rows });
            }
        });
        return out;
    }

    function veinFilterItemIconHtml() {
        return '<span class="vein-filter-icon-wrap"><svg class="vein-filter-icon-svg vein-filter-icon-svg--muted" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">' +
            '<path fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>' +
            '<path fill="none" stroke="currentColor" stroke-width="1.1" stroke-linecap="round" d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/></svg></span>';
    }

    var veinFilterDrawerEl = null;

    function removeVeinFilterDrawer() {
        if (veinFilterDrawerEl && veinFilterDrawerEl.parentNode) {
            veinFilterDrawerEl.parentNode.removeChild(veinFilterDrawerEl);
            veinFilterDrawerEl = null;
        }
    }

    function invalidateMapSizeSoon() {
        setTimeout(function() {
            try { map.invalidateSize(); } catch (e1) { /* ignore */ }
        }, 60);
        setTimeout(function() {
            try { map.invalidateSize(); } catch (e2) { /* ignore */ }
        }, 280);
    }

    function addOverlayControls() {
        removeVeinFilterDrawer();
        var mc = mapDiv.parentElement;
        if (mc) {
            mc.classList.remove('vein-map-with-filter');
        }

        if (filterMode) {
            return;
        }

        if (!mc) {
            return;
        }
        mc.classList.add('vein-map-with-filter');

        var aside = document.createElement('aside');
        aside.className = 'vein-filter-drawer';
        aside.setAttribute('aria-label', isJa ? '地図の表示フィルター' : 'Map display filters');

        var head = document.createElement('div');
        head.className = 'vein-filter-drawer__head';

        var title = document.createElement('div');
        title.className = 'vein-filter-drawer__title';
        title.textContent = isJa ? '表示' : 'Layers';

        var toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'vein-filter-drawer__toggle';
        toggleBtn.setAttribute('aria-expanded', 'true');
        toggleBtn.title = isJa ? 'パネルを畳む' : 'Collapse panel';
        toggleBtn.innerHTML = '&#8249;';
        toggleBtn.addEventListener('click', function() {
            var collapsed = aside.classList.toggle('vein-filter-drawer--collapsed');
            toggleBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
            toggleBtn.innerHTML = collapsed ? '&#8250;' : '&#8249;';
            toggleBtn.title = collapsed ? (isJa ? 'パネルを開く' : 'Expand panel') : (isJa ? 'パネルを畳む' : 'Collapse panel');
            invalidateMapSizeSoon();
        });

        head.appendChild(title);
        head.appendChild(toggleBtn);

        var scroll = document.createElement('div');
        scroll.className = 'vein-filter-drawer__scroll';

        function appendImportanceVisualToggleRow(parent) {
            var sec = document.createElement('div');
            sec.className = 'vein-filter-section';
            var cap = document.createElement('p');
            cap.className = 'vein-filter-section__label';
            cap.textContent = isJa ? '表示オプション' : 'Display options';
            sec.appendChild(cap);

            var row = document.createElement('label');
            row.className = 'vein-filter-row' + (importanceVisualEnabled ? ' vein-filter-row--on' : '');
            var inp = document.createElement('input');
            inp.type = 'checkbox';
            inp.checked = importanceVisualEnabled;
            inp.setAttribute('data-vein-importance-visual', '1');
            row.appendChild(inp);

            var iconHost = document.createElement('span');
            iconHost.innerHTML = '<span class="vein-filter-icon-wrap"><svg class="vein-filter-icon-svg vein-filter-icon-svg--muted" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" d="M12 3l2.6 5.28 5.83.85-4.21 4.1.99 5.77L12 16.9 6.79 19l.99-5.77-4.21-4.1 5.83-.85L12 3z"/></svg></span>';
            while (iconHost.firstChild) row.appendChild(iconHost.firstChild);

            var lab = document.createElement('span');
            lab.className = 'vein-filter-label';
            lab.textContent = isJa ? '重要度で強調表示' : 'Highlight by importance';
            var fakeToggle = document.createElement('span');
            fakeToggle.className = 'vein-filter-toggle-ui';
            fakeToggle.setAttribute('aria-hidden', 'true');
            row.appendChild(lab);
            row.appendChild(fakeToggle);
            inp.addEventListener('change', function () {
                importanceVisualEnabled = !!inp.checked;
                if (importanceVisualEnabled) row.classList.add('vein-filter-row--on');
                else row.classList.remove('vein-filter-row--on');
                refreshAllMarkerImportanceVisual();
            });
            sec.appendChild(row);
            parent.appendChild(sec);
        }

        function appendVeinCategoryFilterRow(parent, ce) {
            var cid = ce.id;
            var row = document.createElement('label');
            row.className = 'vein-filter-row vein-filter-row--nested' + (activeCategoryFilters.has(cid) ? ' vein-filter-row--on' : '');
            var inp = document.createElement('input');
            inp.type = 'checkbox';
            inp.checked = activeCategoryFilters.has(cid);
            inp.setAttribute('data-vein-cat-id', cid);
            row.appendChild(inp);
            var iconHost = document.createElement('span');
            iconHost.innerHTML = veinFilterCategoryIconHtml();
            while (iconHost.firstChild) {
                row.appendChild(iconHost.firstChild);
            }
            var lab = document.createElement('span');
            lab.className = 'vein-filter-label';
            lab.textContent = ce.label;
            var fakeToggle = document.createElement('span');
            fakeToggle.className = 'vein-filter-toggle-ui';
            fakeToggle.setAttribute('aria-hidden', 'true');
            row.appendChild(lab);
            row.appendChild(fakeToggle);
            (function (catId) {
                function syncCat() {
                    if (inp.checked) {
                        activeCategoryFilters.add(catId);
                        row.classList.add('vein-filter-row--on');
                    } else {
                        activeCategoryFilters.delete(catId);
                        row.classList.remove('vein-filter-row--on');
                    }
                    updateVisibleMarkers();
                }
                inp.addEventListener('change', syncCat);
            }(cid));
            parent.appendChild(row);
        }

        function appendVeinPoiItemFilterRow(parent, it, extraClass) {
            var iid = it.id;
            var row = document.createElement('label');
            row.className = 'vein-filter-row vein-filter-row--nested' + (extraClass ? (' ' + extraClass) : '') + (activePoiItemFilters.has(iid) ? ' vein-filter-row--on' : '');
            var inp = document.createElement('input');
            inp.type = 'checkbox';
            inp.checked = activePoiItemFilters.has(iid);
            inp.setAttribute('data-vein-poi-item-id', iid);
            row.appendChild(inp);
            var iconHostIt = document.createElement('span');
            iconHostIt.innerHTML = veinFilterItemIconHtml();
            while (iconHostIt.firstChild) {
                row.appendChild(iconHostIt.firstChild);
            }
            var labIt = document.createElement('span');
            labIt.className = 'vein-filter-label';
            labIt.textContent = it.label;
            var fakeToggleIt = document.createElement('span');
            fakeToggleIt.className = 'vein-filter-toggle-ui';
            fakeToggleIt.setAttribute('aria-hidden', 'true');
            row.appendChild(labIt);
            row.appendChild(fakeToggleIt);
            (function (itemId) {
                inp.addEventListener('change', function () {
                    if (inp.checked) {
                        activePoiItemFilters.add(itemId);
                        row.classList.add('vein-filter-row--on');
                    } else {
                        activePoiItemFilters.delete(itemId);
                        row.classList.remove('vein-filter-row--on');
                    }
                    updateVisibleMarkers();
                });
            }(iid));
            parent.appendChild(row);
        }

        function appendVeinItemFilterRow(parent, it) {
            var iid = it.id;
            var row = document.createElement('label');
            row.className = 'vein-filter-row vein-filter-row--nested' + (activeItemFilters.has(iid) ? ' vein-filter-row--on' : '');
            row.setAttribute('data-vein-item-search', (it.label + ' ' + iid + ' ' + String(it.group || '')).toLowerCase());
            var inp = document.createElement('input');
            inp.type = 'checkbox';
            inp.checked = activeItemFilters.has(iid);
            inp.setAttribute('data-vein-item-id', iid);
            row.appendChild(inp);
            var iconHostIt = document.createElement('span');
            iconHostIt.innerHTML = veinFilterItemIconHtml();
            while (iconHostIt.firstChild) {
                row.appendChild(iconHostIt.firstChild);
            }
            var labIt = document.createElement('span');
            labIt.className = 'vein-filter-label';
            labIt.textContent = it.label;
            var fakeToggleIt = document.createElement('span');
            fakeToggleIt.className = 'vein-filter-toggle-ui';
            fakeToggleIt.setAttribute('aria-hidden', 'true');
            row.appendChild(labIt);
            row.appendChild(fakeToggleIt);
            (function (itemId) {
                inp.addEventListener('change', function () {
                    if (inp.checked) {
                        activeItemFilters.add(itemId);
                        row.classList.add('vein-filter-row--on');
                    } else {
                        activeItemFilters.delete(itemId);
                        row.classList.remove('vein-filter-row--on');
                    }
                    updateVisibleMarkers();
                });
            }(iid));
            parent.appendChild(row);
        }

        function appendAdvancedItemFilterSection(scrollParent) {
            var items = flattenItemMasterForFilter(itemMasterGlobal);
            if (items.length === 0) return;
            var details = document.createElement('details');
            details.className = 'vein-filter-adv';
            var sum = document.createElement('summary');
            sum.className = 'vein-filter-adv__summary';
            sum.textContent = isJa ? '詳細：アイテムで絞り込み' : 'Advanced: filter by item';
            var inner = document.createElement('div');
            inner.className = 'vein-filter-adv__inner';
            var searchInp = document.createElement('input');
            searchInp.type = 'search';
            searchInp.className = 'vein-filter-adv__search';
            searchInp.setAttribute('autocomplete', 'off');
            searchInp.placeholder = isJa ? 'アイテムを検索...' : 'Search items...';
            var listHost = document.createElement('div');
            listHost.className = 'vein-filter-adv__list';
            items.forEach(function (it) {
                appendVeinItemFilterRow(listHost, it);
            });
            searchInp.addEventListener('input', function () {
                var q = String(searchInp.value || '').trim().toLowerCase();
                var nodes = listHost.querySelectorAll('[data-vein-item-search]');
                var ni;
                for (ni = 0; ni < nodes.length; ni++) {
                    var el = nodes[ni];
                    var hay = el.getAttribute('data-vein-item-search') || '';
                    el.style.display = !q || hay.indexOf(q) >= 0 ? '' : 'none';
                }
            });
            inner.appendChild(searchInp);
            inner.appendChild(listHost);
            details.appendChild(sum);
            details.appendChild(inner);
            scrollParent.appendChild(details);
        }

        appendImportanceVisualToggleRow(scroll);

        var catMasterOn = categoryFilterMasterEnabled();

        if (!catMasterOn) {
            var objLabel = document.createElement('p');
            objLabel.className = 'vein-filter-section__label';
            objLabel.textContent = isJa ? 'オブジェクト' : 'Objects';
            scroll.appendChild(objLabel);

            var objSection = document.createElement('div');
            objSection.className = 'vein-filter-section';

            Object.keys(styles).forEach(function (key) {
                if (key === 'trash' && !isDebug) return;
                if (key === 'other') return;
                var st = styles[key];
                var row = document.createElement('label');
                row.className = 'vein-filter-row' + (activeCategories.has(key) ? ' vein-filter-row--on' : '');

                var inp = document.createElement('input');
                inp.type = 'checkbox';
                inp.checked = activeCategories.has(key);
                inp.setAttribute('data-vein-style-key', key);

                var typ = (st.objType || (attrMappingGlobal[key] && attrMappingGlobal[key].type) || 'loot');
                row.appendChild(inp);
                var iconHost2 = document.createElement('span');
                iconHost2.innerHTML = veinFilterObjectIconHtml(typ);
                while (iconHost2.firstChild) {
                    row.appendChild(iconHost2.firstChild);
                }

                var lab2 = document.createElement('span');
                lab2.className = 'vein-filter-label';
                lab2.textContent = st.label || key;

                var fakeToggle2 = document.createElement('span');
                fakeToggle2.className = 'vein-filter-toggle-ui';
                fakeToggle2.setAttribute('aria-hidden', 'true');

                row.appendChild(lab2);
                row.appendChild(fakeToggle2);

                (function (styleKey) {
                    function syncRow() {
                        if (inp.checked) {
                            activeCategories.add(styleKey);
                            row.classList.add('vein-filter-row--on');
                        } else {
                            activeCategories.delete(styleKey);
                            row.classList.remove('vein-filter-row--on');
                        }
                        updateVisibleMarkers();
                    }
                    inp.addEventListener('change', syncRow);
                }(key));

                objSection.appendChild(row);
            });

            scroll.appendChild(objSection);
        } else {
            var hier = collectCategoryRowsByPrimaryObject();
            var byObj = hier.byObj;
            var orderArr = hier.orderArr;

            orderArr.forEach(function (key) {
                if (key === 'trash' && !isDebug) return;
                if (key === 'other') return;
                var st = styles[key];
                if (!st) return;
                var catRows = byObj[key] || [];
                if (catRows.length === 0 && !isPoiObjectKey(key)) return;

                var group = document.createElement('div');
                group.className = 'vein-filter-group';
                if (isDefaultGroupCollapsed(key)) {
                    group.classList.add('vein-filter-group--collapsed');
                }

                var gh = document.createElement('label');
                gh.className = 'vein-filter-row vein-filter-group__head' + (activeCategories.has(key) ? ' vein-filter-row--on' : '');
                var objInp = document.createElement('input');
                objInp.type = 'checkbox';
                objInp.checked = activeCategories.has(key);
                objInp.setAttribute('data-vein-style-key', key);
                gh.appendChild(objInp);
                var typH = (st.objType || (attrMappingGlobal[key] && attrMappingGlobal[key].type) || 'loot');
                var iconHead = document.createElement('span');
                iconHead.innerHTML = veinFilterObjectIconHtml(typH);
                while (iconHead.firstChild) {
                    gh.appendChild(iconHead.firstChild);
                }
                var titleEl = document.createElement('span');
                titleEl.className = 'vein-filter-label';
                titleEl.textContent = st.label || key;
                var headToggle = document.createElement('span');
                headToggle.className = 'vein-filter-toggle-ui';
                headToggle.setAttribute('aria-hidden', 'true');
                gh.appendChild(titleEl);
                gh.appendChild(headToggle);
                var collapseBtn = document.createElement('button');
                collapseBtn.type = 'button';
                collapseBtn.className = 'vein-filter-group__collapse';
                collapseBtn.setAttribute('aria-label', isJa ? '項目の開閉' : 'Toggle group');
                var collapseArrow = document.createElement('span');
                collapseArrow.className = 'vein-filter-group__collapse-arrow';
                collapseArrow.textContent = '▾';
                var collapseLabel = document.createElement('span');
                collapseLabel.className = 'vein-filter-group__collapse-label';
                collapseBtn.appendChild(collapseArrow);
                collapseBtn.appendChild(collapseLabel);
                function syncCollapseUi(collapsed) {
                    collapseBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
                    collapseLabel.textContent = collapsed
                        ? (isJa ? '開く' : 'Open')
                        : (isJa ? '閉じる' : 'Close');
                }
                syncCollapseUi(group.classList.contains('vein-filter-group--collapsed'));
                collapseBtn.addEventListener('click', function (ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    var collapsed = group.classList.toggle('vein-filter-group--collapsed');
                    syncCollapseUi(collapsed);
                    invalidateMapSizeSoon();
                });
                gh.appendChild(collapseBtn);
                (function (styleKey) {
                    objInp.addEventListener('change', function () {
                        if (objInp.checked) {
                            activeCategories.add(styleKey);
                            gh.classList.add('vein-filter-row--on');
                        } else {
                            activeCategories.delete(styleKey);
                            gh.classList.remove('vein-filter-row--on');
                        }
                        updateVisibleMarkers();
                    });
                }(key));
                group.appendChild(gh);

                var body = document.createElement('div');
                body.className = 'vein-filter-group__body';
                if (isPoiObjectKey(key)) {
                    var poiGroups = collectItemRowsGroupedByCategoryRows(catRows);
                    if (poiGroups.length > 0) {
                        poiGroups.forEach(function (pg) {
                            var subHead = document.createElement('div');
                            subHead.className = 'vein-filter-subgroup-title';
                            subHead.textContent = pg.title;
                            body.appendChild(subHead);
                            pg.rows.forEach(function (it) {
                                appendVeinPoiItemFilterRow(body, it, 'vein-filter-row--nested-deep');
                            });
                        });
                    } else {
                        // item_master 未整備時は従来どおりカテゴリ行にフォールバック
                        catRows.forEach(function (ce) {
                            appendVeinCategoryFilterRow(body, ce);
                        });
                    }
                } else {
                    catRows.forEach(function (ce) {
                        appendVeinCategoryFilterRow(body, ce);
                    });
                }
                group.appendChild(body);
                scroll.appendChild(group);
            });

            if (byObj.__orphan__ && byObj.__orphan__.length) {
                var og = document.createElement('div');
                og.className = 'vein-filter-group';
                var ogh = document.createElement('div');
                ogh.className = 'vein-filter-group__head';
                var otitle = document.createElement('div');
                otitle.className = 'vein-filter-group__title';
                otitle.textContent = isJa ? 'その他' : 'Other';
                ogh.appendChild(otitle);
                og.appendChild(ogh);
                var obody = document.createElement('div');
                obody.className = 'vein-filter-group__body';
                byObj.__orphan__.forEach(function (ce) {
                    appendVeinCategoryFilterRow(obody, ce);
                });
                og.appendChild(obody);
                scroll.appendChild(og);
            }

            var noneCe = {
                id: '__none__',
                label: isJa ? '中身なし' : 'No slot / empty'
            };
            var noneGroup = document.createElement('div');
            noneGroup.className = 'vein-filter-group';
            var noneBody = document.createElement('div');
            noneBody.className = 'vein-filter-group__body';
            appendVeinCategoryFilterRow(noneBody, noneCe);
            noneGroup.appendChild(noneBody);
            scroll.appendChild(noneGroup);
        }

        appendAdvancedItemFilterSection(scroll);

        aside.appendChild(head);
        aside.appendChild(scroll);

        mc.insertBefore(aside, mapDiv);
        veinFilterDrawerEl = aside;
        invalidateMapSizeSoon();
    }

    function formatContentsSummaryForPopup(label, names) {
        if (!names || names.length === 0) return '';
        if (names.length === 1) return label + '：' + names[0];
        return label + '：<br>・' + names.join('<br>・');
    }

    /** ポップアップ内訳: スロットごとの見出しのみ（特記は aggregateSpecialHtmlForPin でピン1か所）。 */
    function formatAllContentsForPopup(contentsArr, isJa) {
        if (!contentsArr || contentsArr.length === 0) return '';
        var parts = [];
        contentsArr.forEach(function(c) {
            if (!c) return;
            var catLab = categoryLabelFromEntry(c, isJa);
            var itemName = itemNameFromEntry(c, isJa);
            var qtyStr = itemQtyStringForEntry(c);
            var reqSuffix = lockpickReqSuffix(c, isJa);
            var head = '';
            if (itemName) {
                head = catLab ? (catLab + '：' + itemName) : itemName;
                // ホバーと同様: 数量が 1 のときは × を付けない
                head += hoverQtySuffix(qtyStr);
                head += reqSuffix;
            } else if (catLab) {
                head = catLab;
                head += hoverQtySuffix(qtyStr);
                head += reqSuffix;
            } else {
                return;
            }
            parts.push('<div style="font-size:13px;font-weight:bold;color:#222;margin-bottom:4px;line-height:1.35;">' +
                '【' + escapeHtmlPin(head) + '】</div>');
        });
        return parts.join('');
    }

    /** 1行目ヘッダーから列名→インデックス（エディタの CSV 列追加・順序差に追従） */
    function csvHeaderIndexMap(headerCols) {
        var m = {};
        if (!headerCols || !headerCols.length) return m;
        for (var hi = 0; hi < headerCols.length; hi++) {
            var name = String(headerCols[hi] || '').trim();
            if (name) m[name] = hi;
        }
        return m;
    }

    function csvIx(cmap, colName, legacyIndex) {
        return Object.prototype.hasOwnProperty.call(cmap, colName) ? cmap[colName] : legacyIndex;
    }

    function loadFromCSV(text) {
        var rawText = text.trim();
        if (rawText.charCodeAt(0) === 0xFEFF) rawText = rawText.slice(1);
        var rows = rawText.split('\n');
        if (rows.length < 2) return;

        var headerCols = parseCSVRow(rows[0]);
        var cmap = csvHeaderIndexMap(headerCols);
        var ix = function(name, leg) { return csvIx(cmap, name, leg); };

        for (var i = 1; i < rows.length; i++) {
            var rawRow = rows[i];
            var cols = parseCSVRow(rows[i]);
            if (cols.length < 6) continue;

            var x = parseFloat(cols[ix('x', 1)]);
            var y = parseFloat(cols[ix('y', 2)]);
            if (isNaN(x) || isNaN(y)) continue;

            var attribute = (cols[ix('attribute', 5)] || '').trim();
            var category = (cols[ix('category', 8)] || '').trim();
            var catIx = ix('categories', 9);
            var categoriesJson = (catIx >= 0 && cols.length > catIx ? cols[catIx] : null) || '[]';

            var catIds = [];
            var categoriesArr = [];
            try {
                var arr = JSON.parse(categoriesJson);
                if (Array.isArray(arr)) {
                    arr.forEach(function(c) {
                        if (c && c.cat_id) {
                            catIds.push(c.cat_id);
                            categoriesArr.push(c);
                        }
                    });
                }
            } catch (e) { /* ignore */ }

            if (catIds.length === 0 && category) {
                var cid = legacyCategoryToCatId(category);
                if (cid) catIds.push(cid);
            }
            var pinItemIdsU = collectPinItemIdsFromContents(categoriesArr);
            var attrU = (attribute || '').toUpperCase();
            var styleKey = resolveFilterStyleKey(attribute);
            if (!subsetAllowsMarker(styleKey, catIds, pinItemIdsU)) continue;
            var visualStyle = pickVisualStyle(styleKey);
            var myCategories = [styleKey];
            var pinCategoryIdsU = catIds.slice();

            var objInfo = attrMappingGlobal[attribute] || attrMappingGlobal[attrU] || {};
            var pinLike = {
                // 例外表示名判定のため、オブジェクト名は attr_mapping 側を優先。
                obj_jp: (objInfo && objInfo.name_jp) || '',
                obj_en: (objInfo && objInfo.name_en) || (cols[ix('obj_name_en', 6)] || ''),
                name_jp: cols[ix('name_jp', 3)] || '',
                name_en: cols[ix('name_en', 4)] || '',
                memo_jp: cols[ix('memo_jp', 13)] || '',
                memo_en: cols[ix('memo_en', 14)] || ''
            };
            var headline = buildPinHeadline(pinLike, isJa, categoriesArr, category);
            var description = buildPinDescription(pinLike, isJa);
            var filterTT = '';
            pinLike.name_jp = cols[ix('name_jp', 3)] || '';
            pinLike.name_en = cols[ix('name_en', 4)] || '';
            pinLike.hover_tooltip = buildHoverTooltipText(pinLike, isJa, categoriesArr, category);

            var mdsIx = ix('marker_display_style', 16);
            var mdsCol = (mdsIx >= 0 && cols.length > mdsIx ? cols[mdsIx] : '').trim();
            var pin = { coords: [x, y], x: x, y: y };
            pin.hover_tooltip = pinLike.hover_tooltip;
            pin.importance = (cols[ix('importance', 10)] || '').trim();
            // popup 詳細（アイテム表示）用
            pin.contents = categoriesArr;
            pin.category = category;
            mergePinStyleFromConfig(pin, attribute, categoriesArr);
            if (mdsCol) pin.marker_display_style = normalizeMarkerDisplayStyle(mdsCol);
            var marker = createMarkerFromPin(pin, visualStyle, myCategories, null, headline, description, filterTT);
            if (!marker) continue;

            allMarkers.push({ marker: marker, categories: myCategories, pinCategoryIds: pinCategoryIdsU, pinItemIds: pinItemIdsU, rank: 'standard' });
        }

        addOverlayControls();
        updateVisibleMarkers();
    }

    /** データ JSON/CSV のブラウザキャッシュを避ける（ローカル検証でエディタ保存がすぐ反映されるように） */
    function dataCacheBust() {
        return 't=' + Date.now() + '&_=' + Math.random().toString(36).slice(2, 11);
    }

    /** 表示プリセット（view-presets.json）を読み込み適用。未指定/未取得時は built-in へフォールバック。 */
    function loadViewPresetsJson() {
        if (!presetMode) return Promise.resolve();
        var fallback = builtinPresetRule(presetMode);
        var presetUrl = (mapDiv.getAttribute('data-view-presets-url') || '').trim() || (baseUrl + 'view-presets.json');
        var sep = presetUrl.indexOf('?') >= 0 ? '&' : '?';
        return fetch(presetUrl + sep + dataCacheBust())
            .then(function (r) { return r.ok ? r.json() : null; })
            .catch(function () { return null; })
            .then(function (raw) {
                var selected = null;
                if (raw && typeof raw === 'object') {
                    if (raw.presets && typeof raw.presets === 'object') {
                        selected = raw.presets[presetMode] || null;
                    } else {
                        selected = raw[presetMode] || null;
                    }
                }
                if (!selected) selected = fallback;
                if (selected) {
                    applyViewPresetRule(selected);
                } else if (isDebug) {
                    console.warn('map.js: preset not found, mode=', presetMode);
                }
            });
    }

    function loadConfigJson() {
        var sep = baseUrl.indexOf('?') >= 0 ? '&' : '?';
        return fetch(baseUrl + 'config.json' + sep + dataCacheBust())
            .then(function (r) { return r.ok ? r.json() : null; })
            .catch(function () { return null; })
            .then(function (cfg) {
                if (cfg && cfg.pin_marker_by_attribute && typeof cfg.pin_marker_by_attribute === 'object') {
                    pinMarkerByAttribute = cfg.pin_marker_by_attribute;
                }
                if (cfg && cfg.pin_marker_by_category_id && typeof cfg.pin_marker_by_category_id === 'object') {
                    pinMarkerByCategoryId = cfg.pin_marker_by_category_id;
                }
                if (cfg && cfg.pin_marker_by_item_id && typeof cfg.pin_marker_by_item_id === 'object') {
                    pinMarkerByItemId = cfg.pin_marker_by_item_id;
                }
                if (cfg && cfg.attr_mapping && typeof cfg.attr_mapping === 'object') {
                    attrMappingGlobal = cfg.attr_mapping;
                }
                if (cfg && cfg.category_master && typeof cfg.category_master === 'object') {
                    categoryMasterGlobal = cfg.category_master;
                } else {
                    categoryMasterGlobal = {};
                }
                if (cfg && Array.isArray(cfg.category_list) && cfg.category_list.length) {
                    categoryListOrderGlobal = cfg.category_list.map(function (x) {
                        return String(x || '').trim();
                    }).filter(function (s) { return !!s; });
                } else {
                    categoryListOrderGlobal = [];
                }
                if (cfg && cfg.item_master && typeof cfg.item_master === 'object') {
                    itemMasterGlobal = cfg.item_master;
                } else {
                    itemMasterGlobal = {};
                }
                if (cfg && Array.isArray(cfg.map_object_attr_ids) && cfg.map_object_attr_ids.length) {
                    mapObjectAttrIdsOrder = cfg.map_object_attr_ids.map(function (x) {
                        return String(x || '').trim();
                    }).filter(function (s) { return !!s; });
                } else {
                    mapObjectAttrIdsOrder = null;
                }
                if (cfg && cfg.category_special_rules && typeof cfg.category_special_rules === 'object') {
                    categorySpecialRules = cfg.category_special_rules;
                } else {
                    categorySpecialRules = {};
                }
                skillNameMaster = normalizeSkillNameMaster(cfg && cfg.skill_name_master);
                rebuildVeinFilterFromAttrMapping();
                if (isDebug) {
                    console.log('map.js: config.json loaded, pin_marker attrs=', Object.keys(pinMarkerByAttribute).length);
                }
            });
    }

    // -------- エリア描画（areas.json） --------
    var areaLayer = null;
    var areaIconLayerGroup = null;
    /** フィルタ同期用: 各エリアの polygon・中央アイコン・属性メタ */
    var allAreaItems = [];
    map.createPane('areas');  // ピンより背面に配置するため専用ペインを作成
    map.getPane('areas').style.zIndex = 350;

    /** 画像座標ポリゴンの幾何学的重心（凹多角形でも実用上可） */
    function polygonCentroidImageXY(pts) {
        var n = pts.length;
        if (n < 3) return null;
        var twice = 0, cx = 0, cy = 0;
        for (var i = 0; i < n; i++) {
            var j = (i + 1) % n;
            var xi = Number(pts[i][0]), yi = Number(pts[i][1]);
            var xj = Number(pts[j][0]), yj = Number(pts[j][1]);
            if (isNaN(xi) || isNaN(yi) || isNaN(xj) || isNaN(yj)) return null;
            var cross = xi * yj - xj * yi;
            twice += cross;
            cx += (xi + xj) * cross;
            cy += (yi + yj) * cross;
        }
        if (Math.abs(twice) < 1e-9) {
            var sx = 0, sy = 0;
            for (var k = 0; k < n; k++) {
                sx += Number(pts[k][0]);
                sy += Number(pts[k][1]);
            }
            return [sx / n, sy / n];
        }
        var a = 3 * twice;
        return [cx / a, cy / a];
    }

    /** エリア中央アイコン用の画像座標（多角形=重心・円=中心・矩形=中心） */
    function areaCenterIconImageXY(a) {
        var shape = a.shape || 'polygon';
        if (shape === 'circle') {
            var cx = Number(a.x), cy = Number(a.y);
            if (isNaN(cx) || isNaN(cy)) return null;
            return [cx, cy];
        }
        if (shape === 'rect') {
            var x = Number(a.x), y = Number(a.y), w = Number(a.width), h = Number(a.height);
            if (isNaN(x) || isNaN(y) || isNaN(w) || isNaN(h)) return null;
            return [x + w / 2, y + h / 2];
        }
        var pts = a.points || [];
        return polygonCentroidImageXY(pts);
    }

    function areaWantsCenterIcon(a) {
        if (a.show_center_icon === true) return true;
        if (a.show_center_icon === false) return false;
        return !!String(a.svg_icon_id || '').trim();
    }

    /** areas.json の categories が配列／JSON文字列のどちらでも扱う */
    function areaCategoriesAsArray(area) {
        var c = area.categories;
        if (Array.isArray(c)) return c;
        if (typeof c === 'string' && c.trim()) {
            try {
                var p = JSON.parse(c.trim());
                return Array.isArray(p) ? p : [];
            } catch (e) { return []; }
        }
        return [];
    }

    /** config の pin_marker_by_attribute（＋任意でカテゴリ）からエリア中央用アイコンを解決 */
    function resolveAreaCenterIconFromMaster(area) {
        var pin = {
            svg_icon_id: '',
            svg_icon_scope: '',
            marker_icon_color: '',
            marker_bg_color: '',
            marker_display_style: 'standard'
        };
        var cats = areaCategoriesAsArray(area);
        mergePinStyleFromConfig(pin, String(area.attribute || '').trim(), cats);
        var sid = String(pin.svg_icon_id || '').trim();
        if (!sid) return null;
        var symHex = String(pin.marker_icon_color || '#ffffff').trim();
        if (!isSafeSvgIconColor(symHex)) symHex = '#ffffff';
        return { pinSvgId: sid, scope: String(pin.svg_icon_scope || '').trim(), symHex: symHex };
    }

    /** エリア JSON をピンと同じフィルタ判定用メタに変換 */
    function buildAreaFilterMetaForArea(a) {
        var attrRaw = String(a.attribute || '').trim();
        var styleKey = resolveFilterStyleKey(attrRaw);
        var myCategories = [styleKey];
        var cats = areaCategoriesAsArray(a);
        var pinCategoryIds = [];
        if (cats && cats.length) {
            cats.forEach(function (c) {
                if (c && c.cat_id) {
                    var cid = String(c.cat_id).trim();
                    if (cid && pinCategoryIds.indexOf(cid) < 0) pinCategoryIds.push(cid);
                }
            });
        }
        if (pinCategoryIds.length === 0 && a.category) {
            var legacy = String(a.category || '').trim();
            if (legacy) {
                var cmEnt = categoryMasterGlobal[legacy];
                if (cmEnt && cmEnt.id) {
                    var cidM = String(cmEnt.id).trim();
                    if (cidM) pinCategoryIds.push(cidM);
                } else {
                    var cidL = legacyCategoryToCatId(legacy);
                    if (cidL) pinCategoryIds.push(cidL);
                }
            }
        }
        var pinItemIds = collectPinItemIdsFromContents(cats);
        return {
            categories: myCategories,
            pinCategoryIds: pinCategoryIds,
            pinItemIds: pinItemIds
        };
    }

    function createAreaCenterIconMarker(a) {
        if (!areaWantsCenterIcon(a)) return null;
        var ri = resolveAreaCenterIconFromMaster(a);
        if (!ri) return null;
        var xy = areaCenterIconImageXY(a);
        if (!xy) return null;
        var latLng = map.unproject(xy, maxZoom);
        var marker = L.marker(latLng);
        attachIconOnlySvgToMarker(marker, ri.pinSvgId, ri.scope, ri.symHex);
        bindMarkerImportanceVisual(marker, a.importance);
        bindAreaPopup(marker, a);
        var name = isJa ? (a.name_jp || a.name_en || '') : (a.name_en || a.name_jp || '');
        var tt = name || (isJa ? 'エリア' : 'Area');
        marker.bindTooltip(tt, {
            direction: 'top', sticky: true, className: 'item-tooltip',
            opacity: 0.9, offset: [0, -10]
        });
        return marker;
    }

    function styleAreaPolygon(area) {
        // attribute や cat_id などからスタイルを決めてもよいが、ここではひとまず固定色系
        return {
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillColor: '#00ffff',
            fillOpacity: 0.18,
            pane: 'areas'
        };
    }

    function circlePointsFromImage(cx, cy, radius, segments) {
        var n = Math.max(16, segments || 48);
        var pts = [];
        for (var i = 0; i < n; i++) {
            var theta = (Math.PI * 2 * i) / n;
            pts.push([
                cx + radius * Math.cos(theta),
                cy + radius * Math.sin(theta)
            ]);
        }
        return pts;
    }

    function addAreasFromJson(areas) {
        if (!Array.isArray(areas)) return;
        if (areaLayer) {
            map.removeLayer(areaLayer);
            areaLayer = null;
        }
        if (areaIconLayerGroup) {
            map.removeLayer(areaIconLayerGroup);
            areaIconLayerGroup = null;
        }
        allAreaItems = [];
        if (areas.length === 0) return;
        areaLayer = L.layerGroup([], { pane: 'areas' });
        areaIconLayerGroup = L.layerGroup();

        areas.forEach(function (a) {
            if (!a) return;
            var meta = buildAreaFilterMetaForArea(a);
            var primaryObj = markerPrimaryObjectKey(meta);
            if (!subsetAllowsMarker(primaryObj, meta.pinCategoryIds, meta.pinItemIds)) return;
            var shape = a.shape || 'polygon';
            var latlngs;
            if (shape === 'circle') {
                var cx = a.x, cy = a.y, radius = a.radius;
                if (typeof cx !== 'number' || typeof cy !== 'number' || typeof radius !== 'number') return;
                if (radius <= 0) return;
                var cPts = circlePointsFromImage(cx, cy, radius, 48);
                latlngs = cPts.map(function (pt) { return map.unproject(pt, maxZoom); });
            }

            else if (shape === 'rect') {
                var x = a.x, y = a.y, w = a.width, h = a.height;
                if (typeof x !== 'number' || typeof y !== 'number' || typeof w !== 'number' || typeof h !== 'number') return;
                var rectPts = [
                    [x, y],
                    [x + w, y],
                    [x + w, y + h],
                    [x, y + h]
                ];
                latlngs = rectPts.map(function (pt) { return map.unproject(pt, maxZoom); });
            } else {
                var pts = a.points || [];
                if (!Array.isArray(pts) || pts.length < 3) return;
                latlngs = pts.map(function (pt) {
                    if (!Array.isArray(pt) || pt.length < 2) return null;
                    return map.unproject([pt[0], pt[1]], maxZoom);
                }).filter(Boolean);
            }

            if (!latlngs || latlngs.length < 3) return;
            var poly = L.polygon(latlngs, styleAreaPolygon(a));
            bindAreaPopup(poly, a);
            var iconMarker = createAreaCenterIconMarker(a);
            areaLayer.addLayer(poly);
            if (iconMarker) areaIconLayerGroup.addLayer(iconMarker);
            allAreaItems.push({
                poly: poly,
                iconMarker: iconMarker,
                categories: meta.categories,
                pinCategoryIds: meta.pinCategoryIds,
                pinItemIds: meta.pinItemIds
            });
        });

        areaLayer.addTo(map);
        areaIconLayerGroup.addTo(map);
        updateVisibleAreas();
    }

    function bindAreaPopup(layer, area) {
        var name = isJa ? (area.name_jp || area.name_en || '') : (area.name_en || area.name_jp || '');
        var memo = isJa ? (area.memo_jp || '') : (area.memo_en || area.memo_jp || '');
        var title = name || (isJa ? 'エリア' : 'Area');
        var html = '<div style="font-family:sans-serif;min-width:180px;">' +
            '<div style="font-size:14px;font-weight:bold;margin-bottom:4px;border-bottom:1px solid #ccc;padding-bottom:4px;">' +
            title + '</div>';
        if (memo) {
            html += '<div style="font-size:12px;color:#444;background:#f4f4f4;padding:5px;border-radius:3px;line-height:1.4;">' +
                String(memo).replace(/<br\s*\/?>/g, '<br>') + '</div>';
        }
        html += '</div>';
        layer.bindPopup(html);
    }

    function loadAreas() {
        var areasUrl = baseUrl + 'areas.json';
        return fetch(areasUrl + (areasUrl.indexOf('?') >= 0 ? '&' : '?') + dataCacheBust())
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function (data) {
                var areas = data && data.areas ? data.areas : (Array.isArray(data) ? data : []);
                addAreasFromJson(areas);
            })
            .catch(function (e) {
                // areas.json が無くても致命的ではないので warn のみにする
                if (isDebug) console.warn('map.js: areas.json load failed or not found', e);
            });
    }

    // config.json を先に読み、CSV 経路でも pin_marker_by_attribute で SVG を付与できるようにする
    function startPinLoad() {
        // data-pins 指定時は pins_export.json を優先
        if (customPins !== null && customPins !== '') {
            fetch(pinsJsonUrl + (pinsJsonUrl.indexOf('?') >= 0 ? '&' : '?') + dataCacheBust())
                .then(function(r) { if (!r.ok) throw new Error(r.status); return r.json(); })
                .then(function(data) {
                    var pins = data && data.pins ? data.pins : (Array.isArray(data) ? data : []);
                    addMarkersFromPins(pins);
                    return loadAreas();
                })
                .catch(function(e) {
                    console.warn('map.js: pins_export.json load failed, falling back to CSV', e);
                    return fetch(csvUrl + (csvUrl.indexOf('?') >= 0 ? '&' : '?') + dataCacheBust()).then(function(r) { if (!r.ok) throw new Error(r.status); return r.text(); });
                })
                .then(function(text) {
                    if (typeof text === 'string') {
                        loadFromCSV(text);
                        return loadAreas();
                    }
                })
                .catch(function(e) { console.error('map.js:', e); });
        } else {
            fetch(csvUrl + (csvUrl.indexOf('?') >= 0 ? '&' : '?') + dataCacheBust())
                .then(function(r) { if (!r.ok) throw new Error(r.status); return r.text(); })
                .then(function (text) {
                    loadFromCSV(text);
                    return loadAreas();
                })
                .catch(function(e) {
                    console.error('map.js: Failed to load pins. csvUrl=', csvUrl, e);
                });
        }
    }

    loadViewPresetsJson().then(loadConfigJson).then(startPinLoad);
    if (isDebug) {
        console.log('map.js (vein world map): baseUrl=', baseUrl, 'csvUrl=', csvUrl, 'pinsJsonUrl=', pinsJsonUrl, 'showAllPins=', showAllPins);
    }
})();
