# Lời dẫn cho 13 slide

Đề tài: **HỆ THỐNG KHUYẾN NGHỊ CHO SỰ HÀI LÒNG CỦA THÀNH VIÊN DÀI HẠN TẠI NETFLIX**. Giảng viên hướng dẫn: **TS. Hà Minh Tân**. Thời lượng dự kiến: 12–15 phút.

Chỉ vào sơ đồ, biểu đồ và dashboard khi nói. MovieLens là dữ liệu thử nghiệm, không phải dữ liệu thuê bao Netflix.

## Nguyễn Hoàng Phước — 25210169 — slide 1–5

1. **Nhóm:** Giới thiệu học phần, giảng viên và bốn thành viên.
2. **Đề tài:** Nhóm xây hệ thống gợi ý phim cho bài toán thành viên dài hạn. MovieLens 25M cung cấp dữ liệu để thử quy trình.
3. **Luồng hệ thống:** Đi theo năm phần trên slide: dữ liệu, xử lý, ứng viên, xếp hạng, hiển thị.
4. **Đầu ra:** Lượt chấm trước tạo danh sách gợi ý Top 10. Lượt chấm xảy ra sau dùng để đánh giá danh sách.
5. **Dữ liệu:** `ratings.csv` ghi người dùng chấm phim nào, bao nhiêu sao và lúc nào; `movies.csv` có tên và thể loại. MovieLens không có thông tin thuê bao hay mức hài lòng thật của Netflix.

## Nguyễn Hoàng Tân — 25210188 — slide 6–7

6. **Pipeline:** RAW giữ tệp gốc; BRONZE kiểm tra bản ghi; SILVER lọc người dùng và chia thời gian; GOLD tạo đặc trưng. HDFS và Spark thuộc cấu hình full.
7. **Chia lịch sử:** Full dùng ngưỡng 20 lượt chấm trong 180 ngày; smoke dùng 5 lượt trong 30 ngày. Train đứng trước validation và test. Đặc trưng chỉ tính từ train.

## Lê Thị Bích Tuyền — 25210236 — slide 8–9

8. **Mô hình:** Phim phổ biến là mốc so sánh. ALS học mẫu chấm điểm để tạo ứng viên. Nhánh kết hợp xếp lại ứng viên bằng đặc trưng.
9. **Phạm vi:** Full thiết kế với MovieLens 25M, HDFS, Spark ALS và TensorFlow MLP. Kết quả bản nộp là smoke cục bộ bằng Python/NumPy ALS và bộ xếp hạng lại logistic.

## Nguyễn Lê Thành Đạt — 25410029 — slide 10–13

10. **Dashboard:** Ảnh chụp ở chế độ SMOKE cho thấy người dùng 1 và ba danh sách gợi ý. Khi demo trực tiếp, đọc nhãn SMOKE/FULL trước khi nói về kết quả.
11. **Biểu đồ:** Bản lưu 15:24 ngày 29/09/2026 có 24 người dùng. Precision@10 và NDCG@10 của ALS cục bộ là 9,17% và 18,89%; nhánh kết hợp là 5,83% và 14,21%. Đây là kết quả trên dữ liệu mẫu.
12. **Kiểm chứng:** 21 bài kiểm thử đạt; bản smoke có 24 người dùng. Nhóm cần chạy MovieLens 25M trong môi trường full trước khi kết luận về Spark ALS hoặc TensorFlow MLP.
13. **Kết thúc:** Hệ thống hiện có luồng xử lý, mô hình thử và dashboard. Cảm ơn thầy và các bạn, mời câu hỏi.
