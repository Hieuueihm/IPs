# FlexTransform — ý tưởng đang được hiện thực

Cập nhật 2026-11-04. Baseline hiện hành là [a_cg_packed4_system160](experiments/BASELINE.md), đã sign-off STA 160 MHz trên XC7Z020-CLG400-2.

Bài toán là dùng cùng phần cứng cho FFT fixed-point nhiều precision và NTT nhiều modulus, phục vụ các kernel PQC/Falcon/FN-DSA. Giữ đúng precision, rounding và kết quả reference; giảm chi phí nhân, cộng/trừ, trạng thái, điều khiển và kết nối bằng cách dùng chung nơi các phép không cần hoạt động đồng thời.

Cách hiện thực được nhận dùng 16 tile giống nhau, mỗi tile bốn leaf nhân 16×16. FFT32/64/128 tính theo các lượt phần 32 bit trong tile; NTT dùng lại bộ nhân cho Montgomery, và q nhỏ tách thành hai nhóm leaf0/1, leaf2/3, mỗi nhóm hai lane packed16; hai gói mỗi ba clock và dùng chung T-high/NZ, reducer cuối, add/sub và side/tag. Constant-geometry và bộ nhớ chia bank phục vụ các mode, kết hợp PS7/AXI-Lite để nạp context/root/descriptor/dữ liệu.

**Đa precision và đa modulus là yêu cầu; ghép PE liên tile là một lựa chọn nghiên cứu.** Baseline này chưa ghép nhiều tile để làm một phép nhân rộng; không dùng tên gọi PE để thay đổi bản chất đó. Kết quả chạy đúng và đạt P&R chưa tự chứng minh novelty so với paper khác.

[Kiến trúc](docs/architecture_v1.md), [contract 3.1](spec/FlexTransform/3.1/README.md), [PLAN](PLAN.md), [báo cáo](study/results/a_cg_packed4_system160.md). Phần đề xuất cây ghép liên tile và các lựa chọn cũ được giữ tại [IDEA lịch sử](docs/plan_history/pre_baseline_160_2026_11_04/IDEA.md).
