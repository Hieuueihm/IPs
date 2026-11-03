# 04 — Verification plan and acceptance gates

## 04.1 Oracle và mức bằng chứng

Scoreboard so bit, không dùng tolerance float. W128 đối chiếu pinned C R8,
W32/64 đối chiếu oracle số nguyên đúng tài liệu 01. NTT primitive có thêm oracle
`a*b*inverse_mod(65536,q)%q`; kernel đối chiếu thứ tự root/tầng đã định, không
chỉ kiểm round-trip. SPLIT/MERGE phải kiểm riêng, không chỉ kiểm chúng triệt tiêu
nhau. Không lấy chính RTL đang kiểm làm generator expected output.

Fixture phát hành là seed cho testbench, không thay thế toàn bộ regression.
Kết quả baseline cũ không tự động đánh dấu PASS cho RTL người dùng sắp viết.
Trạng thái test gồm NOT_RUN/PASS/FAIL/WAIVED; NOT_RUN không phải PASS.

## 04.2 Mandatory test suites

| Test ID | Stimulus/điểm kiểm bắt buộc |
|---|---|
| T_CFG | Mọi tuple op/fmt/profile/logn/jobs hợp lệ; malformed nhiều field cùng lúc; priority lỗi; invalid không issue, đọc root/data hay write |
| T_NATIVE | CMD latch/arbitration, tag, completion một lần, DONE write STATE, RETURN chờ response cũ; OK sau commit cuối |
| T_STABILITY | valid và toàn payload giữ khi blocked, gồm 1.024 cycle stall; không drop/duplicate; kiểm combinational loops |
| T_RESET | Reset ở mọi context/pipeline state, host request/response pending, DONE; clear control/valid, không stale write/completion |
| T_FLUSH | IDLE/FILL/ISSUE/COLLECT/WRITE/DONE, ngay write cuối, pause high, response blocked, completion đã publish; ABORTED/mask0, preserve OK, không rollback, bound 256 |
| T_MEMORY | Mọi store/line; byte-enable one-hot/all/zero; alignment/range/store/state errors; little-endian; ACK sau commit, response một lần |
| T_FP_PRIM | signed extrema, ±half-LSB ties, wrap pre-add, low-limb MSB unsigned, carry vào retained slice, div2e wrap, 3M và mọi width |
| T_FP_KERNEL | Mọi N/W/FFT-family op; toàn bộ synthetic C suite và application-captured calls sẵn có; layout split-real/imag và N=1/2 |
| T_NTT_PRIM | Hai q: 0,1,q−1 và random canonical; Mont so oracle modular độc lập; full T/carry, add/sub canonical |
| T_NTT_KERNEL | Mọi N/profile/NTT-family op; q3329 N256 incomplete và inverse128; root order, scaling/domain; q12289 so C capture |
| T_ARRAY | Mọi width/tile-mode/mask, sign, raw/pair/tail/scalar, continuous-ready II=1, latency đã công bố và long stall |
| T_CONTEXT | Hai context xen kẽ, phase triplet, duplicate/current-epoch unknown ID, stale epoch, giữ A/B/root/side-data, không reuse trước commit |
| T_JOBS | Mọi jobs hợp lệ N8/16/32 × hai q × op5..8; pattern khác nhau mỗi job, so từng standalone oracle, partial mask và canary |
| T_BANK | Bijection 8.192 word/store, bank-port budget, broadcast cùng row, collision khác row, read/write cùng địa chỉ và gather/scatter nhiều round |
| T_ROOT | Hash/mọi ROM word, inverse trước quantize, sum sau quantize, root-cache invalidation/config/epoch, không đọc padded root |
| T_STRESS | Ít nhất 10.000 accepted valid commands, random seed được lưu, thêm invalid command/pause/flush/reset/backpressure; scoreboard giao dịch và dữ liệu |
| T_PROFILE | Ít nhất 20 coefficient patterns mỗi cấu hình được đo, cùng command/initial state/flow trace phải cùng issue/address/root/cycle trace |
| T_SIGNER | LP64 R8 pristine, bốn chữ ký: hai N512 và hai N1024; input C thực, kernel đi qua RTL, không fallback hay replay output; verifier độc lập và reject sửa message/signature |
| T_MUTATE | Chủ động đổi một output word, bỏ/mistag frame, sai rounding hoặc root; scoreboard phải bắt được mutation, không âm thầm dùng lại expected |
| T_PERF | Báo cycle/kernel, active/pause, frames, lane/leaf useful slots, bank/root service rounds, queue peaks và backpressure; loại host load/read khỏi kernel cycles |
| T_RELEASE | Tool/version/seed/command/hash tái lập; lint không lỗi, không latch/multi-driver/uninitialized control; manifest và review waiver có người chịu trách nhiệm |

Mỗi MUST trong [requirements.json](requirements.json) MUST có kết quả test hoặc
waiver review được ghi rõ. Test cơ sở dùng scalar/math oracle; kiểm packing,
handshake và commit dùng scoreboard riêng. (FT-DV-001)

## 04.3 Assertions / formal properties cần viết

| Property | Nghĩa vụ |
|---|---|
| P_HOLD | valid && !ready => valid/payload giữ ở edge sau, trừ reset; internal cancel phải qua quy tắc epoch, không drop external response |
| P_ONCE | Không completion/response nếu chưa accept; mỗi accepted transaction đúng một reply trừ reset |
| P_DONE | OK => mọi write đã commit, không context/pipeline side-effect còn tồn tại |
| P_CONTEXT | Không reuse context, overwrite operand/root/product hoặc retire thiếu phase |
| P_EPOCH | Canceled epoch không tạo write hay complete command mới; wrap epoch chỉ sau drain |
| P_BANK | Mỗi bank tối đa 1R+1W/edge; collision được serialize; write enable không vượt footprint |
| P_STAGE | Memory pass sau chỉ đọc sau commit barrier; hai tầng NTT fused trong tile không cần RAM barrier giữa chúng |
| P_MASK | Inactive lane/job không có side effect, upper/reserved packet bits zero |
| P_FLUSH | First sampled flush edge trở đi không command write; ACK độc lập cpl_ready và pause |
| P_PAUSE | Pause giữ datapath/context/command write, published external responses vẫn có thể ACK |
| P_CFG | Mode/fmt/profile/N/jobs không thay trong command; invalid command không issue |
| P_CANON | Canonical NTT inputs => canonical outputs; không mất carry Montgomery |

Formal MAY tách proof theo block. Liveness được giả định clock chạy và host
eventually drain memory response; không giả định arithmetic output hoặc tag đúng
để làm proof tự đúng. Báo proof depth, assumptions và inconclusive status. Danh
sách trên là nghĩa vụ thiết kế, chưa phải kết quả proof.

## 04.4 Coverage, determinism và liveness

Functional coverage MUST đóng các cross hợp lệ op×fmt×N×profile×jobs; các tuple
không hợp lệ có reject coverage. Bổ sung context×phase×lane, bank collision,
tail/pair, và pause/flush/reset ở từng state cùng first/last write. Không yêu cầu
hit cross bất khả thi; exclusion phải có lý do review.

Mục tiêu code coverage sau exclusion review: line >=95%, branch >=90%. Tỷ lệ
này không thay thế functional coverage và assertion. Uncovered control/error
path cần testcase hoặc waiver, không được xóa RTL chỉ để tăng coverage.

Lịch hoạt động và thời gian MUST độc lập coefficient với cùng cấu hình, initial
state và flow-control trace. Root-cache valid cold tại mỗi CMD/flush. Schedule
phụ thuộc địa chỉ công khai được phép; schedule phụ thuộc residue/giá trị số học
không được phép. Chưa suy ra chống power/EM leakage từ yêu cầu này. (FT-DV-002)

Một valid command MUST publish completion trong <=1.048.576 active clocks nếu
không reset/flush, clock liên tục và consumer nội bộ fair. Pause chỉ loại khỏi
active count; external completion-ready không ảnh hưởng publication. Không có
external host-memory traffic trong RUN. Đây là bound phát hiện deadlock, không
là mục tiêu throughput. Hardware watchdog MAY có; testbench MUST timeout và
báo FAIL nếu vượt bound. (FT-DV-003)

## 04.5 Deliverables và gate để nhận RTL

Release RTL MUST có implementation manifest công bố ít nhất các mục 03.9,
source revision/hash, tool versions, test commands/seeds, test result từng ID,
coverage/exclusions, assertion/proof status, numeric/reference provenance,
cycle/stall report, deviation/waiver và known issues. (FT-DV-004)

Gate functional: không mismatch trên valid input, không assertion failure,
mọi mandatory suite PASS hoặc waiver được review rõ; không biến NOT_RUN thành
PASS. Gate application: T_SIGNER PASS mới được gọi là kiểm kernel trong luồng
R8, không đồng nghĩa chứng nhận FN-DSA. Gate physical/security riêng: synthesis,
STA/PPA, CDC/DFT/power/side-channel chưa làm phải ghi NOT_RUN. Không bịa MHz,
diện tích, area saving hoặc hiệu năng từ số leaf.

`scripts/check_flextransform_spec.py` chỉ kiểm tính nhất quán bộ spec/ROM/fixture,
không chạy các suite RTL trên. Spec package check PASS không là RTL signoff.
