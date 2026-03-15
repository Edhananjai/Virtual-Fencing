/**
 * map.js — Leaflet map setup, fence drawing, and animal marker management.
 */

let map;
let fenceLayer = null;       // L.polygon for the current fence
let drawingPoints = [];       // Temp points while drawing
let drawingMarkers = [];      // Temp markers while drawing
let drawingMode = false;
let animalMarkers = {};       // { node_name: L.marker }
let trailLines = {};          // { node_name: L.polyline }

const TRAIL_MAX_POINTS = 50;

// Custom animal icon
const animalIcon = L.divIcon({
    html: '<div style="font-size:24px;">&#128004;</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    className: 'animal-icon',
});

const alertIcon = L.divIcon({
    html: '<div style="font-size:24px;">&#9888;&#65039;</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    className: 'alert-icon',
});


function initMap(centerLat, centerLon, zoom) {
    map = L.map('map').setView([centerLat, centerLon], zoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
    }).addTo(map);

    // Click handler for drawing fence
    map.on('click', onMapClick);
}


function drawFence(vertices) {
    if (fenceLayer) {
        map.removeLayer(fenceLayer);
    }
    if (vertices && vertices.length >= 3) {
        fenceLayer = L.polygon(vertices, {
            color: '#00e676',
            fillColor: '#00e676',
            fillOpacity: 0.1,
            weight: 2,
            dashArray: '8 4',
        }).addTo(map);
    }
}


function onMapClick(e) {
    if (!drawingMode) return;

    const point = [e.latlng.lat, e.latlng.lng];
    drawingPoints.push(point);

    // Add a small circle marker at each click point
    const marker = L.circleMarker(e.latlng, {
        radius: 6,
        color: '#e94560',
        fillColor: '#e94560',
        fillOpacity: 1,
    }).addTo(map);
    drawingMarkers.push(marker);

    // Draw preview polygon
    drawFence(drawingPoints);
}


function startDrawing() {
    drawingMode = true;
    drawingPoints = [];
    clearDrawingMarkers();
    if (fenceLayer) {
        map.removeLayer(fenceLayer);
        fenceLayer = null;
    }
}


function clearDrawingMarkers() {
    drawingMarkers.forEach(m => map.removeLayer(m));
    drawingMarkers = [];
}


function finishDrawing() {
    drawingMode = false;
    clearDrawingMarkers();
    return drawingPoints.length >= 3 ? [...drawingPoints] : null;
}


function cancelDrawing() {
    drawingMode = false;
    drawingPoints = [];
    clearDrawingMarkers();
}


function updateAnimalMarker(nodeName, lat, lon, insideFence) {
    // null/undefined = not monitoring (use normal icon), true = inside, false = outside
    const icon = (insideFence === false) ? alertIcon : animalIcon;

    if (animalMarkers[nodeName]) {
        animalMarkers[nodeName].setLatLng([lat, lon]);
        animalMarkers[nodeName].setIcon(icon);
    } else {
        animalMarkers[nodeName] = L.marker([lat, lon], { icon })
            .bindTooltip(nodeName, { permanent: true, direction: 'top', offset: [0, -15] })
            .addTo(map);
    }

    // Update trail
    if (!trailLines[nodeName]) {
        trailLines[nodeName] = L.polyline([], {
            color: '#53c5ff',
            weight: 2,
            opacity: 0.6,
        }).addTo(map);
    }
    const trail = trailLines[nodeName];
    const latlngs = trail.getLatLngs();
    latlngs.push(L.latLng(lat, lon));
    if (latlngs.length > TRAIL_MAX_POINTS) {
        latlngs.shift();
    }
    trail.setLatLngs(latlngs);
}
