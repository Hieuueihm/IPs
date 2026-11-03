# Kết quả RTL: reducer và radix-4 factor

Ngày 26/10/2026. Phạm vi: số học cụm nhỏ cho q3329/q12289 và FFT32 raw.
Các số GE/độ dài gate là generic, chưa có timing đích hoặc đo công suất.

## 1. Đối chứng reducer

Giữ nguyên cụm bốn multiplier, tất cả mode 0/1/2/3, CT/GS, ba cạnh lấy mẫu,
II=1, profile runtime và tag. Cả ba dùng **cùng mạng sinh m**; thay phần tính S
hoặc high(mq), nên so được tác động của reduction thay vì đổi cả butterfly.

| Reducer trong shared cluster | Total GE | FF bit | Độ dài gate | So area baseline |
|---|---:|---:|---:|---:|
| Original shift-add | 29 300,0 | 643 | 124 | 1,000× |
| CSA cho weighted sum S | 29 488,9 | 643 | 109 | 1,006× |
| **Compact high(mq)** | **28 197,5** | **643** | **118** | **0,962×** |

Chọn **compact** để đo bước radix-4: area thấp nhất trong các bản có độ dài gate
không vượt original. Đây là quy tắc sàng lọc theo proxy, không phải chốt timing ASIC.
CSA còn đáng giữ khi ưu tiên đường logic: tăng0,64% GE, giảm124→109 gate. Không
bỏ CSA chỉ vì nó không nhỏ nhất. Reducer độc lập fixed-q có tradeoff khác: compact
nhỏ hơn nhưng có thể nhiều gate trên đường dài hơn original; không có winner mọi mục tiêu.

Reducer động standalone: original2 109,1 GE/depth51, CSA2 149,2/depth41,
compact1 828,9/depth50. Không cộng trực tiếp số standalone này vào core vì synthesis
có thể chia sẻ/prune và retime khác. Bảng đầy đủ gồm hai fixed-q nằm trong
[reducer_compare.md](../study/results/reducer_compare.md),
[JSON](../study/results/reducer_compare.json).

RTL chung: [mont_reduce16_functions.vh](../hdl/proto/mont_reduce16_functions.vh).
Ba cấu hình trong [flex_reduce_cluster.sv](../hdl/proto/flex_reduce_cluster.sv)
là bản thử riêng từ cụm cũ; **không sửa source hoặc kết quả baseline cũ**.

## 2. Radix-4 factor đã dựng đủ phần nào

[flex_radix4_factor.sv](../hdl/proto/flex_radix4_factor.sv) có cùng bốn mode của
cụm cũ: bốn BF NTT độc lập, hai tầng trên bốn hệ số, bypass tầng hai, và tích
signed32×32 raw cho FFT. Riêng mode paired dùng root `[uR,u²R,u³R]`; baseline
dùng `[common,distinct0,distinct1]`. Cả hai cần ba word; bảng phải được precompute
đúng representation ngoài hot path. Không thêm phép tính root ẩn vào throughput.

Factor có bốn cạnh lấy mẫu, II=1:

~~~text
Input registers → preprocess/constant inverse → register
                → central multipliers + reduction → register
                → postprocess/constant forward → output registers
~~~

Forward thực hiện ba tích với twiddle trước recombination và nhân c ở cuối.
Inverse nhân ci ở đầu, rồi ba tích với twiddle. Cả hai có đầy đủ modular add/sub,
reduction và nhánh bypass. Không dùng c chưa encode làm hằng của Montgomery.
Các hệ số c/ci theo root orientation của generator hiện có; chưa pin C Falcon/Kyber
NTT để khẳng định tương đương reference đó.

Bản **mixed** cho phép CT/GS/profile thay đổi từng transaction, nên có hai nhánh
constant ở pre/post. Bản **epoch** dùng một bộ nhân hằng + reducer chung cho hai
vị trí; profile và inverse phải giữ ổn định đến khi pipeline drain. Mode vẫn có
thể đổi từng transaction trong epoch, gồm FFT và NTT. Bản epoch không hứa hỗ trợ
đổi profile/direction liên tục như bản mixed.

Trong shared core, bốn multiplier vẫn phải giữ cho FFT/bốn BF NTT độc lập;
mode paired factor chỉ dùng ba. Khi tổng hợp NTT-pair-only, leaf thứ tư và các
đường FFT/independent BF mới được prune. Hai trường hợp phải báo riêng.

Đối chứng radix-2 có bản ba cạnh và bản thêm thanh ghi output thành bốn cạnh.
Bản bốn cạnh giữ II=1; các fixed-q được so cùng bốn cạnh. Đệm output là đối chứng
latency, chưa phải thiết kế radix-2 đã retime tối ưu. Mapping heuristic có thể
đổi nhẹ cả logic khi thêm wrapper/FF, nên dùng số cùng vòng để tính tỷ lệ.

## 3. Kết quả radix-4

Bảng đầy đủ và tỷ lệ trong [radix4_compare.md](../study/results/radix4_compare.md),
[JSON](../study/results/radix4_compare.json). Bảng dưới cùng dùng compact và II=1.

### 3.1 Core đầy đủ FFT + NTT mọi mode

| Core | Cạnh lấy mẫu | Total GE | FF bit | Độ dài gate |
|---|---:|---:|---:|---:|
| Radix-2 shared | 3 | 28 271,5 | 643 | 118 |
| Radix-2 shared, thêm output FF | 4 | 28 986,7 | 784 | 119 |
| Radix-4 shared mixed CT/GS | 4 | 40 557,8 | 778 | 101 |
| Radix-4 shared epoch, một constant-unit | 4 | 39 082,8 | 778 | 100 |

Epoch giảm area so với factor mixed, nhưng vẫn **+34,83% GE** so với radix-2
cùng bốn cạnh, hoặc **+38,24%** so với bản radix-2 ba cạnh. Đường gate ngắn hơn,
chưa có target timing để kết luận tốc độ. Ở cùng clock, II và data/nhóm như nhau;
factor không tạo thêm throughput, còn có thêm một cạnh latency so với baseline3.

Nguyên nhân resource: mode FFT và bốn BF độc lập giữ cả bốn multiplier; factor
paired không tiết kiệm được leaf vật lý ở bản shared. Nó còn cần pre/post route,
modular recombination, mạng hằng và reducer cho nhánh đó. Tối ưu chung một bộ
constant không xóa hết chi phí phục vụ nhiều mode. Đây là kết quả ứng viên RTL
hiện tại, không phải chứng minh mọi kiến trúc radix-4 shared đều thua.

### 3.2 Chỉ NTT-pair, cùng bốn cạnh

| Profile | Radix-2 GE / depth | Radix-4 mixed GE / depth | Radix-4 epoch GE / depth |
|---|---:|---:|---:|
| Runtime hai q | 21 259,1 / 119 | 22 803,9 / 97 | 21 279,2 / 104 |
| Fixed12289 | 17 779,7 / 109 | 16 900,7 / 87 | 16 412,7 / 90 |
| Fixed3329 | 15 407,6 / 113 | 15 133,6 / 87 | 14 467,9 / 89 |

Factor epoch runtime q có area chênh0,09% với radix-2, xem như ngang nhau trong
flow generic; depth119→104 đáng đo timing tiếp. Với fixed q12289, factor epoch
giảm **7,69% area**, fixed q3329 giảm **6,10%**; đây là nơi leaf thứ tư thực sự
được prune và constant network được chuyên biệt hóa. Các baseline fixed-q cũng
dùng compact, cùng bốn cạnh, nên không trộn lợi ích đổi reducer vào lợi ích radix.

Epoch yêu cầu drain khi đổi profile/direction; không dùng số này để quảng bá
khả năng chuyển CT/GS mỗi cycle. Mixed vẫn được đo để thể hiện giá của contract
mạnh hơn. Không quy các số gate-depth thành phần trăm tăng Fmax.

### 3.3 Quyết định cho core hiện tại

**Giữ cụm radix-2 một/hai tầng + compact reducer làm đường phát triển shared core.**
Giữ CSA là ứng viên khi ưu tiên timing. Chưa chọn radix-4 factor làm default
FFT/NTT vì chi phí của các mode dùng chung trong bản đo này còn cao.

Giữ radix-4 epoch làm ứng viên cho cụm NTT chuyên biệt/profile cố định hoặc một
phương án giảm số mode. Bản pair-only không đủ thay toàn core: không có FFT,
bốn BF độc lập hoặc tầng lẻ bypass. Đưa nó vào core cần tính lại phần bổ sung,
không lấy số16,4k/14,5k làm area của toàn core linh hoạt.

## 4. Kiểm chứng

Reducer: **139 292 transaction**, gồm duyệt hết65 536 Tlow mỗi q, T biên/lo=0,
random đến (q−1)², đổi profile và valid bubbles. Chín cấu hình reducer gồm ba
implementation × dynamic/fixed12289/fixed3329 được kiểm theo profile hỗ trợ.

Cụm đổi reducer: **16 102 transaction ×3 implementation**, mọi mode/CT/GS,
56 trace NTT/INTT theo từng nhóm và70 CMUL C R8 được ghép trong driver từ các
tích FFT32 RTL. Không sai khác; ghépW128, rounding và3M vẫn ở driver, chưa phải
FFT128 mới trong RTL.

Radix-4: **17 510 transaction**, kiểm cả baseline và factor, tất cả mode và
latency3/4 cạnh. 640 vector unit với root tùy ý không thỏa quan hệ hai tầng NTT
được thay bằng2 048 vector factorable mới. Các nhóm transform với root thật
được giữ lại. Chưa chấp nhận arbitrary roots cho mode radix-4 paired.

Cùng17 510 transaction được nhóm thành bốn epoch profile/direction; testbench
ngừng issue, drain rồi mới đổi epoch. Bốn cấu hình một constant-unit được kiểm
theo mode/profile hỗ trợ. Kiểm tag, thứ tự, valid bubbles và latency chính xác.
Các top pair-only/fixed-q không nhận mọi mode trong bộ vector; coverage được
báo riêng trong log, không gọi mọi vector là testcase hợp lệ cho mọi top.

Expected NTT dùng integer arithmetic theo từng tầng; chưa differential C NTT.
Normalization INTT và BASEMUL không trong cụm. Các trace không phải một full
transform có RAM/scheduler/stall; không dùng số này để báo speedup FN-DSA.

## 5. Tái lập

~~~powershell
python -X utf8 scripts/benchmark_reducers.py
wsl --exec env LD_LIBRARY_PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/lib/x86_64-linux-gnu PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin:/usr/bin:/bin python3 -X utf8 /mnt/d/IPs/NTRU/scripts/benchmark_reducers.py --synth-only --yosys /mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin/yosys
python -X utf8 scripts/benchmark_radix4.py
wsl --exec env LD_LIBRARY_PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/lib/x86_64-linux-gnu PATH=/mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin:/usr/bin:/bin python3 -X utf8 /mnt/d/IPs/NTRU/scripts/benchmark_radix4.py --synth-only --yosys /mnt/d/IPs/NTRU/study/tools/yosys_native/root/usr/bin/yosys
~~~

Lệnh radix-4 đọc selection của reducer và sinh wrappers cố định implementation.
`--synth-only` kiểm hash RTL/header/testbench, và kiểm selection chưa đổi. Build/log
ở `study/build/reducer_compare/`, `study/build/radix4_compare/`. Flow Yosys0.52,
`synth -flatten -noabc`, `abc -fast -g` generic gates, GE gồm FF ×4,67.

Chưa có fabric compressor chia sẻ FFT/reduction được hiện thực trong vòng này.
Ứng viên CSA ở đây nằm **trong reducer**; không được gán kết quả của nó thành
bằng chứng đã chia sẻ toàn cây cộng FFT/NTT. FFT64/128/interconnect/timing đích
và số cụm toàn core vẫn chưa chốt.
