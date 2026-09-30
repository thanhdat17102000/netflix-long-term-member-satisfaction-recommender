# HỆ THỐNG KHUYẾN NGHỊ CHO SỰ HÀI LÒNG CỦA THÀNH VIÊN DÀI HẠN TẠI NETFLIX

Đây là đồ án môn Công nghệ dữ liệu lớn của Nhóm 9. Nhóm dùng MovieLens 25M để thử nghiệm cách khuyến nghị phim cho thành viên dài hạn trong bối cảnh Netflix. Dự án gồm phần xử lý dữ liệu, mô hình khuyến nghị, đánh giá và dashboard trình bày kết quả.

MovieLens 25M là dữ liệu công khai của GroupLens, không phải dữ liệu Netflix. Bộ dữ liệu không có thời gian thuê bao, thời lượng xem, tỷ lệ xem hết hay thông tin hủy thuê bao. Vì vậy, các chỉ số về “người dùng dài hạn” và “hài lòng” trong đồ án chỉ là cách đo thay thế từ lịch sử chấm điểm.

## Nhóm thực hiện

| Sinh viên | MSSV |
| --- | --- |
| Nguyễn Hoàng Phước | 25210169 |
| Nguyễn Hoàng Tân | 25210188 |
| Lê Thị Bích Tuyền | 25210236 |
| Nguyễn Lê Thành Đạt | 25410029 |

Giảng viên hướng dẫn: **TS. Hà Minh Tân**.

Bản nộp ở thư mục cha là một file `Nhom9_Netflix_BanNop.pdf`: năm trang báo cáo, tiếp theo là 12 trang slide. Số liệu trong bản nộp lấy từ bản lưu `artifacts/metrics/submission_smoke_metrics.json` lúc 15:24 ngày 29/09/2026 (giờ Việt Nam). File `web_smoke_metrics.json` được tạo lại khi chạy dashboard nên thời điểm tạo của nó có thể khác.

## 1. Mục tiêu

Tổ chức dữ liệu theo bốn tầng `RAW → BRONZE → SILVER → GOLD`, sau đó so sánh ba cách gợi ý:

1. Gợi ý theo mức độ phổ biến của phim.
2. Spark ALS tạo danh sách phim ứng viên.
3. Spark ALS kết hợp TensorFlow MLP để xếp hạng lại ứng viên.

Kết quả được đánh giá trên các lượt chấm xảy ra sau dữ liệu huấn luyện. Cách chia này giúp tránh để mô hình học trước thông tin của tập kiểm tra.

## 1.1 Các phần của dự án

Dashboard chỉ là nơi xem kết quả. Phần xử lý và đánh giá nằm trong các bước sau:

1. **Lưu trữ:** đưa sáu tệp MovieLens vào HDFS và sắp xếp dữ liệu theo bốn tầng.
2. **Xử lý:** dùng Apache Spark đọc và kiểm tra dữ liệu, nối các bảng, rồi chia lượt chấm theo thời gian.
3. **Tạo ứng viên:** dùng Spark ALS học từ lịch sử chấm điểm để chọn phim có thể phù hợp với từng người dùng.
4. **Xếp hạng lại:** dùng TensorFlow MLP kết hợp điểm ALS với thể loại, Tag Genome, năm phát hành và lịch sử người dùng.
5. **Đánh giá:** so sánh ba cách gợi ý bằng RMSE và các chỉ số Top-N trên tập kiểm tra.
6. **Trình bày:** lưu dữ liệu đầu ra, mô hình và chỉ số; mở dashboard để xem kết quả và trạng thái từng bước.

Đồ án tập trung vào cách đi từ dữ liệu chấm điểm đến danh sách gợi ý có thể đánh giá và chạy lại được. Netflix là bối cảnh minh họa; mọi kết quả thực nghiệm đều dựa trên MovieLens.

## 2. Cách xác định người dùng dài hạn và phản hồi tích cực

- Trong cấu hình full, người dùng đủ điều kiện khi có ít nhất `20` lượt chấm trải dài `180` ngày.
- `activity_span_days` là số ngày giữa lượt chấm đầu tiên và cuối cùng.
- Lượt chấm từ `4.0` sao trở lên được xem là phản hồi tích cực để đánh giá ngoại tuyến.
- Cấu hình smoke dùng ngưỡng `30` ngày và `5` lượt chấm để chạy với dữ liệu mẫu nhỏ; ngưỡng full vẫn giữ nguyên.

## 3. Giới hạn của dữ liệu

MovieLens không cho biết một người đã thuê bao bao lâu, có hủy thuê bao hay không, xem phim trong bao lâu hoặc có xem hết phim không. `SatisfiedHitRate@10` và `satisfaction_lift_vs_popularity` chỉ phản ánh lượt chấm từ 4 sao trở lên trong tập kiểm tra; chúng không đo trực tiếp sự hài lòng của người dùng Netflix.

## 4. Chuẩn bị dữ liệu MovieLens 25M

Đặt file `ml-25m.zip` tại:

```text
data/input/ml-25m.zip
```

Giải nén đủ sáu tệp `ratings.csv`, `movies.csv`, `tags.csv`, `links.csv`, `genome-scores.csv` và `genome-tags.csv`. Không đưa tệp ZIP hoặc CSV lớn vào kho mã nguồn.

Nguồn: [MovieLens 25M](https://grouplens.org/datasets/movielens/25m/) hoặc Kaggle mirror tương đương.

## 5. Kiểm tra tệp đầu vào

Sau `scripts/01_upload_raw.sh`, kiểm tra:

- `artifacts/raw_manifest.sha256`
- `artifacts/raw_manifest.json`

Tệp manifest ghi tên, dung lượng, mã SHA-256, số dòng, tiêu đề cột và thời điểm kiểm tra của từng tệp. Chỉ có thể xác nhận thông tin này cho cấu hình full sau khi đặt đủ dữ liệu vào `data/input/`.

## 6. Sơ đồ pipeline

```text
MovieLens CSV
  -> HDFS/local RAW
  -> BRONZE + quarantine
  -> SILVER (long-term users, temporal split)
  -> GOLD (train/val/test features, popularity)
  -> Spark ALS
  -> 100 candidates/user (smoke: 20)
  -> TensorFlow MLP re-ranker
  -> Top-10 + evaluation
```

Có hai cấu hình chạy: `smoke` dùng dữ liệu mẫu nhỏ để kiểm tra nhanh; `full` dùng MovieLens 25M.

## 7. HDFS / warehouse layout

```text
/ml25m/                  # full, storage_backend=hdfs
  raw/
  bronze/
  silver/
  gold/
  quarantine/

data/warehouse/ml25m_smoke/   # smoke, storage_backend=local
  raw/ bronze/ silver/ gold/ quarantine/
```

Đường dẫn lưu trữ nằm trong `configs/*.yaml` qua các mục `storage_backend`, `hdfs_root` và `local_warehouse`.

## 8. Schema RAW / BRONZE / SILVER / GOLD

Xem [schemas/data_contracts.md](schemas/data_contracts.md). Tóm tắt:

- RAW: giữ nguyên các tệp CSV đầu vào.
- BRONZE: chuẩn hóa kiểu cột, tách ngày từ thời điểm chấm và đưa bản ghi lỗi vào khu vực riêng.
- SILVER: `ratings`, `movies`, `genome_scores`, `user_stats`, `long_term_users`, `user_train`, `user_validation`, `user_test`.
- GOLD: `train`, `validation`, `test`, `movie_features`, `user_features`, `popularity`, `als_candidates`, `reranker_features`, `reranker_test_features`, `reranked_recommendations`.

## 9. Môi trường chạy

Cấu hình full cần:

- Ubuntu/Lubuntu single-node
- Hadoop 3.3.6, HDFS pseudo-distributed
- Spark 3.5.1
- Java 17
- Python 3.10
- PySpark ALS, TensorFlow CPU 2.15.1
- PyYAML, pytest, matplotlib

Dự án không tự cài các phần mềm hệ thống. Cài thư viện Python bằng lệnh:

```bash
pip install -r requirements.txt
```

Nếu thiếu Hadoop, Spark hoặc TensorFlow, script sẽ dừng và báo phần còn thiếu. Dự án không tạo kết quả thay thế để giả lập lần chạy full.

## 10. Dashboard trình bày kết quả

Bạn vẫn có thể mở dashboard với dữ liệu mẫu khi chưa cài Java, Hadoop hoặc Spark:

```bash
python -m src.web
```

Mở http://127.0.0.1:8765. Dashboard ưu tiên kết quả full khi có đủ tệp đầu ra; nếu thiếu, trang hiển thị dữ liệu mẫu smoke. Hai nguồn không bị trộn số liệu. Giao diện dùng HTML, CSS và JavaScript thuần, không gọi dịch vụ bên ngoài.

Ở chế độ `SMOKE`, các chỉ số và gợi ý được tính bằng Python/NumPy cục bộ. ALS và bộ xếp hạng logistic ở chế độ này chỉ phục vụ kiểm tra, không phải kết quả của Spark ALS hoặc TensorFlow MLP.

Dashboard một trang gồm:

- Thanh đầu trang cho biết cấu hình đang hiển thị, thời điểm tạo kết quả và nguồn dữ liệu.
- Sơ đồ thể hiện các bước `RAW → BRONZE → SILVER → GOLD → ALS → RE-RANKER → EVALUATION` cùng trạng thái có thể kiểm chứng.
- Phần dữ liệu cho xem số dòng, cấu trúc tệp, dữ liệu thiếu, bản ghi trùng và cách chia theo thời gian.
- Phần mô hình so sánh phim phổ biến, ALS và mô hình kết hợp. Nhãn của chế độ smoke phân biệt rõ mô hình cục bộ với Spark và TensorFlow.
- Phần gợi ý cho phép chọn người dùng để xem lịch sử, danh sách phim và các đặc trưng có sẵn.
- Phần tái lập ghi lệnh chạy cùng các tệp cần có để chuyển sang kết quả full.

Các API chỉ đọc:

```text
GET /api/health
GET /api/dashboard
GET /api/profile
GET /api/users?q=1
GET /api/users/{user_id}
GET /api/recommendations?user_id=1&model=hybrid&limit=10
GET /api/movies?query=Toy&genre=Comedy&year_from=1990&year_to=2000
GET /api/models
GET /api/metrics
GET /api/pipeline
GET /api/data-quality
```

Ví dụ kiểm tra nhanh:

```bash
curl http://127.0.0.1:8765/api/dashboard
curl "http://127.0.0.1:8765/api/recommendations?user_id=1&model=hybrid&limit=10"
```

## 11. Chạy smoke

Chế độ smoke dùng dữ liệu mẫu trong `tests/fixtures/ml-25m`, nên không cần tải MovieLens 25M. Trên Windows, các script Bash cần Git Bash hoặc WSL.

```bash
python -m compileall -q src tests
python -m pytest -q
bash scripts/01_upload_raw.sh --profile smoke
bash scripts/02_run_bronze.sh --profile smoke
bash scripts/03_run_silver.sh --profile smoke
bash scripts/04_run_gold.sh --profile smoke
bash scripts/05_train_als.sh --profile smoke
bash scripts/06_generate_candidates.sh --profile smoke
bash scripts/07_train_reranker.sh --profile smoke
bash scripts/08_evaluate.sh --profile smoke
```

Script cũng chấp nhận `smoke` hoặc `full` dưới dạng đối số trực tiếp.

## 12. Chạy full

Cấu hình full cần MovieLens 25M cùng Hadoop HDFS. Trên máy có Docker Desktop (khuyến nghị 16 GB RAM cho Docker):

```bash
bash scripts/run_full_docker.sh
```

Script này dựng NameNode/DataNode Hadoop 3.3.6, tải `ml-25m` (Kaggle nếu có `kaggle.json`, không thì GroupLens), rồi chạy bước 01–08 trong container. NameNode UI: http://127.0.0.1:9870. Model ALS nằm trên `hdfs://namenode:9000/ml25m/gold/models/als`. Dữ liệu HDFS nằm trong đĩa của container; tạo lại NameNode sẽ format cụm mới.

Chạy tay trên máy đã có `hdfs` và Spark:

```bash
bash scripts/00_download_ml25m.sh
bash scripts/01_upload_raw.sh --profile full
bash scripts/02_run_bronze.sh --profile full
bash scripts/03_run_silver.sh --profile full
bash scripts/04_run_gold.sh --profile full
bash scripts/05_train_als.sh --profile full
bash scripts/06_generate_candidates.sh --profile full
bash scripts/07_train_reranker.sh --profile full
bash scripts/08_evaluate.sh --profile full
```

ALS full: `rank=64`, `regParam=0.1`, `maxIter=10`, `nonnegative=true`, `implicitPrefs=false`, `seed=42`.

## 13. Xem chỉ số và danh sách gợi ý

Sau khi bước đánh giá chạy xong, các tệp kết quả nằm tại:

```text
artifacts/metrics/metrics.json
artifacts/metrics/metrics.csv
artifacts/metrics/als_rmse.json
artifacts/recommendations/top10_recommendations.csv
artifacts/figures/metric_comparison.png
```

RMSE áp dụng cho cách gợi ý phim phổ biến và ALS khi dự đoán điểm chấm. Các chỉ số Precision, Recall, MAP, NDCG, HitRate và SatisfiedHitRate ở ngưỡng 10 phim dùng để đánh giá danh sách gợi ý. Coverage cho biết mức độ bao phủ danh mục phim. Mô hình kết hợp chỉ xếp hạng, không dự đoán số sao nên không có RMSE.

## 14. Lỗi thường gặp

- Thiếu `ml-25m.zip` hoặc một trong sáu tệp CSV: script 01 dừng và báo lỗi.
- Không có lệnh `hdfs` khi cấu hình dùng HDFS: chạy trên máy đã cài Hadoop hoặc chọn chế độ smoke cục bộ.
- Thiếu `spark-submit`: script thử chạy bằng Python có PySpark; nếu cũng không có PySpark thì dừng.
- Lỗi nhập `src.common`: chạy script từ thư mục dự án; các script đã đặt `PYTHONPATH`.
- Người dùng có dưới ba lượt chấm sau khi lọc sẽ không được chia thành train, validation và test. Có thể xem ngưỡng tại `min_split_interactions`.
- Windows không chạy `.sh` trong PowerShell: dùng Git Bash/WSL.

## 15. Tránh rò rỉ dữ liệu theo thời gian

Không chia ngẫu nhiên. Với mỗi `userId`:

1. Sắp xếp theo `timestamp`, sau đó theo `movieId`.
2. Dùng các lượt chấm cũ để huấn luyện, phần tiếp theo để điều chỉnh và phần mới nhất để kiểm tra.
3. Giữ ít nhất một bản ghi ở mỗi phần khi người dùng có từ ba lượt chấm trở lên.
4. Kiểm tra `max(train_ts) <= min(val_ts)` và `max(val_ts) <= min(test_ts)`. Cùng một giây vẫn hợp lệ vì MovieLens ghi nhiều rating trong một timestamp.
5. Không dùng nhãn của tập test để huấn luyện, chọn đặc trưng, dừng sớm hoặc chọn siêu tham số.
6. Thống kê độ phổ biến, đặc trưng người dùng/phim và bộ chọn nhãn Genome chỉ được học từ tập train.
7. Bộ xếp hạng lại dùng validation để học và điều chỉnh; test chỉ dành cho bước đánh giá cuối.

Tag Genome được chọn theo phương sai trên các phim thuộc tập train; dự án không dùng PCA.

## 16. Những kết quả đã được xác nhận

| Output | Trạng thái |
|---|---|
| Kiểm thử Python | 21 bài kiểm thử đã đạt ngày 29/09/2026; không cần Spark |
| Dashboard smoke | Chạy với dữ liệu mẫu và bộ xử lý Python/NumPy cục bộ |
| Bảng dữ liệu Spark | Chỉ có sau khi chạy các script tương ứng trong môi trường Spark |
| Mô hình Spark ALS và RMSE | Cần chạy script 05 với môi trường đầy đủ |
| Mô hình TensorFlow và lịch sử huấn luyện | Cần chạy script 07 với TensorFlow |
| Chỉ số MovieLens 25M | Chưa có khi thiếu dữ liệu và môi trường full |

## 17. Giới hạn và hướng phát triển

- Lượt chấm từ 4 sao chỉ là cách đo thay thế, không phải câu trả lời khảo sát hay tỷ lệ duy trì thuê bao.
- ALS hiện học từ điểm chấm trực tiếp; dự án chưa có dữ liệu thời lượng xem để học từ hành vi xem ngầm.
- Bộ xếp hạng lại dùng MLP trên bảng đặc trưng, chưa mô hình hóa chuỗi hành vi xem.
- MovieLens 25M cần đủ bộ nhớ và dung lượng lưu trữ để chạy HDFS/Spark.
- Có thể mở rộng bằng dữ liệu hành vi xem, đánh giá A/B, độ đa dạng gợi ý và cách xử lý phim hoặc người dùng mới.

Video demo: [videos/demo_script.md](videos/demo_script.md). Thuyết trình: [videos/presentation_script.md](videos/presentation_script.md).
