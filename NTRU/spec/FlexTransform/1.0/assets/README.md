# Exact ROM, fixtures and executable oracle

Các file dưới đây là một phần contract FT-SPEC-1.0; SHA256 ở
[manifest](../manifest.json). Không dùng float để dựng lại FFT root.

| File | Encoding / mục đích |
|---|---|
| fft_q64_64.mem | 1.024 row, mỗi dòng 64 hex digit: re128 ở high128, im128 ở low128; signed two's complement |
| ntt_q12289_forward.mem / inverse.mem | 1.024 row, mỗi dòng 4 hex digit, canonical root×65536 mod12289 |
| ntt_q3329_forward.mem / inverse.mem | 128 row, mỗi dòng 4 hex digit, canonical root×65536 mod3329 |
| kernel_fixtures.jsonl | Một JSON record mỗi dòng, mọi tuple CMD hợp lệ gồm batch nhỏ; a/b/expected là list jobs, mỗi job là list hex words |
| primitive_fixtures.json | Edge/tie/wrap cho fixed mul/div2e và canonical Montgomery |
| command_fixtures.json | CMD valid/invalid và priority expected_status |
| reference_model.py | Oracle số nguyên độc lập cycle; validate/evaluate/read_roots; chỉ dùng standard library |
| provenance.json | Pinned C commit/config và hash các nguồn sinh asset/vector |

Word trong fixture là đúng W bit unsigned hex, giữ đủ leading zero. Diễn giải
signed FFT theo W, không tự coi word có bit cao là số dương. Output SPLIT đã
concatenate f0 rồi f1. MERGE input A/B có N/2 word. B không dùng ghi dưới dạng
`[[]]` cho một job; layout host xem 03.4. Format RES16 mới=3 dù baseline cũ dùng
width=0 cho NTT; provenance ghi rõ conversion này.

Ví dụ Python (không cần môi trường simulator):

```python
import importlib.util, json
from pathlib import Path
p = Path('spec/FlexTransform/1.0/assets')
s = importlib.util.spec_from_file_location('ft_oracle', p/'reference_model.py')
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
r = json.loads((p/'kernel_fixtures.jsonl').read_text().splitlines()[0])
decode = lambda jobs: [[int(x, 16) for x in job] for job in jobs]
assert m.evaluate(r['command'], decode(r['a']), decode(r['b']), m.read_roots(p)) == decode(r['expected'])
```

FFT và q12289 roots lấy từ pinned scalar LP64 R8
`ad1e5bf7714d53230ad457364db8a46a1b459c94`, FPR_MODE=2, AVX2=0.
q3329 root[k] là 17^bitreverse7(k); inverse lấy nghịch đảo root thường rồi
encode Montgomery. Không đồng nghĩa toàn bộ IP là core ML-KEM.

`baseline_expected` fixture giữ nguyên expected của baseline capture/oracle;
`spec_integer_oracle` ghi rõ expected được sinh theo contract cho batch/identity
chưa có baseline. W32/64 và q3329 có evidence theo integer contract, không phải
chứng minh an toàn giảm precision cho FN-DSA. Bộ fixture này không thay thế
toàn bộ test plan 04 hay kiểm live signer.

Rebuild từ repo gốc: `python -X utf8 scripts/build_flextransform_spec_assets.py`;
sau đó chạy `python -X utf8 scripts/check_flextransform_spec.py`. Generator cần
baseline captures nêu trong provenance; dùng bản phát hành đã hash không cần
captures để chạy oracle. Thay đổi ROM/contract phải qua CHANGELOG/version review.
