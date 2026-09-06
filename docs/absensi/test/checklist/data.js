window.FEATURE = "Quản lý Lịch học & Nghiệp vụ đào tạo TMU (Jadwal)";
window.UPDATED = "2026-09-06";
window.CHECKLISTS_DATA = [
  {
    file: "checklist-jadwal-schedule.md",
    scope: "feature",
    target: "Quản lý Lịch học (1 Lớp = 1 Môn học)",
    items: [
      {
        chk: "CHK-SCH-001",
        p: 1,
        auto: "Yes",
        ref: "BUG-SCH-001",
        category: "Khởi tạo & Thêm mới",
        content: "Thêm lịch học cho lớp học phần mới tạo (chưa có bản ghi tương ứng trong bảng matakuliah) tự động khởi tạo môn học ngầm và lưu lịch học thành công vào CSDL, không gây lỗi khóa ngoại 1452 Cannot add or update a child row."
      },
      {
        chk: "CHK-SCH-002",
        p: 1,
        auto: "Yes",
        ref: "FR-SCH-002",
        category: "Khởi tạo & Thêm mới",
        content: "Thêm lịch học cho lớp học phần đã có sẵn bản ghi môn học hợp lệ liên kết chính xác matakuliah_id sẵn có, không sinh thêm bản ghi môn học rác."
      },
      {
        chk: "CHK-SCH-003",
        p: 2,
        auto: "Yes",
        ref: "FR-SCH-003",
        category: "Khởi tạo & Thêm mới",
        content: "Thêm lịch học với mốc buổi học bắt đầu tùy chỉnh (buoi_bat_dau, ví dụ: buổi 5) lưu đúng giá trị vào CSDL phục vụ điểm danh giữa kỳ."
      },
      {
        chk: "CHK-SCH-004",
        p: 2,
        auto: "Yes",
        ref: "FR-SCH-004",
        category: "Khởi tạo & Thêm mới",
        content: "Tự động tính toán hạn đi muộn (batas_terlambat = jam_mulai + 15 phút) khi người dùng không nhập hoặc để trống."
      },
      {
        chk: "CHK-SCH-005",
        p: 3,
        auto: "Yes",
        ref: "FR-SCH-005",
        category: "Khởi tạo & Thêm mới",
        content: "Thêm nhiều ca học cho cùng một lớp trong các ngày khác nhau (ví dụ: Thứ Hai và Thứ Năm) lưu trữ độc lập và hiển thị đầy đủ trên danh sách."
      },
      {
        chk: "CHK-SCH-010",
        p: 1,
        auto: "Yes",
        ref: "FR-SCH-010",
        category: "Cập nhật & Sửa đổi",
        content: "Cập nhật / Sửa lịch học (/jadwal/edit/<id>) chỉ gửi kelas_id tự động bảo toàn môn học hợp lệ mà không làm mất liên kết bảng điểm danh."
      },
      {
        chk: "CHK-SCH-011",
        p: 2,
        auto: "Yes",
        ref: "FR-SCH-011",
        category: "Cập nhật & Sửa đổi",
        content: "Sửa giờ học hoặc thứ của lịch học cập nhật ngay lập tức sang bảng danh sách và card thông tin ca học trên Dashboard."
      },
      {
        chk: "CHK-SCH-012",
        p: 2,
        auto: "Yes",
        ref: "FR-SCH-012",
        category: "Cập nhật & Sửa đổi",
        content: "Sửa mốc buổi bắt đầu (buoi_bat_dau) cập nhật chuẩn xác cách tính số buổi tiếp theo trong get_buoi_hoc_hien_tai_cua_lop."
      },
      {
        chk: "CHK-SCH-013",
        p: 3,
        auto: "Yes",
        ref: "E-SCH-001",
        category: "Cập nhật & Sửa đổi",
        content: "Truy cập đường dẫn sửa lịch học với ID không tồn tại (/jadwal/edit/99999) điều hướng an toàn về /jadwal kèm flash message báo lỗi tiếng Việt."
      },
      {
        chk: "CHK-SCH-020",
        p: 1,
        auto: "Yes",
        ref: "FR-SCH-020",
        category: "Xóa & Ràng buộc toàn vẹn",
        content: "Xóa lịch học chưa phát sinh dữ liệu điểm danh (POST /jadwal/hapus/<id>) xóa thành công bản ghi khỏi CSDL và chuyển hướng về danh sách với thông báo thành công."
      },
      {
        chk: "CHK-SCH-021",
        p: 2,
        auto: "Yes",
        ref: "BR-SCH-003",
        category: "Xóa & Ràng buộc toàn vẹn",
        content: "Xóa lịch học đã có sinh viên điểm danh kích hoạt ràng buộc xóa liên đới (CASCADE) hoặc cảnh báo dữ liệu an toàn theo thiết kế DB."
      },
      {
        chk: "CHK-SCH-022",
        p: 2,
        auto: "Yes",
        ref: "BR-SCH-004",
        category: "Xóa & Ràng buộc toàn vẹn",
        content: "Xóa lớp học (/kelas/hapus/<id>) tự động xóa liên đới (CASCADE) môn học và toàn bộ lịch học liên quan."
      },
      {
        chk: "CHK-SCH-030",
        p: 1,
        auto: "Yes",
        ref: "BR-SCH-001",
        category: "Validation & BVA",
        content: "Giờ kết thúc trước hoặc bằng giờ bắt đầu (jam_mulai >= jam_selesai) bị từ chối với thông báo: 'Giờ kết thúc phải sau giờ bắt đầu.'"
      },
      {
        chk: "CHK-SCH-031",
        p: 2,
        auto: "Yes",
        ref: "BR-SCH-002",
        category: "Validation & BVA",
        content: "Thiếu trường bắt buộc (lớp, thứ, giờ bắt đầu, giờ kết thúc) trả về thông báo lỗi: 'Vui lòng nhập đầy đủ thông tin.'"
      },
      {
        chk: "CHK-SCH-032",
        p: 3,
        auto: "Yes",
        ref: "BVA-SCH-001",
        category: "Validation & BVA",
        content: "Giá trị biên buổi học bắt đầu: nhập buoi_bat_dau = 1 (giá trị tối thiểu hợp lệ) lưu thành công."
      },
      {
        chk: "CHK-SCH-033",
        p: 3,
        auto: "Yes",
        ref: "BVA-SCH-002",
        category: "Validation & BVA",
        content: "Giá trị biên buổi học bắt đầu: nhập buoi_bat_dau = 60 (giá trị tối đa hợp lệ) lưu thành công."
      },
      {
        chk: "CHK-SCH-034",
        p: 3,
        auto: "Yes",
        ref: "BVA-SCH-003",
        category: "Validation & BVA",
        content: "Giá trị không hợp lệ: nhập buoi_bat_dau <= 0 hoặc chuỗi chữ bị trình duyệt/Backend chặn và chuẩn hóa về tối thiểu 1."
      },
      {
        chk: "CHK-SCH-035",
        p: 2,
        auto: "Yes",
        ref: "BVA-SCH-004",
        category: "Validation & BVA",
        content: "Khung giờ đặc biệt: Ca học từ 06:00 đến 23:00 (khung giờ xuyên ngày dài nhất) xử lý chính xác định dạng HH:MM:SS."
      },
      {
        chk: "CHK-SCH-040",
        p: 1,
        auto: "Yes",
        ref: "SEC-SCH-001",
        category: "Bảo mật & Phân quyền",
        content: "Truy cập các route quản lý lịch học (/jadwal, /jadwal/tambah, /jadwal/edit/<id>, /jadwal/hapus/<id>) khi chưa đăng nhập bị chuyển hướng về /login."
      },
      {
        chk: "CHK-SCH-041",
        p: 2,
        auto: "Yes",
        ref: "SEC-SCH-002",
        category: "Bảo mật & Phân quyền",
        content: "Phiên đăng nhập vai trò Khách (is_guest: True) không thể thực hiện thêm/sửa/xóa lịch học (bảo vệ bởi admin_required)."
      },
      {
        chk: "CHK-SCH-042",
        p: 2,
        auto: "Yes",
        ref: "SEC-SCH-003",
        category: "Bảo mật & Phân quyền",
        content: "Dữ liệu tên lớp chứa ký tự đặc biệt HTML/Script (<script>, \", ') được render an toàn dưới dạng text, không gây lỗ hổng XSS trên bảng lịch học hoặc modal xác nhận xóa."
      },
      {
        chk: "CHK-SCH-050",
        p: 1,
        auto: "Yes",
        ref: "FR-ATT-010",
        category: "Thời gian thực & Điểm danh",
        content: "Lịch học đang diễn ra trong ngày hiện tại (get_jadwal_aktif) tự động hiển thị trên Dashboard camera phục vụ quét mặt sinh trắc học."
      },
      {
        chk: "CHK-SCH-051",
        p: 2,
        auto: "Yes",
        ref: "FR-ATT-011",
        category: "Thời gian thực & Điểm danh",
        content: "Popup 'Thông tin buổi học' trên Topbar tự động nhận diện ca học gần nhất khớp với danh sách lịch học trong CSDL."
      },
      {
        chk: "CHK-SCH-052",
        p: 2,
        auto: "Yes",
        ref: "FR-ATT-012",
        category: "Thời gian thực & Điểm danh",
        content: "Sinh viên quét mặt đúng giờ học ghi nhận trạng thái hadir nếu trước batas_terlambat, ghi nhận terlambat nếu sau batas_terlambat."
      },
      {
        chk: "CHK-SCH-060",
        p: 2,
        auto: "No",
        ref: "UI-SCH-001",
        category: "Giao diện & UI/UX",
        content: "Bảng danh sách lịch học hỗ trợ cuộn ngang (overflow-x-auto) mượt mà trên màn hình di động/tablet mà không làm vỡ layout."
      },
      {
        chk: "CHK-SCH-061",
        p: 2,
        auto: "No",
        ref: "UI-SCH-002",
        category: "Giao diện & UI/UX",
        content: "Cột 'Thao tác' (Sửa/Xóa) được ghim cố định bên phải (sticky right-0) với hiệu ứng đổ bóng mờ chuẩn Dark Mode công nghệ cao."
      },
      {
        chk: "CHK-SCH-062",
        p: 3,
        auto: "No",
        ref: "UI-SCH-003",
        category: "Giao diện & UI/UX",
        content: "Toàn bộ tiêu đề, nhãn input, nút bấm và thông báo tuân thủ font chữ mặc định Open Sans (font-family: 'Open Sans', sans-serif)."
      }
    ]
  }
];
