(function() {
    console.log("Map Script Loaded via GitHub (Sub-Category Support V1)");

    var maxZoom = 5; 
    var imgW = 6253;
    var imgH = 7104;
    var mapPadding = 1500; 

    // ★追加機能：HTMLの data-filter 属性からフィルタ設定を読み込む
    var mapDiv = document.getElementById('game-map');
    var filterMode = mapDiv ? mapDiv.getAttribute('data-filter') : null; //例: 'blueprint'

    var csvUrl = 'https://raw.githubusercontent.com/lime0404forest-commits/map/main/games/StarRupture/None/master_data.csv';
    
    // ★キャッシュ対策：バージョンを更新
    var tileUrl = 'https://lost-in-games.com/starrupture-map/tiles/{z}/{x}/{y}.webp?v=20260112_SUB1';

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

    var catMapping = {
        'LOC_SPARE_2': styles.scanner, 
        'LOC_BASE': styles.start, 
        'ITEM_WEAPON': styles.blueprint,
        'ITEM_OTHER': styles.warbond, 
        'ITEM_GEAR': styles.point, 
        'LOC_SPARE_1': styles.lem,
        'LOC_CAVEORMINE': styles.cave, 
        'LOC_POI': styles.monolith, 
        'MISC_OTHER': styles.trash,
        'LOC_TREASURE': styles.other, 
        'RES_PLANT': styles.other, 
        'RES_MINERAL': styles.other,
        'RES_OTHER': styles.other, 
        'LOC_SETTLE': styles.other, 
        'CHAR_NPC': styles.other,
        'CHAR_TRADER': styles.other, 
        'CHAR_OTHER': styles.other, 
        'MISC_ENEMY': styles.other,
        'LOC_ENEMY': styles.other, 
        'MISC_QUEST': styles.other, 
        'LOC_MEMO': styles.other
    };

    window.map = L.map('game-map', {
        crs: L.CRS.Simple, 
        minZoom: 0, 
        maxZoom: maxZoom, 
        zoom: 3, 
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
    map.setZoom(3); // 初期ズーム固定

    L.tileLayer(tileUrl, { 
        minZoom: 0, maxZoom: maxZoom, tileSize: 256, noWrap: true, bounds: imageBounds, attribution: 'Map Data', tms: false
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

        // 判定用関数: カテゴリコードが、指定されたフィルタ(例:blueprint)に属するか？
        var isMatch = function(code, filter) {
            if (!code) return false;
            var s = catMapping[code];
            if (!s) return false;
            // stylesオブジェクトのキーを探す
            var styleKey = Object.keys(styles).find(key => styles[key] === s);
            return styleKey === filter;
        };

        for (var i = 1; i < rows.length; i++) {
            var cols = parseCSVRow(rows[i]);
            // 列数チェック（新フォーマットは最低でも9列以上はあるはず）
            if (cols.length < 8) continue;

            var x = parseFloat(cols[1]); 
            var y = parseFloat(cols[2]);
            if (isNaN(x) || isNaN(y)) continue;

            // ★修正：列番号の変更（サブカテゴリ対応）
            // 5:Main, 6:Sub1, 7:Sub2
            var catMain = cols[5] ? cols[5].trim().toUpperCase() : "";
            var catSub1 = cols[6] ? cols[6].trim().toUpperCase() : "";
            var catSub2 = cols[7] ? cols[7].trim().toUpperCase() : "";

            // デバッグモード以外で「ゴミ箱」ならスキップ
            if (catMain === 'MISC_OTHER' && !isDebug) continue;

            // ★フィルタリング処理
            // data-filter="blueprint" 等がある場合、Main/Sub1/Sub2のいずれかが一致すれば表示
            if (filterMode) {
                if (!isMatch(catMain, filterMode) && 
                    !isMatch(catSub1, filterMode) && 
                    !isMatch(catSub2, filterMode)) {
                    continue; // 一致しなければこのピンは生成しない
                }
            }

            // ピンの見た目は「Mainカテゴリ」で決定
            var style = catMapping[catMain] || styles.other;
            
            // ★修正：列番号の変更（Importance以降がズレる）
            // 3:NameJP, 4:NameEN は変わらず
            // 8:Importance, 9:MemoJP, 10:MemoEN に移動
            var name = isJa ? cols[3] : (cols[4] || cols[3]);
            var memo = isJa ? cols[9] : (cols[10] || "");

            var latLng = map.unproject([x, y], maxZoom);
            var marker;

            if (style.emoji) {
                var extra = (catMain === 'MISC_OTHER') ? ' debug-marker' : '';
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
            var styleObj = styles[key];
            var lbl = styleObj.label;
            
            if (layers[lbl]) {
                overlayMaps[lbl] = layers[lbl];
                
                // ★修正：フィルタモード時は、生成されたレイヤーを強制的にONにする
                if (filterMode) {
                    layers[lbl].addTo(map);
                } else {
                    // 通常時：初期非表示設定（pointも含める）
                    const hiddenKeys = ['monolith', 'scanner', 'cave', 'other', 'point'];
                    if (!hiddenKeys.includes(key)) {
                        layers[lbl].addTo(map);
                    }
                }
            }
        });
        L.control.layers(null, overlayMaps, { collapsed: false, position: 'topright' }).addTo(map);
    })
    .catch(e => console.error(e));
})();