import requests
from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup
import re
import hashlib
import time
from functools import wraps

class SimpleCache:
    def __init__(self, default_ttl=14400):  # 4 hours in seconds
        self.cache = {}
        self.default_ttl = default_ttl
    
    def _is_expired(self, entry):
        return time.time() > entry['expires_at']
    
    def get(self, key):
        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                return entry['value']
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value, ttl=None):
        expires_at = time.time() + (ttl or self.default_ttl)
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
    
    def clear_expired(self):
        expired_keys = [k for k, v in self.cache.items() if self._is_expired(v)]
        for key in expired_keys:
            del self.cache[key]

# Initialize cache with 4-hour default TTL
cache = SimpleCache(default_ttl=14400)

app = Flask(__name__)
# CORS is handled by Nginx, so we don't need flask_cors here

def process_loigiaihay(target_url, content):
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Determine if it's a detail page based on URL pattern
        is_detail = False
        if re.search(r'-[ae]\d+\.html$', target_url):
            is_detail = True

        if is_detail:
            # Parse as single post
            title_tag = soup.find('h1', class_='title') or soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            
            # Content usually in #box-content or .article-content
            # On loigiaihay, #box-content is the main container for the solution
            content_div = soup.find('div', {'id': 'box-content'}) or soup.find('div', class_='article-content')
            
            if content_div:
                # Remove unwanted script/style tags and ads
                for unwanted in content_div(['script', 'style', 'iframe', 'ins']):
                    unwanted.decompose()
                # Remove common ad classes/ids if they appear inside
                for ad in content_div.find_all(class_=re.compile(r'ads|related|social|comment|breadcrumb')):
                    ad.decompose()
                
                content_html = str(content_div)
            else:
                content_html = "Content not found"

            post_data = {
                "id": 0,
                "date": "2024-01-01T00:00:00",
                "slug": target_url.split('/')[-1].replace('.html', ''),
                "link": target_url,
                "title": {
                    "rendered": title
                },
                "content": {
                    "rendered": content_html,
                    "protected": False
                },
                "excerpt": {
                    "rendered": "",
                    "protected": False
                }
            }
            return post_data

        else:
            # Parse as list of posts (Category/Section page)
            articles = []
            
            # Target the main content container specifically
            # For loigiaihay lists, it's often .list-page or #content or .box-content
            main_content = soup.find('div', class_='list-page') or soup.find('div', {'id': 'content'}) or soup.find('div', {'id': 'box-content'}) or soup.find('body')
            
            if not main_content:
                return content

            # Find all links that look like individual lessons/chapters (a or e markers)
            # We want to EXCLUDE category links (c marker) from being treated as post items
            links = main_content.find_all('a', href=True)
            
            seen_links = set()
            
            for a in links:
                href = a['href']
                text = a.get_text(strip=True)
                
                # Normalize href
                if not href.startswith('http'):
                    full_url = f"https://loigiaihay.com{href}" if href.startswith('/') else f"https://loigiaihay.com/{href}"
                else:
                    full_url = href

                # Ignore external links or non-html links
                if 'loigiaihay.com' not in full_url or not full_url.endswith('.html'):
                    continue

                # STRICT FILTER: Only include links that are articles (a) or chapters (e)
                # Category links (c) are skipped as they are not "post items" to be rendered as posts
                match = re.search(r'-([ae])(\d+)\.html$', full_url)
                if not match:
                    continue

                if full_url in seen_links:
                    continue
                
                # Basic cleaning of the title (e.g. "1. Bài 1" -> "Bài 1")
                # Sometimes titles have numbers prefixing them
                clean_title = re.sub(r'^\d+\.\s*', '', text)
                
                # If title is too short, it might be just "Xem thêm" or similar
                if len(clean_title) < 5:
                    continue

                seen_links.add(full_url)
                
                p_type = match.group(1)
                p_id = int(match.group(2))

                articles.append({
                    "id": p_id,
                    "date": "2024-01-01T00:00:00",
                    "slug": full_url.split('/')[-1].replace('.html', ''),
                    "link": full_url,
                    "title": {
                        "rendered": clean_title
                    },
                    "content": {
                        "rendered": "",
                    },
                     "excerpt": {
                        "rendered": ""
                    }
                })

            return articles

    except Exception as e:
        print(f"Loigiaihay parsing error: {e}")
        return content # Fallback to raw HTML

@app.route('/url/<path:target_url>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(target_url):
    """
    Proxy request to the target_url.
    Usage: http://localhost:5000/url/https://capthathinh.com/wp-json/wp/v2/posts
    
    For image compression, use the 'quality' parameter (1-100):
    http://localhost:5000/url/https://example.com/image.jpg?quality=50
    """
    # Check if the URL scheme is missing (Flask path might strip one / from https://)
    # Often browser/clients might normalize /url/https:// to /url/https:/
    # But let's assume the user sends it correctly. 
    # If fetch fails, we can try to fix the URL.
    
    if target_url.startswith('https:/') and not target_url.startswith('https://'):
        target_url = target_url.replace('https:/', 'https://', 1)
    elif target_url.startswith('http:/') and not target_url.startswith('http://'):
        target_url = target_url.replace('http:/', 'http://', 1)
    
    # Create cache key based on URL and request method
    cache_key = hashlib.md5(f"{request.method}:{target_url}".encode()).hexdigest()
    
    # Try to get cached response
    cached_data = cache.get(cache_key)
    if cached_data:
        print(f"Cache hit for {target_url}")
        # Reconstruct the appropriate response from cached data
        if isinstance(cached_data, dict) and 'json' in cached_data:
            return jsonify(cached_data['json'])
        elif isinstance(cached_data, dict) and 'content' in cached_data:
            # Filter headers from cache as well, in case stale headers were stored
            excluded_headers = [
                'content-encoding', 'content-length', 'transfer-encoding', 'connection',
                'access-control-allow-origin', 'access-control-allow-methods', 'access-control-allow-headers',
                'server', 'date', 'x-powered-by'
            ]
            cached_headers = [(name, value) for (name, value) in cached_data.get('headers', [])
                               if name.lower() not in excluded_headers]
            return Response(cached_data['content'], cached_data['status_code'], cached_headers)
        else:
            return cached_data
    
    print(f"Cache miss for {target_url}, fetching fresh data")
    
    try:
        # Headers to exclude from forwarded request
        forward_excluded_headers = ['host', 'accept-encoding', 'content-length']
        
        print(f"Fetching: {target_url}", flush=True)
        # Forward the request
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for (key, value) in request.headers if key.lower() not in forward_excluded_headers},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=True,
            timeout=60 # Increased timeout for large files
        )

        content_len = len(resp.content)
        print(f"Fetched: {target_url} - Status: {resp.status_code} - Size: {content_len} bytes", flush=True)

        # Special handling for loigiaihay.com
        if 'loigiaihay.com' in target_url and resp.status_code == 200:
            # Only process HTML responses
            content_type = resp.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type:
               processed_content = process_loigiaihay(target_url, resp.content)
               # Cache the processed response as JSON data
               cache_data = {
                   'json': processed_content
               }
               cache.set(cache_key, cache_data)
               return jsonify(processed_content)

        # Create response
        # Exclude headers that should be handled by the proxy or Flask
        # We must exclude all hop-by-hop headers and those that might cause truncation/parsing issues
        excluded_headers = [
            'content-encoding', 'content-length', 'transfer-encoding', 'connection',
            'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'upgrade',
            'access-control-allow-origin', 'access-control-allow-methods', 'access-control-allow-headers',
            'server', 'date', 'x-powered-by'
        ]
        headers = [(name, value) for (name, value) in resp.headers.items()
                   if name.lower() not in excluded_headers]

        if 'image' in resp.headers.get('Content-Type', '').lower():
            try:
                from PIL import Image, ImageOps, ImageDraw, ImageFont
                import io

                img = Image.open(io.BytesIO(resp.content))
                
                # Determine image format
                format = img.format or "PNG"
                
                # 1. Add 4px white border
                img_with_border = ImageOps.expand(img, border=4, fill='white')

                # 2. Flip image horizontally (Left-Right)
                img_with_border = ImageOps.mirror(img_with_border)
                
                # 3. Round corners
                # Create a mask for rounded corners
                mask = Image.new("L", img_with_border.size, 0)
                draw = ImageDraw.Draw(mask)
                # Radius for rounded corners. The user asked for "bo tròn góc hình", not specific radius, 
                # but "rounded" usually implies a visible radius. Let's pick 10px or proportional.
                # Since we added 4px border, maybe a slightly larger radius looks good? Let's stick to a safe 20px.
                draw.rounded_rectangle([(0,0), img_with_border.size], radius=20, fill=255)
                
                # Apply mask (handling transparency if image has it, or just alpha channel)
                # If image is JPEG it might be RGB. We need RGBA for transparency.
                img_with_border = img_with_border.convert("RGBA")
                result_img = Image.new("RGBA", img_with_border.size)
                result_img.paste(img_with_border, (0, 0), mask)
                
                # 4. Add "2026" or custom watermark to top-right
                draw_result = ImageDraw.Draw(result_img)
                watermark_text = request.args.get('text', '2026')
                
                # Try to load a font
                try:
                    # MacOS common font path
                    font = ImageFont.truetype("Arial Unicode.ttf", 36)
                except IOError:
                    try: 
                        font = ImageFont.truetype("Arial Unicode.ttf", 36)
                    except IOError:
                        font = ImageFont.load_default()

                # Calculate position
                # textbbox is cleaner but available in newer Pillow. 
                # Fallback to textlen/textsize if needed, but Pillow 10+ deprecated textsize.
                # Let's assume a reasonably recent Pillow.
                try:
                    bbox = draw_result.textbbox((0, 0), watermark_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except AttributeError:
                    # Fallback for older Pillow
                    text_width, text_height = draw_result.textsize(watermark_text, font=font)

                padding = 10
                # Top right position
                x = result_img.width - text_width - padding - 4 # -4 for the border
                y = padding + 4 # +4 for the border offset
                
                # Draw text with some shadow/outline for visibility? 
                # User just said "adds watermark 2026". Let's do red or black/white visible text.
                # "góc phải trên" -> Top Right.
                # Let's use red color for visibility as it's common for distinct marks, or white with shadow.
                # Given the 2026 implies a date/year mark, maybe just a solid color.
                # Let's pick a visible color, e.g., Red or semitransparent white? 
                # "watermark" often implies semi-transparent. 
                # But without spec, let's just draw solid text. 
                # Let's use a standard visible color like Red or White with shadow. 
                # Let's go with Red for now as it stands out.
                draw_result.text((x, y), watermark_text, font=font, fill=(255, 0, 0, 255))

                # Get quality parameter from request, default to 85
                try:
                    quality = int(request.args.get('quality', 85))
                    # Ensure quality is within valid range (1-100)
                    quality = max(1, min(100, quality))
                except ValueError:
                    # If quality parameter is not a valid integer, use default
                    quality = 85
                
                # Save to buffer with compression
                output_buffer = io.BytesIO()
                if format.upper() == "JPEG":
                    # For JPEG, use quality parameter
                    result_img.save(output_buffer, format=format, quality=quality, optimize=True)
                else:
                    # For PNG and others, use optimize flag
                    result_img.save(output_buffer, format=format, optimize=True)
                processed_content = output_buffer.getvalue()

                # Update headers
                headers = [(name, value) for (name, value) in headers # Use already cleaned headers
                           if name.lower() != 'content-type']
                headers.append(('Content-Type', f'image/{format.lower()}'))
                # Flask will automatically calculate Content-Length for the Response object

                # Cache the processed image response data
                cache_data = {
                    'content': processed_content,
                    'status_code': resp.status_code,
                    'headers': headers
                }
                cache.set(cache_key, cache_data)
                return Response(processed_content, resp.status_code, headers)

            except Exception as e:
                # If processing fails, fallback to original
                print(f"Image processing failed: {e}")
                # Fall through to return original
                pass

        # Cache the response data
        cache_data = {
            'content': resp.content,
            'status_code': resp.status_code,
            'headers': headers
        }
        cache.set(cache_key, cache_data)
        return Response(resp.content, resp.status_code, headers)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Proxy server running on port 50010")
    print("Example: http://localhost:50010/url/https://capthathinh.com/wp-json/wp/v2/posts")
    app.run(host='0.0.0.0', port=50010, debug=False)
