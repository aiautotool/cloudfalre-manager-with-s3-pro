import requests
import json
import random
import re
import unicodedata
import os

class AIAgent:
    GEMINI_API_KEYS = [
        "AIzaSyBovMWTUGo5uvelS_U9slDmgSv-7o0DcQ4",
        "AIzaSyAjZp5L2GOCNM0zs8WJwG_Ijky4HxmRuyk",
        "AIzaSyAhPShLq1yuKIDRDpz1LyQzaQZFNB5cUAc",
        "AIzaSyAbdVxzi79-gZtoF-BmoZHVdrTFPj9HNjE",
        "AIzaSyAdL0fuN2kgyvViIKwtX2c0xB3iq56wScY"
    ]

    AUTHORS = [
        {"id": 1, "name": "Nguyên Minh Tuân", "job": "Chuyên gia công nghệ"},
        {"id": 2, "name": "Trân Quôc Huy", "job": "Nhà báo"},
        {"id": 3, "name": "Lê Hoàng Anh", "job": "Chuyên gia marketing"},
        {"id": 4, "name": "Phạm Ngọc Lan", "job": "Giảng viên"},
        {"id": 5, "name": "Võ Thanh Long", "job": "Kỹ sư hệ thông"},
        {"id": 6, "name": "Nguyên Đức Anh", "job": "Chuyên gia tài chính"},
        {"id": 7, "name": "Hoàng Tuân Kiệt", "job": "Nhiêp ảnh gia"},
        {"id": 8, "name": "Phan Minh Quân", "job": "Biên tâp viên"},
        {"id": 9, "name": "Bùi Thị Lan", "job": "Blogger"},
        {"id": 10, "name": "Đặng Thu Hà", "job": "Chuyên gia sức khỏe"},
        {"id": 11, "name": "Lý Quôc Khánh", "job": "Chuyên gia âm thanh"},
        {"id": 12, "name": "Trân Minh Phúc", "job": "Chuyên gia dữ liệu"},
        {"id": 13, "name": "Nguyên Thị Yên", "job": "Nhà nghiên cứu"},
        {"id": 14, "name": "Võ Quôc Nam", "job": "Chuyên gia logistics"},
        {"id": 15, "name": "Hoàng Gia Bảo", "job": "Doanh nhân"},
        {"id": 16, "name": "Trịnh Minh Khoa", "job": "Chuyên gia pháp lý"},
        {"id": 17, "name": "Lâm Thanh Tùng", "job": "Chuyên gia CNTT"},
        {"id": 18, "name": "Phạm Thúy An", "job": "Chuyên gia nhân sự"},
        {"id": 19, "name": "Nguyên Quôc Bảo", "job": "Nhà phân tích"},
        {"id": 20, "name": "Đỗ Thanh Bình", "job": "Cô vân chiên lược"},
        {"id": 21, "name": "Phan Hoàng Long", "job": "Chuyên gia AI"},
        {"id": 22, "name": "Nguyên Hữu Phúc", "job": "Kỹ sư phân mêm"},
        {"id": 23, "name": "Lê Thị Mai", "job": "Chuyên gia giáo dục"},
        {"id": 24, "name": "Trương Quôc Khánh", "job": "Chuyên gia thương mại"},
        {"id": 25, "name": "Nguyên Văn Hùng", "job": "Chuyên gia xây dựng"},
        {"id": 26, "name": "Hoàng Thị Ngọc", "job": "Chuyên gia thời trang"},
        {"id": 27, "name": "Phạm Quôc Dũng", "job": "Chuyên gia an ninh"},
        {"id": 28, "name": "Lý Minh Châu", "job": "Chuyên gia UX/UI"},
        {"id": 29, "name": "Trân Văn Phát", "job": "Chuyên gia đâu tư"},
        {"id": 30, "name": "Nguyên Thu Hương", "job": "Chuyên gia truyên thông"},
        {"id": 31, "name": "Đặng Quôc Việt", "job": "Chuyên gia blockchain"},
        {"id": 32, "name": "Phạm Thanh Tùng", "job": "Chuyên gia thương mại điên tử"},
        {"id": 33, "name": "Hoàng Đức Long", "job": "Chuyên gia SEO"},
        {"id": 34, "name": "Nguyên Bảo Trân", "job": "Chuyên gia nôi dung"},
        {"id": 35, "name": "Trịnh Văn An", "job": "Chuyên gia đào tạo"},
        {"id": 36, "name": "Lê Minh Đức", "job": "Chuyên gia sản xuât"},
        {"id": 37, "name": "Phan Thị Kim", "job": "Chuyên gia bán hàng"},
        {"id": 38, "name": "Nguyên Quang Vinh", "job": "Chuyên gia startup"},
        {"id": 39, "name": "Đỗ Mỹ Linh", "job": "Chuyên gia thương hiêu"},
        {"id": 40, "name": "Trân Thanh Hải", "job": "Chuyên gia vân hành"},
        {"id": 41, "name": "Nguyên Nhật Minh", "job": "Chuyên gia phân tích"},
        {"id": 42, "name": "Lê Quôc Thịnh", "job": "Chuyên gia xuât nhâp khâu"},
        {"id": 43, "name": "Phạm Anh Khoa", "job": "Chuyên gia đào tạo online"},
        {"id": 44, "name": "Võ Minh Tâm", "job": "Chuyên gia quản lý dự án"},
        {"id": 45, "name": "Nguyên Hồng Phúc", "job": "Chuyên gia tư vân"},
        {"id": 46, "name": "Lê Thanh Bình", "job": "Chuyên gia nghiên cứu thị trường"},
    ]

    @staticmethod
    def strip_blog_tags(text):
        start_tag = "[startblog]"
        end_tag = "[endblog]"
        
        start_index = text.find(start_tag)
        end_index = text.find(end_tag)
        
        if start_index != -1 and end_index != -1:
            content = text[start_index + len(start_tag):end_index]
            return content.strip()
        
        return text.replace(start_tag, "").replace(end_tag, "").strip()

    @staticmethod
    def slugify(text):
        if not text:
            return ""
        text = unicodedata.normalize('NFD', str(text))
        text = text.encode('ascii', 'ignore').decode('utf-8')
        text = text.lower()
        text = re.sub(r'\s+', '-', text)
        text = re.sub(r'[^\w\-]+', '', text)
        text = re.sub(r'\-\-+', '-', text)
        text = text.strip('-')
        return text

    @classmethod
    def select_author(cls, title):
        authors_text = "\n".join([f"{a['id']}: {a['name']} ({a['job']})" for a in cls.AUTHORS])
        prompt = (
            f"Dựa vào tiêu đề bài viết sau, hãy chọn ra ID của tác giả phù hợp nhất trong danh sách bên dưới.\n"
            f"Tiêu đề: {title}\n\n"
            f"Danh sách tác giả:\n{authors_text}\n\n"
            f"Chỉ trả về duy nhất con số ID của tác giả, không giải thích gì thêm."
        )
        
        res = cls.call_ai_agent(prompt, "Bạn là một biên tập viên chuyên nghiệp.")
        
        if res:
            match = re.search(r'\d+', res)
            if match:
                selected_id = int(match.group())
                if any(a['id'] == selected_id for a in cls.AUTHORS):
                    return selected_id
        return 1

    @classmethod
    def call_ai_agent(cls, prompt, system_prompt=None, temperature=0.7, max_tokens=8000):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # 1. Gemini
        api_key = random.choice(cls.GEMINI_API_KEYS)
        print(f"   [AI] Đang gọi Gemini (API Key kết thúc bằng ...{api_key[-4:]})...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        gemini_prompt = (system_prompt + "\n\n" + prompt) if system_prompt else prompt
        payload = {
            "contents": [{"role": "user", "parts": [{"text": gemini_prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}
        }
        try:
            response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
            res_json = response.json()
            if 'candidates' in res_json and res_json['candidates']:
                return cls.strip_blog_tags(res_json['candidates'][0]['content']['parts'][0]['text'])
        except: pass

        # 2. Custom Gemini
        print("   [AI] Đang gọi Custom Gemini (aiautotool.com)...")
        url = "https://gemini.aiautotool.com/v1/chat/completions"
        payload = {
            "model": "gemini-2.5-flash",
            "messages": messages,
            "stream": False, "temperature": temperature, "max_tokens": max_tokens
        }
        try:
            response = requests.post(url, headers={"Content-Type": "application/json", "Authorization": "Bearer sk-demo"}, json=payload, timeout=60)
            res_json = response.json()
            if 'choices' in res_json and len(res_json['choices']) > 0:
                return cls.strip_blog_tags(res_json['choices'][0]['message']['content'])
        except: pass

        # 3. Pollinations
        print("   [AI] Đang gọi Pollinations AI...")
        url = "https://text.pollinations.ai/openai"
        payload = {
            "model": "openai",
            "messages": messages,
            "temperature": 1.0, 
            "max_tokens": max_tokens, "stream": False
        }
        try:
            response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=90)
            res_json = response.json()
            if 'choices' in res_json and len(res_json['choices']) > 0:
                return cls.strip_blog_tags(res_json['choices'][0]['message']['content'])
        except: pass

        

        # 5. Xiaomi MiMo
        print("   [AI] Đang gọi Xiaomi MiMo (mimo-v2-flash)...")
        url = "https://api.xiaomimimo.com/v1/chat/completions"
        headers = {
            "Authorization": "Bearer sk-sifcsluc3thlsaqn8pevh2b0mdw1ca2hsvwsqofeowbnkmzk",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mimo-v2-flash",
            "messages": messages,
            "max_completion_tokens": 1024,
            "temperature": 0.3,
            "top_p": 0.95,
            "stream": False,
            "stop": None,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "thinking": {
                "type": "disabled"
            }
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            res_json = response.json()
            if 'choices' in res_json and len(res_json['choices']) > 0:
                return cls.strip_blog_tags(res_json['choices'][0]['message']['content'])
        except: pass
        # 4. LLM7
        print("   [AI] Đang gọi LLM7.io...")
        try:
            import openai
            client = openai.OpenAI(base_url="https://api.llm7.io/v1", api_key="unused")
            response = client.chat.completions.create(
                model="default",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return cls.strip_blog_tags(response.choices[0].message.content)
        except: pass

        return None
