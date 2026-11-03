# A: liveness, đóng gói địa chỉ và cổng đọc

Quan sát RTL hiện tại bằng testbench chỉ đọc, rồi kiểm mô hình bộ nhớ mới; chưa sửa RTL.

| W | Chiều | BF | Slot | X/W: cổng đọc cũ | X/W: xen kẽ mới | Mỗi mảng operand/side | Mỗi mảng tổng |
|---|---|---:|---:|---:|---:|---:|---:|
| 32 | xuôi | 24 | 8 | 2 / 2 | 1 / 1 | 16 | 8 |
| 32 | ngược | 24 | 8 | 2 / 2 | 1 / 1 | 16 | 8 |
| 64 | xuôi | 24 | 4 | 1 / 1 | 1 / 1 | 16 | 8 |
| 64 | ngược | 24 | 4 | 1 / 1 | 1 / 1 | 16 | 8 |
| 128 | xuôi | 24 | 2 | 1 / 1 | 1 / 1 | 16 | 8 |
| 128 | ngược | 24 | 2 | 1 / 1 | 1 / 1 | 16 | 8 |

NTT: 12 cấu hình ×40 request PASS, gồm q3329/12289/8380417/2^31−1 và packed16 q3329/12289, hai chiều.
FIFO side có tối đa 6 word sống, ánh xạ vào 16 entry PASS, 1R/1W.

## Giới hạn

- Core-like intervals 3/12/48, 24 BF per case, LEAF_PD=2 IN_REG=1, no arbitrary burst acceptance claim.
- Dense/interleaved variants are memory event models, not rewritten RTL or a routed netlist.
- Interleaving needs two GS carry/borrow contexts, new beat decode and rechecked core bank timing.
- The previous real operand/root must be held or reused from an earlier existing pipeline register; register/timing cost not measured.
- Single R/W counts are consumed logical accesses; LUTRAM packing and LUT savings still need synthesis.
- NTT FIFO checks use fixed phase, one slot, q tests and per-word packed mode; core packed16 bank integration is not modeled.

Nguồn: [model](../../model/tile_a_liveness.py), [JSON và log](tile_a_liveness.json).
