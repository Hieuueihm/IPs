# 03 — Bộ nhớ, root và lịch thực thi

Contract0.2 đã khóa: geometry giữ baseline, read→accept2 và rsp→commit1 theo spec09; model đã replay theo lịch mới. Port/FSM normative ở spec08..11, không tự đổi latency rồi giữ gap cũ.

## 1. Dung lượng và cổng

| Bộ nhớ | Tổ chức logic | Cổng yêu cầu | Resource mục tiêu |
|---|---|---|---|
| Data | 32 bank ×256×32 | Mỗi bank 1R sync +1W/clock | 32 RAMB18 |
| Root | 16 RAM ×512×32 | Mỗi tile 1R sync; host ghi khi idle | 16 RAMB18 |
| Descriptor | 10 entry ×46 bit | Host ghi, stage prefetch | LUTRAM/FF, đo lại |
| Write context | 16 entry, 36 bit/entry | Một push/pop mỗi clock | LUTRAM/FF, đo lại |
| Tile state | Các RAM nhỏ độc lập, xem spec05 | Mỗi RAM đúng số cổng đã quy định | LUTRAM |

Data và root mỗi loại khai báo 32 KiB logic. Không cộng thêm bộ BRAM ping-pong: hai buffer dùng các vùng row trong cùng bank. BRAM vật lý lớn hơn dung lượng logic khai báo.

Không reset nội dung RAM để tránh biến RAM thành FF. Reset chỉ xóa valid/context. Không dựa vào read-first/write-first: cùng bank/cùng row read và write tại cùng cạnh là lịch bị cấm.

## 2. Decode cấu hình trước khi chạy

Đặt ln=logn, jl=jobs_log, f=fmt, pk=packed16, hm=hmin. Tính bằng số nguyên **đủ bit trước khi kiểm range**, không để unsigned underflow biến cấu hình sai thành địa chỉ hợp lệ.

```text
FFT:
  n=max(ln-1,0); base_log=f+1; job_word_log=ln+f
NTT:
  n=ln-(1 nếu pk && hm==0, ngược lại hm)
  base_log=max(0,hm-pk); job_word_log=ln-pk

bj=min(jl,max(0,5-n)); rj=jl-bj
rowlog=max(0,n-5)
plane_log=base_log+rj
M=2^n; rows=2^rowlog; planes=2^plane_log
stages=n + (NTT && pk && hm==0)
```

Chỉ nhận plane_log≤3, rowlog+plane_log≤7, cùng các điều kiện mode/q/logn trong spec01. Số row dùng mỗi buffer=rows*planes≤128; cả hai buffer≤256. Một line host chứa4 word; tổng word=2^(job_word_log+jl). Với FFT N1, word của phần ảo dummy không phải dữ liệu host hợp lệ.

Ví dụ FFT128 N1024: n9, base_log3, bj0, rj0, rows16, planes8; mỗi buffer128 row, không còn chỗ thêm job. Packed q12289 N32 ×16 job: n4, bj1, rj3, planes8; vừa, nhưng không phải mọi batch16 đều vừa.

## 3. Bank map và row map

Một job được tách `jb=job mod2^bj`, `jr=job>>bj`. p là chỉ số position theo geometry, bpl là plane trong một job; pl=(jr<<base_log)|bpl.

```text
row(buf,p,pl) = buf*rows*planes + pl*rows + (p>>5)

n>=6:
  bank(p,stage) = (p &31) XOR (((p>>(n-1)) &1)<<4)
n<6:
  v=rol_n(p,-stage) << (5-n)        // v=0 nếu n=0
  bank(p,jb,stage)=rol_5(v | (jb<<(5-n-bj)),stage)
```

`rol_w` rotate trong đúng w bit. Row fields không chồng nhau, nên RTL dùng nối bit/OR sau khi config đã kiểm bounds; không cần phép nhân/chia động. Dùng binary bank index5 bit trong state, decode sát mux. Không pipeline one-hot32 qua mọi stage.

## 4. Butterfly geometry

Một tầng thường đọc far `(i,i+M/2)` và ghi near `(2i,2i+1)`; inverse đảo hướng. Mapping host đầu/cuối phải dùng stage embedding tương ứng: thuận từ stage0 tới n, nghịch từ n về0. Phần FFT/NTT nguyên thủy vẫn dùng root theo thuật toán; geometry không tự thay root bằng một công thức khác.

Full packed hmin0 thêm tầng internal: cuối thuận hoặc đầu nghịch, hai butterfly nằm trong hai word. n0 có một word thực và một nhánh dummy; read dummy phải trả0 và write dummy phải bị mask. Không cho dummy làm thay đổi expected output count.

Root và mapping được pack theo thứ tự sử dụng `(tile,k,plane/beat)`. Descriptor mỗi tầng:

```text
{active_mask[15:0], root_base[8:0], root_mask[4:0], gap[15:0]} // 46 bit
```

root_mask là period−1, period lũy thừa2≤32. Root span cộng mọi beat phải≤512. Không cho phép arbitrary descriptor rồi hứa core vẫn chạy đúng; generator phải kiểm active mask, root span, terminal tag, dependencies và gap. START kiểm những điều kiện tĩnh rẻ: configured, root_commit và descriptor-valid đủ tầng. Tính đúng toán học/root-order vẫn thuộc generator/oracle.

Identity stages0 chỉ cần configured và input hợp lệ; không đòi descriptor/root cho một tầng không chạy.

## 5. Mạng nối bốn nguồn

Với tile t và dữ liệu bank đã đọc:

```text
x = near ? (swap ? bank[(2*t)^16] : bank[2*t])
         : (far_bit ? bank[t+16] : bank[t])
y = dummy ? 0
          : near ? (swap ? bank[(2*t+1)^16] : bank[2*t+1])
                 : (far_bit ? bank[t] : bank[t+16])
```

Đây là wire constant +mux4×32, không phải crossbar32×32. Select/mask/tag phải qua FF cùng latency BRAM. Mạng write chọn nguồn theo **write context**, không theo read stage đang chạy.

Forward bank b lấy tile b>>1 hoặc (b>>1)^8 theo swap, word b&1. Inverse bank b lấy tile b&15, chọn low/high theo k và nửa bank. Valid/mask dùng đúng cùng nhánh data. Kiểm bijection trên mọi tầng, chiều, batch; không chỉ nhìn hình dây.

## 6. Lịch arithmetic ban đầu

| Mode | Nhận request tại tile | Period theo butterfly | Lượt product |
|---|---|---:|---|
| NTT32 | pha0 trong period3 | 3 | T ở0, m ở5, mq ở10 |
| Packed16 | pha0 và1 trong period3 | 2 gói/3 clock | Mỗi nhóm giữ offset0/5/10 |
| FFT32/64/128 | 2L beat đầu vào/butterfly | 3/12/45 | p0 rồi p1 rồi p2 |

FUSE5, raw leaf3 là lựa chọn pipeline ban đầu. 5 mod3 khác0 nên feedback T/m/mq không trùng slot trong cùng nhóm. Nếu thay FUSE phải kiểm lại điều kiện này và toàn pipeline valid/history.

Packed steady-state:

| phi_launch (phi_req trừ2 modulo3) | Nhóm leaf0/1 | Nhóm leaf2/3 |
|---:|---|---|
| 0 | T | m |
| 1 | mq | T |
| 2 | m | mq |

Các ô thuộc các gói khác nhau. Một history T_hi/NZ dài10 phục vụ hai nhóm, vì tối đa một T-packet hợp lệ về mỗi clock. Reducer cuối xử lý hai lane/clock, không phải bốn lane/clock.

Core baseline đọc ở pha1 cho scalar, pha1/2 cho packed để request đến tile pha0/1. Bản viết lại chỉ giữ các pha này nếu tổng read→accept latency và reset phase khớp; version0.2 dùng read phase1 cho scalar,1/2 cho packed theo timing.json; không dùng phi_launch để quyết định req_ready.

## 7. Chồng lấp tầng

Planner giữ riêng thời gian read và write của từng event, latency phụ thuộc mode/direction/native. Chỉ phát tầng mới khi:

1. Không hai access tranh cùng cổng bank hoặc root.
2. Mỗi read thấy phiên bản dữ liệu của đúng tầng trước.
3. Không RAW cùng cạnh và không overwrite dữ liệu tầng trước chưa đọc.
4. Tile có buffer/side credit, product slot và đường output đúng lịch.
5. Write context queue còn chỗ trước request đầu tầng.

Không chèn global barrier cho mọi tầng chỉ để đơn giản hóa mà vẫn claim cycle baseline. Có thể dựng bản barrier ở milestone đầu để kiểm correctness, sau đó bật overlap và đo chênh lệch.

## 8. Hoàn tất và host

Context queue dùng active_mask và expected terminal tag đã sinh bởi planner. Track tail_seen16; pop sau khi các write tail đều commit. DONE khi tầng cuối pop, không còn request/product/output pending và tile busy đều0. Identity không chạy tile, DONE với cycles0 theo convention đã kiểm.

Host map/gather xử lý line128 bit thành4 word, phục vụ1/2/4 phase bank hoặc special case nhỏ. Tính bank/row trước, register rồi mới service. READ qua gather→round→shift→response; không hardcode mọi READ có cùng latency. IFFT đọc lại cùng line phải cho cùng kết quả, không normalize tích lũy hai lần.
