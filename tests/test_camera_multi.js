const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function loadCameraManager() {
    const calls = {
        success: [], spoofWarning: [], spoofIndicator: [], toast: [], refresh: 0,
        faceResults: []
    };
    const indicator = { textContent: '' };
    const sandbox = {
        window: { crypto: { randomUUID: () => 'camera-test-id' } },
        document: { querySelector: () => indicator },
        console,
        setTimeout: (callback) => callback(),
        clearInterval: () => {},
        DashboardUI: {
            showRecognitionSuccess: data => calls.success.push(data),
            showSpoofingWarning: data => calls.spoofWarning.push(data),
            updateSpoofingIndicator: data => calls.spoofIndicator.push(data),
            renderFaceResults: (...args) => calls.faceResults.push(args),
            showToast: (...args) => calls.toast.push(args),
            refreshAbsensiTable: () => { calls.refresh += 1; }
        }
    };
    const source = fs.readFileSync('static/js/camera.js', 'utf8');
    vm.runInNewContext(`${source}\nthis.CameraManager = CameraManager;`, sandbox);
    return { manager: sandbox.CameraManager, calls, indicator };
}

{
    const { manager, calls, indicator } = loadCameraManager();
    manager.isProcessing = true;
    const spoofDetail = { is_real: false, label: 'SPOOFING', score: 0.2 };
    manager._handleRecognitionResult({
        status: 'ok',
        results: [
            { status: 'ok', data: { nama: 'A', nim: '001' },
              spoofing: { is_real: true, label: 'REAL', score: 1.0 } },
            { status: 'error', tipe: 'spoofing', spoofing: spoofDetail }
        ]
    });

    assert.strictEqual(calls.success.length, 0, 'global success overlay must stay hidden');
    assert.strictEqual(calls.spoofWarning.length, 1);
    assert.deepStrictEqual(calls.spoofWarning[0], spoofDetail);
    assert.deepStrictEqual(calls.spoofIndicator[0], spoofDetail);
    assert.strictEqual(calls.refresh, 1);
    assert.strictEqual(calls.faceResults.length, 1);
    assert.strictEqual(calls.faceResults[0][0].length, 2);
    assert.strictEqual(manager.isProcessing, false);
}

{
    const { manager, calls, indicator } = loadCameraManager();
    manager._handleRecognitionResult({
        status: 'error',
        results: [
            { status: 'error', tipe: 'no_jadwal' },
            { status: 'error', tipe: 'no_jadwal' }
        ]
    });

    assert.ok(calls.toast.some(item => item[1] === 'Không có lịch học'));
    assert.strictEqual(manager.isProcessing, false);
}

{
    const { manager, calls } = loadCameraManager();
    manager.isProcessing = true;
    const results = Array.from({ length: 10 }, (_, index) => ({
        status: 'skip',
        tipe: 'verifying',
        track_id: index + 1,
        user_id: index + 101,
        bbox: [index * 10, 0, 50, 50],
        display_status: 'warning',
        display_label: `Đang xác minh (2/3)`
    }));

    manager._handleRecognitionResult({ status: 'skip', results });

    assert.strictEqual(calls.faceResults.length, 1);
    assert.strictEqual(calls.faceResults[0][0].length, 10);
    assert.strictEqual(manager.isProcessing, false);
}

const cameraSource = fs.readFileSync('static/js/camera.js', 'utf8');
assert.match(cameraSource, /captureWidth:\s*1280/);
assert.match(cameraSource, /captureHeight:\s*720/);

console.log('camera multi-face UI tests: OK');
