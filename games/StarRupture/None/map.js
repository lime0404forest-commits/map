(function() {
    'use strict';
    // map.js v20260208 - (No.) removed, multi-blueprint fix, CSV escape fix, LEM rank in popup

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

    // データソース: data-csv / data-pins がなければ同階層のファイルを相対パスで参照
    var baseUrl = '';
    var scriptSrc = document.currentScript && document.currentScript.src;
    if (scriptSrc) {
        var idx = scriptSrc.lastIndexOf('/');
        if (idx >= 0) baseUrl = scriptSrc.substring(0, idx + 1);
    }

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
        var iconHtml = '<div style="position:relative;">' + (visualStyle.emoji || '📌');
        if (bpNum) {
            iconHtml += '<span style="position:absolute;bottom:-5px;right:-8px;background:#e74c3c;color:white;border-radius:50%;font-size:10px;min-width:16px;height:16px;text-align:center;line-height:16px;font-weight:bold;border:1px solid white;box-shadow:1px 1px 2px rgba(0,0,0,0.3);">' + bpNum + '</span>';
        }
        iconHtml += '</div>';

        var marker = L.marker(latLng, {
            icon: L.divIcon({
                html: iconHtml,
                className: 'emoji-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            })
        });

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

        // フィルタモード時: 「設計図：チューブ」形式の tooltipLabelText を優先、なければ displayName、さらに cleanTextForFilter
        var tooltipText = filterMode ? (tooltipLabelText || displayName || cleanTextForFilter(rawText, filterMode)) : rawText;
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
                        var rank = (c.attributes && c.attributes['ランク']) || '';
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
                contentsSummary = lemNamesFromContents.length > 1 ? (visualStyle.label + '：<br>・' + lemNamesFromContents.join('<br>・')) : (lemNamesFromContents.length === 1 ? (visualStyle.label + '：' + lemNamesFromContents[0]) : nameForLabel);
            } else if (filterMode === 'blueprint') {
                contentsSummary = blueprintNamesFromContents.length > 1 ? (visualStyle.label + '：<br>・' + blueprintNamesFromContents.join('<br>・')) : (blueprintNamesFromContents.length === 1 ? (visualStyle.label + '：' + blueprintNamesFromContents[0]) : (nameForLabel ? visualStyle.label + '：' + nameForLabel : name));
            } else {
                contentsSummary = name;
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

    function loadFromCSV(text) {
        var rows = text.trim().split('\n');
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
            var categoriesJson = cols[9] || '[]';

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
            var contentsSummary = filterMode
                ? (filterMode === 'lem' ? formatContentsSummaryForPopup(visualStyle.label, lemNames) : formatContentsSummaryForPopup(visualStyle.label, blueprintNames))
                : name;
            if (contentsSummary === '' && nameForLabel) contentsSummary = visualStyle.label + '：' + nameForLabel;

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

    // data-pins 指定時は pins_export.json を優先
    if (customPins !== null && customPins !== '') {
        fetch(pinsJsonUrl + (pinsJsonUrl.indexOf('?') >= 0 ? '&' : '?') + cacheBuster)
            .then(function(r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function(data) {
                var pins = data && data.pins ? data.pins : (Array.isArray(data) ? data : []);
                addMarkersFromPins(pins);
            })
            .catch(function(e) {
                console.warn('map.js: pins_export.json load failed, falling back to CSV', e);
                return fetch(csvUrl + '?' + cacheBuster).then(function(r) { if (!r.ok) throw new Error(r.status); return r.text(); });
            })
            .then(function(text) {
                if (typeof text === 'string') loadFromCSV(text);
            })
            .catch(function(e) { console.error('map.js:', e); });
    } else {
        fetch(csvUrl + '?' + cacheBuster)
            .then(function(r) { if (!r.ok) throw new Error(r.status); return r.text(); })
            .then(loadFromCSV)
            .catch(function(e) {
                console.error('map.js: Failed to load pins. Check CSV URL and CORS.', e);
            });
    }
})();
