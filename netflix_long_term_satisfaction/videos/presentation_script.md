# Lời dẫn cho 12 slide

Đề tài: **HỆ THỐNG KHUYẾN NGHỊ CHO SỰ HÀI LÒNG CỦA THÀNH VIÊN DÀI HẠN TẠI NETFLIX**. Giảng viên hướng dẫn: **TS. Hà Minh Tân**. Thời lượng dự kiến: 12–15 phút.

Slide là phần trình bày hệ thống. Khi thuyết trình, dùng sơ đồ và dashboard để giải thích; không đọc lại chữ trên màn hình. MovieLens là dữ liệu thử nghiệm, không phải dữ liệu thuê bao Netflix.

## Nguyễn Hoàng Phước — 25210169 — slide 1–4

1. **Mở đầu:** Giới thiệu tên đề tài. Nhóm xây một hệ thống gợi ý phim và dùng MovieLens để thử quy trình.
2. **Đầu ra:** Lịch sử chấm điểm tạo danh sách ứng viên, mô hình xếp hạng để chọn Top 10. Các lượt chấm diễn ra sau được dùng để đánh giá.
3. **Kiến trúc:** Chỉ lần lượt năm phần trên sơ đồ: đầu vào, xử lý, tạo ứng viên, xếp hạng và dashboard/API.
4. **Dữ liệu:** `ratings.csv` ghi người dùng chấm phim nào, bao nhiêu sao, vào lúc nào; `movies.csv` có tên và thể loại. MovieLens không có thông tin thuê bao hay mức hài lòng thật của Netflix.

## Nguyễn Hoàng Tân — 25210188 — slide 5–6

5. **Chọn người dùng và chia thời gian:** Bản full chọn người có ít nhất 20 lượt chấm trong 180 ngày; smoke dùng ngưỡng 5 lượt trong 30 ngày. Train đứng trước validation và test. Đặc trưng chỉ tính từ train.
6. **Pipeline dữ liệu:** RAW giữ tệp gốc; BRONZE kiểm tra bản ghi; SILVER lọc người dùng và chia lịch sử; GOLD tạo đặc trưng. HDFS và Spark thuộc cấu hình full.

## Lê Thị Bích Tuyền — 25210236 — slide 7–9

7. **Mô hình:** Phim phổ biến là mốc so sánh. ALS học mẫu chấm điểm để tạo ứng viên. Nhánh kết hợp xếp lại các ứng viên đó bằng đặc trưng.
8. **Phạm vi chạy:** Full được thiết kế với MovieLens 25M, HDFS, Spark ALS và TensorFlow MLP. Bản nộp hiện có kết quả smoke cục bộ bằng Python/NumPy ALS và bộ xếp hạng lại logistic.
9. **Kết quả smoke:** Bản lưu 15:24 ngày 29/09/2026 có 24 người dùng đủ điều kiện. Precision@10 và NDCG@10 của ALS cục bộ lần lượt là 9,17% và 18,89%; nhánh kết hợp là 5,83% và 14,21%. Chỉ số trên dữ liệu mẫu chưa chứng minh hiệu quả của bản full.

## Nguyễn Lê Thành Đạt — 25410029 — slide 10–12

10. **Dashboard:** Ảnh chụp ở chế độ SMOKE cho thấy một người dùng và ba danh sách gợi ý. Khi demo trực tiếp, kiểm tra nhãn SMOKE/FULL trước khi đọc số.
11. **Phần đã kiểm chứng:** Bộ kiểm thử có 21 bài đạt; bản lưu smoke có 24 người dùng. Nhóm cần chạy MovieLens 25M trên môi trường full trước khi kết luận về Spark ALS hoặc TensorFlow MLP.
12. **Kết thúc:** Tóm lại hệ thống có luồng dữ liệu, mô hình thử và dashboard. Cảm ơn thầy và các bạn, mời câu hỏi.
