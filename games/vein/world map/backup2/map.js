(function() {
    'use strict';
    // map.js v20260216 - 全部用: 複数アイテム・戦時債権数量・換金ポイント表示

    var maxZoom = 5;
    var imgW = 6253;
    var imgH = 7104;
    var mapPadding = 1500;

    var mapDiv = document.getElementById('game-map');
    if (!mapDiv) {
        console.error('map.js: #game-map element not found');
        return;
    }

    // 設定読み込み
    var showLabels = mapDiv.getAttribute('data-show-labels') === 'true';
    var htmlZoom = parseInt(mapDiv.getAttribute('data-zoom'), 10);
    var defaultZoom = (!isNaN(htmlZoom)) ? htmlZoom : 2;
    var filterMode = mapDiv.getAttribute('data-filter');
    var customCsv = mapDiv.getAttribute('data-csv');
    var customPins = mapDiv.getAttribute('data-pins');  // pins_export.json 用
    // テスト用: 未指定時は「その他」等も表示（本番 embed では付けない想定）
    var showAllPins = mapDiv.getAttribute('data-show-all-pins') === 'true';

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
    var tileUrl = 'https://lost-in-games.com/starrupture-map/tiles/{z}/{x}/{y}.webp?v=20260111_FINAL3';

    var isJa = (document.documentElement.lang || navigator.language || '').toLowerCase().indexOf('ja') === 0;
    var isDebug = new URLSearchParams(window.location.search).get('debug') === 'true';

    // スタイル定義（cat_id / オブジェクト種別 → 表示）
    var styles = {
        scanner:   { emoji: '📡', color: '#2ecc71', label: isJa ? 'ジオスキャナー' : 'Geo Scanner' },
        start:     { emoji: '🚀', color: '#ffffff', label: isJa ? '開始地点' : 'Start Point' },
        blueprint: { emoji: '📜', color: '#3498db', label: isJa ? '設計図' : 'Blueprints' },
        warbond:   { emoji: '💀', color: '#e74c3c', label: isJa ? '戦時債権' : 'War Bonds' },
        war_bonds: { emoji: '💀', color: '#e74c3c', label: isJa ? '戦時債権' : 'War Bonds' },
        point:     { emoji: '💎', color: '#f1c40f', label: isJa ? '換金アイテム' : 'Cash Items' },
        trade_item:{ emoji: '💎', color: '#f1c40f', label: isJa ? '換金アイテム' : 'Cash Items' },
        lem:       { emoji: '⚡', color: '#9b59b6', label: isJa ? 'LEM' : 'LEM Gear' },
        cave:      { emoji: '⛏️', color: '#7f8c8d', label: isJa ? '地下洞窟' : 'Caves' },
        monolith:  { emoji: '🗿', color: '#1abc9c', label: isJa ? 'モノリス' : 'Monoliths' },
        other:     { emoji: '📦', color: '#95a5a6', label: isJa ? 'その他' : 'Others' },
        trash:     { emoji: '❌', color: '#555555', label: isJa ? '調査済み(空)' : 'Checked(Empty)' }
    };

    // オブジェクトID（attribute）→ スタイルキー（ランドマークなど外形で決まるもの）
    var attrToStyle = {
        'GEO_SCANNER': 'scanner',
        'SPACESHIP': 'start',
        'UNDERGROUND_CAVE': 'cave',
        'MONOLITH': 'monolith',
        'COLONY': 'other',
        'DRONE_WRECK': 'other',
        'RUBBLE_PILE': 'other',
        'PERSONAL_STORAGE': 'other',
        'CONSOLE': 'other',
        'ITEM_PRINTER': 'other',
        'SEARCH': 'other',
        'KEYCARD': 'other'
    };

    // cat_id → スタイルキー
    var catIdToStyle = {
        'blueprint': 'blueprint',
        'lem': 'lem',
        'war_bonds': 'warbond',
        'trade_item': 'point',
        'keycard': 'other',
        'plant': 'other'
    };

    // オブジェクトID（attribute）→ ポップアップ用表示名
    var attrToDisplayName = {
        'DEAD_BODY': { jp: '遺体', en: 'Dead Body' },
        'STORAGE_BOX': { jp: 'ストレージボックス', en: 'Storage Box' },
        'DRONE_WRECK': { jp: 'ドローンの残骸', en: 'Drone Wreck' },
        'RUBBLE_PILE': { jp: 'がれきの山', en: 'Rubble Pile' },
        'PERSONAL_STORAGE': { jp: 'パーソナルストレージ', en: 'Personal Storage' },
        'CONSOLE': { jp: 'コンソール', en: 'Console' },
        'UNDERGROUND_CAVE': { jp: '地下洞窟', en: 'Underground Cave' },
        'MONOLITH': { jp: 'モノリス', en: 'Monolith' },
        'GEO_SCANNER': { jp: 'ジオスキャナー', en: 'Geo Scanner' },
        'SPACESHIP': { jp: '宇宙船', en: 'Spaceship' },
        'COLONY': { jp: '群生地', en: 'Colony' },
        'ITEM_PRINTER': { jp: 'アイテムプリンター', en: 'Item Printer' },
        'SEARCH': { jp: 'サーチ', en: 'Search' },
        'KEYCARD': { jp: 'キーカード', en: 'Keycard' }
    };

    window.map = L.map('game-map', {
        crs: L.CRS.Simple,
        minZoom: 0,
        maxZoom: maxZoom,
        zoom: defaultZoom,
        maxBoundsViscosity: 0.8,
        preferCanvas: true
    });

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
    map.setZoom(defaultZoom);

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
        var mp = markerPx || 56;
        var baseOnly = buildPinStackSvg('', symColor);
        var href = escapeHtmlAttr(iconSrcWithBust);
        return '<div class="demo-pin-composite" style="position:relative;width:' + mp + 'px;height:' + mp + 'px;display:block;">' +
            '<div class="demo-svg-inner" style="' +
            'color:' + escapeHtmlAttr(pinBgColor) + ';' +
            'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;' +
            'line-height:0;background:transparent;">' + baseOnly + '</div>' +
            '<img src="' + href + '" alt="" decoding="async" draggable="false" ' +
            'class="demo-pin-icon-img" ' +
            'style="position:absolute;left:50%;top:50%;width:24px;height:24px;max-width:24px;max-height:24px;' +
            'transform:translate(-50%,-50%);object-fit:contain;box-sizing:border-box;pointer-events:none;z-index:2;"/>' +
            '</div>';
    }

    /** Leaflet iconAnchor: マップ座標を viewBox (24,47) の尻尾先に合わせる（48×48 ピンSVG） */
    function leafletPinAnchorAtTail(markerPx) {
        var mp = markerPx || 56;
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
                html: html,
                className: 'demo-svg-icon demo-pin-zoom-adapt',
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
    var blueprintCount = 0;
    var currentRankFilter = 'all';

    Object.keys(styles).forEach(function(key) {
        if (key === 'trash' && !isDebug) return;
        if (key === 'war_bonds') return;  // warbond と重複
        if (key === 'trade_item') return; // point と重複

        if (filterMode) {
            if (key === filterMode || key === 'war_bonds' && filterMode === 'warbond' || key === 'trade_item' && filterMode === 'point') {
                activeCategories.add(key);
            }
            if ((filterMode === 'blueprint' || filterMode === 'lem') && key === 'start') {
                activeCategories.add(key);
            }
        } else if (showAllPins) {
            if (key === 'trash' && !isDebug) return;
            if (key === 'war_bonds' || key === 'trade_item') return;
            activeCategories.add(key);
        } else {
            var hiddenKeys = ['monolith', 'scanner', 'cave', 'other', 'point', 'trade_item', 'war_bonds'];
            if (!hiddenKeys.includes(key)) activeCategories.add(key);
        }
    });

    function getRank(text) {
        if (!text) return 'standard';
        var s = String(text).toLowerCase();
        if (s.indexOf('greater') >= 0 || s.indexOf('上級') >= 0) return 'greater';
        if (s.indexOf('lesser') >= 0 || s.indexOf('下級') >= 0) return 'lesser';
        return 'standard';
    }

    // LEM表示名をランク付きで整形: 上級→接頭辞付き, 下級→接頭辞付き, 中級/接頭語なし→接頭辞なし
    function formatLemDisplayName(itemNameJp, itemNameEn, rank, isJa) {
        var baseJp = (itemNameJp || '').replace(/LEM\s*$/, '');
        var baseEn = (itemNameEn || '').replace(/\s*LEM\s*$/i, '').trim();
        var suffixJp = 'LEM', suffixEn = ' LEM';
        var rankVal = (rank && typeof rank === 'object' ? rank['ランク'] : rank) || '';
        var displayJp, displayEn;
        if (rankVal === '上級') {
            displayJp = '上級' + baseJp + suffixJp;
            displayEn = 'Greater ' + baseEn + suffixEn;
        } else if (rankVal === '下級') {
            displayJp = '下級' + baseJp + suffixJp;
            displayEn = 'Lesser ' + baseEn + suffixEn;
        } else {
            displayJp = baseJp + suffixJp;
            displayEn = baseEn + suffixEn;
        }
        return isJa ? displayJp : displayEn;
    }

    function updateVisibleMarkers() {
        allMarkers.forEach(function(item) {
            var isCatMatch = item.categories.some(function(cat) { return activeCategories.has(cat); });
            var isRankMatch = (currentRankFilter === 'all') ||
                (item.categories.indexOf('start') >= 0) ||
                (item.rank === currentRankFilter);

            if (isCatMatch && isRankMatch) {
                if (!map.hasLayer(item.marker)) {
                    item.marker.addTo(map);
                    if (showLabels && item.marker.openTooltip) item.marker.openTooltip();
                }
            } else {
                if (map.hasLayer(item.marker)) map.removeLayer(item.marker);
            }
        });
    }

    /** エディター svg_icon_assets.replace_current_color と同じ契約（currentColor → 指定色） */
    function replaceSvgCurrentColor(svgText, hex) {
        var h = String(hex || '#ffffff').trim();
        if (!/^#[0-9a-fA-F]{6}$/.test(h)) h = '#ffffff';
        return String(svgText).replace(/currentColor/gi, h);
    }

    var jsonMarkerPxRaw = parseInt(mapDiv.getAttribute('data-demo-pin-marker-size'), 10);
    var JSON_PIN_MARKER_PX = (!isNaN(jsonMarkerPxRaw) && jsonMarkerPxRaw >= 44 && jsonMarkerPxRaw <= 80) ? jsonMarkerPxRaw : 56;
    var JSON_PIN_ANCHOR = leafletPinAnchorAtTail(JSON_PIN_MARKER_PX);

    function svgIconUrlCandidates(pinSvgId, scope) {
        var idPart = encodeURIComponent(pinSvgId) + '.svg';
        var list = [];
        if (scope === 'common' && svgIconsCommonBase) {
            list.push(svgIconsCommonBase.replace(/\/?$/, '/') + idPart);
        }
        list.push(baseUrl + 'assets/icons/' + idPart);
        if (scope !== 'common' && svgIconsCommonBase) {
            list.push(svgIconsCommonBase.replace(/\/?$/, '/') + idPart);
        }
        return list;
    }

    function fetchFirstSvgAsObjectUrl(urls, index, bust, symHex, done, fail) {
        if (index >= urls.length) {
            fail();
            return;
        }
        var u = urls[index];
        var sep = u.indexOf('?') >= 0 ? '&' : '?';
        fetch(u + sep + bust)
            .then(function (r) {
                if (!r.ok) throw new Error('bad status');
                return r.text();
            })
            .then(function (text) {
                text = String(text).replace(/<script[\s\S]*?<\/script>/gi, '');
                var patched = replaceSvgCurrentColor(text, symHex);
                var blob = new Blob([patched], { type: 'image/svg+xml;charset=utf-8' });
                done(URL.createObjectURL(blob));
            })
            .catch(function () {
                fetchFirstSvgAsObjectUrl(urls, index + 1, bust, symHex, done, fail);
            });
    }

    function cleanTextForFilter(text, mode) {
        if (!mode || !text) return text;
        var keywords = {
            'blueprint': ['設計図', 'Blueprint', 'Recipe'],
            'lem': ['LEM'],
            'warbond': ['戦時', 'Warbond'],
            'scanner': ['スキャナー', 'Scanner']
        };
        var targetKeys = keywords[mode];
        if (!targetKeys) return text;
        var lines = String(text).split(/\r\n|\n|\r|<br>/);
        var filtered = lines.filter(function(line) {
            return targetKeys.some(function(k) { return line.indexOf(k) >= 0; });
        });
        return filtered.length > 0 ? filtered.join('<br>') : '';
    }

    function createMarkerFromPin(pin, visualStyle, myCategories, bpNum, displayName, memo, rawText, tooltipLabelText, objectName, contentsSummary) {
        var coords = pin.coords || [pin.x, pin.y];
        var x = coords[0], y = coords[1];
        if (typeof x !== 'number' || typeof y !== 'number') return null;

        var latLng = map.unproject([x, y], maxZoom);
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
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });

        var marker = L.marker(latLng, { icon: emojiIcon });

        if (pinSvgId && typeof wrapPinBasePlusImgIcon === 'function') {
            var scope = pin.svg_icon_scope || '';
            var candidates = svgIconUrlCandidates(pinSvgId, scope);
            var bust = 't=' + Date.now();
            fetchFirstSvgAsObjectUrl(
                candidates,
                0,
                bust,
                symHex,
                function (objUrl) {
                    var innerHtml = wrapPinBasePlusImgIcon(pinBg, objUrl, symHex, JSON_PIN_MARKER_PX);
                    marker.setIcon(
                        L.divIcon({
                            html: innerHtml,
                            className: 'map-pin-svg-composite demo-pin-zoom-adapt',
                            iconSize: [JSON_PIN_MARKER_PX, JSON_PIN_MARKER_PX],
                            iconAnchor: JSON_PIN_ANCHOR
                        })
                    );
                },
                function () {
                    if (isDebug) console.warn('[map.js] svg_icon fetch failed', pinSvgId, candidates);
                }
            );
        }

        var popupTitle = (objectName && String(objectName).trim()) ? objectName : displayName;
        var popupSub = (contentsSummary && String(contentsSummary).trim()) ? contentsSummary : '';
        var popupHtml = '<div style="font-family:sans-serif;min-width:180px;">' +
            '<div style="font-size:14px;font-weight:bold;margin-bottom:4px;border-bottom:1px solid #ccc;padding-bottom:4px;">' + popupTitle + '</div>';
        if (popupSub) {
            popupHtml += '<div style="font-size:12px;color:#333;margin-bottom:4px;">' + popupSub + '</div>';
        }
        if (memo) {
            popupHtml += '<div style="font-size:12px;color:#444;background:#f4f4f4;padding:5px;border-radius:3px;line-height:1.4;">' + memo + '</div>';
        }
        popupHtml += '</div>';
        marker.bindPopup(popupHtml);

        // フィルタモード時: tooltipLabelText を優先。全部用時: contentsSummary があればそのプレーンテキスト版をツールチップに（複数アイテムを一覧表示）
        var tooltipText;
        if (filterMode) {
            tooltipText = tooltipLabelText || displayName || cleanTextForFilter(rawText, filterMode);
        } else {
            var summaryPlain = (contentsSummary && String(contentsSummary).trim()) ? contentsSummary.replace(/<br\s*\/?>\s*・?/g, ', ') : '';
            tooltipText = summaryPlain || rawText;
        }
        if (!tooltipText || String(tooltipText).trim() === '') {
            tooltipText = rawText || visualStyle.label || '—';
        }
        var tooltipOpts = showLabels ? {
            permanent: true, direction: 'top', className: 'item-tooltip-permanent',
            opacity: 0.9, offset: [0, -20]
        } : {
            direction: 'top', sticky: true, className: 'item-tooltip',
            opacity: 0.9, offset: [0, -10]
        };
        marker.bindTooltip(tooltipText, tooltipOpts);

        return marker;
    }

    function addMarkersFromPins(pins) {
        if (!Array.isArray(pins)) return;

        pins.forEach(function(pin) {
            var coords = pin.coords || [pin.x, pin.y];
            var x = parseFloat(coords[0]), y = parseFloat(coords[1]);
            if (isNaN(x) || isNaN(y)) return;

            var objId = (pin.obj_id || pin.attribute || '').toUpperCase();
            var contents = pin.contents || [];
            var catIds = contents.map(function(c) { return c.cat_id; }).filter(Boolean);
            if (catIds.length === 0 && pin.category) {
                var catMap = { '設計図': 'blueprint', 'LEM': 'lem', '戦時債権': 'war_bonds', '交換アイテム': 'trade_item', 'キーカード': 'keycard', '植物': 'plant' };
                var cid = catMap[pin.category] || pin.category;
                if (cid) catIds.push(cid);
            }

            var styleKey = attrToStyle[objId] || null;
            if (!styleKey && catIds.length > 0) {
                styleKey = catIdToStyle[catIds[0]] || 'other';
            }
            if (!styleKey) styleKey = 'other';

            var visualStyle = styles[styleKey] || styles.other;
            var myCategories = [styleKey];
            catIds.forEach(function(cid) {
                var sk = catIdToStyle[cid] || cid;
                if (myCategories.indexOf(sk) < 0) myCategories.push(sk);
            });

            var isBlueprint = (styleKey === 'blueprint');
            var bpNum = (isBlueprint && filterMode === 'blueprint') ? ++blueprintCount : null;
            var name = isJa ? (pin.obj_jp || pin.name_jp || pin.name) : (pin.obj_en || pin.name_en || pin.name_jp || pin.name || '');

            var blueprintNamesFromContents = [];
            var lemNamesFromContents = [];
            if (filterMode === 'blueprint' && contents && contents.length > 0) {
                contents.forEach(function(c) {
                    if (c.cat_id === 'blueprint' && (c.item_jp || c.item_en || c.item_name_jp || c.item_name_en)) {
                        var bpName = isJa ? (c.item_jp || c.item_name_jp || c.item_en || c.item_name_en) : (c.item_en || c.item_name_en || c.item_jp || c.item_name_jp);
                        blueprintNamesFromContents.push(bpName);
                    }
                });
            }
            if (filterMode === 'lem' && contents && contents.length > 0) {
                contents.forEach(function(c) {
                    if (c.cat_id === 'lem' && (c.item_jp || c.item_en || c.item_name_jp || c.item_name_en)) {
                        var jp = c.item_name_jp || c.item_jp;
                        var en = c.item_name_en || c.item_en;
                        var attrs = c.attributes || c.props || {};
                        var rank = attrs['ランク'] || '';
                        lemNamesFromContents.push(formatLemDisplayName(jp, en, rank, isJa));
                    }
                });
            }
            var nameForLabel = lemNamesFromContents.length > 0 ? lemNamesFromContents.join(', ') : (blueprintNamesFromContents.length > 0 ? blueprintNamesFromContents.join(', ') : name);

            var displayName = name;
            var memo = isJa ? (pin.memo_jp || '') : (pin.memo_en || pin.memo_jp || '');
            var rawText = memo || name;
            var tooltipLabelText = filterMode ? (filterMode === 'lem' ? nameForLabel : (visualStyle.label + '：' + nameForLabel)) : '';

            var objNameMap = attrToDisplayName[objId];
            var objectName = (pin.obj_jp || pin.obj_en) ? (isJa ? (pin.obj_jp || pin.obj_en) : (pin.obj_en || pin.obj_jp)) : (objNameMap ? (isJa ? objNameMap.jp : objNameMap.en) : name);
            var contentsSummary;
            if (filterMode === 'lem') {
                contentsSummary = lemNamesFromContents.length > 1 ? lemNamesFromContents.join('<br>・') : (lemNamesFromContents.length === 1 ? lemNamesFromContents[0] : nameForLabel);
            } else if (filterMode === 'blueprint') {
                contentsSummary = blueprintNamesFromContents.length > 1 ? (visualStyle.label + '：<br>・' + blueprintNamesFromContents.join('<br>・')) : (blueprintNamesFromContents.length === 1 ? (visualStyle.label + '：' + blueprintNamesFromContents[0]) : (nameForLabel ? visualStyle.label + '：' + nameForLabel : name));
            } else {
                contentsSummary = (contents && contents.length > 0) ? formatAllContentsForPopup(contents, isJa) : name;
            }
            if (!contentsSummary) contentsSummary = name;

            var marker = createMarkerFromPin(pin, visualStyle, myCategories, bpNum, displayName, memo, rawText, tooltipLabelText, objectName, contentsSummary);
            if (!marker) return;

            var itemRank = getRank(JSON.stringify(pin));
            allMarkers.push({ marker: marker, categories: myCategories, rank: itemRank });
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

    function addOverlayControls() {
        var overlayMaps = {};
        Object.keys(styles).forEach(function(key) {
            if (key === 'trash' && !isDebug) return;
            if (key === 'war_bonds' || key === 'trade_item') return;
            var lbl = styles[key].label;
            overlayMaps[lbl] = L.layerGroup();
            if (activeCategories.has(key)) overlayMaps[lbl].addTo(map);
        });

        if (!filterMode) {
            L.control.layers(null, overlayMaps, { collapsed: false, position: 'topright' }).addTo(map);
        }

        map.on('overlayadd', function(e) {
            var key = Object.keys(styles).find(function(k) { return styles[k].label === e.name; });
            if (key) { activeCategories.add(key); updateVisibleMarkers(); }
        });
        map.on('overlayremove', function(e) {
            var key = Object.keys(styles).find(function(k) { return styles[k].label === e.name; });
            if (key) { activeCategories.delete(key); updateVisibleMarkers(); }
        });
    }

    // ランクフィルター（LEM等）
    if (!filterMode || filterMode === 'lem') {
        var rankControl = L.control({ position: 'bottomright' });
        rankControl.onAdd = function() {
            var div = L.DomUtil.create('div', 'rank-filter-control');
            div.style.cssText = 'background:rgba(255,255,255,0.9);padding:5px;border-radius:4px;box-shadow:0 1px 5px rgba(0,0,0,0.4);display:flex;gap:5px;margin-right:10px;margin-bottom:10px;';
            div.innerHTML = '<style>.rank-btn{border:1px solid #ccc;background:#fff;padding:2px 8px;cursor:pointer;border-radius:3px;font-size:12px;font-weight:bold;color:#333}.rank-btn.active{background:#333;color:#fff;border-color:#000}</style>' +
                '<button class="rank-btn active" data-rank="all">ALL</button>' +
                '<button class="rank-btn" data-rank="greater" style="color:#e67e22">Greater</button>' +
                '<button class="rank-btn" data-rank="standard">Standard</button>' +
                '<button class="rank-btn" data-rank="lesser" style="color:#7f8c8d">Lesser</button>';
            var btns = div.querySelectorAll('.rank-btn');
            for (var i = 0; i < btns.length; i++) {
                (function(btn) {
                    btn.addEventListener('click', function(e) {
                        btns.forEach(function(b) { b.classList.remove('active'); });
                        e.target.classList.add('active');
                        currentRankFilter = e.target.getAttribute('data-rank');
                        updateVisibleMarkers();
                        L.DomEvent.stopPropagation(e);
                    });
                })(btns[i]);
            }
            L.DomEvent.disableClickPropagation(div);
            return div;
        };
        rankControl.addTo(map);
    }

    function formatContentsSummaryForPopup(label, names) {
        if (!names || names.length === 0) return '';
        if (names.length === 1) return label + '：' + names[0];
        return label + '：<br>・' + names.join('<br>・');
    }

    // 全部用: 全スロットを表示（複数アイテム・戦時債権は数量・換金はポイント表示）
    function formatAllContentsForPopup(contentsArr, isJa) {
        if (!contentsArr || contentsArr.length === 0) return '';
        var lines = [];
        contentsArr.forEach(function(c) {
            if (!c || !c.cat_id) return;
            var styleKey = catIdToStyle[c.cat_id] || c.cat_id || 'other';
            var label = (styles[styleKey] || styles.other).label;
            var itemName = isJa ? (c.item_name_jp || c.item_name_en || '') : (c.item_name_en || c.item_name_jp || '');
            var attrs = c.attributes || c.props || {};
            var qtyStr = c.qty != null && c.qty !== '' ? String(c.qty) : '1';
            if (c.cat_id === 'war_bonds') {
                lines.push((itemName || label) + ' x' + qtyStr);
            } else if (c.cat_id === 'trade_item') {
                var pt = attrs['ポイント'];
                lines.push(itemName + (pt != null && pt !== '' ? ' ' + pt + 'pt' : ''));
            } else if (c.cat_id === 'lem') {
                lines.push(formatLemDisplayName(c.item_name_jp, c.item_name_en, attrs['ランク'], isJa));
            } else {
                lines.push(label + '：' + (itemName || '—'));
            }
        });
        return lines.join('<br>・');
    }

    function loadFromCSV(text) {
        var rawText = text.trim();
        if (rawText.charCodeAt(0) === 0xFEFF) rawText = rawText.slice(1);
        var rows = rawText.split('\n');
        if (rows.length < 2) return;

        for (var i = 1; i < rows.length; i++) {
            var rawRow = rows[i];
            var cols = parseCSVRow(rows[i]);
            if (cols.length < 6) continue;

            var x = parseFloat(cols[1]);
            var y = parseFloat(cols[2]);
            if (isNaN(x) || isNaN(y)) continue;

            var attribute = (cols[5] || '').trim();
            var category = (cols[8] || '').trim();
            var categoriesJson = (cols.length > 9 ? cols[9] : null) || '[]';

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
                var catMap = { '設計図': 'blueprint', 'LEM': 'lem', '戦時債権': 'war_bonds', '交換アイテム': 'trade_item', 'キーカード': 'keycard', '植物': 'plant' };
                var cid = catMap[category] || category;
                if (cid) catIds.push(cid);
            }

            var styleKey = attrToStyle[attribute] || null;
            if (!styleKey && catIds.length > 0) {
                styleKey = catIdToStyle[catIds[0]] || 'other';
            }
            if (!styleKey) styleKey = 'other';

            var visualStyle = styles[styleKey] || styles.other;
            var myCategories = [styleKey];
            catIds.forEach(function(cid) {
                var sk = catIdToStyle[cid] || cid;
                if (myCategories.indexOf(sk) < 0) myCategories.push(sk);
            });

            var isBlueprint = (styleKey === 'blueprint');
            var bpNum = (isBlueprint && filterMode === 'blueprint') ? ++blueprintCount : null;
            var name = isJa ? (cols[3] || '') : (cols[4] || cols[3] || '');

            var blueprintNames = [];
            var lemNames = [];
            if (filterMode === 'blueprint' && categoriesArr.length > 0) {
                categoriesArr.forEach(function(c) {
                    if (c.cat_id === 'blueprint' && (c.item_name_jp || c.item_name_en)) {
                        blueprintNames.push(isJa ? (c.item_name_jp || c.item_name_en) : (c.item_name_en || c.item_name_jp));
                    }
                });
            }
            if (filterMode === 'lem' && categoriesArr.length > 0) {
                categoriesArr.forEach(function(c) {
                    if (c.cat_id === 'lem' && (c.item_name_jp || c.item_name_en)) {
                        var rank = (c.attributes && c.attributes['ランク']) || '';
                        lemNames.push(formatLemDisplayName(c.item_name_jp, c.item_name_en, rank, isJa));
                    }
                });
            }
            var nameForLabel = lemNames.length > 0 ? lemNames.join(', ') : (blueprintNames.length > 0 ? blueprintNames.join(', ') : name);

            var displayName = name;
            var memo = isJa ? (cols[13] || '') : (cols[14] || cols[13] || '');
            var rawText = memo || name;
            var tooltipLabelText = filterMode ? (filterMode === 'lem' ? nameForLabel : (visualStyle.label + '：' + nameForLabel)) : '';

            var objNameMap = attrToDisplayName[attribute];
            var objectName = objNameMap ? (isJa ? objNameMap.jp : objNameMap.en) : name;
            var contentsSummary;
            if (filterMode === 'lem') {
                contentsSummary = lemNames.length > 1 ? lemNames.join('<br>・') : (lemNames.length === 1 ? lemNames[0] : (nameForLabel || ''));
            } else if (filterMode === 'blueprint') {
                contentsSummary = formatContentsSummaryForPopup(visualStyle.label, blueprintNames);
                if (contentsSummary === '' && nameForLabel) contentsSummary = visualStyle.label + '：' + nameForLabel;
            } else if (filterMode) {
                contentsSummary = formatContentsSummaryForPopup(visualStyle.label, blueprintNames);
                if (contentsSummary === '' && nameForLabel) contentsSummary = visualStyle.label + '：' + nameForLabel;
            } else {
                contentsSummary = categoriesArr.length > 0 ? formatAllContentsForPopup(categoriesArr, isJa) : name;
            }

            var pin = { coords: [x, y], x: x, y: y };
            var marker = createMarkerFromPin(pin, visualStyle, myCategories, bpNum, displayName, memo, rawText, tooltipLabelText, objectName, contentsSummary);
            if (!marker) continue;

            var itemRank = getRank(rawRow);
            allMarkers.push({ marker: marker, categories: myCategories, rank: itemRank });
        }

        addOverlayControls();
        updateVisibleMarkers();
    }

    var cacheBuster = 't=' + Date.now();

    // -------- エリア描画（areas.json） --------
    var areaLayer = null;
    map.createPane('areas');  // ピンより背面に配置するため専用ペインを作成
    map.getPane('areas').style.zIndex = 350;

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
        if (!Array.isArray(areas) || areas.length === 0) return;
        if (areaLayer) {
            map.removeLayer(areaLayer);
        }
        areaLayer = L.layerGroup([], { pane: 'areas' });

        areas.forEach(function (a) {
            if (!a) return;
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
            areaLayer.addLayer(poly);
        });

        areaLayer.addTo(map);
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
        return fetch(areasUrl + (areasUrl.indexOf('?') >= 0 ? '&' : '?') + cacheBuster)
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

    // data-pins 指定時は pins_export.json を優先
    if (customPins !== null && customPins !== '') {
        fetch(pinsJsonUrl + (pinsJsonUrl.indexOf('?') >= 0 ? '&' : '?') + cacheBuster)
            .then(function(r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function(data) {
                var pins = data && data.pins ? data.pins : (Array.isArray(data) ? data : []);
                addMarkersFromPins(pins);
                return loadAreas();
            })
            .catch(function(e) {
                console.warn('map.js: pins_export.json load failed, falling back to CSV', e);
                return fetch(csvUrl + '?' + cacheBuster).then(function(r) { if (!r.ok) throw new Error(r.status); return r.text(); });
            })
            .then(function(text) {
                if (typeof text === 'string') {
                    loadFromCSV(text);
                    return loadAreas();
                }
            })
            .catch(function(e) { console.error('map.js:', e); });
    } else {
        fetch(csvUrl + '?' + cacheBuster)
            .then(function(r) { if (!r.ok) throw new Error(r.status); return r.text(); })
            .then(function (text) {
                loadFromCSV(text);
                return loadAreas();
            })
            .catch(function(e) {
                console.error('map.js: Failed to load pins. csvUrl=', csvUrl, e);
            });
    }
    if (isDebug) {
        console.log('map.js (none_test): baseUrl=', baseUrl, 'csvUrl=', csvUrl, 'pinsJsonUrl=', pinsJsonUrl, 'showAllPins=', showAllPins);
    }
})();
