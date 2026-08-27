/**
 * camera.js — Streaming kamera ke dashboard via WebSocket
 * Mengirim frame kamera ke server setiap 500ms untuk proses recognition
 */

// === State kamera ===
const CameraManager = {
    stream: null,           // MediaStream dari getUserMedia
    video: null,            // Element <video>
    canvas: null,           // Canvas untuk capture frame
    ctx: null,              // Canvas 2D context
    isActive: false,        // Status kamera aktif/tidak
    intervalId: null,       // Interval pengiriman frame
    socket: null,           // SocketIO connection
    frameInterval: 250,     // One in-flight frame; backpressure controls cadence.
    captureWidth: 1280,
    captureHeight: 720,
    lastResult: null,       // Hasil recognition terakhir
    isProcessing: false,    // Mencegah penumpukan frame (backpressure)
    lastProcessTime: 0,     // Waktu terakhir frame dikirim (untuk timeout)
    clientId: (window.crypto && window.crypto.randomUUID)
        ? window.crypto.randomUUID()
        : 'cam_' + Date.now() + '_' + Math.random().toString(36).slice(2),

    /**
     * Inisialisasi kamera manager
     * Dipanggil saat halaman dashboard dimuat
     */
    init: function () {
        this.video = document.getElementById('camera-feed');
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');

        // Inisialisasi SocketIO
        this._initSocket();

        console.log('[CAMERA] Manager berhasil diinisialisasi.');
    },

    /**
     * Inisialisasi koneksi SocketIO
     */
    _initSocket: function () {
        // Gunakan SocketIO jika tersedia
        if (typeof io !== 'undefined') {
            this.socket = io({
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: 5
            });

            this.socket.on('connect', () => {
                console.log('[SOCKET] Terhubung ke server.');
                DashboardUI.updateConnectionStatus(true);
            });

            this.socket.on('disconnect', () => {
                console.log('[SOCKET] Terputus dari server.');
                DashboardUI.updateConnectionStatus(false);
            });

            // Terima hasil recognition dari server
            this.socket.on('recognition_result', (data) => {
                console.log('[SOCKET] recognition_result:', data);
                this._handleRecognitionResult(data);
            });

            // Terima update absensi baru (broadcast ke semua client)
            this.socket.on('absensi_update', (data) => {
                DashboardUI.addAbsensiRow(data);
                DashboardUI.updateStats(data.stats);
            });

            this.socket.on('connect_error', (err) => {
                console.warn('[SOCKET] Gagal terhubung:', err.message);
            });
        } else {
            console.warn('[CAMERA] SocketIO tidak tersedia, gunakan mode polling.');
        }
    },

    /**
     * Nyalakan kamera — akses webcam dan mulai stream
     */
    start: async function () {
        if (this.isActive) return;

        try {
            const health = await this._checkFaceHealth();
            if (!health.ready || !health.automatic_attendance_ready) {
                DashboardUI.showToast(
                    'warning',
                    'Mô hình chưa sẵn sàng',
                    health.error || 'Hãy cập nhật gallery khuôn mặt trước khi mở camera.'
                );
                return;
            }

            // Minta akses kamera
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: this.captureWidth },
                    height: { ideal: this.captureHeight },
                    facingMode: 'user'
                },
                audio: false
            });

            // Tampilkan di video element
            this.video.srcObject = this.stream;
            this.video.classList.add('active');
            await this.video.play();

            // Preserve the actual stream aspect ratio. The browser is asked for
            // 1280x720, while the backend detector still letterboxes to 640.
            this.canvas.width = this.video.videoWidth || this.captureWidth;
            this.canvas.height = this.video.videoHeight || this.captureHeight;

            this.isActive = true;

            // Sembunyikan placeholder
            const placeholder = document.getElementById('camera-placeholder');
            if (placeholder) placeholder.classList.add('hidden');

            // Mulai kirim frame ke server
            this._startStreaming();

            // Beritahu server kamera ON
            if (this.socket && this.socket.connected) {
                this.socket.emit('camera_toggle', {
                    active: true,
                    client_id: this.clientId
                });
            }

            DashboardUI.updateCameraButtons(true);
            DashboardUI.showToast('success', 'Máy ảnh đã bật', 'Nhận diện khuôn mặt và chống giả mạo đang hoạt động.');

            console.log('[CAMERA] Kamera berhasil dinyalakan.');
        } catch (err) {
            console.error('[CAMERA] Gagal akses kamera:', err);
            DashboardUI.showToast('error', 'Không thể truy cập máy ảnh',
                'Hãy bảo đảm máy ảnh đã được kết nối và bạn đã cấp quyền truy cập.');
        }
    },

    _checkFaceHealth: async function () {
        const response = await fetch('/api/face/health', {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });
        if (response.status === 401) {
            window.location.href = '/login';
            return { ready: false, automatic_attendance_ready: false };
        }
        const payload = await response.json().catch(() => ({}));
        return {
            ready: response.ok && payload.ready === true,
            automatic_attendance_ready: payload.automatic_attendance_ready === true,
            error: payload.error || payload.pesan || null
        };
    },

    /**
     * Matikan kamera — stop stream dan clear interval
     */
    stop: function () {
        if (!this.isActive) return;

        // Stop interval pengiriman frame
        this._stopStreaming();

        // Stop media stream
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        // Reset video element
        this.video.srcObject = null;
        this.video.classList.remove('active');

        this.isActive = false;

        // Tampilkan placeholder
        const placeholder = document.getElementById('camera-placeholder');
        if (placeholder) placeholder.classList.remove('hidden');

        // Beritahu server kamera OFF
        if (this.socket && this.socket.connected) {
            this.socket.emit('camera_toggle', {
                active: false,
                client_id: this.clientId
            });
        } else {
            fetch('/api/camera/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active: false, client_id: this.clientId }),
                keepalive: true
            }).catch(() => {});
        }

        // Sembunyikan overlay recognition
        DashboardUI.hideRecognitionOverlay();
        if (typeof DashboardUI.renderFaceResults === 'function') {
            DashboardUI.renderFaceResults([], 0, 0);
        }
        DashboardUI.updateCameraButtons(false);
        DashboardUI.showToast('info', 'Máy ảnh đã tắt', 'Đã dừng truyền hình ảnh.');

        console.log('[CAMERA] Kamera dimatikan.');
    },

    /**
     * Mulai streaming — capture dan kirim frame periodik
     */
    _startStreaming: function () {
        this.intervalId = setInterval(() => {
            if (!this.isActive || !this.video.videoWidth) return;
            
            // Safety timeout: jika isProcessing nyangkut lebih dari 5 detik, paksa buka
            if (this.isProcessing) {
                if (Date.now() - this.lastProcessTime > 5000) {
                    console.warn('[CAMERA] Timeout response dari server, force unlock isProcessing.');
                    this.isProcessing = false;
                } else {
                    return; // Tunggu response
                }
            }
            
            this.isProcessing = true; // Kunci frame
            this.lastProcessTime = Date.now(); // Catat waktu mulai
            this._captureAndSend();
        }, this.frameInterval);
    },

    /**
     * Stop streaming
     */
    _stopStreaming: function () {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

    },

    /**
     * Capture frame dari video dan kirim ke server
     */
    _captureAndSend: function () {
        // Gambar video ke canvas
        this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

        // Konversi ke base64 JPEG (kompresi 70%)
        const frameData = this.canvas.toDataURL('image/jpeg', 0.7);

        // Kirim via SocketIO (lebih cepat dari HTTP)
        if (this.socket && this.socket.connected) {
            this.socket.emit('process_frame', {
                frame: frameData,
                client_id: this.clientId
            });
        } else {
            // Fallback: kirim via HTTP POST
            this._sendFrameHTTP(frameData);
        }
    },

    /**
     * Fallback: kirim frame via HTTP jika WebSocket tidak tersedia
     */
    _sendFrameHTTP: async function (frameData) {
        try {
            const response = await fetch('/api/absensi/proses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame: frameData, client_id: this.clientId })
            });
            if (response.status === 401) {
                this.stop();
                window.location.href = '/login';
                return;
            }
            const result = await response.json();
            this._handleRecognitionResult(result);
        } catch (err) {
            this.isProcessing = false;
            console.warn('[CAMERA] Gagal kirim frame via HTTP:', err);
        }
    },

    /**
     * Handle hasil recognition dari server
     */
    _handleRecognitionResult: function (data) {
        if (data && data.status === 'error' && data.pesan && (data.pesan.includes('hết hạn') || data.pesan.includes('het han'))) {
            this.stop();
            window.location.href = '/login';
            return;
        }
        this.lastResult = data;
        if (typeof DashboardUI.renderFaceResults === 'function') {
            DashboardUI.renderFaceResults(
                Array.isArray(data.results) ? data.results : [],
                this.canvas ? this.canvas.width : this.captureWidth,
                this.canvas ? this.canvas.height : this.captureHeight
            );
        }
        // Per-face labels are the source of truth. The old global processing
        // pill is intentionally no longer rendered.
        var indicatorSpan = null;

        // Response nhiều khuôn mặt: hiển thị theo nhóm và chỉ refresh một lần.
        if (Array.isArray(data.results) && data.results.length > 1) {
            this._handleMultiRecognitionResult(data, indicatorSpan);
            return;
        }
        
        // Default: buka kunci langsung (kecuali untuk error tertentu)
        let releaseLockNow = true;

        // Skip — berbagai tipe
        if (data.status === 'skip') {
            if (data.tipe === 'verifying') {
                if (indicatorSpan) indicatorSpan.textContent = '🔍 ' + (data.pesan || 'Đang xác minh...');
            } else if (data.tipe === 'no_face') {
                if (indicatorSpan) indicatorSpan.textContent = 'Đang tìm khuôn mặt...';
            } else {
                if (indicatorSpan) indicatorSpan.textContent = 'Đang tìm khuôn mặt...';
            }
            if (releaseLockNow) this.isProcessing = false;
            return;
        }

        if (data.status === 'error') {
            // Spoofing terdeteksi
            if (data.tipe === 'spoofing') {
                if (indicatorSpan) indicatorSpan.textContent = '⚠️ Phát hiện giả mạo!';
                DashboardUI.showSpoofingWarning(data);
            } else if (data.tipe === 'duplikat') {
                if (indicatorSpan) indicatorSpan.textContent = '✓ Đã điểm danh';
                this._throttledToast('info', 'Đã điểm danh', data.pesan || 'Sinh viên đã điểm danh hôm nay.');
                releaseLockNow = true;
            } else if (data.tipe === 'unknown') {
                if (indicatorSpan) indicatorSpan.textContent = '? Không nhận diện được khuôn mặt';
                this._throttledToast('warning', 'Không nhận diện được', data.pesan || 'Khuôn mặt không khớp với dữ liệu đã đăng ký.');
                releaseLockNow = true;
            } else if (data.tipe === 'no_jadwal') {
                if (indicatorSpan) indicatorSpan.textContent = '⏰ Không có lịch học';
                this._throttledToast('warning', 'Không có lịch học', data.pesan || 'Hiện không có lịch học nào đang diễn ra.');
                releaseLockNow = true;
            } else if (data.tipe === 'multiple_active_schedules') {
                if (indicatorSpan) indicatorSpan.textContent = '⚠ Lịch học bị trùng';
                this._throttledToast('warning', 'Cần xử lý lịch học', data.pesan || 'Có nhiều lịch học đang hoạt động cho lớp này.');
                releaseLockNow = true;
            } else if (data.tipe === 'database_unavailable') {
                this._throttledToast('error', 'CSDL chưa sẵn sàng', data.pesan || 'Không thể đọc/ghi cơ sở dữ liệu lúc này.');
                releaseLockNow = true;
            } else if (data.tipe === 'model_unavailable') {
                if (indicatorSpan) indicatorSpan.textContent = 'Mô hình chưa sẵn sàng';
                this._throttledToast(
                    'warning', 'Mô hình chưa sẵn sàng',
                    data.pesan || 'Hãy chạy test_setup.py một lần để tải mô hình InsightFace.'
                );
            } else {
                if (indicatorSpan) indicatorSpan.textContent = 'Đang xử lý...';
                console.warn('[CAMERA] Recognition error:', data.pesan);
            }
            if (releaseLockNow) this.isProcessing = false;
            return;
        }

        if (data.status === 'ok') {
            if (indicatorSpan) indicatorSpan.textContent = '✓ ' + data.data.nama;
            // Wajah berhasil dikenali dan absensi dicatat
            const statusLabels = {
                hadir: 'Có mặt',
                terlambat: 'Đi muộn',
                izin: 'Vắng có phép',
                sakit: 'Nghỉ ốm',
                alpha: 'Vắng không phép'
            };
            DashboardUI.showToast('success', 'Đã ghi nhận điểm danh',
                `${data.data.nama} — ${statusLabels[data.data.status_absensi] || data.data.status_absensi}`);
            // Refresh tabel absensi
            DashboardUI.refreshAbsensiTable();
            // Tahan sebentar setelah berhasil absen sebelum scan lagi
            releaseLockNow = true;
            this.isProcessing = false;
        }

        // Update spoofing indicator
        if (data.spoofing) {
            DashboardUI.updateSpoofingIndicator(data.spoofing);
        }
    },

    /** Handle kết quả của một frame có nhiều khuôn mặt. */
    _handleMultiRecognitionResult: function (data, indicatorSpan) {
        const results = data.results || [];
        const successes = results.filter(item => item.status === 'ok' && item.data);
        const verifying = results.filter(item => item.status === 'skip' && item.tipe === 'verifying');
        const conflicts = results.filter(item => item.tipe === 'identity_conflict');
        const unknown = results.filter(item => item.tipe === 'unknown');
        const spoofing = results.filter(item => item.tipe === 'spoofing');
        const duplicates = results.filter(item => item.tipe === 'duplikat');
        const noSchedule = results.filter(item => item.tipe === 'no_jadwal');
        const multipleActiveSchedules = results.filter(item => item.tipe === 'multiple_active_schedules');
        const dbErrors = results.filter(item => item.tipe === 'database_unavailable');

        if (successes.length > 0) {
            const names = successes.map(item => item.data.nama).join(', ');
            if (indicatorSpan) indicatorSpan.textContent = `✓ Đã điểm danh ${successes.length} người`;
            DashboardUI.showToast('success', `Đã ghi ${successes.length} lượt điểm danh`, names);
            DashboardUI.refreshAbsensiTable();
        } else if (verifying.length > 0) {
            if (indicatorSpan) indicatorSpan.textContent = `🔍 Đang xác minh ${verifying.length} khuôn mặt...`;
        } else if (duplicates.length > 0) {
            if (indicatorSpan) indicatorSpan.textContent = '✓ Các sinh viên đã điểm danh';
            this._throttledToast('info', 'Đã điểm danh', `${duplicates.length} sinh viên đã có dữ liệu điểm danh.`);
        } else if (spoofing.length > 0) {
            if (indicatorSpan) indicatorSpan.textContent = '⚠️ Phát hiện giả mạo';
            DashboardUI.showSpoofingWarning(spoofing[0].spoofing || spoofing[0]);
        } else if (conflicts.length > 0) {
            if (indicatorSpan) indicatorSpan.textContent = '⚠ Trùng danh tính trong khung hình';
            this._throttledToast(
                'warning', 'Cần tách vị trí',
                'Hai khuôn mặt bị gán cùng một sinh viên. Hãy đứng tách nhau và thử lại.'
            );
        } else if (unknown.length > 0) {
            if (indicatorSpan) indicatorSpan.textContent = '? Có khuôn mặt chưa nhận diện';
            this._throttledToast(
                'warning', 'Chưa nhận diện',
                `${unknown.length} khuôn mặt chưa khớp dữ liệu đăng ký.`
            );
        } else if (noSchedule.length > 0) {
            if (indicatorSpan) indicatorSpan.textContent = '⏰ Không có lịch học';
            this._throttledToast(
                'warning', 'Không có lịch học',
                'Không có lịch học phù hợp vào thời điểm này.'
            );
        } else if (multipleActiveSchedules.length > 0) {
            if (indicatorSpan) indicatorSpan.textContent = '⚠ Lịch học bị trùng';
            this._throttledToast(
                'warning', 'Cần xử lý lịch học',
                'Có nhiều lịch học đang hoạt động cho cùng một lớp; chưa ghi điểm danh.'
            );
        } else if (dbErrors.length > 0) {
            this._throttledToast(
                'error', 'CSDL chưa sẵn sàng',
                'Không thể đọc/ghi cơ sở dữ liệu lúc này.'
            );
        } else if (indicatorSpan) {
            indicatorSpan.textContent = 'Đang tìm khuôn mặt...';
        }

        // Không để một lượt điểm danh thành công che mất khuôn mặt giả mạo khác.
        if (successes.length > 0 && spoofing.length > 0) {
            DashboardUI.showSpoofingWarning(spoofing[0].spoofing || spoofing[0]);
            this._throttledToast(
                'warning', 'Phát hiện giả mạo',
                `${spoofing.length} khuôn mặt không vượt qua kiểm tra chống giả mạo.`
            );
        }

        const representativeSpoof = spoofing[0] || results.find(item => item.spoofing);
        if (representativeSpoof) {
            DashboardUI.updateSpoofingIndicator(representativeSpoof.spoofing);
        }

        this.isProcessing = false;
    },

    /** Toast với throttle để tránh spam thông báo lặp lại. */
    _throttledToast: function (type, title, message) {
        var now = Date.now();
        var key = type + ':' + title;
        if (!this._toastTimers) this._toastTimers = {};
        if (this._toastTimers[key] && now - this._toastTimers[key] < 5000) return;
        this._toastTimers[key] = now;
        DashboardUI.showToast(type, title, message);
    }
};
