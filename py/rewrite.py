import requests
import json
from datetime import datetime
import os
import time
import random
import re
import unicodedata

# Đường dẫn file lưu trữ các tiêu đề đã xử lý
LOG_FILE = os.path.join(os.path.dirname(__file__), "processed_titles.log")
# Đường dẫn file lưu trữ tiến trình hiện tại (trang)
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "progress.json")

from ai_agent import AIAgent

def load_processed_titles():
    """Tải danh sách các tiêu đề đã được xử lý từ file log."""
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_processed_title(title):
    """Lưu tiêu đề đã xử lý thành công vào file log."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(title + "\n")

def load_progress():
    """Tải tiến trình (số trang) từ file JSON."""
    if not os.path.exists(PROGRESS_FILE):
        return {"current_page": 1}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"   [!] Lỗi tải file tiến trình: {e}")
        return {"current_page": 1}

def save_progress(page, last_title=""):
    """Lưu tiến trình hiện tại vào file JSON."""
    data = {
        "current_page": page,
        "last_title": last_title,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"   [!] Lỗi lưu file tiến trình: {e}")

SYSTEM_PROMPT = (
    "CHỈ VIẾT BÀI MÀ KHÔNG NÓI GÌ THÊM. Tuyệt đối không chào hỏi, không dẫn dắt, không giải thích. "
    "Bạn là một chuyên gia sáng tạo nội dung cao cấp (Senior Editor & Rewriter). "
    "Nhiệm vụ của bạn là VIẾT LẠI (REWRITE) bài viết gốc thành một phiên bản mới tốt hơn, sâu sắc hơn, tuân thủ tiêu chí 'Helpful Content' nội dung không thay đổi ý nghĩa của bài viết gốc "
    "Mục tiêu: Nội dung mới phải Unique, văn phong tự nhiên, chuyên nghiệp, không bị phát hiện là AI.\n\n"
    "CẤU TRÚC BẮT BUỘC:\n"
    "- Bắt đầu bằng [startblog] và kết thúc bằng [endblog].\n"
    "- Tiêu đề (H1): Giữ nguyên tiêu đề gốc hoặc tinh chỉnh nhẹ cho hấp dẫn hơn nhưng vẫn sát nghĩa.\n"
    "- Mở đầu: Viết lại phần dẫn dắt một cách cuốn hút.\n"
    "- Thân bài: Tái cấu trúc lại các ý của bài gốc. Có thể bổ sung thêm ví dụ, phân tích sâu hơn nếu cần. Sử dụng H2, H3 hợp lý.\n"
    "- Kết bài: Tóm tắt và kêu gọi hành động (CTA) tự nhiên.\n\n"
    "HÌNH ẢNH MINH HỌA:\n"
    "Bài viết gốc có chứa các hình ảnh minh họa được đánh dấu bằng [IMG_1], [IMG_2], [IMG_3]...\n"
    "Bạn BẮT BUỘC phải giữ lại toàn bộ các thẻ này và chèn chúng vào các vị trí phù hợp trong bài viết mới để minh họa cho nội dung.\n"
    "Tuyệt đối không được bỏ sót hình ảnh nào.\n\n"
    "QUY TẮC REWRITE:\n"
    "1. **Không sao chép y nguyên**: Phải diễn đạt lại bằng ngôn từ mới.\n"
    "2. **Giữ nguyên thông tin cốt lõi**: Không bịa đặt thông tin sai lệch so với bài gốc.\n"
    "3. **Văn phong**: Tiếng Việt chuẩn, mượt mà, dễ đọc.\n"
    "4. **Format**: Sử dụng Markdown (Bold, Intalic, List, Table) để trình bày đẹp mắt.\n\n"
    "Output bắt buộc sử dụng markdown. Tuyệt đối không ghi rõ các mục như 'Mở bài', 'Thân bài', 'Kết bài' mà hãy viết liền mạch như một bài báo."
    "Quan trọng: Loại bỏ toàn bộ các thông tin liên hệ, nhận diện thương hiệu, số điện thoại, địa chỉ, tên công ty, tên blog, tên website có trong bài viết."
   
)

def select_author(title):
    # Thử gọi AI với fallback
    return AIAgent.select_author(title)

def strip_blog_tags(text):
    return AIAgent.strip_blog_tags(text)

def call_ai_agent(prompt, system_prompt=None, temperature=0.7, max_tokens=8000):
    return AIAgent.call_ai_agent(prompt, system_prompt, temperature, max_tokens)

def slugify(text):
    return AIAgent.slugify(text)

def strip_html_tags(text):
    """Xóa thẻ HTML đơn giản khỏi nội dung source để AI dễ đọc hơn."""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def extract_images_to_placeholders(html_content):
    """
    Tìm các thẻ img trong HTML, thay thế bằng placeholder [IMG_n] và trả về dict map.
    """
    images = {}
    counter = 1
    
    def replace_match(match):
        nonlocal counter
        img_tag = match.group(0)
        # Tạo placeholder có khoảng trắng để AI dễ nhận diện
        placeholder = f" [IMG_{counter}] " 
        key = f"[IMG_{counter}]"
        images[key] = img_tag
        counter += 1
        return placeholder

    # Regex bắt thẻ img (cơ bản)
    processed_html = re.sub(r'<img[^>]*?/?>', replace_match, html_content, flags=re.IGNORECASE | re.DOTALL)
    return processed_html, images

def restore_images_from_placeholders(content, images_dict):
    """
    Thay thế các placeholder [IMG_n] trong content bằng thẻ img dạng markdown ![alt](url "title").
    """
    year_pattern = r'\b20(1[0-9]|2[0-5])\b' 

    for key, img_tag in images_dict.items():
        # Lấy src, alt và title từ thẻ img gốc (linh hoạt hơn với dấu ngoặc và khoảng trắng)
        src_match = re.search(r'src\s*=\s*(?:["\']([^"\']*)["\']|([^\s>]+))', img_tag, re.IGNORECASE)
        alt_match = re.search(r'alt\s*=\s*(?:["\']([^"\']*)["\']|([^\s>]+))', img_tag, re.IGNORECASE)
        title_match = re.search(r'title\s*=\s*(?:["\']([^"\']*)["\']|([^\s>]+))', img_tag, re.IGNORECASE)
        
        src = (src_match.group(1) or src_match.group(2) or "") if src_match else ""
        alt = (alt_match.group(1) or alt_match.group(2) or "") if alt_match else ""
        title = (title_match.group(1) or title_match.group(2) or "") if title_match else ""
        
        # Cập nhật năm trong alt và title
        if alt:
            alt = re.sub(year_pattern, "2026", alt)
        if title:
            title = re.sub(year_pattern, "2026", title)
        
        # Format markdown: ![alt](src "title")
        if title:
            markdown_img = f"![{alt}]({src} \"{title}\")"
        else:
            markdown_img = f"![{alt}]({src})"

        # Thay thế placeholder (hỗ trợ cả trường hợp bị kèm markdown khác như bold)
        # Sử dụng escape cho key vì key có thể chứa [ và ]
        escaped_key = re.escape(key)
        # Regex tìm placeholder, có thể bao quanh bởi dấu sao hoặc gạch dưới
        pattern = rf'[\*_]*{escaped_key}[\*_]*'
        content = re.sub(pattern, f"\n\n{markdown_img}\n\n", content)
        
    return content

def aiautotool_pingbackstatus(title, content, author_id=1):
    publish = 1
    today = datetime.now()
    year = today.year 
    month = today.month
    day = today.day
    
    form_url = "https://docs.google.com/forms/d/1QGOhe7-LRXLUMpxcjqrhlt5jN56dx0PPcV7D7y08JIM/formResponse"
    form_url = "https://docs.google.com/forms/u/1/d/e/1FAIpQLSf3QvNGVHgI6GjVEt9xNEzS6kix-vc_kkVDhHAhEdWBWUbf0A/formResponse"
   
    # Dữ liệu gửi
    content = content.replace("[endblog]", "").replace("[Endblog]", "")
    slug = slugify(title)
    authorid = ''
    form_data = {
        "entry.1171459721": authorid,
        "entry.1177795647": title,
        "entry.327767971": slug,
        "entry.634618594": content,
        "entry.1496062259": str(publish),
        "entry.266364423_year": str(year),
        "entry.266364423_month": str(month),
        "entry.266364423_day": str(day),
        "entry.1171459721": str(author_id)
    }
    
    try:
        response = requests.post(form_url, data=form_data, timeout=10)
        print(f"   [PINGBACK] Status Code: {response.status_code}")
        return response.status_code
    except Exception as e:
        print(f"   [PINGBACK] Lỗi gửi form: {e}")
        return None

# --- AI FUNCTIONS (REWRITE MODE) ---

def rewrite_content_with_fallback(title, source_content, max_retries=3):
    for attempt in range(1, max_retries + 1):
        print(f"\n--- Đang viết lại nội dung cho: {title} (Lần thử {attempt}/{max_retries}) ---")
        
        user_prompt = f"Tiêu đề: {title}\n\nNội dung gốc tham khảo:\n{source_content}\n\nYêu cầu: Hãy viết lại bài viết trên dựa theo tiêu đề và nội dung gốc, tuân thủ System Prompt."
        
        content = call_ai_agent(user_prompt, SYSTEM_PROMPT)
        if content:
            print(f"=> Thành công với AI Agent ở lần thử {attempt}!")
            return content

        print(f"   [!] Lần thử {attempt} thất bại.")
        if attempt < max_retries:
            wait_time = attempt * 5
            print(f"   => Đang đợi {wait_time} giây trước khi thử lại...")
            time.sleep(wait_time)

    print(f"   [!] Tất cả {max_retries} lần thử đều thất bại.")
    return None

# --- WORDPRESS CRAWLER ---

def fetch_wp_posts(page=1, per_page=10):
    url = f"https://healthmart.vn/wp-json/wp/v2/posts?page={page}&per_page={per_page}"
    print(f"\n>>> Đang tải danh sách bài viết trang {page} từ {url} ...")
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            posts = response.json()
            print(f"   => Tìm thấy {len(posts)} bài viết.")
            return posts
        elif response.status_code == 400:
            print("   => Đã hết bài viết (Page out of bounds).")
            return []
        else:
            print(f"   => Lỗi tải trang: {response.status_code}")
            return []
    except Exception as e:
        print(f"   => Lỗi kết nối crawl: {e}")
        return []

# ================== CHƯƠNG TRÌNH CHÍNH ==================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("BẮT ĐẦU CRAWL VÀ REWRITE TỪ BLOGTOC.COM (GIỮ LẠI HÌNH ẢNH)")
    print("="*50)

    # Tải tiến trình đã lưu
    progress = load_progress()
    current_page = progress.get("current_page", 1)
    last_title = progress.get("last_title", "")
    
    print(f"[*] Tiếp tục từ trang: {current_page}")
    if last_title:
        print(f"[*] Bài viết cuối cùng được xử lý: {last_title}")
    
    while True:
        posts = fetch_wp_posts(page=current_page)
        
        if not posts:
            print("\n>>> Đã hoàn thành hoặc không lấy được thêm bài viết. Kết thúc chương trình.")
            break
            
        processed_titles = load_processed_titles()
        
        count_processed_in_page = 0
        
        for post in posts:
            title = post.get("title", {}).get("rendered", "")
            content_html = post.get("content", {}).get("rendered", "")
            
            import html
            title = html.unescape(title)
            
            if not title: continue
            if title in processed_titles:
                count_processed_in_page += 1
                continue
            
            # (Năm cũ sẽ được thay thế sau khi tách hình ảnh ở Bước 1.5)

            print(f"\n--- Đang xử lý: {title} ---")
            
            # --- BƯỚC 1: Tách hình ảnh và thay bằng placeholder ---
            content_with_placeholders, img_map = extract_images_to_placeholders(content_html)
            
            # --- BƯỚC 1.5: Thay thế các năm cũ thành 2026 (sau khi đã tách hình ảnh) ---
            year_pattern = r'\b20(1[0-9]|2[0-5])\b' 
            title = re.sub(year_pattern, "2026", title)
            content_with_placeholders = re.sub(year_pattern, "2026", content_with_placeholders)

            if img_map:
                print(f"   => Tìm thấy {len(img_map)} hình ảnh trong bài viết gốc.")
            else:
                print("   => Không tìm thấy hình ảnh nào.")
                
            # --- BƯỚC 2: Làm sạch code HTML thừa (chỉ giữ lại placeholder và text) ---
            clean_source_content = strip_html_tags(content_with_placeholders)
            
            if len(clean_source_content) > 20000:
                 clean_source_content = clean_source_content[:20000] + "...(đã cắt bớt)..."

            # --- BƯỚC 3: Rewrite nội dung ---
            new_content = rewrite_content_with_fallback(title, clean_source_content)
            
            if new_content:
                print(f"   => Rewrite thành công ({len(new_content)} ký tự)")
                
                # --- BƯỚC 4: Khôi phục hình ảnh từ placeholder ---
                if img_map:
                    print("   => Đang khôi phục hình ảnh gốc vào bài viết mới...")
                    new_content = restore_images_from_placeholders(new_content, img_map)
                
                # Xác định tác giả
                author_id = select_author(title)
                author_name = next((a['name'] for a in AIAgent.AUTHORS if a['id'] == author_id), "N/A")
                print(f"   => Đã chọn tác giả ID: {author_id} ({author_name})")

                # --- BƯỚC 5: Gửi form ---
                print("   => Đang gửi pingback...")
                status = aiautotool_pingbackstatus(title, new_content, author_id)
                
                if status == 200:
                    save_processed_title(title)
                    processed_titles.add(title) 
                else:
                    print(f"   [!] Gửi form thất bại (Status: {status})")
            else:
                print("   [!] Rewrite thất bại. Bỏ qua bài này.")
            
            time.sleep(random.randint(2, 5))
        
        current_page += 1
        save_progress(current_page)
        print(f"\n>>> Hoàn thành trang {current_page - 1}. Nghỉ 5 giây trước khi sang trang {current_page}...")
        time.sleep(5)