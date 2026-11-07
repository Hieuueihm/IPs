# Nguồn cấu hình Qiming

Ngày đối chiếu: 2026-11-04. Hiểu Qiming trong yêu cầu là Qiming Star / 启明星 của ALIENTEK. Chưa quan sát bo vật lý hoặc kiểm tra revision của bo người dùng.

- [Trang sản phẩm chính hãng](https://www.alientek.com/Product_Details/79.html).
- [Tài liệu chính hãng Qiming V2](https://www.openedv.com/docs/build/html/boards/fpga/zdyz_qimxing%28V2%29.html), có link kho tài liệu và hình board.
- [Tài liệu Qiming V1](https://www.openedv.com/docs/build/html/boards/fpga/zdyz_qimxing.html).
- [ALIENTEK, phần mô tả core Zynq-7020](https://www.openedv.com/thread-331204-1-1.html), mục 3.3.2: XC7Z020CLG400-2; 3.3.8: PL oscillator 50 MHz; 3.3.9: PS oscillator 33.333 MHz. Bài này nằm trong hướng dẫn Linghang V2, dùng để đối chiếu core ATK-7020 dùng chung; không lấy pin ngoại vi của carrier Linghang gán cho Qiming.
- [Thông số core ATK-7020 do ALIENTEK phát hành, bản lưu tại Elecfans](https://file.elecfans.com/web2/M00/53/3E/pYYBAGLOdYeAWDNtAAE2zu4pJ5s022.pdf): core tương thích carrier Linghang/Qiming. Đây là tài liệu tác giả ALIENTEK được lưu trên một host khác.

Chọn hệ thống tối thiểu PS7 + OCM/JTAG + AXI-Lite + lõi, không dùng DDR, SD, UART, Ethernet hay I/O PL của carrier. FCLK0 của PS được Vivado tính ra 100.000000 MHz từ clock tham chiếu 33.333333 MHz; MMCM tạo 160 MHz cho toàn miền AXI/lõi. Không dùng preset của QMTECH hoặc ZedBoard, không tự đặt pin PL.

Phạm vi kiểm timing là thiết kế tích hợp trên chip nói trên, không bao gồm ngoại vi đang tắt, phần mềm PS chưa chạy trên bo thật, hoặc các ngoại vi sẽ ghép về sau. Các chân dedicated PS/FIXED_IO do IP PS7 quản lý. Không coi việc P&R này là đo hoạt động vật lý trên bo.
