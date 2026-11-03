# FlexTransform — lõi FFT/NTT dùng chung phần cứng

Thiết kế dùng 16 tile, mỗi tile có bốn bộ nhân 16×16. FFT và NTT dùng lại các
bộ nhân này. RTL đang phát triển nằm trong `hdl/tile/`, `hdl/net/`, `hdl/core_ntt/`.

## Đọc từ đâu?

1. [Kiến trúc hiện tại](docs/architecture_v1.md): thiết kế làm gì, phần nào đã có.
2. [Danh sách source RTL](hdl/README.md): file cần dùng và file cũ cần tránh nhầm.
3. [Đặc tả 2.0](spec/FlexTransform/2.0/README.md): yêu cầu khi hoàn thiện thiết kế.
4. [Kết quả đọc code ngày 01/11](docs/implementation_review_2026_11_01.md): kiểm tra và lỗi đang biết.
5. [Hướng giảm tài nguyên](docs/shared_logic_plan.md): những phần có thể dùng chung; chưa thay RTL.
6. [Thử gộp mạng và tổng root](docs/shared_logic_experiment.md): mô phỏng và đo tài nguyên trên bản thử riêng.

## Các thư mục

| Thư mục | Chứa gì? |
|---|---|
| `hdl/tile/` | Tile đang phát triển; các phép nhân, cộng/trừ và butterfly |
| `hdl/net/` | Mạng nối bộ nhớ với tile |
| `hdl/core_ntt/` | Lõi FFT/NTT đang phát triển, gồm điều khiển và bảng root |
| `sim/tile_thu/`, `sim/core_ntt/` | Testbench và lệnh chạy cho RTL hiện tại |
| `model/` | Mô hình Python/C để kiểm số học và lịch đọc/tính/ghi |
| `scripts/` | Sinh bảng, tạo vector và kiểm kết quả |
| `spec/FlexTransform/2.0/` | Đặc tả mục tiêu hiện tại; một số chức năng chưa có trong RTL |
| `third_party/r8/` | Mã C tham chiếu R8 và NTRUGen |
| `study/results/` | Báo cáo; phải đọc đúng phiên bản và phân biệt đo thực với dự báo |
| `docs/plan_history/` | Quyết định và tài liệu cũ, dùng để tra cứu lịch sử |

## Trạng thái cần nhớ

- Tile và core là hai cấp kiểm tra khác nhau. Tile chạy đúng chưa bảo đảm cả core đúng.
- Lượt kiểm 01/11: core NTT đạt 48/48 ca; FFT32 N8 có lỗi chuyển tầng sớm.
- Kết quả 5.992 kernel/bốn chữ ký thuộc [lõi cũ](docs/autonomous_kernel_rtl.md).
  Core mới chưa được xác nhận bằng cùng lượt kiểm ứng dụng đó.
- Các file `PLAN.md`, `IDEA.md`, `ARCHITECTURE.md` ở root và tài liệu trong
  `docs/plan_history/` ghi quá trình nghiên cứu. Dùng trang kiến trúc hiện tại
  ở trên làm điểm bắt đầu.

## Cách viết tài liệu và giải thích

Dùng tiếng Việt rõ, ngắn. Giữ nguyên tên tín hiệu/file để tra code. Khi dùng
thuật ngữ mới, giải thích nghĩa ngay lần đầu. Mỗi kết quả ghi rõ là mô phỏng
RTL, mô hình tính toán hay số đo FPGA; không trộn số liệu của các phiên bản.
