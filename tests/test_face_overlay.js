const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const sandbox = {
    console,
    setInterval: () => 1,
    document: { addEventListener: () => {}, getElementById: () => null }
};
const source = fs.readFileSync('static/js/dashboard.js', 'utf8');
vm.runInNewContext(`${source}\nthis.DashboardUI = DashboardUI;`, sandbox);

const mapped = sandbox.DashboardUI.mapFaceBoxToVideo(
    [100, 50, 100, 100], 640, 480,
    { left: 0, top: 0, width: 800, height: 400 },
    { left: 0, top: 0, width: 800, height: 400 }
);

// object-fit: cover: scale 1.25, vertical crop 100px; horizontal mirror.
assert.deepStrictEqual(JSON.parse(JSON.stringify(mapped)), {
    left: 550, top: -37.5, width: 125, height: 125
});

assert.strictEqual(
    sandbox.DashboardUI._escapeHtml('<img src=x onerror="alert(1)">'),
    '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'
);

const renderedBoxes = [];
const layer = {
    replaceChildren: () => { renderedBoxes.length = 0; },
    appendChild: box => renderedBoxes.push(box),
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 })
};
const video = {
    videoWidth: 1280,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 })
};
sandbox.document.getElementById = id => {
    if (id === 'face-box-layer') return layer;
    if (id === 'camera-feed') return video;
    return null;
};
sandbox.document.createElement = () => ({
    className: '', style: {}, child: null,
    appendChild(child) { this.child = child; }
});

const tenVerifying = Array.from({ length: 10 }, (_, index) => ({
    bbox: [index * 100, 100, 80, 80],
    track_id: index + 1,
    user_id: index + 101,
    tipe: 'verifying',
    display_status: 'warning',
    display_label: 'Đang xác minh (2/3)'
}));
sandbox.DashboardUI.renderFaceResults(tenVerifying, 1280, 720);
assert.strictEqual(renderedBoxes.length, 10);
assert.ok(renderedBoxes.every(box => box.className === 'face-box warning'));
assert.ok(renderedBoxes.every(box => box.child.textContent === 'Đang xác minh (2/3)'));

sandbox.DashboardUI.renderFaceResults([{
    bbox: [100, 100, 80, 80], track_id: 1, user_id: 101,
    status: 'ok', data: { nama: 'DAO VINH', nim: '24D400056' },
    display_status: 'recognized', display_label: 'DAO VINH — 24D400056'
}], 1280, 720);
assert.strictEqual(renderedBoxes[0].className, 'face-box recognized');
assert.strictEqual(renderedBoxes[0].child.textContent, 'DAO VINH — 24D400056');

// A following verification frame for the same track/identity keeps the green
// identity label briefly instead of flickering back to yellow.
sandbox.DashboardUI.renderFaceResults([{
    bbox: [102, 100, 80, 80], track_id: 1, user_id: 101,
    tipe: 'verifying', display_status: 'warning',
    display_label: 'Đang xác minh (1/3)'
}], 1280, 720);
assert.strictEqual(renderedBoxes[0].className, 'face-box recognized');
assert.strictEqual(renderedBoxes[0].child.textContent, 'DAO VINH — 24D400056');

console.log('face overlay mapping tests: OK');
