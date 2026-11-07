# Baseline 160 MHz trước khi nhận packed16 bốn leaf

Bản lưu nguyên byte ngày 2026-11-04. Mốc trước: `a_cg_z020_system160`, spec 3.0, 31.242 LUT, setup +0,038 ns, hold +0,011 ns. Source RTL và bằng chứng P&R cũ giữ tại đường dẫn cũ. `snapshot.json` pin các tài liệu, registry và workflow trước lần cập nhật.

Baseline hiện hành xem [experiments/BASELINE.md](../../../experiments/BASELINE.md). Spec 3.0 là contract lịch sử, không thay ngầm thành lịch packed16 mới.

Link tương đối bên trong snapshot được hiểu theo vị trí gốc ở root repo; không chạy build hoặc coi snapshot là source hiện hành. Để kiểm nguyên byte workflow cũ, checker hỗ trợ --manifest cùng --workflow-snapshot trỏ archive này.
