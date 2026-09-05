# Rules

- **Single Output File Rule**: Trong một công việc/task, chỉ thực hiện/cập nhật trực tiếp trên cùng 1 file output duy nhất (ví dụ: `scripts/create_google_form.js`). Tránh sinh ra nhiều file mới rải rác hoặc tạo dư thừa file khác nhau cho cùng một yêu cầu.
- **Single HTML Demo/Wireframe File with Tabs & Versioning Rule**: Trong cùng 1 ứng dụng/dự án, CHỈ DÙNG ĐÚNG 1 FILE HTML DEMO DUY NHẤT. Tuyệt đối không tạo nhiều file HTML lẻ tẻ. Khi có thêm phương án mới, cải tiến hoặc màn hình mới, BẮT BUỘC phải tích hợp trực tiếp vào file HTML đó bằng cách thêm các Tab điều hướng mới (tab switcher) hoặc viết nối tiếp xuống dưới. Không cần sửa đè — nếu việc sửa đè tốn token hơn tạo mới thì chỉ cần tạo một Tab mới ghi rõ phiên bản (ví dụ: `Version 2`, `Version 3`...) để vừa tiết kiệm token, vừa bảo toàn lịch sử đối chiếu cho người dùng.
- **Include Output Links & Explorer Path Rule**: Tất cả các Agent (bao gồm Antigravity và Codex CLI), khi sinh ra hoặc gửi file output/báo cáo/preview, BẮT BUỘC phải đính kèm đồng thời:
  1. Link Markdown clickable (`[Tên file](file:///path/to/file)`).
  2. Đường dẫn thư mục/file Explorer chuẩn Windows (ví dụ: `E:\TMU UNIVERSITY\MACHINE LEARNING\SOURCE 1_ƯU TIÊN\...`) để người dùng dễ dàng truy cập và tra cứu.

- **Frontend & UI/UX Rule Synchronization (Tuân thủ toàn diện RuleFE.md)**:
  - Mọi hoạt động thiết kế, lập trình giao diện người dùng (Frontend UI/UX) BẮT BUỘC phải tuân thủ nghiêm ngặt 100% các điều khoản trong tài liệu [RuleFE.md](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_ƯU TIÊN/RuleFE.md) (`E:\TMU UNIVERSITY\MACHINE LEARNING\SOURCE 1_ƯU TIÊN\RuleFE.md`).
  - **Điều 1: Triết lý & Mindset AI4BA (Orchestrator Mindset)**: Giữ vai trò thực thi (Human-in-the-loop), không tự ý sửa code khi chưa có xác nhận từ người dùng. Giữ nguyên vẹn 100% phong cách thiết kế cũ ngoài các thành phần được yêu cầu đổi.
  - **Điều 2: Bảng đặc tả giao diện chuẩn IT-BA**: Mọi wireframe/screen description phải đủ 5 cột chuẩn (#, Items, Control Type, Data Type/Action, Description & Validation).
  - **Điều 3: Phạm vi bảo vệ Backend (Zero-Backend-Touch)**: Tuyệt đối cấm chạm file BE ([app.py](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_ƯU%20TIÊN/Absensi/app.py), [config.py](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_ƯU%20TIÊN/Absensi/config.py), [database.py](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_ƯU%20TIÊN/Absensi/database.py), [face/](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_ƯU%20TIÊN/Absensi/face)). Nếu phải sửa BE, bắt buộc hỏi xác nhận 2 lần riêng biệt bằng văn bản chat thường.
  - **Quy tắc giải trình 4 điểm trước khi sửa code (Pre-modification 4-Point Explanation Rule)**: Trước khi chỉnh sửa bất kỳ file code FE hay BE nào, Agent BẮT BUỘC phải nhắn giải trình cho người dùng trước gồm đầy đủ 4 nội dung:
    1. **Sửa phần nào**: Nêu rõ tệp tin, vị trí dòng, hàm hoặc thành phần giao diện cụ thể cần can thiệp.
    2. **Sửa như thế nào**: Trình bày phương án thay đổi cụ thể (thay thế, thêm mới, loại bỏ).
    3. **Tại sao sửa**: Phân tích nguyên nhân kỹ thuật hoặc yêu cầu nghiệp vụ dẫn đến cần sửa đổi.
    4. **Mục đích là gì**: Nêu rõ kết quả kỳ vọng đạt được, tính năng hoàn thành hoặc lỗi được khắc phục.
  - **Điều 4: Tự động đấu nối hợp đồng API & Chuẩn hóa UTF-8 Safe**: Tự thích ứng các API Backend. Xử lý chuẩn hóa lỗi mã hóa tiếng Việt (mojibake) hiển thị ở flash message và form error ngay tại Frontend mà không sửa Backend.
  - **Điều 5: Nguyên tắc bố cục & Thẩm mỹ AI4BA**: Dark mode công nghệ cao (`#0a0a0a`, `#141414`, neon `#ff5500`), container auth căn giữa 380px - 440px, font Plus Jakarta Sans.
  - **Điều 6: Checklist kiểm thử trước khi bàn giao**: Rà soát đầy đủ 5 tiêu chí verification trước khi kết thúc task.
  - **Bảo toàn Tuyệt đối Luồng 2 Tính năng Key khi Chỉnh sửa UI (Immutable 2 Key ML Feature Flows Rule - KIM CHỈ NAM BẤT BIẾN)**: Dù tinh chỉnh, thay đổi bố cục hoặc thiết kế lại UI/UX (Frontend/Template) ở bất kỳ màn hình nào, TUYỆT ĐỐI BẢO ĐẢM GIỮ NGUYÊN VẸN 100% LUỒNG HOẠT ĐỘNG (User Flow & Data Flow) của 2 tính năng key: (1) Đăng ký sinh viên 24 góc quét camera & huấn luyện gallery ArcFace; (2) Camera điểm danh thời gian thực nhận diện khuôn mặt trên Dashboard. Mọi can thiệp giao diện chỉ được tinh chỉnh thẩm mỹ/presentation, tuyệt đối không được làm gián đoạn, phá vỡ hay ảnh hưởng tới luồng xử lý, ID phần tử, endpoint và hợp đồng dữ liệu của 2 tính năng này.
  - **Quy tắc Tối ưu Chiều cao Thanh Lọc & Điều khiển (Compact Horizontal Filter Bar UX Rule)**: Với các box/thanh công cụ lọc (Filter Bar), tìm kiếm danh sách, BẮT BUỘC bố trí nhãn ("Lọc theo:", "Lọc theo lớp:") và ô điều khiển (select dropdown, checklist, input) nằm cùng trên một hàng ngang (inline `flex items-center gap-3`). Giảm padding khối lọc xuống mức tinh gọn (`py-2.5 px-4` thay vì container cao lãng phí) nhằm giảm thiểu chiều cao box, tối ưu không gian hiển thị danh sách dữ liệu phía dưới theo chuẩn UX AI4BA.
  - Khi cập nhật rule xong, hỏi lại người dùng bằng tiếng Việt và không tự ý sửa đổi mã nguồn ngoài phạm vi người dùng yêu cầu.

## BA Kit Conventions

- **Doc sạch**: Template chỉ chứa cấu trúc. Doc sinh ra chỉ chứa nội dung nghiệp vụ thật, không chứa meta-text hoặc hướng dẫn ngoài nghiệp vụ.
- **No-re-ask rule**: Không hỏi lại câu người dùng đã trả lời trong cùng session hoặc trong các tài liệu đã chốt.
- **IT-BA framing**: Dùng ngôn ngữ nghiệp vụ. Không hỏi các chi tiết kỹ thuật chuyên sâu (như DB column type, endpoint path, JWT internal algorithm) trừ khi ở bước SRS/Technical Spec.
- **Vietnamese-friendly typography**: Dùng tiếng Việt chuẩn mực, thuật ngữ tiếng Anh trong domain (Submit, Email, OTP...) giữ nguyên không dịch máy móc.
- **L1 plan preview**: Hiển thị kế hoạch duyệt bằng ngôn ngữ nghiệp vụ tự nhiên (prose) cho người dùng duyệt trước khi tạo/sửa file.
