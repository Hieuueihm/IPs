# Hướng dẫn toán học đến RTL - contract 0.2

Tài liệu dẫn giải riêng, không sửa `rebuild/flextransform/microarchitecture/LOCK_0_2.json`
và không thay baseline được chấp nhận. Ngày phát hành: 07/11/2026.

Phiên bản hướng dẫn **1.2** có **58 sơ đồ structural vector**, gồm18 hình D01..D18
mở sâu theo pin/net. Chương36 là wiring trong tile/core, chương37 có23 hồ sơ
port/register với semantics cho **444/444 cổng**, chương38 là bảng mux và token theo cạnh.
Sơ đồ không phải mapped netlist sau tổng hợp hoặc sơ đồ transistor.
Bản1.0 và1.1 được giữ tại `output/pdf/archive/guide_1_0/` và `guide_1_1/`.

- PDF: `output/pdf/FlexTransform_Contract_0_2_Toan_hoc_den_RTL.pdf` từ workspace root.
- Bản đọc/sửa: `SPEC_TOAN_HOC_DEN_RTL.md` (sinh từ nguồn nội dung).
- Nguồn nội dung: `content.py`; nguồn layout và bảng cổng/FSM: `build_pdf.py`.
- Nguồn sơ đồ: `structural.py`; SVG sửa độc lập: `structural_svg/`.
- Phần chi tiết pin: `structural_detail.py`; binding/register: `detail_contract.py`.
- `structural_manifest.json`: chỉ mục58 hình, module tương ứng và hash SVG.
- `source_manifest.json`: SHA-256 của các nguồn contract đã dùng.
- `build_qa.json`: coverage module/port, font, phép tính mẫu và audit layout.

## Dựng lại

Yêu cầu Python có `reportlab`, `pypdf`, `pdfplumber`, `Pillow`; font Windows Arial và Consolas.

```powershell
python -X utf8 docs/implementation_guide/contract_0_2/build_pdf.py
pdftoppm -r 65 -png output/pdf/FlexTransform_Contract_0_2_Toan_hoc_den_RTL.pdf tmp/pdfs/flextransform_spec_0_2/page
python -X utf8 docs/implementation_guide/contract_0_2/qa_pdf.py
python -X utf8 docs/implementation_guide/contract_0_2/qa_structural.py
python -X utf8 rebuild/flextransform/tools/check_design.py
python -X utf8 scripts/check_baseline.py
```

Trong phiên dựng đầu dùng bundled Python/Poppler của Codex. Bản PDF có bookmark/mục lục,
font tiếng Việt nhúng và bảng cổng trực tiếp từ `ports.json`. Kiểm render là bước bắt buộc
sau thay đổi nội dung/layout; text extraction không thay thế kiểm hình.

## Giới hạn chứng cứ

Không sinh RTL hoặc kế thừa PASS/PPA của baseline. Các mục tiêu LUT/timing của bản viết lại
vẫn là mục tiêu. Hash, coverage và kiểm PDF không phải functional verification RTL.
