# Cloud Management Pro - Seohtmls3

**Cloud Management Pro** là công cụ quản lý toàn diện dành cho Webmaster và SEOer, tích hợp quản lý Cloudflare DNS, AWS S3, Google Search Console và Google Sheets vào một giao diện duy nhất. Ứng dụng được thiết kế để tự động hóa các tác vụ lặp đi lặp lại và đơn giản hóa quy trình triển khai website vệ tinh.

## 🚀 Tính Năng Nổi Bật

### 1. Cloudflare DNS Manager
*   **Quản lý DNS**: Thêm, sửa, xóa các bản ghi DNS (A, CNAME, TXT, v.v.) một cách dễ dàng.
*   **Quản lý Đa Domain**: Chuyển đổi nhanh giữa các domain và tài khoản Cloudflare khác nhau.
*   **Công cụ tiện ích**:
    *   Export danh sách DNS sang định dạng script cho MikroTik.
    *   Bật/tắt Proxy (đám mây vàng) chỉ với 1 click.
    *   Trỏ nhanh tên miền về IP hoặc Hostname bất kỳ.

### 2. AWS S3 Buckets Manager
*   **Quản lý Bucket**: Tạo, xóa, tìm kiếm S3 Buckets.
*   **Website Hosting**: Tự động cấu hình S3 Bucket thành Static Website Hosting (tự động set index.html, error.html).
*   **Upload thông minh**: Upload file lẻ hoặc cả thư mục lên Bucket.
*   **S3 & Cloudflare Integration**:
    *   Tính năng **"⚡ Add DNS"**: Tự động tạo bản ghi CNAME trên Cloudflare trỏ về S3 Bucket đang chọn chỉ với 1 click.
*   **Quản lý nâng cao**: Xem và chỉnh sửa Policy, CORS, Public Access Block.

### 3. Google Search Console (GSC) Automation
*   **Xác minh Website (Verification)**:
    *   Hỗ trợ xác minh tự động bằng phương pháp upload file HTML lên S3 Bucket.
    *   Tự động submit verification token lên Google.
*   **Quản lý Profile**: Hỗ trợ nhiều tài khoản Google khác nhau.
*   **Thống kê (Statistics)**: Xem nhanh lượt click, impressions, CTR của các site vệ tinh.

### 4. Google Sheet & Tiện ích khác
*   **Google Sheets**: Tích hợp để quản lý danh sách site, keyword hoặc data dự án (cần file `credentials.json`).
*   **System Tools**: Script dọn dẹp "System Data" trên Mac (nằm trong `clean_mac_system_data.sh`).

---

## 🛠 Hướng Dẫn Cài Đặt (Build)

Bạn có thể chạy trực tiếp từ source code (Python) hoặc build thành ứng dụng độc lập (.app/.dmg) trên macOS.

### Yêu cầu hệ thống
*   **OS**: macOS (đã test trên macOS Sonoma/Ventura).
*   **Python**: Phiên bản 3.10 trở lên.
*   **Git**: Để tải source code.

### Cách 1: Chạy từ Source Code (Dành cho Dev)

1.  **Clone repository**:
    ```bash
    git clone https://github.com/aiautotool/cloudfalre-manager-with-s3-pro.git
    cd cloudfalre-manager-with-s3-pro
    ```

2.  **Cài đặt môi trường ảo (Khuyên dùng)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Cài đặt thư viện dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Chạy ứng dụng**:
    ```bash
    python main.py
    ```

### Cách 2: Build thành file cài đặt .dmg (Khuyên dùng cho End User)

Chúng tôi đã chuẩn bị sẵn script `rebuild.sh` để tự động hóa quá trình đóng gói ứng dụng bằng **PyInstaller**.

1.  **Mở Terminal** tại thư mục dự án.

2.  **Cấp quyền chạy cho script**:
    ```bash
    chmod +x rebuild.sh
    ```

3.  **Chạy lệnh build**:
    ```bash
    ./rebuild.sh
    ```

4.  **Kết quả**:
    Sau khi chạy xong (khoảng 1-2 phút), bạn sẽ thấy file cài đặt `Seohtmls3.dmg` xuất hiện trong thư mục gốc. Bạn có thể mở file này và kéo ứng dụng vào Applications để sử dụng như app thông thường.

---

## 📖 Hướng Dẫn Sử Dụng Cơ Bản

### 1. Cấu hình ban đầu
Khi mở ứng dụng lần đầu, bạn cần nhập các thông tin xác thực (Credentials). Các thông tin này sẽ được lưu trữ cục bộ an toàn.

*   **Tab Cloudflare**: Nhập **API Token** (cần quyền Edit Zone DNS).
*   **Tab AWS S3**: Nhập **Access Key ID** và **Secret Access Key**. Nếu có nhiều profile AWS, bạn có thể lưu thành các Profile khác nhau.
*   **Google Services**: Để dùng tính năng GSC/Sheet, bạn cần file `credentials.json` (OAuth 2.0 Client ID) từ Google Cloud Console và đặt vào thư mục gốc hoặc load trong ứng dụng.

### 2. Quy trình Deploy 1 Site vệ tinh S3 + Cloudflare
1.  **Vào Tab AWS S3**:
    *   Bấm **"New Bucket"**, nhập tên (trùng với tên miền, ví dụ `www.example.com`).
    *   Chọn Bucket vừa tạo, bấm **"Apply Web & Policy"** để bật Hosting và mở quyền truy cập công khai.
    *   Upload file `index.html` lên bucket.
2.  **Liên kết Cloudflare**:
    *   Vẫn tại Tab S3, tích chọn **"Link Cloudflare DNS"**.
    *   Chọn tên miền gốc `example.com` từ dropdown Cloudflare (nếu đã load).
    *   Bấm nút cam **"⚡ Add DNS"**. Tool sẽ tự động tạo bản ghi CNAME `www` trỏ về endpoint của S3.
3.  **Xác minh GSC (Tab GSC)**:
    *   Chuyển sang Tab GSC, chọn bucket và bấm Verify. Tool sẽ lấy file HTML từ Google, upload lên S3 và xác nhận.

---

## 📂 Cấu Trúc Dự Án

*   `main.py`: Entry point của ứng dụng (Giao diện chính).
*   `s3_api.py`, `cloudflare_api.py`: Các module xử lý logic gọi API.
*   `google_search_console.py`, `google_sheet_manager.py`: Module xử lý dịch vụ Google.
*   `rebuild.sh`: Script build app cho macOS.
*   `Seohtmls3.spec`: Cấu hình đóng gói PyInstaller.
*   `UI_MOCKUP.md`: Tài liệu tham khảo thiết kế UI.
*   `clean_mac_system_data.sh`: Script phụ trợ dọn dẹp máy Mac.

## ⚠️ Lưu ý
*   Ứng dụng được thiết kế tối ưu cho macOS. Trên Windows có thể cần điều chỉnh file `rebuild.sh` và đường dẫn file.
*   Luôn bảo mật file `credentials.json` và các API Key của bạn.

---
**Phát triển bởi AiAutoTool Team**
https://github.com/aiautotool/cloudfalre-manager-with-s3-pro
