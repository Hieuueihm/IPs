# 3.1 — bộ nhớ, root và lịch

Nguồn: [core baseline](../../../experiments/a_cg_packed4_system160/rtl/a_cg_fast.sv), [planner baseline](../../../experiments/a_cg_packed4/planner.py). Không dùng layout 64 bank hoặc generator của core cũ.

- Dữ liệu: **32 bank × 256 hàng × 32 bit = 32 KiB khai báo**. Ping-pong dùng các hàng trong bank; không cấp thêm một bộ bank toàn phần.
- Root: **16 RAM × 512 hàng × 32 bit = 32 KiB khai báo**, một RAM cho mỗi tile. Địa chỉ nạp 9 bit, destination mask 16 bit. Bảng theo thứ tự sử dụng, chọn đúng chiều/mode.
- Mapping và danh sách truy cập constant-geometry lấy từ planner/fixture được pin. Dữ liệu trung gian giữ tại tile, chia sẻ điều khiển theo pha; không xem mô hình lịch ban đầu như tự động đạt mọi thông số RTL.
- Host đọc/ghi dòng 128 bit với chỉ số 10 bit; các word/limb thấp trước theo fixture/native API. Packed16 có hai hệ số 16 bit mỗi word; FFT64/128 mỗi thành phần có 2/4 word.
- Từng batch đồng cấu hình; số job vừa bank và plane/row mới hợp lệ. Planner và cấu hình RTL phải đồng ý về địa chỉ, số tầng, root và chu kỳ.

Mỗi bank có một cổng đọc đồng bộ và một cổng ghi, lịch không được tạo RAW cùng cạnh ở cùng hàng hoặc xung đột truy cập. Simulation baseline có các assert tương ứng. Không tự đổi layout, số lane, latency RAM hay pipeline mà giữ nguyên descriptor/gap cũ.

P&R dùng **32 RAMB18 dữ liệu + 16 RAMB18 root = 48 RAMB18**. Đây là tài nguyên vật lý; không nhầm dung lượng BRAM vật lý với dung lượng logic thực khai báo. IFFT normalize tại host-read chứ không ghi kết quả normalized lại RAM.

## Cấp việc packed16 bốn leaf

Tại core, packed đọc bank và root ở pha1/2 (NTT32 chỉ pha1); pipeline hai tầng đưa request tới tile ở pha0/1. Mỗi lần vẫn đọc một gói 64 bit/tile và root32; hai gói ở hai clock riêng, không tăng cổng RAM hay mux hơn bốn nguồn. Output vẫn một gói64 ở mỗi clock có valid; hai luồng dùng chung side/tag RAM16 entry.

Planner chính thức: `experiments/a_cg_packed4/planner.py`. Với seq=k*planes+part, thời điểm operand tương đối A=2+3*(seq//2)+seq%2 cho packed16; NTT32 vẫn A=2+3*seq. Chồng lấp tầng chọn gap được kiểm bank-conflict, RAW và phiên bản dữ liệu. Root vẫn theo thứ tự k/tile và hmin/chiều; không bỏ nửa root khi tăng mật độ phát.
