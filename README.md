# HỆ THỐNG KHUYẾN NGHỊ CHO SỰ HÀI LÒNG CỦA THÀNH VIÊN DÀI HẠN TẠI NETFLIX

Đây là bản nộp đồ án Công nghệ dữ liệu lớn của Nhóm 9. Nhóm dùng dữ liệu MovieLens để thử nghiệm hệ thống khuyến nghị trong đề tài. MovieLens không phải dữ liệu Netflix; các chỉ số về thành viên dài hạn và phản hồi tích cực là cách đo thay thế từ lịch sử chấm điểm.

## Hai file nộp

- [Nhom9_Netflix_BaoCao.docx](Nhom9_Netflix_BaoCao.docx): báo cáo Word.
- [Nhom9_Netflix_ThuyetTrinh.pptx](Nhom9_Netflix_ThuyetTrinh.pptx): slide PowerPoint để thuyết trình.

Mã nguồn và hướng dẫn chạy nằm trong [thư mục dự án](netflix_long_term_satisfaction/README.md).

## Nhóm thực hiện

| Sinh viên | MSSV |
| --- | --- |
| Nguyễn Hoàng Phước | 25210169 |
| Nguyễn Hoàng Tân | 25210188 |
| Lê Thị Bích Tuyền | 25210236 |
| Nguyễn Lê Thành Đạt | 25410029 |

Giảng viên hướng dẫn: **TS. Hà Minh Tân**.

Số liệu trong báo cáo và slide dựa trên [bản lưu kết quả smoke](netflix_long_term_satisfaction/artifacts/metrics/submission_smoke_metrics.json) tạo lúc 15:24 ngày 29/09/2026 (giờ Việt Nam). Bản này chạy trên dữ liệu mẫu bằng Python/NumPy, có 24 người dùng đủ điều kiện và 216/24/48 lượt train/validation/test. Đây chưa phải kết quả của pipeline full dùng Spark ALS và TensorFlow MLP.
