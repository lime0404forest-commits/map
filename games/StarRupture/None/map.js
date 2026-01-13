(function() {
    console.log("Map Script Loaded via GitHub (Numbered Blueprints Fixed)");

    var maxZoom = 5; 
    var imgW = 6253;
    var imgH = 7104;
    var mapPadding = 1500; 

    // HTML要素を取得
    var mapDiv = document.getElementById('game-map');
    
    // ▼ HTML設定読み込み ▼
    var showLabels = mapDiv ? mapDiv.getAttribute('data-show-labels') === 'true' : false;
    var htmlZoom = mapDiv ? parseInt(mapDiv.getAttribute('data-zoom')) : null;
    
    // デフォルトズーム設定（1を指定されましたが、画像がない場合は真っ黒になります。その場合は3に戻してください）
    var defaultZoom = (htmlZoom !== null && !isNaN(htmlZoom)) ? htmlZoom : 1;
    
    var filterMode = mapDiv ? mapDiv.getAttribute('data-filter') : null;
    var customCsv = mapDiv ? mapDiv.getAttribute('data-csv') : null;
    // ▲ 設定読み込みここまで ▲

    var csvUrl = customCsv || 'https://raw.githubusercontent.com/lime0404forest-commits/map/main/games/StarRupture/None/master_data.csv';
    var tileUrl = 'https://lost-in-games.com/starrupture-map/tiles/{z}/{x}/{y}.webp?v=20260111_FINAL3';

    var isJa = (document.documentElement.lang || navigator.language).toLowerCase().indexOf('ja') === 0;
    var isDebug = new URLSearchParams(window.location.search).get('debug') === 'true';

    // カテゴリ定義
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

    var catMapping = {
        'LOC_SPARE_2': 'scanner', 
        'LOC_BASE': 'start', 
        'ITEM_WEAPON': 'blueprint',
        'ITEM_OTHER': 'warbond', 
        'ITEM_GEAR': 'point', 
        'LOC_SPARE_1': 'lem',
        'LOC_CAVEORMINE': 'cave', 
        'LOC_POI': 'monolith', 
        'MISC_OTHER': 'trash',
        'LOC_TREASURE': 'other', 
        'RES_PLANT': 'other', 'RES_MINERAL': 'other', 'RES_OTHER': 'other', 
        'LOC_SETTLE': 'other', 'CHAR_NPC': 'other', 'CHAR_TRADER': 'other', 
        'CHAR_OTHER': 'other', 'MISC_ENEMY': 'other', 'LOC_ENEMY': 'other', 
        'MISC_QUEST': 'other', 'LOC_MEMO': 'other'
    };

    window.map = L.map('game-map', {
        crs: L.CRS.Simple, minZoom: 0, maxZoom: maxZoom, zoom: defaultZoom,
        maxBoundsViscosity: 0.8, preferCanvas: true
    });

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
        minZoom: 0, maxZoom: maxZoom, tileSize: 256, noWrap: true, 
        bounds: imageBounds, attribution: 'Map Data', tms: false
    }).addTo(map);

    function updateZoomClass() {
        var c = document.getElementById('game-map');
        if(c) {
            c.className = c.className.replace(/zoom-level-\d+/g, '').trim();
            c.classList.add('zoom-level-' + map.getZoom());
        }
    }
    map.on('zoomend', updateZoomClass);
    updateZoomClass();

    var allMarkers = [];
    var activeCategories = new Set();
    
    // 設計図用のカウンター
    var blueprintCount = 0;

    Object.keys(styles).forEach(key => {
        if (key === 'trash' && !isDebug) return;
        if (filterMode) {
            if (key === filterMode) activeCategories.add(key);
        } else {
            const hiddenKeys = ['monolith', 'scanner', 'cave', 'other', 'point'];
            if (!hiddenKeys.includes(key)) activeCategories.add(key);
        }
    });

    function updateVisibleMarkers() {
        allMarkers.forEach(item => {
            var isVisible = item.categories.some(cat => activeCategories.has(cat));
            if (isVisible) {
                if (!map.hasLayer(item.marker)) {
                    item.marker.addTo(map);
                }
            } else {
                if (map.hasLayer(item.marker)) {
                    map.removeLayer(item.marker);
                }
            }
        });
    }

    function cleanTextForFilter(text, mode) {
        if (!mode || !text) return text;
        var keywords = {
            'blueprint': ['設計図', 'Blueprint', 'Recipe'],
            'lem': ['LEM', 'Module'],
            'warbond': ['戦時', 'Warbond'],
            'scanner': ['スキャナー', 'Scanner']
        };
        var targetKeys = keywords[mode];
        if (!targetKeys) return text; 
        var lines = text.split(/\r\n|\n|\r|<br>/);
        var filteredLines = lines.filter(line => {
            return targetKeys.some(key => line.includes(key));
        });
        if (filteredLines.length > 0) {
            return filteredLines.join('<br>');
        } else {
            return text;
        }
    }

    var cacheBuster = 't=' + Date.now();
    fetch(csvUrl + '?' + cacheBuster)
    .then(r => { if(!r.ok) throw new Error(r.status); return r.text(); })
    .then(text => {
        var rows = text.trim().split('\n');

        function parseCSVRow(row) {
            const result = [];
            let current = '';
            let inQuotes = false; 
            // ★修正箇所：ここに重複していた let inQuotes = false; を削除しました
            for (let char of row) {
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

        function getStyleKey(code) {
            if (!code) return null;
            return catMapping[code] || 'other';
        }

        for (var i = 1; i < rows.length; i++) {
            var cols = parseCSVRow(rows[i]);
            if (cols.length < 8) continue;

            var x = parseFloat(cols[1]); 
            var y = parseFloat(cols[2]);
            if (isNaN(x) || isNaN(y)) continue;

            var catMain = cols[5] ? cols[5].trim().toUpperCase() : "";
            var catSub1 = cols[6] ? cols[6].trim().toUpperCase() : "";
            var catSub2 = cols[7] ? cols[7].trim().toUpperCase() : "";

            if (catMain === 'MISC_OTHER' && !isDebug) continue;

            var myCategories = [];
            var k1 = getStyleKey(catMain); if(k1) myCategories.push(k1);
            var k2 = getStyleKey(catSub1); if(k2) myCategories.push(k2);
            var k3 = getStyleKey(catSub2); if(k3) myCategories.push(k3);
            
            myCategories = [...new Set(myCategories)];

            var visualStyle = styles[k1] || styles.other;
            
            // 設計図なら番号を振る
            var isBlueprint = (k1 === 'blueprint');
            var bpNum = isBlueprint ? ++blueprintCount : null;

            var name = isJa ? cols[3] : (cols[4] || cols[3]);
            
            // ポップアップ用タイトルにも番号をつける
            var displayName = name;
            if (bpNum) {
                displayName = name + ' <span style="font-size:0.9em;color:#888;">(No.' + bpNum + ')</span>';
            }

            var memo = isJa ? cols[9] : (cols[10] || "");

            var latLng = map.unproject([x, y], maxZoom);
            var marker;

            if (visualStyle.emoji) {
                var extra = (catMain === 'MISC_OTHER') ? ' debug-marker' : '';
                
                // アイコンHTMLに番号バッジを重ねる
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
                    radius: 5, fillColor: visualStyle.color, color: "#000", weight: 1, opacity: 1, fillOpacity: 0.8
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
            
            var rawText = memo ? memo : name;
            var tooltipText = filterMode ? cleanTextForFilter(rawText, filterMode) : rawText;

            var tooltipOptions = {};
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
                categories: myCategories
            });
        }

        var overlayMaps = {};
        Object.keys(styles).forEach(key => {
            if (key === 'trash' && !isDebug) return;
            var lbl = styles[key].label;
            var dummyGroup = L.layerGroup(); 
            overlayMaps[lbl] = dummyGroup;

            if (activeCategories.has(key)) {
                dummyGroup.addTo(map);
            }
        });

        L.control.layers(null, overlayMaps, { collapsed: false, position: 'topright' }).addTo(map);

        map.on('overlayadd', function(e) {
            var key = Object.keys(styles).find(k => styles[k].label === e.name);
            if (key) {
                activeCategories.add(key);
                updateVisibleMarkers();
            }
        });

        map.on('overlayremove', function(e) {
            var key = Object.keys(styles).find(k => styles[k].label === e.name);
            if (key) {
                activeCategories.delete(key);
                updateVisibleMarkers();
            }
        });

        updateVisibleMarkers();
    })
    .catch(e => console.error(e));
})();