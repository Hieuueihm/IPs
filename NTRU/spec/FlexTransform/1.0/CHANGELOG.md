# Change control

## 1.0 — 2026-10-26 — Candidate implementation baseline

Khóa REF16, native interfaces, numeric/kernel contracts, memory packing,
context/pause/flush, error priority, verification gates và traceability.
Không thêm/sửa RTL. Giao diện mới không tương thích nhị phân prototype cũ.

Mỗi change request MUST có ID, yêu cầu bị ảnh hưởng, ví dụ trước/sau, ảnh hưởng
software/oracle/RTL/test, người review và quyết định. Sửa contract/ROM/bit layout
phải phát hành version mới cùng migration note và regression. Thêm profile tương
thích cần minor version; sửa diễn đạt không đổi nghĩa dùng patch/errata và cập
nhật manifest. Không sửa asset rồi giữ nguyên hash/version.

Pipeline/FIFO/CSA thay đổi trong contract cho phép không bắt buộc đổi spec;
MUST đổi implementation revision/manifest và chạy lại test liên quan. Các con
số hiệu năng chỉ thuộc đúng implementation revision đã đo. Lưu spec version
và release manifest SHA trong báo cáo RTL để có thể tái lập.
