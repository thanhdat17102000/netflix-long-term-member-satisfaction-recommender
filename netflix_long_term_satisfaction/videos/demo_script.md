# Kịch bản quay demo

Đề tài: **HỆ THỐNG KHUYẾN NGHỊ CHO SỰ HÀI LÒNG CỦA THÀNH VIÊN DÀI HẠN TẠI NETFLIX**.

## Chuẩn bị

Mở thư mục dự án, `configs/smoke.yaml`, `configs/full.yaml` và `tests/fixtures/ml-25m`. Nói rõ MovieLens 25M đầy đủ không nằm trong kho mã nguồn. Kiểm tra trước nhãn SMOKE/FULL trên dashboard và thời điểm tạo tệp kết quả để không đọc nhầm số từ lần chạy cũ.

## Lời mở đầu gợi ý

“Nhóm em thực hiện đề tài hệ thống khuyến nghị cho sự hài lòng của thành viên dài hạn tại Netflix. Bản demo dùng MovieLens để thử quy trình xử lý dữ liệu, tạo phim ứng viên, xếp hạng lại và đánh giá bằng những lượt chấm về sau. Trên máy này, dashboard đang dùng dữ liệu mẫu; nhóm sẽ phân biệt rõ kết quả đó với cấu hình full.”

## Quay phần chạy chương trình

1. Chạy `python -m pytest -q` và cho xem kết quả kiểm thử.
2. Nếu máy có đủ Spark và Hadoop, chạy lần lượt các script `01_upload_raw.sh` đến `08_evaluate.sh` với `--profile smoke`. Ở mỗi bước, chỉ vào đầu vào và tệp đầu ra thực sự được tạo.
3. Nếu máy chưa có các phần mềm trên, chỉ trình bày mã nguồn và cấu hình của pipeline Spark; không nói rằng pipeline đã chạy thành công.
4. Chạy `python -m src.web`, mở `http://127.0.0.1:8765` và giới thiệu dashboard.

## Quay dashboard

1. Chỉ vào nhãn SMOKE/FULL, nguồn dữ liệu và thời điểm tạo kết quả. Giải thích SMOKE dùng Python/NumPy cục bộ; FULL chỉ xuất hiện khi có đủ tệp kết quả của pipeline đầy đủ.
2. Ở mục **Bài toán**, nói cách chia lượt chấm theo thời gian và quy ước từ 4 sao là phản hồi tích cực.
3. Ở mục **Pipeline**, đi từ RAW đến EVALUATION. Đọc trạng thái từ dữ liệu hiển thị; các tên bước trong SMOKE là sơ đồ thiết kế, không chứng minh Spark đã chạy.
4. Ở mục **Dữ liệu**, xem số phim, số người dùng đủ điều kiện, bảng phim và lịch sử chấm điểm. Mở phần kiểm tra chất lượng dữ liệu.
5. Ở mục **So sánh mô hình**, chỉ vào ba cột kết quả. Với SMOKE, gọi đúng tên ALS cục bộ và bộ xếp hạng logistic. Nếu cách gợi ý phim phổ biến có SatisfiedHit@10 bằng 0, đọc trực tiếp ba giá trị thay vì diễn giải “lift 0%” là hòa nhau.
6. Ở mục **Giải thích**, chọn một người dùng, xem ba danh sách gợi ý và lịch sử train/validation/test. Chỉ đọc lý do có trong dữ liệu; khi thiếu đặc trưng, giao diện sẽ báo chưa có dữ liệu giải thích.
7. Ở mục **Tái lập**, cho xem các lệnh chạy và những tệp còn cần để có kết quả FULL.

## Những điểm cần nói đúng

- ALS tạo phim ứng viên; bộ xếp hạng lại sắp xếp danh sách ứng viên.
- Tập test chỉ dùng để đánh giá. Các chỉ số từ lượt chấm MovieLens không đo trực tiếp sự hài lòng của người dùng Netflix.
- Báo cáo và slide phải ghi cùng thời điểm, cùng số liệu với tệp kết quả được mở trong video.
