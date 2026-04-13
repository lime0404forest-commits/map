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
        st.textContent = '.map-pin-leaflet-shell{background:transparent!important;border:none!important;}';
        document.head.appendChild(st);
    })();

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
    var tileUrl = baseUrl + 'tiles/{z}/{x}/{y}.webp';

    var isJa = (document.documentElement.lang || navigator.language || '').toLowerCase().indexOf('ja') === 0;
    var isDebug = new URLSearchParams(window.location.search).get('debug') === 'true';

    // レイヤーフィルター用（config.attr_mapping から再構築）
    var styles = {};
    var attrToStyle = {};
    /** VEIN: ピン表示グルーピングはオブジェクト(attribute)のみ。カテゴリ cat_id はフィルターに混ぜない。 */
    var catIdToStyle = {};

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
            if (fm) {
                if (key.toUpperCase() === fm.toUpperCase()) activeCategories.add(key);
                return;
            }
            activeCategories.add(key);
        });
    }

    /** config.json 読込後: オブジェクトマスタ1件 = フィルター1項目（絵文字・色は type に応じた既定） */
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
                label: isJa ? labelJa : labelEn
            };
            attrToStyle[attrId] = attrId;
            attrToStyle[String(attrId).toUpperCase()] = attrId;
        });
        styles.other = styles.other || {
            emoji: TYPE_EMOJI.other,
            color: '#7f8c8d',
            label: isJa ? 'その他' : 'Other'
        };
        if (isDebug) {
            styles.trash = { emoji: '❌', color: '#555555', label: isJa ? '調査済み(空)' : 'Checked(Empty)' };
        }
        initActiveCategoriesForVein();
    }

    function resolveFilterStyleKey(rawAttr) {
        var a = String(rawAttr || '').trim();
        if (!a) return 'other';
        if (styles[a]) return a;
        var u = a.toUpperCase();
        if (attrToStyle[u]) return attrToStyle[u];
        if (attrToStyle[a]) return attrToStyle[a];
        return 'other';
    }

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

    /** Leaflet が .leaflet-marker-icon に transform: translate3d を直指定するため、embed の scale は子要素に掛ける */
    var MAP_PIN_LEAFLET_SHELL = 'map-pin-leaflet-shell';
    function wrapDivIconZoomScale(innerHtml, zoomSurfaceClass, transformOrigin) {
        var o = transformOrigin || '50% 50%';
        return '<div class="' + zoomSurfaceClass + '" style="width:100%;height:100%;box-sizing:border-box;transform-origin:' + o + ';">' +
            innerHtml + '</div>';
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
                html: wrapDivIconZoomScale(html, 'demo-svg-icon demo-pin-zoom-adapt', '50% 50%'),
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

    function normalizeMarkerDisplayStyle(v) {
        var s = String(v || '').trim().toLowerCase().replace(/-/g, '_');
        if (s === 'icon_only' || s === 'icononly') return 'icon_only';
        return 'standard';
    }

    function applyPinMarkerPartial(pin, pm) {
        if (!pm || typeof pm !== 'object') return;
        var sid = (pm.svg_icon_id || '').trim();
        if (sid) pin.svg_icon_id = sid;
        var scp = (pm.svg_icon_scope || '').trim();
        if (scp) pin.svg_icon_scope = scp;
        var ic = (pm.icon_color || '').trim();
        if (/^#[0-9a-fA-F]{6}$/.test(ic)) pin.marker_icon_color = ic;
        var bg = (pm.background_color || '').trim();
        if (/^#[0-9a-fA-F]{6}$/.test(bg)) pin.marker_bg_color = bg;
        var ds = (pm.display_style || '').trim();
        if (ds) pin.marker_display_style = normalizeMarkerDisplayStyle(ds);
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

    function updateVisibleMarkers() {
        allMarkers.forEach(function(item) {
            var isCatMatch = item.categories.some(function(cat) { return activeCategories.has(cat); });
            // VEIN: LEM ランクフィルターは使用しない
            if (isCatMatch) {
                if (!map.hasLayer(item.marker)) {
                    item.marker.addTo(map);
                    if (showLabels && item.marker.openTooltip) item.marker.openTooltip();
                }
            } else {
                if (map.hasLayer(item.marker)) map.removeLayer(item.marker);
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
    var JSON_PIN_MARKER_PX = (!isNaN(jsonMarkerPxRaw) && jsonMarkerPxRaw >= 44 && jsonMarkerPxRaw <= 80) ? jsonMarkerPxRaw : 56;
    var JSON_PIN_ANCHOR = leafletPinAnchorAtTail(JSON_PIN_MARKER_PX);

    function svgIconUrlCandidates(pinSvgId, scope) {
        var idPart = encodeURIComponent(pinSvgId) + '.svg';
        var commonU = svgIconsCommonBase ? svgIconsCommonBase.replace(/\/?$/, '/') + idPart : '';
        var gameU = baseUrl + 'assets/icons/' + idPart;
        var list = [];
        // scope==='game' のときだけゲームローカルを先に（それ以外は共通 assets を優先＝CSV マージで scope 未設定でも /assets/icons/ が効く）
        if (scope === 'game') {
            list.push(gameU);
            if (commonU) list.push(commonU);
        } else {
            if (commonU) list.push(commonU);
            list.push(gameU);
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
                var patched = replaceSvgCurrentColor(normalizeSvgPaintsToCurrentColor(text), symHex);
                var blob = new Blob([patched], { type: 'image/svg+xml;charset=utf-8' });
                done(URL.createObjectURL(blob));
            })
            .catch(function () {
                fetchFirstSvgAsObjectUrl(urls, index + 1, bust, symHex, done, fail);
            });
    }

    /** ピン／エリア共通: アイコンのみマーカー（Leaflet ルートは translate3d のため内側で scale） */
    function attachIconOnlySvgToMarker(marker, pinSvgId, scope, symHex) {
        var candidates = svgIconUrlCandidates(pinSvgId, scope);
        var bust = 't=' + Date.now();
        var iconOnlyPx = 56;
        var iconOnlyImgPx = 48;
        var iconOnlyImgStyle =
            'position:absolute;left:50%;top:50%;width:' + iconOnlyImgPx + 'px;height:' + iconOnlyImgPx + 'px;' +
            'transform:translate(-50%,-50%);object-fit:contain;pointer-events:none;' +
            '-webkit-filter:drop-shadow(0 1px 2px rgba(0,0,0,0.9)) drop-shadow(0 0 6px rgba(0,0,0,0.4));' +
            'filter:drop-shadow(0 1px 2px rgba(0,0,0,0.9)) drop-shadow(0 0 6px rgba(0,0,0,0.4));';
        fetchFirstSvgAsObjectUrl(
            candidates,
            0,
            bust,
            symHex,
            function (objUrl) {
                var href = escapeHtmlAttr(objUrl);
                var core = '<div class="map-pin-icon-only-wrap" style="position:relative;width:' + iconOnlyPx + 'px;height:' + iconOnlyPx + 'px;">' +
                    '<img class="map-pin-icon-only-img" src="' + href + '" alt="" draggable="false" decoding="async" style="' + iconOnlyImgStyle + '"/>' +
                    '</div>';
                var html = wrapDivIconZoomScale(core, 'map-pin-icon-only demo-pin-zoom-adapt', '50% 50%');
                marker.setIcon(
                    L.divIcon({
                        html: html,
                        className: MAP_PIN_LEAFLET_SHELL,
                        iconSize: [iconOnlyPx, iconOnlyPx],
                        iconAnchor: [Math.round(iconOnlyPx / 2), Math.round(iconOnlyPx / 2)]
                    })
                );
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

    function specialRuleText(rule, isJa) {
        if (!rule || typeof rule !== 'object') return '';
        var nt = String(rule.note_type || '').trim();
        var rt = String(rule.req_type || '').trim();
        var app = String(rule.applicability || 'always').trim();
        var maybeTag = app === 'sometimes' ? (isJa ? '（場合あり）' : ' (Sometimes)')
            : (app === 'lenient' ? (isJa ? '（やや緩め）' : ' (Relaxed)') : '');
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
            var iname = String(rule.item_name || '').trim();
            var icnt = String(rule.item_count || '').trim();
            if (!iname) return '';
            return nt + maybeTag + ': ' + (icnt ? (iname + ' ×' + icnt) : iname);
        }
        if (rt === 'スキルレベル') {
            var sid2 = String(rule.skill_id || '').trim();
            var slv = String(rule.skill_level || '').trim();
            if (!sid2 || !slv) return '';
            var nm2 = skillDisplayNameForRule(sid2, isJa);
            return nt + maybeTag + ': ' + nm2 + ' Lv.' + slv;
        }
        if (rt === 'スキル') {
            var sid3 = String(rule.skill_id || '').trim();
            if (!sid3) return '';
            var nm3 = skillDisplayNameForRule(sid3, isJa);
            return nt + maybeTag + ': ' + (isJa ? ('スキル ' + nm3) : ('Skill ' + nm3));
        }
        var lv = String(rule.level || '').trim();
        if (!lv) return '';
        return nt + maybeTag + ': Lv.' + lv;
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
                var qtyPart = qty ? (' ×' + qty) : '';
                var suffix = qtyPart + req;
                if (itemName) rows.push((cat ? (cat + '：') : '') + itemName + suffix);
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
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });

        var marker = L.marker(latLng, { icon: emojiIcon });

        if (pinSvgId && typeof wrapPinBasePlusImgIcon === 'function') {
            var scope = (pin.svg_icon_scope || '').trim();
            var candidates = svgIconUrlCandidates(pinSvgId, scope);
            var bust = 't=' + Date.now();
            if (displayStyle === 'icon_only') {
                attachIconOnlySvgToMarker(marker, pinSvgId, scope, symHex);
            } else {
                fetchFirstSvgAsObjectUrl(
                    candidates,
                    0,
                    bust,
                    symHex,
                    function (objUrl) {
                        var innerHtml = wrapPinBasePlusImgIcon(pinBg, objUrl, symHex, JSON_PIN_MARKER_PX);
                        var html = wrapDivIconZoomScale(innerHtml, 'map-pin-svg-composite demo-pin-zoom-adapt', '50% 100%');
                        marker.setIcon(
                            L.divIcon({
                                html: html,
                                className: MAP_PIN_LEAFLET_SHELL,
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

            var attrRaw = (pin.obj_id || pin.attribute || '').trim();
            var contents = pin.contents || [];

            var styleKey = resolveFilterStyleKey(attrRaw);
            var visualStyle = styles[styleKey] || styles.other;
            // フィルターはオブジェクト(attribute)単位のみ（カテゴリ cat_id は混ぜない）
            var myCategories = [styleKey];

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

            allMarkers.push({ marker: marker, categories: myCategories, rank: 'standard' });
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

    var veinLayerControl = null;
    var veinOverlayEventsBound = false;

    function addOverlayControls() {
        if (veinLayerControl) {
            map.removeControl(veinLayerControl);
            veinLayerControl = null;
        }
        var overlayMaps = {};
        Object.keys(styles).forEach(function(key) {
            if (key === 'trash' && !isDebug) return;
            var lbl = styles[key].label;
            overlayMaps[lbl] = L.layerGroup();
            if (activeCategories.has(key)) overlayMaps[lbl].addTo(map);
        });

        if (!filterMode) {
            veinLayerControl = L.control.layers(null, overlayMaps, { collapsed: false, position: 'topright' });
            veinLayerControl.addTo(map);
        }

        if (!veinOverlayEventsBound) {
            veinOverlayEventsBound = true;
            map.on('overlayadd', function(e) {
                var key = Object.keys(styles).find(function(k) { return styles[k].label === e.name; });
                if (key) { activeCategories.add(key); updateVisibleMarkers(); }
            });
            map.on('overlayremove', function(e) {
                var key = Object.keys(styles).find(function(k) { return styles[k].label === e.name; });
                if (key) { activeCategories.delete(key); updateVisibleMarkers(); }
            });
        }
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
                if (qtyStr) head += ' ×' + qtyStr;
                head += reqSuffix;
            } else if (catLab) {
                head = catLab;
                if (qtyStr) head += ' ×' + qtyStr;
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
                var catMap = { '設計図': 'blueprint', 'LEM': 'lem', '戦時債権': 'war_bonds', '交換アイテム': 'trade_item', 'キーカード': 'keycard', '植物': 'plant' };
                var cid = catMap[category] || category;
                if (cid) catIds.push(cid);
            }

            var attrU = (attribute || '').toUpperCase();
            var styleKey = resolveFilterStyleKey(attribute);
            var visualStyle = styles[styleKey] || styles.other;
            var myCategories = [styleKey];

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
            mergePinStyleFromConfig(pin, attribute, categoriesArr);
            if (mdsCol) pin.marker_display_style = normalizeMarkerDisplayStyle(mdsCol);
            var marker = createMarkerFromPin(pin, visualStyle, myCategories, null, headline, description, filterTT);
            if (!marker) continue;

            allMarkers.push({ marker: marker, categories: myCategories, rank: 'standard' });
        }

        addOverlayControls();
        updateVisibleMarkers();
    }

    /** データ JSON/CSV のブラウザキャッシュを避ける（ローカル検証でエディタ保存がすぐ反映されるように） */
    function dataCacheBust() {
        return 't=' + Date.now() + '&_=' + Math.random().toString(36).slice(2, 11);
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
                if (cfg && cfg.category_special_rules && typeof cfg.category_special_rules === 'object') {
                    categorySpecialRules = cfg.category_special_rules;
                } else {
                    categorySpecialRules = {};
                }
                if (cfg && cfg.skill_name_master && typeof cfg.skill_name_master === 'object') {
                    skillNameMaster = cfg.skill_name_master;
                } else {
                    skillNameMaster = {};
                }
                rebuildVeinFilterFromAttrMapping();
                if (isDebug) {
                    console.log('map.js: config.json loaded, pin_marker attrs=', Object.keys(pinMarkerByAttribute).length);
                }
            });
    }

    // -------- エリア描画（areas.json） --------
    var areaLayer = null;
    var areaIconLayerGroup = null;
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

    function addAreaCenterIconMarker(a) {
        if (!areaWantsCenterIcon(a)) return;
        var ri = resolveAreaCenterIconFromMaster(a);
        if (!ri) return;
        var xy = areaCenterIconImageXY(a);
        if (!xy) return;
        var latLng = map.unproject(xy, maxZoom);
        var marker = L.marker(latLng);
        attachIconOnlySvgToMarker(marker, ri.pinSvgId, ri.scope, ri.symHex);
        bindAreaPopup(marker, a);
        var name = isJa ? (a.name_jp || a.name_en || '') : (a.name_en || a.name_jp || '');
        var tt = name || (isJa ? 'エリア' : 'Area');
        marker.bindTooltip(tt, {
            direction: 'top', sticky: true, className: 'item-tooltip',
            opacity: 0.9, offset: [0, -10]
        });
        areaIconLayerGroup.addLayer(marker);
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
        if (areas.length === 0) return;
        areaLayer = L.layerGroup([], { pane: 'areas' });
        areaIconLayerGroup = L.layerGroup();

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
            addAreaCenterIconMarker(a);
        });

        areaLayer.addTo(map);
        areaIconLayerGroup.addTo(map);
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

    loadConfigJson().then(startPinLoad);
    if (isDebug) {
        console.log('map.js (vein world map): baseUrl=', baseUrl, 'csvUrl=', csvUrl, 'pinsJsonUrl=', pinsJsonUrl, 'showAllPins=', showAllPins);
    }
})();
