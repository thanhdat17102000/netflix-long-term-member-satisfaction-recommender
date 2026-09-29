# Gợi ý lời trình bày cho 12 slide

Đề tài: **HỆ THỐNG KHUYẾN NGHỊ CHO SỰ HÀI LÒNG CỦA THÀNH VIÊN DÀI HẠN TẠI NETFLIX**.

Thời lượng dự kiến: 12–15 phút. Bốn thành viên nói phần được phân công dưới đây và chuyển ý sang người tiếp theo. Giảng viên hướng dẫn: TS. Hà Minh Tân. Khi trình bày số liệu, đọc theo bản báo cáo và dashboard đã chốt cho cùng một lần chạy.

## Nguyễn Hoàng Phước — 25210169 — slide 1–4, khoảng 3 phút

“Nhóm em thực hiện đề tài hệ thống khuyến nghị cho sự hài lòng của thành viên dài hạn tại Netflix. Nhóm dùng MovieLens 25M công khai để thử nghiệm cách khuyến nghị phim. Vì MovieLens không có thông tin thuê bao hay thời lượng xem, nhóm không thể đo sự hài lòng thật của thành viên Netflix.”

“Trong cấu hình đầy đủ, nhóm chọn người có ít nhất 20 lượt chấm trải dài 180 ngày. Khi đánh giá gợi ý, một lượt chấm từ 4 sao được xem là phản hồi tích cực. Đây là hai quy ước để thực nghiệm trên dữ liệu hiện có, không phải định nghĩa về khách hàng dài hạn hay mức hài lòng của Netflix.”

## Nguyễn Hoàng Tân — 25210188 — slide 5–6, khoảng 3 phút

“MovieLens 25M gồm sáu tệp đầu vào. Nhóm giữ bản gốc ở tầng RAW, chuẩn hóa dữ liệu tại BRONZE, tạo các bảng và chia lịch sử theo thời gian ở SILVER, rồi chuẩn bị đặc trưng cho mô hình tại GOLD. Khi chạy cấu hình full, HDFS dùng để lưu dữ liệu và Spark xử lý các bảng lớn.”

“Nhóm chia lượt chấm theo thời gian để phần dùng đánh giá xảy ra sau phần huấn luyện. Các thống kê về phim và người dùng được tính từ dữ liệu huấn luyện, tránh đưa thông tin của tập kiểm tra vào mô hình.”

## Lê Thị Bích Tuyền — 25210236 — slide 7–9, khoảng 4 phút

“Nhóm so sánh ba cách gợi ý: chọn phim phổ biến, Spark ALS và ALS kết hợp bộ xếp hạng lại TensorFlow MLP. ALS tạo danh sách ứng viên từ lịch sử chấm điểm. MLP dùng thêm đặc trưng về phim và người dùng để sắp xếp danh sách đó.”

“Các chỉ số như Precision@10, NDCG@10 và SatisfiedHitRate@10 đánh giá danh sách trên các lượt chấm về sau. RMSE chỉ dùng cho mô hình dự đoán số sao; bộ xếp hạng lại không có chỉ số này.”

“Dashboard giúp xem dữ liệu, trạng thái xử lý, kết quả của từng mô hình và gợi ý cho một người dùng cụ thể. Ở chế độ SMOKE, dashboard dùng bộ dữ liệu mẫu và mô hình Python/NumPy cục bộ. Bộ xếp hạng lại trong bản này là logistic, không phải TensorFlow MLP.”

“Slide số liệu lấy từ bản lưu `submission_smoke_metrics.json` tạo lúc 15:24 ngày 29/09/2026. Có 24 người dùng đủ điều kiện. Những số này cho thấy chương trình chạy trên dữ liệu mẫu; chúng không đại diện cho kết quả MovieLens 25M.”

## Nguyễn Lê Thành Đạt — 25410029 — slide 10–12, khoảng 3–4 phút

“Khi demo, nhóm mở dashboard và chỉ vào nhãn SMOKE hoặc FULL trước khi đọc số. Có thể chọn một người dùng để so sánh ba danh sách gợi ý và xem các lượt chấm nằm ở train, validation hay test.”

“Hiện dự án có mã nguồn, cấu hình, dữ liệu mẫu và kết quả smoke. Để báo cáo kết quả full, nhóm còn phải chuẩn bị MovieLens 25M, môi trường Hadoop/Spark/TensorFlow, chạy toàn bộ pipeline và lưu đầu ra của lần chạy. Vì vậy, phần kết luận chỉ nói về những gì đã được kiểm chứng. Em xin cảm ơn thầy và các bạn.”
