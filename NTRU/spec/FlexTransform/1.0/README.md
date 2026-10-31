# FlexTransform IP — Implementation Specification 1.0

| Thuộc tính | Giá trị |
|---|---|
| Document ID | FT-SPEC-1.0 |
| Ngày | 2026-10-26 |
| Trạng thái | Candidate implementation baseline — để review trước khi viết RTL |
| Reference configuration | REF16: 16 tile, 64 lá nhân 16×16, hai context batch |
| Giao diện | Native synchronous valid/ready; một clock domain |
| Phạm vi | Kernel FFT/NTT cho ứng dụng FN-DSA; không phải toàn bộ signer |
| Phần triển khai | Người dùng tự viết RTL; bộ spec này không thêm/sửa RTL |

Đây là đặc tả IP theo cách tổ chức dùng cho triển khai và kiểm chứng: yêu cầu có
ID, contract số học và giao diện cụ thể, xử lý lỗi/flush, ownership bộ nhớ và
verification traceability. **Không tuyên bố một chứng nhận công nghiệp, tuân thủ
AXI hay chứng nhận FN-DSA.** Cụm “implementation baseline” khóa hợp đồng chức
năng; không có nghĩa microarchitecture mới đã được triển khai hoặc signoff.

## Cách sử dụng và thứ tự ưu tiên

1. [Profiles và giới hạn](00_scope_profiles.md).
2. [Số học, kernel và thứ tự dữ liệu](01_numeric_kernels.md).
3. [Ports, handshake, lỗi, reset và flush](02_interfaces_protocol.md).
4. [Phân khối, bộ nhớ, context và cấp dữ liệu](03_microarchitecture_memory.md).
5. [Kế hoạch kiểm chứng và điều kiện chấp nhận](04_verification_acceptance.md).
6. [Yêu cầu và traceability](05_requirements.md); bản máy đọc là
   [requirements.json](requirements.json).
7. [Danh mục giao diện](interface.json), [cấu hình](profiles.json),
   [ROM và fixture](assets/README.md), [quản lý thay đổi](CHANGELOG.md).
8. [Trình tự tích hợp và ví dụ giao dịch](06_integration_examples.md).

Các từ **MUST**, **MUST NOT**, **SHOULD**, **MAY** lần lượt là bắt buộc, cấm,
khuyến nghị có thể thay bằng phương án tương đương có giải trình, và tùy chọn.
Các ID `FT-*` trong requirements.json là các yêu cầu bắt buộc có trace đến test.
Các phương trình/thuật toán và packing trong tài liệu 01/02 là normative ngay
cả khi một phương trình không có một ID riêng.

Khi có mâu thuẫn, MUST dừng review và ghi change request; không tự chọn một
cách diễn giải trong RTL. Tài liệu 00..04 và các bảng interface/profile/ROM
phải thống nhất. Hình chỉ minh họa, không được dùng để ghi đè contract số học
hoặc protocol. Phải tăng version/errata khi sửa contract hoặc nội dung ROM.

## Quyết định đã khóa cho bản 1.0

- W32/Q16.16, W64/Q32.32, W128/Q64.64; cùng mảng 16 tile; rounding theo
  [contract R8](../../../docs/numeric_contract.md) ở W128.
- NTT chỉ hai profile q12289/q3329, residue 16 bit canonical; CT forward,
  GS inverse. q3329 N256 là incomplete 7 tầng, không có BASEMUL.
- Ba working store A/B/C, mỗi store 64 bank ×16 bit ×128 row; logical address
  mapping cố định, gather/scatter nhiều lượt nếu trùng bank.
- Một command batch đang hoạt động; pipeline có thể giữ hai context microbatch.
  Không trộn mode/W/q/N/hướng trong batch. Chỉ đổi cấu hình sau khi drain.
- Batch NTT nhỏ có tối đa 8 job cùng cấu hình, tổng hệ số không quá 64.
  Các job là đa thức độc lập, không phải các đoạn của một đa thức lớn.
- Giao diện host-memory là raw 128-bit line/16 byte; địa chỉ byte, byte-enable
  16 bit. Không cần biết precision để nạp RAM. Đây không phải AXI.
- Flush không rollback RAM; command đang chạy trả ABORTED, vùng output không
  còn hợp lệ. Completion OK chỉ sau khi mọi kết quả đã commit vào RAM.

## Phần người triển khai được điều chỉnh

Pipeline latency, cây cộng/CSA, cách suy ra RAM, arbitration, packing mỗi beat
và vị trí register MAY thay đổi nếu giữ nguyên contract. REF16 khóa hai context
để có baseline chung; cấu hình nhiều context hơn phải công bố trong implementation
manifest và kiểm lại. Số bank/cổng/tile khác không thuộc REF16 1.0; cần profile
mới thay vì âm thầm thay đổi số liệu cấu hình.

Chưa có yêu cầu MHz/area/power/FPGA cụ thể. Không lấy lane capacity làm throughput
kernel. Verification 04 yêu cầu báo cáo cycle/lane/stall và một ngưỡng liveness
rộng; mục tiêu tăng throughput là mục tiêu thiết kế, không phải kết quả đã đạt.

## Bằng chứng sẵn có và giới hạn

Baseline trước bộ spec đã kiểm 5.992 kernel/325.492 word và bốn chữ ký khớp C.
[Bằng chứng](../../../docs/autonomous_kernel_rtl.md),
[profiling](../../../docs/kernel_parallelism_profile.md).
Đó là reference cho số học/dữ liệu, **không tự chứng minh RTL mới theo spec này**.
Giao diện native, batching, context và flush ở đây là hợp đồng triển khai mới;
không binary-compatible với prototype hoặc AXI-Lite scaffold trước đó.

Mỗi release RTL MUST giao kèm implementation manifest, danh sách test đã chạy,
deviation và traceability. Đạt chức năng không đồng nghĩa đã signoff physical,
side-channel hoặc triển khai toàn FN-DSA.

## Kiểm tra bộ tài liệu

Từ root repo: `python -X utf8 scripts/check_flextransform_spec.py`.
Tool kiểm hash, ROM/fixture, enum/field, liên kết và coverage yêu cầu; không
compile, mô phỏng hay sinh RTL.
