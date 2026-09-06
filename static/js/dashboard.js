/**
 * dashboard.js — Logic tombol ON/OFF kamera, update real-time tabel absensi
 * Mengontrol UI dashboard dan menampilkan hasil recognition
 */

const DashboardUI = {
    _faceSuccessHoldMs: 2500,
    _faceSuccessByTrack: new Map(),

    _escapeHtml: function (value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    /**
     * Inisialisasi event listener dan UI dashboard
     */
    init: function () {
        // Tombol kontrol kamera
        const btnOn = document.getElementById('btn-camera-on');
        const btnOff = document.getElementById('btn-camera-off');

        if (btnOn) {
            btnOn.addEventListener('click', () => CameraManager.start());
        }
        if (btnOff) {
            btnOff.addEventListener('click', () => CameraManager.stop());
        }

        // Tải dữ liệu ban đầu và auto-refresh absensi ngày hôm nay mỗi 30 giây
        this.refreshAbsensiTable();
        setInterval(() => this.refreshAbsensiTable(), 30000);

        console.log('[DASHBOARD] UI berhasil diinisialisasi.');
    },

    /**
     * Update tampilan tombol kamera berdasarkan status
     */
    updateCameraButtons: function (isActive) {
        const btnOn = document.getElementById('btn-camera-on');
        const btnOff = document.getElementById('btn-camera-off');

        if (isActive) {
            if (btnOn) btnOn.style.display = 'none';
            if (btnOff) btnOff.style.display = 'flex';
        } else {
            if (btnOn) btnOn.style.display = 'flex';
            if (btnOff) btnOff.style.display = 'none';
        }
    },

    /**
     * Update indikator koneksi WebSocket
     */
    updateConnectionStatus: function (connected) {
        const indicator = document.getElementById('connection-status');
        if (!indicator) return;

        if (connected) {
            indicator.textContent = 'Đã kết nối';
            indicator.classList.remove('text-error');
            indicator.classList.add('text-emerald-500');
        } else {
            indicator.textContent = 'Mất kết nối';
            indicator.classList.remove('text-emerald-500');
            indicator.classList.add('text-error');
        }
    },

    /**
     * Update indikator anti-spoofing
     */
    updateSpoofingIndicator: function (spoofData) {
        const indicator = document.getElementById('spoofing-indicator');
        if (!indicator) return;

        if (spoofData.is_real) {
            indicator.className = 'active';
            indicator.querySelector('.dot').style.background = '#34d399';
            indicator.querySelector('.label').textContent = 'Chống giả mạo: Bình thường';
        } else {
            indicator.className = 'warning';
            indicator.querySelector('.dot').style.background = '#f87171';
            indicator.querySelector('.label').textContent = 'PHÁT HIỆN GIẢ MẠO!';
        }
    },

    /**
     * Tampilkan peringatan spoofing
     */
    showSpoofingWarning: function (data) {
        const overlay = document.getElementById('recognition-overlay');
        if (!overlay) return;

        overlay.innerHTML = `
            <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-3xl text-error">gpp_bad</span>
                <div>
                    <p class="recognition-name text-error">⚠️ Phát hiện giả mạo!</p>
                    <p class="recognition-detail">Điểm: ${data.score || '-'} — Khuôn mặt không phải người thật</p>
                </div>
            </div>
        `;
        overlay.classList.add('active');

        // Sembunyikan setelah 3 detik
        setTimeout(() => overlay.classList.remove('active'), 3000);

        this.showToast('error', 'Phát hiện giả mạo',
            'Hệ thống phát hiện hành vi giả mạo. Vui lòng sử dụng khuôn mặt thật.');
    },

    /**
     * Tampilkan hasil recognition berhasil di overlay
     */
    showRecognitionSuccess: function (data) {
        const overlay = document.getElementById('recognition-overlay');
        if (!overlay) return;

        const statusClass = data.status_absensi === 'hadir' ? 'hadir' : 'terlambat';
        const statusLabels = {
            hadir: 'Có mặt',
            terlambat: 'Đi muộn',
            izin: 'Vắng có phép',
            sakit: 'Nghỉ ốm',
            alpha: 'Vắng không phép'
        };
        const statusLabel = statusLabels[data.status_absensi] || data.status_absensi;
        const statusIcon = data.status_absensi === 'hadir' ? 'check_circle' : 'schedule';

        overlay.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <span class="material-symbols-outlined text-3xl text-emerald-400">face</span>
                    <div>
                        <p class="recognition-name">${this._escapeHtml(data.nama)}</p>
                        <p class="recognition-detail">${this._escapeHtml(data.nim)} — ${this._escapeHtml(data.nama_kelas)} — ${this._escapeHtml(data.nama_mk)}</p>
                    </div>
                </div>
                <span class="status-badge ${statusClass}">
                    <span class="material-symbols-outlined" style="font-size:14px">${statusIcon}</span>
                    ${this._escapeHtml(statusLabel)}
                </span>
            </div>
        `;
        overlay.classList.add('active');

        // Sembunyikan setelah 5 detik
        setTimeout(() => overlay.classList.remove('active'), 5000);
    },

    /**
     * Sembunyikan overlay recognition
     */
    hideRecognitionOverlay: function () {
        const overlay = document.getElementById('recognition-overlay');
        if (overlay) overlay.classList.remove('active');
    },

    /**
     * Convert a server bbox to the visible, mirrored video position. The camera
     * uses object-fit: contain, so letterboxing offsets must be accounted for.
     */
    mapFaceBoxToVideo: function (bbox, frameWidth, frameHeight, videoRect, layerRect) {
        if (!bbox || bbox.length !== 4 || !frameWidth || !frameHeight) return null;
        const [x, y, width, height] = bbox.map(Number);
        if (![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) return null;

        const scale = Math.min(videoRect.width / frameWidth, videoRect.height / frameHeight);
        const renderedWidth = frameWidth * scale;
        const renderedHeight = frameHeight * scale;
        const offsetX = (videoRect.width - renderedWidth) / 2;
        const offsetY = (videoRect.height - renderedHeight) / 2;

        // The CSS video is scaleX(-1), hence use the mirrored source x but keep
        // label text itself unmirrored in the HTML overlay.
        return {
            left: (videoRect.left - layerRect.left) + offsetX + (frameWidth - x - width) * scale,
            top: (videoRect.top - layerRect.top) + offsetY + y * scale,
            width: width * scale,
            height: height * scale
        };
    },

    renderFaceResults: function (results, frameWidth, frameHeight) {
        const layer = document.getElementById('face-box-layer');
        const video = document.getElementById('camera-feed');
        if (!layer || !video) return;

        layer.replaceChildren();
        if (!Array.isArray(results) || results.length === 0 || !video.videoWidth) return;

        const now = Date.now();
        this._faceSuccessByTrack.forEach((cached, key) => {
            if (cached.expiresAt <= now) this._faceSuccessByTrack.delete(key);
        });
        const visibleResults = results.map(result => {
            const hasIdentityKey = result.track_id !== null && result.track_id !== undefined &&
                result.user_id !== null && result.user_id !== undefined;
            const identityKey = hasIdentityKey ? `${result.track_id}:${result.user_id}` : null;
            if (identityKey && result.display_status === 'recognized' && result.data) {
                this._faceSuccessByTrack.set(identityKey, {
                    displayLabel: result.display_label,
                    data: result.data,
                    expiresAt: now + this._faceSuccessHoldMs
                });
                return result;
            }
            const cached = identityKey ? this._faceSuccessByTrack.get(identityKey) : null;
            if (cached && cached.expiresAt > now && result.tipe === 'verifying') {
                return {
                    ...result,
                    display_status: 'recognized',
                    display_label: cached.displayLabel,
                    data: cached.data
                };
            }
            return result;
        });

        const layerRect = layer.getBoundingClientRect();
        const videoRect = video.getBoundingClientRect();
        visibleResults.forEach(result => {
            const position = this.mapFaceBoxToVideo(
                result.bbox, frameWidth, frameHeight, videoRect, layerRect
            );
            if (!position) return;

            const box = document.createElement('div');
            const status = ['recognized', 'warning', 'error'].includes(result.display_status)
                ? result.display_status : 'warning';
            box.className = `face-box ${status}`;
            box.style.left = `${position.left}px`;
            box.style.top = `${position.top}px`;
            box.style.width = `${position.width}px`;
            box.style.height = `${position.height}px`;

            const label = document.createElement('span');
            label.className = 'face-box-label';
            const recognitionLabels = {
                spoofing: 'Giả mạo',
                identity_conflict: 'Xung đột danh tính',
                unknown: 'Không khớp',
                verifying: 'Đang xác minh',
                no_jadwal: 'Đã nhận diện — không có lịch học',
                needs_calibration: 'Cần hiệu chuẩn',
                duplikat: 'Đã điểm danh'
            };
            label.textContent = result.display_label ||
                recognitionLabels[result.tipe] || 'Đang phân tích';
            box.appendChild(label);
            layer.appendChild(box);
        });
    },

    /**
     * Tambahkan baris baru ke tabel absensi hari ini
     */
    addAbsensiRow: function (data) {
        const tbody = document.getElementById('absensi-tbody');
        if (!tbody) return;

        // Hapus pesan "belum ada absensi" jika ada
        const emptyRow = tbody.querySelector('.empty-row');
        if (emptyRow) emptyRow.remove();

        // Buat baris baru
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-surface-container-high transition-colors absensi-row-new absensi-item-row cursor-context-menu';
        if (data.id) tr.dataset.id = data.id;
        if (data.nama) tr.dataset.nama = data.nama;
        if (data.status) tr.dataset.status = data.status;

        // Tentukan badge status
        let badgeClass, badgeLabel;
        switch (data.status) {
            case 'hadir':
                badgeClass = 'bg-emerald-500/15 text-emerald-500';
                badgeLabel = 'Có mặt';
                break;
            case 'terlambat':
                badgeClass = 'bg-tertiary/15 text-tertiary';
                badgeLabel = 'Đi muộn';
                break;
            case 'izin':
                badgeClass = 'bg-secondary/15 text-secondary';
                badgeLabel = 'Vắng có phép';
                break;
            case 'sakit':
                badgeClass = 'bg-secondary/15 text-secondary';
                badgeLabel = 'Nghỉ ốm';
                break;
            case 'alpha':
                badgeClass = 'bg-error/15 text-error';
                badgeLabel = 'Vắng không phép';
                break;
            default:
                badgeClass = 'bg-secondary/15 text-secondary';
                badgeLabel = data.status;
        }

        tr.innerHTML = `
            <td class="px-4 py-2.5">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center flex-shrink-0">
                        <span class="material-symbols-outlined text-secondary text-[18px]">person</span>
                    </div>
                    <div class="min-w-0">
                        <p class="font-body-sm text-on-surface font-semibold truncate">${this._escapeHtml(data.nama)}</p>
                        <p class="text-[11px] text-on-surface-variant truncate">${this._escapeHtml(data.nim)} — ${this._escapeHtml(data.nama_kelas)}</p>
                    </div>
                </div>
            </td>
            <td class="px-4 py-2.5 text-body-sm text-on-surface-variant whitespace-nowrap">${this._escapeHtml(data.waktu_absen || '-')}</td>
            <td class="px-4 py-2.5 whitespace-nowrap">
                <span class="px-2.5 py-0.5 rounded-full ${badgeClass} text-[11px] font-bold">${this._escapeHtml(badgeLabel)}</span>
            </td>
        `;

        // Sisipkan di posisi pertama
        tbody.insertBefore(tr, tbody.firstChild);
    },

    /**
     * Update statistik card di dashboard
     */
    updateStats: function (stats) {
        if (!stats) return;

        const hadirEl = document.getElementById('stat-hadir');
        const terlambatEl = document.getElementById('stat-terlambat');
        const alphaEl = document.getElementById('stat-alpha');
        const totalEl = document.getElementById('stat-total');

        if (hadirEl && stats.hadir !== undefined) hadirEl.textContent = stats.hadir;
        if (terlambatEl && stats.terlambat !== undefined) terlambatEl.textContent = stats.terlambat;
        if (alphaEl && stats.alpha !== undefined) alphaEl.textContent = stats.alpha;
        if (totalEl && stats.total !== undefined) totalEl.textContent = stats.total;
    },

    /**
     * Refresh tabel absensi dari server (polling fallback)
     */
    refreshAbsensiTable: async function () {
        try {
            const response = await fetch('/api/absensi/hari-ini');
            const result = await response.json();

            if (result.status === 'ok' && result.data) {
                if (result.stats) {
                    this.updateStats(result.stats);
                }
                const tbody = document.getElementById('absensi-tbody');
                if (!tbody) return;

                tbody.innerHTML = '';
                if (result.data.length === 0) {
                    tbody.innerHTML = `
                        <tr class="empty-row">
                            <td colspan="3" class="px-6 py-12 text-center">
                                <span class="material-symbols-outlined text-3xl text-on-surface-variant/20 mb-2">event_busy</span>
                                <p class="text-body-sm text-on-surface-variant">Hôm nay chưa có dữ liệu điểm danh</p>
                            </td>
                        </tr>
                    `;
                } else {
                    result.data.slice().reverse().forEach(a => this.addAbsensiRow(a));
                }
            }
        } catch (err) {
            console.warn('[DASHBOARD] Gagal refresh absensi:', err);
        }
    },

    /**
     * Tampilkan toast notification
     */
    showToast: function (type, title, message) {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        // Icon per tipe
        const icons = {
            success: 'check_circle',
            error: 'error',
            warning: 'warning',
            info: 'info'
        };

        const cleanTitle = (typeof window !== 'undefined' && typeof window.cleanVietnameseMojibake === 'function')
            ? window.cleanVietnameseMojibake(title) : (title || '');
        const cleanMessage = (typeof window !== 'undefined' && typeof window.cleanVietnameseMojibake === 'function')
            ? window.cleanVietnameseMojibake(message) : (message || '');

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="material-symbols-outlined toast-icon">${icons[type] || 'info'}</span>
            <div class="toast-body">
                <div class="toast-title">${this._escapeHtml(cleanTitle)}</div>
                <div class="toast-message">${this._escapeHtml(cleanMessage)}</div>
            </div>
        `;

        container.appendChild(toast);

        // Auto-hapus setelah 4 detik
        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

// === Inisialisasi saat DOM ready ===
document.addEventListener('DOMContentLoaded', () => {
    // Inisialisasi CameraManager
    if (typeof CameraManager !== 'undefined') {
        CameraManager.init();
    }

    // Inisialisasi DashboardUI
    DashboardUI.init();

    // Sembunyikan tombol OFF secara default
    const btnOff = document.getElementById('btn-camera-off');
    if (btnOff) btnOff.style.display = 'none';
});
