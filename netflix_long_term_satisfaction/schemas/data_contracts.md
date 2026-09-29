# Cấu trúc và quy tắc dữ liệu

Tài liệu này ghi các cột và điều kiện kiểm tra ở từng tầng dữ liệu. MovieLens chỉ có lịch sử chấm điểm, không có thời gian thuê bao, thông tin hủy thuê bao hay thời lượng xem. Các nhãn về người dùng dài hạn và phản hồi tích cực là quy ước để đánh giá ngoại tuyến.

## RAW

RAW giữ nguyên sáu tệp CSV đầu vào: `ratings.csv`, `movies.csv`, `tags.csv`, `links.csv`, `genome-scores.csv` và `genome-tags.csv`. Tệp manifest ghi tên, dung lượng, mã SHA-256, số dòng, tiêu đề cột và thời điểm kiểm tra.

| File | Header |
|---|---|
| ratings.csv | userId,movieId,rating,timestamp |
| movies.csv | movieId,title,genres |
| tags.csv | userId,movieId,tag,timestamp |
| links.csv | movieId,imdbId,tmdbId |
| genome-scores.csv | movieId,tagId,relevance |
| genome-tags.csv | tagId,tag |

## Bronze ratings

| Cột | Kiểu | Quy tắc |
|---|---|---|
| userId | int | Không null |
| movieId | int | Không null |
| rating | double | Trong khoảng 0.5 đến 5.0 |
| timestamp | long | Unix timestamp > 0 |
| event_ts | timestamp | Chuyển từ Unix timestamp |
| event_date | date | Dùng để phân vùng dữ liệu |

## Bronze movies

| Cột | Kiểu | Quy tắc |
|---|---|---|
| movieId | int | Không null |
| title | string | Không null |
| genres | array<string> | Tách từ `\|`; bản ghi thiếu thể loại được tách riêng |
| year | int | Lấy từ `(YYYY)` ở cuối tên phim |

Các bản ghi lỗi được đưa vào `quarantine/`, gồm giá trị trống, dòng trùng, điểm ngoài khoảng cho phép, thời điểm không hợp lệ hoặc thông tin phim/Tag Genome bị thiếu.

## Đặc trưng người dùng ở tầng SILVER

| Cột | Ý nghĩa |
|---|---|
| userId | Mã người dùng ẩn danh |
| rating_count | Tổng số lượt chấm |
| first_timestamp | Thời điểm chấm đầu tiên |
| last_timestamp | Thời điểm chấm cuối cùng |
| activity_span_days | Số ngày giữa lượt đầu và lượt cuối |
| mean_rating | Điểm chấm trung bình |

Tầng SILVER tạo các bảng: `ratings`, `movies`, `genome_scores`, `user_stats`, `long_term_users`, `user_train`, `user_validation` và `user_test`.

Trong cấu hình full, người dùng đủ điều kiện khi `activity_span_days >= 180` và `rating_count >= 20`. Người có ít hơn `min_split_interactions` lượt chấm (mặc định 3) không thể chia thành ba tập theo thời gian.

## Các bảng ở tầng GOLD

| Bảng | Nguồn thống kê | Ý nghĩa |
|---|---|---|
| train / validation / test | Lịch sử đã chia theo thời gian | Không chia ngẫu nhiên |
| movie_features | Tập train | Năm phát hành, thể loại, độ phổ biến và điểm trung bình |
| user_features | Tập train | Số lượt chấm, điểm trung bình và thời điểm gần nhất |
| popularity | Tập train | `movie_rating_count`, `movie_mean_rating` |
| als_candidates | ALS học từ train | `userId`, `movieId`, `rank`, `als_score`; loại phim đã chấm |
| reranker_features | Nhãn từ validation | Ứng viên, đặc trưng và nhãn để học xếp hạng lại |
| reranker_test_features | Nhãn từ test | Chỉ dùng ở bước đánh giá |
| reranked_recommendations | Đặc trưng tập test | Top-10 theo `rerank_score` |

## Đặc trưng cho bộ xếp hạng lại

Mỗi dòng là một cặp người dùng và phim ứng viên. Nhãn bằng 1 khi phim có lượt chấm từ 4 sao trở lên trong phần validation hoặc test tương ứng; các trường hợp còn lại mang nhãn 0. Tag Genome được chọn theo phương sai trên phim ở tập train. Tên cột Genome có dạng `genome_<tagId>`; cột thể loại có dạng `genre_<name>`.

Các đặc trưng gồm điểm ALS, Tag Genome, thể loại, năm phát hành, độ mới và độ phổ biến của phim, thống kê lượt chấm của người dùng cùng thông tin thời gian như `train_last_timestamp` và tuổi phim.
