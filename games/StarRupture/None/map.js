(function() {
    console.log("Map Script Loaded via GitHub (Final Debug Version)");

    // ★設定：フォルダが0～5ならmaxZoomは5
    var maxZoom = 5; 
    var imgW = 6253;
    var imgH = 7104;

    var csvUrl = 'https://raw.githubusercontent.com/lime0404forest-commits/map/main/games/StarRupture/None/master_data.csv';
    var tileUrl = 'https://lost-in-games.com/starrupture-map/tiles/{z}/{x}/{y}.webp?v=20260111';

    var isJa = (document.documentElement.lang || navigator.language).toLowerCase().indexOf('ja') === 0;
    var isDebug = new URLSearchParams(window.location.search).get('debug') === 'true';

    var styles = {
        scanner:   { emoji: '📡', color: '#2ecc71', label: isJa ? 'ジオスキャナー' : 'Geo Scanner' },
        start:     { emoji: '🚀', color: '#ffffff', label: isJa ? '開始地点' : 'Start Point' },
        blueprint: { emoji: '📜', color: '#3498db', label: isJa ? '設計図' : 'Blueprints' },
        warbond:   { emoji: '💀', color: '#e74c3c', label: isJa ? '戦時債権' : 'War Bonds' },
        point:     { emoji: '💎', color: '#f1c40f', label: isJa ? 'ポイント交換' : 'Point Items' },
        lem:       { emoji: '⚡', color: '#9b59b6', label: isJa ? 'LEM' : 'LEM Gear' },
        cave:      { emoji: '⛏️', color: '#7f8c8d', label: isJa ? '地下洞窟' : 'Caves' },
        monolith:  { emoji: '🗿', color: '#1abc9c', label: isJa ? 'モノリス' : 'Monoliths' },
        other:     { emoji: null, color: '#95a5a6', label: isJa ? 'その他' : 'Others' },
        trash:     { emoji: '❌', color: '#555555', label: isJa ? '調査済み(空)' : 'Checked(Empty)' }
    };

    var catMapping = {
        'LOC_SPARE_2': styles.scanner, 'LOC_BASE': styles.start, 'ITEM_WEAPON': styles.blueprint,
        'ITEM_OTHER': styles.warbond, 'ITEM_GEAR': styles.point, 'LOC_SPARE_1': styles.lem,
        'LOC_CAVEorMINE': styles.cave, 'LOC_POI': styles.monolith, 'MISC_OTHER': styles.trash,
        'LOC_TREASURE': styles.other, 'RES_PLANT': styles.other, 'RES_MINERAL': styles.other,
        'RES_OTHER': styles.other, 'LOC_SETTLE': styles.other, 'CHAR_NPC': styles.other,
        'CHAR_TRADER': styles.other, 'CHAR_OTHER': styles.other, 'MISC_ENEMY': styles.other,
        'LOC_ENEMY': styles.other, 'MISC_QUEST': styles.other, 'LOC_MEMO': styles.other
    };

    // ★修正点：ここを 'var map =' から 'window.map =' に変えました。
    // これでコンソールから map.project(...) が使えるようになります！
    window.map = L.map('game-map', {
        crs: L.CRS.Simple, minZoom: 0, maxZoom: maxZoom, zoom: 2, maxBoundsViscosity: 0.8, preferCanvas: true
    });

    var bounds = new L.LatLngBounds(
        map.unproject([0, imgH], maxZoom),
        map.unproject([imgW, 0], maxZoom)
    );
    map.setMaxBounds(bounds);
    map.fitBounds(bounds);

    L.tileLayer(tileUrl, { 
        minZoom: 0, maxZoom: maxZoom, tileSize: 256, noWrap: true, bounds: bounds, attribution: 'Map Data', tms: false
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

    var cacheBuster = 't=' + Date.now();
    fetch(csvUrl + '?' + cacheBuster)
    .then(r => { if(!r.ok) throw new Error(r.status); return r.text(); })
    .then(text => {
        var rows = text.trim().split('\n');
        var layers = {};

        // カンマ区切り修正（"a,b",c に対応）
        function parseCSVRow(row) {
            const result = [];
            let current = '';
            let inQuotes = false;
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

        for (var i = 1; i < rows.length; i++) {
            var cols = parseCSVRow(rows[i]);
            if (cols.length < 6) continue;

            var x = parseFloat(cols[1]); 
            var y = parseFloat(cols[2]);
            if (isNaN(x) || isNaN(y)) continue;

            var category = cols[5] ? cols[5].trim().toUpperCase() : "";
            if (category === 'MISC_OTHER' && !isDebug) continue;

            var style = catMapping[category] || styles.other;
            var name = isJa ? cols[3] : (cols[4] || cols[3]);
            var memo = isJa ? cols[7] : (cols[8] || "");

            var latLng = map.unproject([x, y], maxZoom);
            var marker;

            if (style.emoji) {
                var extra = (category === 'MISC_OTHER') ? ' debug-marker' : '';
                marker = L.marker(latLng, {
                    icon: L.divIcon({
                        html: '<div>' + style.emoji + '</div>',
                        className: 'emoji-icon' + extra,
                        iconSize: [30, 30], iconAnchor: [15, 15]
                    })
                });
            } else {
                marker = L.circleMarker(latLng, {
                    radius: 5, fillColor: style.color, color: "#000", weight: 1, opacity: 1, fillOpacity: 0.8
                });
            }

            var p = '<div style="font-family:sans-serif;min-width:180px;">' +
                    '<div style="font-size:10px;color:' + style.color + ';font-weight:bold;text-transform:uppercase;">' + style.label + '</div>' +
                    '<div style="font-size:14px;font-weight:bold;margin:4px 0;border-bottom:1px solid #ccc;padding-bottom:4px;">' + name + '</div>';
            if (memo) {
                p += '<div style="font-size:12px;color:#444;background:#f4f4f4;padding:5px;border-radius:3px;line-height:1.4;">' + memo + '</div>';
            }
            p += '</div>';
            marker.bindPopup(p);

            var tooltipText = memo ? memo : name;
            marker.bindTooltip(tooltipText, {
                direction: 'top', sticky: true, className: 'item-tooltip', opacity: 0.9, offset: [0, -10]
            });

            if (!layers[style.label]) { layers[style.label] = L.layerGroup(); }
            marker.addTo(layers[style.label]);
        }

        var overlayMaps = {};
        Object.keys(styles).forEach(key => {
            if (key === 'trash' && !isDebug) return;
            var lbl = styles[key].label;
            
            if (layers[lbl]) {
                overlayMaps[lbl] = layers[lbl];
                // 初期非表示リスト
                const hiddenKeys = ['monolith', 'scanner', 'cave'];
                if (!hiddenKeys.includes(key)) {
                    layers[lbl].addTo(map);
                }
            }
        });
        L.control.layers(null, overlayMaps, { collapsed: false, position: 'topright' }).addTo(map);
    })
    .catch(e => console.error(e));
})();