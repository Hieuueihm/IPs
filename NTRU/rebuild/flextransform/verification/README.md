# Verification workspace

Kế hoạch normative ở [spec06](../spec/06_verification.md). Chưa có testbench mới, vì chưa có RTL mới.

Các thư mục sẽ tạo khi triển khai: `unit/`, `tile/`, `core/`, `axi/`, `application/`, `model/`, `assertions/`, `adapters/`. Golden input/output/root được đọc từ nguồn đã khóa; fixtures/gaps theo latency mới ghi vào build riêng.

Không dùng bằng chứng cũ làm PASS cho implementation mới. Không sửa vector C hoặc expected output để giải quyết mismatch. Một latency manifest phải đi cùng mọi descriptor bundle.
