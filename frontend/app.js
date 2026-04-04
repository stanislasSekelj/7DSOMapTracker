document.addEventListener("DOMContentLoaded", () => {
    const mapElement = document.getElementById("map");
    const statusContainer = document.getElementById("connection-status");
    const statusText = statusContainer.querySelector('.status-text');
    const positionInfo = document.getElementById("position-info");
    const xVal = document.getElementById("val-x");
    const yVal = document.getElementById("val-y");

    // Sidebar toggle logic
    const sidebar = document.getElementById("sidebar");
    document.getElementById("menu-toggle").addEventListener("click", () => sidebar.classList.add("active"));
    document.getElementById("menu-close").addEventListener("click", () => sidebar.classList.remove("active"));

    // Initialize map using CRS.Simple (flat coordinate plane)
    const map = L.map('map', {
        crs: L.CRS.Simple,
        minZoom: -1,
        maxZoom: 3,
        zoomControl: false, // will use custom or rely on scroll
        attributionControl: false
    });

    // We normalize the map to a 1000x1000 coordinate system to abstract away the image's actual resolution.
    // L.CRS.Simple places [0,0] at the bottom-left.
    const bounds = [[0, 0], [1000, 1000]]; 
    
    L.imageOverlay('assets/full_map.jpg', bounds).addTo(map);
    map.fitBounds(bounds);

    // ==========================================
    // Interactive Markers Initialization
    // ==========================================
    const categoryLayers = {};
    const nestedGroups = {};

    function convertZeroLuckToLatLng(mapX, mapY) {
        // We know our custom 18x18 tile image corresponds to a total width/height of 9216 units.
        // Coordinate bounds: 
        // X ranges from -4608 (Left) to +4608 (Right)
        // Y ranges from -4608 (Bottom) to +4608 (Top)
        // Since Leaflet places [0,0] at Bottom-Left, and MapY increases going North (Top):
        const lat = ((mapY + 4608) / 9216) * 1000;
        const lng = ((mapX + 4608) / 9216) * 1000;
        return [lat, lng];
    }

    const filesToLoad = [
        'json/gathering.json',
        'json/mining.json',
        'json/stellapoint.json',
        'json/treasure-box.json',
        'json/viewpoint.json',
        'json/warpoints.json'
    ];

    Promise.all(filesToLoad.map(file => fetch(file).then(res => res.json())))
        .then(results => {
            let totalLoaded = 0;
            results.forEach((data, index) => {
                const markersList = data.markers || [];
                totalLoaded += markersList.length;
                
                markersList.forEach(m => {
                    const mapPos = m.position?.map;
                    if (!mapPos || typeof mapPos.x === 'undefined' || typeof mapPos.y === 'undefined') return;

                    let mainCat = m.categoryId || "general";
                    let layerKey = mainCat;

                    // Split heavily saturated generic categories into distinct material types
                    if ((mainCat === "gathering" || mainCat === "mining") && m.title) {
                        layerKey = `${mainCat}_${m.title}`;
                        if (!categoryLayers[layerKey]) categoryLayers[layerKey] = L.layerGroup();
                        if (!nestedGroups[mainCat]) nestedGroups[mainCat] = new Set();
                        nestedGroups[mainCat].add(m.title);
                    } else {
                        if (!categoryLayers[mainCat]) categoryLayers[mainCat] = L.layerGroup();
                        if (!nestedGroups[mainCat]) nestedGroups[mainCat] = new Set();
                    }

                    const [lat, lng] = convertZeroLuckToLatLng(mapPos.x, mapPos.y);

                    const desc = m.description ? `<p>${m.description}</p>` : "";
                    const title = m.title ? `<b>${m.title}</b>` : "Unknown Point";
                    const popupContent = `<div class="marker-popup">${title}${desc}</div>`;

                    const iconOptions = {
                        className: 'zl-marker',
                        iconSize: [24, 24],
                        iconAnchor: [12, 12],
                        popupAnchor: [0, -12]
                    };

                    if (m.iconUrl || m.icon_url) {
                        iconOptions.iconUrl = m.iconUrl || m.icon_url;
                    }

                    const markerOpts = iconOptions.iconUrl ? { icon: L.icon(iconOptions) } : {};

                    L.marker([lat, lng], markerOpts)
                     .bindPopup(popupContent)
                     .addTo(categoryLayers[layerKey]);
                });
            });
            console.log(`Loaded ${totalLoaded} markers from ${filesToLoad.length} files successfully!`);

            buildSidebarMenu();
        })
        .catch(err => {
            console.error("Could not load marker JSON files:", err);
        });

    function saveActiveLayers() {
        const active = [];
        document.querySelectorAll('#custom-layers-control input[type="checkbox"]').forEach(input => {
            if (input.checked && input.dataset.layerKey) {
                active.push(input.dataset.layerKey);
            }
        });
        localStorage.setItem("7ds_saved_layers", JSON.stringify(active));
    }

    function buildSidebarMenu() {
        const container = document.getElementById("custom-layers-control");
        container.innerHTML = `
            <div style="display: flex; gap: 8px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <button id="btn-select-all" class="glass-btn" style="flex:1; padding: 6px; font-size: 0.8rem;">Select All</button>
                <button id="btn-deselect-all" class="glass-btn" style="flex:1; padding: 6px; font-size: 0.8rem;">Clear All</button>
            </div>
            <div id="layer-list-container" style="display:flex; flex-direction:column; gap:8px;"></div>
        `;
        
        const listContainer = document.getElementById("layer-list-container");

        let savedLayers = ['stellapiece', 'treasurebox_01', 'waypoint_open'];
        try {
            const stored = localStorage.getItem("7ds_saved_layers");
            if (stored) savedLayers = JSON.parse(stored);
        } catch(e) {}

        for (const mainCat in nestedGroups) {
            const displayMain = mainCat.charAt(0).toUpperCase() + mainCat.slice(1).replace(/_/g, " ");
            const subs = Array.from(nestedGroups[mainCat]).sort();
            
            const categoryEl = document.createElement("div");
            categoryEl.className = "layer-category";
            
            if (subs.length > 0) {
                // Has subcategories (Accordion)
                categoryEl.innerHTML = `
                    <div class="layer-category-title">
                        <span class="layer-arrow">▶</span>
                        🛡️ ${displayMain}
                    </div>
                    <div class="layer-items"></div>
                `;
                
                const titleNode = categoryEl.querySelector(".layer-category-title");
                titleNode.addEventListener("click", () => {
                    categoryEl.classList.toggle("expanded");
                });

                const itemsContainer = categoryEl.querySelector(".layer-items");
                subs.forEach(sub => {
                    const layerKey = `${mainCat}_${sub}`;
                    // make ID safe (replace spaces and special chars)
                    const safeId = layerKey.replace(/[\s\W+]/g, '-'); 
                    const isChecked = savedLayers.includes(layerKey) ? 'checked' : '';
                    if (isChecked) categoryLayers[layerKey].addTo(map);

                    const itemEl = document.createElement("label");
                    itemEl.className = "layer-item";
                    itemEl.innerHTML = `
                        <input type="checkbox" id="layer-cb-${safeId}" data-layer-key="${layerKey}" ${isChecked}>
                        <span>${sub}</span>
                    `;
                    itemsContainer.appendChild(itemEl);

                    itemEl.querySelector("input").addEventListener("change", (e) => {
                        if (e.target.checked) categoryLayers[layerKey].addTo(map);
                        else map.removeLayer(categoryLayers[layerKey]);
                        saveActiveLayers();
                    });
                });
            } else {
                // Flat item without subs
                const safeId = mainCat.replace(/[\s\W+]/g, '-');
                const isChecked = savedLayers.includes(mainCat) ? 'checked' : '';
                if (isChecked) categoryLayers[mainCat].addTo(map);

                categoryEl.innerHTML = `
                    <label class="layer-category-title" style="margin-bottom:0; font-weight:600;">
                        <input type="checkbox" id="layer-cb-${safeId}" data-layer-key="${mainCat}" style="margin-right:8px;" ${isChecked}>
                        <span>🛡️ ${displayMain}</span>
                    </label>
                `;
                categoryEl.querySelector("input").addEventListener("change", (e) => {
                    if (e.target.checked) categoryLayers[mainCat].addTo(map);
                    else map.removeLayer(categoryLayers[mainCat]);
                    saveActiveLayers();
                });
            }

            listContainer.appendChild(categoryEl);
        }

        // Bind Select/Clear All
        document.getElementById('btn-select-all').addEventListener('click', () => {
            document.querySelectorAll('#layer-list-container input[type="checkbox"]').forEach(input => {
                if (!input.checked) {
                    input.checked = true;
                    categoryLayers[input.dataset.layerKey].addTo(map);
                }
            });
            saveActiveLayers();
        });

        document.getElementById('btn-deselect-all').addEventListener('click', () => {
            document.querySelectorAll('#layer-list-container input[type="checkbox"]').forEach(input => {
                if (input.checked) {
                    input.checked = false;
                    map.removeLayer(categoryLayers[input.dataset.layerKey]);
                }
            });
            saveActiveLayers();
        });
    }


    // Calibration Offsets
    let calibrationDX = 0;
    let calibrationDY = 0;
    const dxLabel = document.getElementById("offset-x");
    const dyLabel = document.getElementById("offset-y");

    document.getElementById("reset-offset").addEventListener("click", () => {
        calibrationDX = 0;
        calibrationDY = 0;
        dxLabel.textContent = calibrationDX;
        dyLabel.textContent = calibrationDY;
    });

    // Use arrow keys to manually nudge the marker offset
    document.addEventListener("keydown", (e) => {
        const step = e.shiftKey ? 1.0 : 0.1; // Hold shift for larger steps
        let changed = false;
        if (e.key === "ArrowUp") {
            calibrationDY += step;
            changed = true;
        } else if (e.key === "ArrowDown") {
            calibrationDY -= step;
            changed = true;
        } else if (e.key === "ArrowLeft") {
            calibrationDX -= step;
            changed = true;
        } else if (e.key === "ArrowRight") {
            calibrationDX += step;
            changed = true;
        }

        if (changed) {
            dxLabel.textContent = calibrationDX.toFixed(1);
            dyLabel.textContent = calibrationDY.toFixed(1);
            
            // If marker exists, instantly apply nudge visually
            if (marker && lastData) {
                updateMarkerPosition(lastData);
            }
        }
    });

    // Create a custom icon for the player marker
    const playerIcon = L.divIcon({
        className: 'player-marker',
        html: '<div class="player-marker-inner"></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15] // Centered perfectly by Leaflet
    });

    let marker = null;
    let ws = null;
    let lastData = null;

    function updateMarkerPosition(data) {
        // The python backend returns float values [0...1]
        // X goes 0->1 from Left to Right
        // Y goes 0->1 from Top to Bottom
        // But Leaflet CRS.Simple coords are [Lat, Lng] where Lat is Y (0 is bottom) and Lng is X (0 is left).
        // Thus: Lat = 1000 - (Y% * 1000), Lng = X% * 1000
        const lat = 1000 - (data.y_pct * 1000) + calibrationDY;
        const lng = data.x_pct * 1000 + calibrationDX;

        // Update UI Display (showing internal 1-100% coords for coolness)
        xVal.textContent = (data.x_pct * 100).toFixed(1) + "%";
        yVal.textContent = (data.y_pct * 100).toFixed(1) + "%";
        positionInfo.classList.remove('hidden');

        if (!marker) {
            marker = L.marker([lat, lng], {icon: playerIcon}).addTo(map);
            // Center the map on player when initially found
            map.setView([lat, lng], 1);
        } else {
            // Smoothly animate the marker's new position
            marker.setLatLng([lat, lng]);
        }

        // Apply Real-time Angular Rotation
        if (data.angle !== undefined) {
            const inner = marker.getElement()?.querySelector('.player-marker-inner');
            if (inner) {
                inner.style.transform = `rotate(${data.angle}deg)`;
            }
        }
    }

    function connectWebSocket() {
        // Connect to the backend Scanner service
        ws = new WebSocket("ws://localhost:8765");

        ws.onopen = () => {
            console.log("Connected to local tracking server");
            statusContainer.classList.remove('status-disconnected');
            statusContainer.classList.add('status-connected');
            statusText.textContent = 'Connected & Scanning';
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.found && data.x_pct !== undefined && data.y_pct !== undefined) {
                lastData = data;
                updateMarkerPosition(data);
            } else {
                // If the backend can't find a confident match for this frame
                positionInfo.classList.add('hidden');
            }
        };

        ws.onclose = () => {
            console.log("Disconnected from local tracking server. Reconnecting in 3s...");
            statusContainer.classList.remove('status-connected');
            statusContainer.classList.add('status-disconnected');
            statusText.textContent = 'Disconnected';
            positionInfo.classList.add('hidden');
            
            // Cleanup marker
            if (marker) {
                map.removeLayer(marker);
                marker = null;
            }

            setTimeout(connectWebSocket, 3000);
        };
        
        ws.onerror = (err) => {
            console.error("WebSocket Error: ", err);
            ws.close();
        };
    }

    // Start connection
    connectWebSocket();
});
