# Synth trên XC7Z020-CLG400-2

**Chỉ synth tại 5 ns; chưa P&R, chưa xác nhận chạy 200 MHz trên chip này.**

| Tài nguyên | Synth toàn core | Chip có | Tỷ lệ |
|---|---:|---:|---:|
| LUT | 37,841 | 53,200 | 71.1% |
| FF | 27,397 | 106,400 | 25.7% |
| DSP | 64 | 220 | 29.1% |
| BRAM36 quy đổi | 24 | 140 | 17.1% |

Thực tế dùng 48 RAMB18E1 và 0 RAMB36. DSP được ánh xạ sang DSP48E1.
Timing nội bộ ước tính sau synth: setup -3.604 ns; hold +0.126 ns.

Đường setup chậm nhất đi qua cộng/trừ trong tile; pipeline host chưa cắt đường này.
```json
{
  "source": "u_exec/engine[0].u_tile/g_in_reg.rdat_reg[0]/C",
  "destination": "u_exec/engine[0].u_tile/rd_reg[29]/D",
  "data_path": "8.501ns  (logic 4.749ns (55.864%)  route 3.752ns (44.136%))",
  "levels": "19  (CARRY4=11 LUT4=3 LUT6=5)"
}
```

## Phạm vi

RTL là bản sao từng byte của dispatch2 đã kiểm packed16, FFT32/64/128 và NTT đa modulus.
Tái dùng bằng chứng 1.026 vector, 38 ca bốn trạng thái, 12 nhóm reset, 74 lần gọi C và 4 xác minh chữ ký.
Không gọi đây là mô phỏng sau ánh xạ hoặc thử phần cứng Z020.
Có đủ host adapter và root cache. Chưa gồm wrapper AXI, DMA, clock/pin board hoặc chương trình ARM.
Không đổi RTL chính và không dùng checkpoint UltraScale+ để báo số của Z020.

## Mục tiêu 30k LUT

Cần giảm thêm 7,841 LUT so với số synth này để đạt 30.000 LUT.
Đổi chip không tự giảm số phép toán. Cho phép thêm chu kỳ mở ra phương án giảm số engine hoặc
chia thời gian phần cộng/tích lũy, nhưng cần đo lại cả mux, bộ nhớ và điều khiển. Chưa triển khai các phương án đó.

[Nguồn dung lượng chip: AMD DS190](https://docs.amd.com/api/khub/documents/juMnxca71Tf2gfjmNyjM8A/content).
