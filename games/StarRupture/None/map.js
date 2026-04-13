(function() {
    console.log("StarRupture map.js v20260411 (hover: item + qty, omit ×1; matches editor preview)");

    var maxZoom = 5;
    var imgW = 6253;
    var imgH = 7104;
    var mapPadding = 1500;

    var mapDiv = document.getElementById('game-map');

    var showLabels = mapDiv ? mapDiv.getAttribute('data-show-labels') === 'true' : false;
    var htmlZoom = mapDiv ? parseInt(mapDiv.getAttribute('data-zoom'), 10) : null;
    var defaultZoom = (htmlZoom !== null && !isNaN(htmlZoom)) ? htmlZoom : 1;
    var filterMode = mapDiv ? mapDiv.getAttribute('data-filter') : null;
    var customCsv = mapDiv ? mapDiv.getAttribute('data-csv') : null;
    var customTiles = mapDiv ? mapDiv.getAttribute('data-tiles') : null;

    var csvUrl = customCsv || 'https://cdn.jsdelivr.net/gh/lime0404forest-commits/map@main/games/StarRupture/None/master_data.csv';
    var tileUrl = customTiles || 'https://lost-in-games.com/starrupture-map/tiles/{z}/{x}/{y}.webp?v=20260111_FINAL3';

    var isJa = (document.documentElement.lang || navigator.language).toLowerCase().indexOf('ja') === 0;
    var isDebug = new URLSearchParams(window.location.search).get('debug') === 'true';

    var styles = {
        scanner:   { emoji: '📡', color: '#2ecc71', label: isJa ? 'ジオスキャナー' : 'Geo Scanner' },
        start:     { emoji: '🚀', color: '#ffffff', label: isJa ? '開始地点' : 'Start Point' },
        blueprint: { emoji: '📜', color: '#3498db', label: isJa ? '設計図' : 'Blueprints' },
        warbond:   { emoji: '💀', color: '#e74c3c', label: isJa ? '戦時債権' : 'War Bonds' },
        point:     { emoji: '💎', color: '#f1c40f', label: isJa ? '換金アイテム' : 'Cash Items' },
        lem:       { emoji: '⚡', color: '#9b59b6', label: isJa ? 'LEM' : 'LEM Gear' },
        cave:      { emoji: '⛏️', color: '#7f8c8d', label: isJa ? '地下洞窟' : 'Caves' },
        monolith:  { emoji: '🗿', color: '#1abc9c', label: isJa ? 'モノリス' : 'Monoliths' },
        other:     { emoji: null, color: '#95a5a6', label: isJa ? 'その他' : 'Others' },
        trash:     { emoji: '❌', color: '#555555', label: isJa ? '調査済み(空)' : 'Checked(Empty)' }
    };

    /** 旧 master_data（LOC_* / ITEM_* コード列） */
    var catMappingLegacy = {
        'LOC_SPARE_2': 'scanner', 'LOC_BASE': 'start', 'ITEM_WEAPON': 'blueprint',
        'ITEM_OTHER': 'warbond', 'ITEM_GEAR': 'point', 'LOC_SPARE_1': 'lem',
        'LOC_CAVEORMINE': 'cave', 'LOC_POI': 'monolith', 'MISC_OTHER': 'trash',
        'LOC_TREASURE': 'other', 'RES_PLANT': 'other', 'RES_MINERAL': 'other', 'RES_OTHER': 'other',
        'LOC_SETTLE': 'other', 'CHAR_NPC': 'other', 'CHAR_TRADER': 'other',
        'CHAR_OTHER': 'other', 'MISC_ENEMY': 'other', 'LOC_ENEMY': 'other',
        'MISC_QUEST': 'other', 'LOC_MEMO': 'other'
    };

    /** エディタ export の category 列（日本語）→ 表示カテゴリ */
    var jpCategoryToStyle = {
        '設計図': 'blueprint',
        'LEM': 'lem',
        '戦時債権': 'warbond',
        '交換アイテム': 'point',
        'キーカード': 'other',
        '植物': 'other'
    };

    /** categories セル内 JSON の cat_id → 表示カテゴリ */
    var catIdToStyle = {
        blueprint: 'blueprint',
        lem: 'lem',
        war_bonds: 'warbond',
        trade_item: 'point',
        keycard: 'other',
        plant: 'other'
    };

    /** attribute 列（エディタのオブジェクト種別）→ ランドマーク系 */
    var attrToStyle = {
        'GEO_SCANNER': 'scanner',
        'UNDERGROUND_CAVE': 'cave',
        'MONOLITH': 'monolith',
        'SPACESHIP': 'start'
    };

    var stylePickOrder = ['blueprint', 'lem', 'warbond', 'point', 'scanner', 'start', 'cave', 'monolith', 'trash', 'other'];

    function pickPrimaryCategory(cats) {
        for (var i = 0; i < stylePickOrder.length; i++) {
            if (cats.indexOf(stylePickOrder[i]) >= 0) return stylePickOrder[i];
        }
        return 'other';
    }

    window.map = L.map('game-map', {
        crs: L.CRS.Simple, minZoom: 0, maxZoom: maxZoom, zoom: defaultZoom,
        maxBoundsViscosity: 0.8, preferCanvas: true
    });

    var map = window.map;
    var imageBounds = new L.LatLngBounds(
        map.unproject([0, imgH], maxZoom), map.unproject([imgW, 0], maxZoom)
    );
    var paddedBounds = new L.LatLngBounds(
        map.unproject([-mapPadding, imgH + mapPadding], maxZoom),
        map.unproject([imgW + mapPadding, -mapPadding], maxZoom)
    );

    map.setMaxBounds(paddedBounds);
    map.fitBounds(imageBounds);
    map.setZoom(defaultZoom);

    L.tileLayer(tileUrl, {
        minZoom: 0, maxZoom: maxZoom, tileSize: 256, noWrap: true, bounds: imageBounds, tms: false
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

        if (filterMode) {
            if (key === filterMode) activeCategories.add(key);
            if ((filterMode === 'blueprint' || filterMode === 'lem') && key === 'start') {
                activeCategories.add(key);
            }
        } else {
            var hiddenKeys = ['monolith', 'scanner', 'cave', 'other', 'point'];
            if (hiddenKeys.indexOf(key) < 0) activeCategories.add(key);
        }
    });

    function getRank(rawRowString) {
        if (!rawRowString) return 'standard';
        var s = rawRowString.toLowerCase();
        if (s.indexOf('greater') >= 0 || s.indexOf('上級') >= 0) return 'greater';
        if (s.indexOf('lesser') >= 0 || s.indexOf('下級') >= 0) return 'lesser';
        return 'standard';
    }

    function updateVisibleMarkers() {
        allMarkers.forEach(function(item) {
            var isCatMatch = item.categories.some(function(cat) { return activeCategories.has(cat); });

            var isRankMatch = true;
            if (currentRankFilter !== 'all') {
                if (item.rank !== currentRankFilter && item.categories.indexOf('start') < 0) {
                    isRankMatch = false;
                }
            }

            if (isCatMatch && isRankMatch) {
                if (!map.hasLayer(item.marker)) item.marker.addTo(map);
            } else {
                if (map.hasLayer(item.marker)) map.removeLayer(item.marker);
            }
        });
    }

    function cleanTextForFilter(text, mode) {
        if (!mode || !text) return text;

        var keywords = {
            blueprint: ['設計図', 'Blueprint', 'Recipe'],
            lem: ['LEM'],
            warbond: ['戦時', 'Warbond'],
            scanner: ['スキャナー', 'Scanner']
        };

        var targetKeys = keywords[mode];
        if (!targetKeys) return text;

        var lines = text.split(/\r\n|\n|\r|<br>/);
        var filteredLines = lines.filter(function(line) {
            return targetKeys.some(function(key) { return line.indexOf(key) >= 0; });
        });

        return filteredLines.length > 0 ? filteredLines.join('<br>') : '';
    }

    function parseCategoriesObjects(jsonStr) {
        if (!jsonStr || String(jsonStr).trim().charAt(0) !== '[') return [];
        try {
            var arr = JSON.parse(jsonStr);
            return Array.isArray(arr) ? arr : [];
        } catch (e) {
            return [];
        }
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

    function hoverQtySuffix(qtyStr) {
        if (qtyStr == null || String(qtyStr).trim() === '') return '';
        var s = String(qtyStr).trim();
        var n = parseFloat(s, 10);
        if (!isNaN(n) && n === 1) return '';
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

    /** pin_site_preview.build_hover_tooltip_text と同じルール（カテゴリ接頭辞なし・数量1は非表示） */
    function buildHoverTooltipTextFromContents(contents, isJa) {
        var rows = [];
        (contents || []).forEach(function(c) {
            if (!c) return;
            var itemName = itemNameFromEntry(c, isJa);
            var cat = categoryLabelFromEntry(c, isJa);
            var qty = itemQtyStringForEntry(c);
            var req = lockpickReqSuffix(c, isJa);
            var suffix = hoverQtySuffix(qty) + req;
            if (itemName) rows.push(itemName + suffix);
            else if (cat) rows.push(cat + suffix);
        });
        return rows.length ? rows.join('\n') : '';
    }

    if (!filterMode || filterMode === 'lem') {
        var rankControl = L.control({ position: 'bottomright' });
        rankControl.onAdd = function() {
            var div = L.DomUtil.create('div', 'rank-filter-control');
            div.style.background = 'rgba(255, 255, 255, 0.9)';
            div.style.padding = '5px';
            div.style.borderRadius = '4px';
            div.style.boxShadow = '0 1px 5px rgba(0,0,0,0.4)';
            div.style.display = 'flex';
            div.style.gap = '5px';
            div.style.marginRight = '10px';
            div.style.marginBottom = '10px';
            div.innerHTML =
                '<style>' +
                '.rank-btn { border: 1px solid #ccc; background: #fff; padding: 2px 8px; cursor: pointer; border-radius: 3px; font-size: 12px; font-weight: bold; color: #333; }' +
                '.rank-btn.active { background: #333; color: #fff; border-color: #000; }' +
                '</style>' +
                '<button class="rank-btn active" data-rank="all">ALL</button>' +
                '<button class="rank-btn" data-rank="greater" style="color:#e67e22;">Greater</button>' +
                '<button class="rank-btn" data-rank="standard">Standard</button>' +
                '<button class="rank-btn" data-rank="lesser" style="color:#7f8c8d;">Lesser</button>';

            var btns = div.querySelectorAll('.rank-btn');
            btns.forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    btns.forEach(function(b) { b.classList.remove('active'); });
                    e.target.classList.add('active');
                    currentRankFilter = e.target.getAttribute('data-rank');
                    updateVisibleMarkers();
                    L.DomEvent.stopPropagation(e);
                });
            });
            L.DomEvent.disableClickPropagation(div);
            return div;
        };
        rankControl.addTo(map);
    }

    function parseCSVRow(row) {
        var result = [];
        var current = '';
        var inQuotes = false;
        for (var i = 0; i < row.length; i++) {
            var char = row[i];
            if (char === '"') inQuotes = !inQuotes;
            else if (char === ',' && !inQuotes) {
                result.push(current);
                current = '';
            } else {
                current += char;
            }
        }
        result.push(current);
        return result;
    }

    function headerToIndex(headerRow) {
        var idx = {};
        headerRow.forEach(function(h, i) {
            idx[String(h).trim()] = i;
        });
        return idx;
    }

    function cell(row, idx, name, fallback) {
        var i = idx[name];
        if (i === undefined || i >= row.length) return fallback !== undefined ? fallback : '';
        var v = row[i];
        return v !== undefined && v !== null ? String(v) : '';
    }

    function parseCategoriesJson(jsonStr) {
        if (!jsonStr || jsonStr.trim().charAt(0) !== '[') return [];
        try {
            var arr = JSON.parse(jsonStr);
            if (!Array.isArray(arr)) return [];
            return arr.map(function(o) {
                return o && o.cat_id ? String(o.cat_id) : '';
            }).filter(Boolean);
        } catch (e) {
            return [];
        }
    }

    function buildCategoriesEditor(idx, row, rawLine) {
        var attribute = cell(row, idx, 'attribute').trim().toUpperCase();
        if (attribute === 'MISC_OTHER' && !isDebug) return null;

        var categoryJp = cell(row, idx, 'category').trim();
        var categoriesCell = cell(row, idx, 'categories');
        var out = [];

        if (categoryJp && jpCategoryToStyle[categoryJp]) {
            out.push(jpCategoryToStyle[categoryJp]);
        }
        parseCategoriesJson(categoriesCell).forEach(function(cid) {
            var st = catIdToStyle[cid];
            if (st) out.push(st);
        });
        var ast = attrToStyle[attribute];
        if (ast) out.push(ast);

        var legacy = catMappingLegacy[attribute];
        if (legacy && legacy !== 'trash') out.push(legacy);
        else if (legacy === 'trash' && isDebug) out.push('trash');

        out = out.filter(function(x, j, a) { return a.indexOf(x) === j; });
        if (out.length === 0) out.push('other');

        return {
            myCategories: out,
            primary: pickPrimaryCategory(out),
            attribute: attribute,
            name: isJa ? cell(row, idx, 'name_jp') : (cell(row, idx, 'name_en') || cell(row, idx, 'name_jp')),
            memo: isJa ? cell(row, idx, 'memo_jp') : (cell(row, idx, 'memo_en') || cell(row, idx, 'memo_jp')),
            x: parseFloat(cell(row, idx, 'x')),
            y: parseFloat(cell(row, idx, 'y')),
            rawLine: rawLine
        };
    }

    function buildCategoriesLegacy(cols, rawLine) {
        if (cols.length < 8) return null;
        var x = parseFloat(cols[1]);
        var y = parseFloat(cols[2]);
        if (isNaN(x) || isNaN(y)) return null;

        var catMain = cols[5] ? cols[5].trim().toUpperCase() : '';
        var catSub1 = cols[6] ? cols[6].trim().toUpperCase() : '';
        var catSub2 = cols[7] ? cols[7].trim().toUpperCase() : '';

        if (catMain === 'MISC_OTHER' && !isDebug) return null;

        var myCategories = [];
        function gsk(code) {
            if (!code) return null;
            return catMappingLegacy[code] || 'other';
        }
        var k1 = gsk(catMain); if (k1) myCategories.push(k1);
        var k2 = gsk(catSub1); if (k2) myCategories.push(k2);
        var k3 = gsk(catSub2); if (k3) myCategories.push(k3);
        myCategories = myCategories.filter(function(x, i, a) { return a.indexOf(x) === i; });

        return {
            myCategories: myCategories,
            primary: pickPrimaryCategory(myCategories),
            attribute: catMain,
            name: isJa ? cols[3] : (cols[4] || cols[3]),
            memo: isJa ? cols[9] : (cols[10] || ''),
            x: x,
            y: y,
            rawLine: rawLine
        };
    }

    var csvSep = csvUrl.indexOf('?') >= 0 ? '&' : '?';
    fetch(csvUrl + csvSep + 't=' + Date.now())
        .then(function(r) { if (!r.ok) throw new Error('CSV ' + r.status); return r.text(); })
        .then(function(text) {
            var lines = text.trim().split(/\r?\n/);
            if (lines.length < 2) return;

            var headerCols = parseCSVRow(lines[0]);
            var colIdx = headerToIndex(headerCols);
            var isEditorCsv = colIdx.memo_jp !== undefined && colIdx.name_jp !== undefined;

            for (var i = 1; i < lines.length; i++) {
                var rawLine = lines[i];
                if (!rawLine.trim()) continue;
                var row = parseCSVRow(rawLine);

                var data = isEditorCsv
                    ? buildCategoriesEditor(colIdx, row, rawLine)
                    : buildCategoriesLegacy(row, rawLine);

                if (!data) continue;
                if (isNaN(data.x) || isNaN(data.y)) continue;

                var primary = data.primary;
                var myCategories = data.myCategories;
                var visualStyle = styles[primary] || styles.other;
                var isBlueprint = myCategories.indexOf('blueprint') >= 0;
                var enableNumbering = (filterMode === 'blueprint');
                var bpNum = (isBlueprint && enableNumbering) ? ++blueprintCount : null;

                var name = data.name || '';
                var itemRank = getRank(data.rawLine);

                var displayName = name;
                if (bpNum) {
                    displayName = name + ' <span style="font-size:0.9em;color:#888;">(No.' + bpNum + ')</span>';
                }

                var memo = data.memo || '';

                var hoverFromContents = '';
                if (isEditorCsv) {
                    hoverFromContents = buildHoverTooltipTextFromContents(
                        parseCategoriesObjects(cell(row, colIdx, 'categories')),
                        isJa
                    );
                }
                var rawText = hoverFromContents || (memo ? memo : name);

                var latLng = map.unproject([data.x, data.y], maxZoom);
                var marker;

                if (visualStyle.emoji) {
                    var extra = (data.attribute === 'MISC_OTHER') ? ' debug-marker' : '';
                    var iconHtml = '<div style="position:relative;">' + visualStyle.emoji;
                    if (bpNum) {
                        iconHtml += '<span style="position:absolute; bottom:-5px; right:-8px; background:#e74c3c; color:white; border-radius:50%; font-size:10px; min-width:16px; height:16px; text-align:center; line-height:16px; font-weight:bold; border:1px solid white; box-shadow: 1px 1px 2px rgba(0,0,0,0.3);">' + bpNum + '</span>';
                    }
                    iconHtml += '</div>';

                    marker = L.marker(latLng, {
                        icon: L.divIcon({
                            html: iconHtml,
                            className: 'emoji-icon' + extra,
                            iconSize: [30, 30], iconAnchor: [15, 15]
                        })
                    });
                } else {
                    marker = L.circleMarker(latLng, {
                        radius: 5, fillColor: visualStyle.color, color: '#000', weight: 1, opacity: 1, fillOpacity: 0.8
                    });
                }

                var p = '<div style="font-family:sans-serif;min-width:180px;">' +
                    '<div style="font-size:10px;color:' + visualStyle.color + ';font-weight:bold;text-transform:uppercase;">' + visualStyle.label + '</div>' +
                    '<div style="font-size:14px;font-weight:bold;margin:4px 0;border-bottom:1px solid #ccc;padding-bottom:4px;">' + displayName + '</div>';
                if (memo) {
                    p += '<div style="font-size:12px;color:#444;background:#f4f4f4;padding:5px;border-radius:3px;line-height:1.4;">' + memo + '</div>';
                }
                p += '</div>';
                marker.bindPopup(p);

                var tooltipText = filterMode ? cleanTextForFilter(rawText, filterMode) : rawText;

                var tooltipOptions;
                if (showLabels) {
                    tooltipOptions = {
                        permanent: true,
                        direction: 'top',
                        className: 'item-tooltip-permanent',
                        opacity: 0.9,
                        offset: [0, -20]
                    };
                } else {
                    tooltipOptions = {
                        direction: 'top',
                        sticky: true,
                        className: 'item-tooltip',
                        opacity: 0.9,
                        offset: [0, -10]
                    };
                }
                marker.bindTooltip(tooltipText, tooltipOptions);

                allMarkers.push({
                    marker: marker,
                    categories: myCategories,
                    rank: itemRank
                });
            }

            var overlayMaps = {};
            Object.keys(styles).forEach(function(key) {
                if (key === 'trash' && !isDebug) return;
                var lbl = styles[key].label;
                var dummyGroup = L.layerGroup();
                overlayMaps[lbl] = dummyGroup;
                if (activeCategories.has(key)) dummyGroup.addTo(map);
            });

            if (!filterMode) {
                L.control.layers(null, overlayMaps, { collapsed: false, position: 'topright' }).addTo(map);
            }

            map.on('overlayadd', function(e) {
                var key = Object.keys(styles).find(function(k) { return styles[k].label === e.name; });
                if (key) {
                    activeCategories.add(key);
                    updateVisibleMarkers();
                }
            });

            map.on('overlayremove', function(e) {
                var key = Object.keys(styles).find(function(k) { return styles[k].label === e.name; });
                if (key) {
                    activeCategories.delete(key);
                    updateVisibleMarkers();
                }
            });

            updateVisibleMarkers();
        })
        .catch(function(e) { console.error('[StarRupture map]', e); });
})();
