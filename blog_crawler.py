#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 크롤러 - 하수구수사대 홈페이지 블로그 자동 생성기
사용법: python blog_crawler.py [블로그 포스트 번호 또는 URL]
예시: python blog_crawler.py 223789808499
      python blog_crawler.py https://m.blog.naver.com/hasugu2118/223789808499
"""

import os
import sys
import io
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from datetime import datetime

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BLOG_ID = "hasugu80"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = os.path.join(BASE_DIR, "blog")
IMAGES_BASE_DIR = os.path.join(BLOG_DIR, "images")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://m.blog.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def extract_log_no(input_str):
    """URL 또는 입력 문자열에서 블로그 포스트 번호(logNo) 추출"""
    input_str = input_str.strip()
    
    # 1. URL 형태인 경우 처리
    if "blog.naver.com" in input_str:
        # 쿼리 파라미터 logNo=... 검색
        query_match = re.search(r'[?&]logNo=(\d+)', input_str)
        if query_match:
            return query_match.group(1)
        
        # 경로 상의 포스트 번호 검색 (예: m.blog.naver.com/hasugu2118/223789808499)
        path_match = re.search(r'blog\.naver\.com/[a-zA-Z0-9_-]+/(\d+)', input_str)
        if path_match:
            return path_match.group(1)
            
    # 2. 순수 숫자만 추출
    digits = re.findall(r'\d+', input_str)
    if digits:
        return digits[-1] # 마지막 숫자 시퀀스 리턴
        
    return input_str


def fetch_html(url):
    """URL에서 HTML 가져오기"""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            charset = "utf-8"
            content_type = resp.headers.get("Content-Type", "")
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].strip()
            return resp.read().decode(charset, errors="replace")
    except urllib.error.URLError as e:
        print(f"[오류] URL 접속 실패: {e}")
        sys.exit(1)


def download_image(img_url, save_path):
    """이미지 다운로드 - ?type=w800 파라미터 유지 (네이버 pstatic 서버 필수)"""
    # ?type=w800 을 붙여서 실제 이미지 크기로 다운로드
    base_url = img_url.split("?")[0]
    download_url = base_url + "?type=w800"
    req = urllib.request.Request(download_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            with open(save_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        # w800이 실패하면 원본 URL 그대로 시도
        try:
            req2 = urllib.request.Request(base_url, headers=HEADERS)
            with urllib.request.urlopen(req2, timeout=15) as resp:
                with open(save_path, "wb") as f:
                    f.write(resp.read())
            return True
        except Exception as e2:
            print(f"  [경고] 이미지 다운로드 실패 ({base_url}): {e2}")
            return False


def _extract_tag_block(html, start_tag):
    """중첩 div를 정확히 추적해 start_tag로 시작하는 블록 전체 추출"""
    idx = html.find(start_tag)
    if idx == -1:
        return ""
    depth = 0
    pos = idx
    length = len(html)
    while pos < length:
        open_pos = html.find('<div', pos)
        close_pos = html.find('</div>', pos)
        if open_pos == -1 and close_pos == -1:
            break
        if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
            depth += 1
            pos = open_pos + 4
        else:
            depth -= 1
            pos = close_pos + 6
            if depth == 0:
                return html[idx:pos]
    return html[idx:]  # fallback


def parse_blog(html, log_no):
    """블로그 HTML 파싱하여 필요한 정보 추출"""
    
    # 제목 추출
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html)
    title = title_match.group(1).replace(" : 네이버 블로그", "").strip() if title_match else "블로그 포스트"
    
    # OG 제목 (더 깔끔한 제목)
    og_title_match = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if og_title_match:
        title = og_title_match.group(1).strip()

    # OG 설명
    og_desc_match = re.search(r'property="og:description"\s+content="([^"]+)"', html)
    description = og_desc_match.group(1).strip() if og_desc_match else ""

    # 작성일 추출
    date_match = re.search(r'<p class="blog_date">\s*([^<]+)\s*</p>', html)
    post_date = date_match.group(1).strip() if date_match else ""

    # 카테고리 추출
    cat_match = re.search(r'class="blog_category"[^>]*><a[^>]*>([^<]+)</a>', html)
    category = cat_match.group(1).strip() if cat_match else ""

    # 썸네일/커버 이미지 (OG 이미지 우선)
    cover_image = ""
    og_img_match = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if og_img_match:
        cover_image = og_img_match.group(1).split("?")[0]
    else:
        cover_match = re.search(r'background-image:url\(\'(https://mblogthumb[^\']+)\'\)', html)
        if cover_match:
            cover_image = cover_match.group(1).split("?")[0]

    # ── 본문 콘텐츠 추출: 중첩 div 태그 카운팅 방식 ──
    content_html = _extract_tag_block(html, '<div class="se-main-container">')
    if not content_html:
        content_html = _extract_tag_block(html, '<div class="se-viewer ')
    if not content_html:
        content_html = _extract_tag_block(html, '<div class="_postView">')

    # ── 이미지 URL 추출 ──
    image_urls = []
    seen = set()

    lazy_imgs = re.findall(r'data-lazy-src="(https://mblogthumb[^"]+)"', html)
    for url in lazy_imgs:
        base = url.split("?")[0]
        if base not in seen:
            seen.add(base)
            image_urls.append(base)

    # data-linkdata src 에서도 보완 수집
    link_data_imgs = re.findall(r'"src"\s*:\s*"(https://mblogthumb[^"]+)"', html)
    for url in link_data_imgs:
        base = url.split("?")[0]
        if base not in seen:
            seen.add(base)
            image_urls.append(base)

    # 커버 이미지도 포함
    if cover_image:
        base = cover_image.split("?")[0]
        if base not in seen and ('mblogthumb' in base or 'blogthumb' in base):
            image_urls.insert(0, base)

    return {
        "title": title,
        "description": description,
        "date": post_date,
        "category": category,
        "cover_image": cover_image,
        "images": image_urls,
        "content_html": content_html,
        "log_no": log_no,
    }


def clean_content_for_website(content_html, log_no, img_map):
    """본문 HTML을 회사 홈페이지용으로 정제"""
    
    # data-lazy-src를 실제 src로 교체, 로컬 이미지 경로 사용
    def replace_img(m):
        full_tag = m.group(0)
        # data-lazy-src 추출
        lazy_match = re.search(r'data-lazy-src="([^"]+)"', full_tag)
        if lazy_match:
            orig_url = lazy_match.group(1).split("?")[0]
            local = img_map.get(orig_url, "")
            if local:
                return f'<img src="{local}" alt="" class="blog-image" loading="lazy">'
        # fallback: src 교체
        src_match = re.search(r'src="(https://mblogthumb[^"?]+)', full_tag)
        if src_match:
            orig_url = src_match.group(1)
            local = img_map.get(orig_url, "")
            if local:
                return f'<img src="{local}" alt="" class="blog-image" loading="lazy">'
        return full_tag

    cleaned = re.sub(r'<img[^>]+>', replace_img, content_html)

    # <a> 링크 제거
    cleaned = re.sub(r'<a\s[^>]*class="[^"]*se-module-image-link[^"]*"[^>]*>(.*?)</a>', r'\1', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<a\s[^>]*href="[^"]*PostList[^"]*"[^>]*>(.*?)</a>', r'\1', cleaned, flags=re.DOTALL)

    # script 태그 제거
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', cleaned, flags=re.DOTALL)

    # 불필요한 속성 제거
    cleaned = re.sub(r'\s*onclick="[^"]*"', '', cleaned)
    cleaned = re.sub(r'\s*data-linkdata=\'[^\']*\'', '', cleaned)
    cleaned = re.sub(r'\s*data-linktype="[^"]*"', '', cleaned)
    cleaned = re.sub(r'\s*data-lazy-src="[^"]*"', '', cleaned)
    cleaned = re.sub(r'\s*data-width="[^"]*"', '', cleaned)
    cleaned = re.sub(r'\s*data-height="[^"]*"', '', cleaned)

    return cleaned


def generate_html(data, log_no, img_map, cover_image_local):
    """회사 홈페이지 스타일의 HTML 생성"""
    
    title = data["title"]
    description = data["description"]
    post_date = data["date"]
    category = data["category"]
    content_html = clean_content_for_website(data["content_html"], log_no, img_map)

    cover_local = cover_image_local

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    {"" if not cover_local else f'<meta property="og:image" content="{cover_local}">'}
    <title>{title} - 하수구수사대</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        :root {{
            --primary: #1a73e8;
            --primary-dark: #0d47a1;
            --accent: #ff5722;
            --text-dark: #1a1a2e;
            --text-mid: #444466;
            --text-light: #888899;
            --bg: #f8f9fc;
            --card-bg: #ffffff;
            --border: #e8eaf0;
            --shadow-sm: 0 2px 8px rgba(0,0,0,.06);
            --shadow-md: 0 8px 32px rgba(0,0,0,.10);
            --shadow-lg: 0 20px 60px rgba(0,0,0,.14);
            --radius: 16px;
            --radius-sm: 8px;
        }}

        body {{
            font-family: 'Noto Sans KR', sans-serif;
            background: var(--bg);
            color: var(--text-dark);
            line-height: 1.8;
            -webkit-font-smoothing: antialiased;
        }}

        /* ── 헤더 ── */
        .site-header {{
            background: linear-gradient(135deg, #0d47a1 0%, #1565c0 50%, #1976d2 100%);
            padding: 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 20px rgba(13,71,161,.35);
        }}
        .header-inner {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 64px;
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            color: #fff;
        }}
        .logo-icon {{
            width: 36px;
            height: 36px;
            background: rgba(255,255,255,.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }}
        .logo-text {{
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -0.3px;
        }}
        .header-nav a {{
            color: rgba(255,255,255,.85);
            text-decoration: none;
            font-size: .9rem;
            font-weight: 500;
            padding: 6px 14px;
            border-radius: var(--radius-sm);
            transition: background .2s, color .2s;
        }}
        .header-nav a:hover {{
            background: rgba(255,255,255,.15);
            color: #fff;
        }}

        /* ── 히어로 (커버 이미지) ── */
        .post-hero {{
            position: relative;
            width: 100%;
            height: 460px;
            overflow: hidden;
            background: linear-gradient(135deg, #1a237e, #283593);
        }}
        .post-hero img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: .72;
        }}
        .post-hero::after {{
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(
                to bottom,
                rgba(0,0,0,0) 30%,
                rgba(10,20,60,.75) 100%
            );
        }}
        .hero-content {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 2;
            padding: 40px 32px 36px;
            max-width: 900px;
            margin: 0 auto;
        }}
        .hero-badge {{
            display: inline-block;
            background: var(--accent);
            color: #fff;
            font-size: .75rem;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 20px;
            letter-spacing: .05em;
            text-transform: uppercase;
            margin-bottom: 12px;
        }}
        .hero-title {{
            font-size: clamp(1.5rem, 3.5vw, 2.4rem);
            font-weight: 700;
            color: #fff;
            line-height: 1.3;
            text-shadow: 0 2px 12px rgba(0,0,0,.4);
            margin-bottom: 14px;
        }}
        .hero-meta {{
            display: flex;
            align-items: center;
            gap: 20px;
            color: rgba(255,255,255,.8);
            font-size: .85rem;
        }}
        .hero-meta span {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        /* ── 본문 레이아웃 ── */
        .post-layout {{
            max-width: 900px;
            margin: 0 auto;
            padding: 48px 24px 80px;
        }}

        /* ── 본문 카드 ── */
        .post-card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow-md);
            padding: 48px;
            margin-bottom: 32px;
        }}

        /* ── 블로그 본문 스타일 ── */
        .blog-body {{
            font-size: 1.05rem;
            color: var(--text-mid);
            line-height: 1.9;
        }}
        .blog-body .blog-image {{
            width: 100%;
            height: auto;
            border-radius: var(--radius-sm);
            margin: 24px 0;
            box-shadow: var(--shadow-sm);
            display: block;
            transition: transform .3s ease, box-shadow .3s ease;
        }}
        .blog-body .blog-image:hover {{
            transform: scale(1.01);
            box-shadow: var(--shadow-md);
        }}
        .blog-body p {{
            margin-bottom: 1em;
        }}
        .blog-body b, .blog-body strong {{
            color: var(--text-dark);
            font-weight: 600;
        }}
        .blog-body blockquote,
        .blog-body .se-quotation-container {{
            border-left: 4px solid var(--primary);
            background: #f0f4ff;
            padding: 16px 20px;
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
            margin: 24px 0;
            font-style: italic;
            color: var(--primary-dark);
        }}
        .blog-body .se-caption {{
            text-align: center;
            color: var(--text-light);
            font-size: .85rem;
            margin-top: -16px;
            margin-bottom: 24px;
            font-style: italic;
        }}

        /* se-viewer 기본 스타일 보정 */
        .se-viewer {{
            font-family: 'Noto Sans KR', sans-serif !important;
        }}
        .se-text-paragraph {{
            margin-bottom: .6em;
        }}
        .se-text-paragraph-align-center {{
            text-align: center;
        }}
        .se-section-image {{
            margin: 20px 0;
        }}
        .se-module-image {{
            text-align: center;
        }}
        .pcol3 {{
            color: var(--accent);
            font-weight: 700;
        }}

        /* ── 공유/정보 박스 ── */
        .post-info-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 32px;
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            margin-bottom: 32px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .post-info-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .author-avatar {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-weight: 700;
            font-size: 1.1rem;
        }}
        .author-info {{
            display: flex;
            flex-direction: column;
        }}
        .author-name {{
            font-weight: 700;
            font-size: .95rem;
            color: var(--text-dark);
        }}
        .post-date {{
            font-size: .82rem;
            color: var(--text-light);
        }}
        .naver-link {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            background: #03c75a;
            color: #fff;
            text-decoration: none;
            border-radius: 20px;
            font-size: .85rem;
            font-weight: 600;
            transition: transform .2s, box-shadow .2s;
        }}
        .naver-link:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(3,199,90,.35);
        }}

        /* ── 하단 CTA ── */
        .cta-section {{
            background: linear-gradient(135deg, #0d47a1, #1976d2);
            border-radius: var(--radius);
            padding: 48px 40px;
            text-align: center;
            color: #fff;
            margin-bottom: 32px;
        }}
        .cta-section h3 {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .cta-section p {{
            opacity: .85;
            margin-bottom: 24px;
            font-size: .95rem;
        }}
        .cta-btn {{
            display: inline-block;
            padding: 14px 36px;
            background: var(--accent);
            color: #fff;
            text-decoration: none;
            border-radius: 30px;
            font-weight: 700;
            font-size: 1rem;
            transition: transform .2s, box-shadow .2s;
            box-shadow: 0 4px 20px rgba(255,87,34,.4);
        }}
        .cta-btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(255,87,34,.5);
        }}

        /* ── 푸터 ── */
        .site-footer {{
            background: #1a1a2e;
            color: rgba(255,255,255,.55);
            text-align: center;
            padding: 32px 24px;
            font-size: .82rem;
            line-height: 1.8;
        }}
        .site-footer strong {{
            color: rgba(255,255,255,.85);
        }}

        /* ── 반응형 ── */
        @media (max-width: 768px) {{
            .post-hero {{ height: 300px; }}
            .hero-content {{ padding: 24px 20px 28px; }}
            .post-card {{ padding: 28px 20px; }}
            .post-layout {{ padding: 28px 16px 60px; }}
            .cta-section {{ padding: 32px 24px; }}
            .header-nav {{ display: none; }}
        }}
    </style>
</head>
<body>

<!-- 헤더 -->
<header class="site-header">
    <div class="header-inner">
        <a href="../index.html" class="logo">
            <div class="logo-icon">🔧</div>
            <span class="logo-text">하수구수사대</span>
        </a>
        <nav class="header-nav">
            <a href="../index.html">홈</a>
            <a href="index.html">블로그</a>
            <a href="../index.html#contact">상담문의</a>
        </nav>
    </div>
</header>

<!-- 히어로 -->
<section class="post-hero">
    {"" if not cover_local else f'<img src="{cover_local}" alt="{title}">' }
    <div style="max-width:900px;margin:0 auto;position:relative;">
        <div class="hero-content">
            {"" if not category else f'<span class="hero-badge">{category}</span>'}
            <h1 class="hero-title">{title}</h1>
            <div class="hero-meta">
                <span>📅 {post_date}</span>
                <span>✍️ 하수구수사대</span>
            </div>
        </div>
    </div>
</section>

<!-- 본문 -->
<main class="post-layout">

    <!-- 작성자 정보 바 -->
    <div class="post-info-bar">
        <div class="post-info-left">
            <div class="author-avatar">하</div>
            <div class="author-info">
                <span class="author-name">하수구수사대</span>
                <span class="post-date">{post_date}</span>
            </div>
        </div>
        <a href="https://blog.naver.com/{BLOG_ID}/{log_no}" target="_blank" rel="noopener" class="naver-link">
            📝 네이버 원문 보기
        </a>
    </div>

    <!-- 블로그 본문 -->
    <article class="post-card">
        <div class="blog-body">
            {content_html}
        </div>
    </article>

    <!-- 하단 CTA -->
    <div class="cta-section">
        <h3>🔧 하수구 막힘 문제로 고민 중이신가요?</h3>
        <p>24시간 신속 출동! 용인·수원·화성 전문 하수구 청소 서비스</p>
        <a href="tel:010-0000-0000" class="cta-btn">📞 지금 바로 전화 상담</a>
    </div>

</main>

<!-- 푸터 -->
<footer class="site-footer">
    <strong>하수구수사대</strong><br>
    용인·수원·화성 하수구 막힘 전문 청소업체<br>
    © {datetime.now().year} 하수구수사대. All rights reserved.
</footer>

</body>
</html>
"""
    return html


def run(log_no):
    """메인 실행 함수"""
    log_no = str(log_no).strip()
    
    # URL에서 블로그 ID 추출 시도
    blog_id = BLOG_ID
    if "blog.naver.com" in log_no:
        m = re.search(r'blog\.naver\.com/([a-zA-Z0-9_-]+)/(\d+)', log_no)
        if m:
            blog_id = m.group(1)
            log_no = m.group(2)
    
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"

    print(f"\n{'='*60}")
    print(f"  [크롤러] 네이버 블로그 크롤러 - 하수구수사대")
    print(f"{'='*60}")
    print(f"  URL : {url}")
    print(f"  포스트 번호 : {log_no}")
    print(f"{'='*60}\n")

    # 디렉터리 생성
    images_dir = os.path.join(IMAGES_BASE_DIR, log_no)
    os.makedirs(BLOG_DIR, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    print(f"[1/4] 디렉터리 준비 완료")
    print(f"      blog/images/{log_no}/\n")

    # HTML 가져오기
    print(f"[2/4] 블로그 페이지 다운로드 중...")
    html = fetch_html(url)
    print(f"      OK ({len(html):,} bytes)\n")

    # 파싱
    print(f"[3/4] 콘텐츠 분석 중...")
    data = parse_blog(html, log_no)
    print(f"      제목    : {data['title']}")
    print(f"      날짜    : {data['date']}")
    print(f"      카테고리: {data['category']}")
    print(f"      이미지  : {len(data['images'])}개 발견\n")

    # 이미지 다운로드
    print(f"[4/4] 이미지 다운로드 중...")
    
    # 1. 커버 이미지 다운로드
    cover_image_local = ""
    if data["cover_image"]:
        cover_url = data["cover_image"]
        ext = os.path.splitext(cover_url.split("?")[0])[1]
        if not ext or len(ext) > 5:
            ext = ".jpg"
        cover_filename = f"cover{ext}"
        cover_save_path = os.path.join(images_dir, cover_filename)
        
        print(f"      [커버 이미지] {cover_filename} 다운로드 중...", end=" ", flush=True)
        if download_image(cover_url, cover_save_path):
            print("OK")
            cover_image_local = f"images/{log_no}/{cover_filename}"
        else:
            print("FAIL")
    
    # 2. 본문 이미지 다운로드 및 매핑
    downloaded = 0
    img_map = {}
    for i, img_url in enumerate(data["images"], 1):
        base_url = img_url.split("?")[0]
        ext = os.path.splitext(base_url)[1]
        if not ext or len(ext) > 5:
            ext = ".jpg"
        safe_filename = f"image_{i}{ext}"
        save_path = os.path.join(images_dir, safe_filename)
        
        print(f"      [{i}/{len(data['images'])}] {safe_filename} ...", end=" ", flush=True)
        if download_image(img_url, save_path):
            print("OK")
            downloaded += 1
            img_map[base_url] = f"images/{log_no}/{safe_filename}"
        else:
            print("FAIL")
        time.sleep(0.3)  # 서버 부하 방지

    print(f"\n      다운로드 완료: {downloaded}/{len(data['images'])}개\n")

    # 3. 커버 이미지 미획득 시 첫 번째 본문 이미지로 대체
    if not cover_image_local and img_map:
        first_img_path = list(img_map.values())[0]
        print(f"      [안내] 커버 이미지가 없거나 실패하여 첫 번째 이미지({first_img_path})를 커버로 대체합니다.")
        cover_image_local = first_img_path

    # HTML 생성
    output_html = generate_html(data, log_no, img_map, cover_image_local)
    html_path = os.path.join(BLOG_DIR, f"{log_no}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(output_html)

    # 메타데이터 JSON 저장 (인덱스 페이지 생성용)
    meta = {
        "log_no": log_no,
        "title": data["title"],
        "description": data["description"],
        "date": data["date"],
        "category": data["category"],
        "cover_image": cover_image_local,
        "html_file": f"{log_no}.html",
        "images_count": downloaded,
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "naver_url": f"https://blog.naver.com/{BLOG_ID}/{log_no}",
    }
    meta_path = os.path.join(BLOG_DIR, f"{log_no}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"{'='*60}")
    print(f"  [완료] 생성 완료!")
    print(f"{'='*60}")
    print(f"  HTML  : blog/{log_no}.html")
    print(f"  META  : blog/{log_no}.json")
    print(f"  IMAGE : blog/images/{log_no}/ ({downloaded}개)")
    print(f"{'='*60}\n")

    # 블로그 인덱스 갱신
    update_blog_index()

    return html_path


def update_blog_index():
    """블로그 인덱스 페이지 (블로그 목록) 자동 갱신"""
    # 모든 JSON 메타 파일 수집
    posts = []
    if os.path.exists(BLOG_DIR):
        for fname in sorted(os.listdir(BLOG_DIR), reverse=True):
            if fname.endswith(".json"):
                with open(os.path.join(BLOG_DIR, fname), "r", encoding="utf-8") as f:
                    try:
                        posts.append(json.load(f))
                    except:
                        pass

    if not posts:
        return

    # 카드 HTML 생성
    cards_html = ""
    for p in posts:
        cover = p.get("cover_image", "")
        cover_html = (
            f'<div class="card-img"><img src="{cover}" alt="{p["title"]}" loading="lazy"></div>'
            if cover else
            '<div class="card-img card-img-placeholder">🔧</div>'
        )
        cards_html += f"""
        <article class="post-card" onclick="location.href='{p['html_file']}'" role="button" tabindex="0">
            {cover_html}
            <div class="card-body">
                {"" if not p.get("category") else f'<span class="card-badge">{p["category"]}</span>'}
                <h2 class="card-title">{p['title']}</h2>
                <p class="card-desc">{p.get('description', '')[:80]}{"..." if len(p.get("description","")) > 80 else ""}</p>
                <div class="card-meta">
                    <span>📅 {p.get('date', '')}</span>
                    <span class="card-read">자세히 보기 →</span>
                </div>
            </div>
        </article>"""

    index_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="하수구수사대 시공 후기 및 블로그 - 용인·수원·화성 하수구 막힘 청소 전문">
    <title>블로그 - 하수구수사대</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        :root {{
            --primary: #1a73e8; --primary-dark: #0d47a1; --accent: #ff5722;
            --text-dark: #1a1a2e; --text-mid: #444466; --text-light: #888899;
            --bg: #f8f9fc; --card-bg: #fff; --radius: 16px; --radius-sm: 8px;
            --shadow-sm: 0 2px 8px rgba(0,0,0,.06); --shadow-md: 0 8px 32px rgba(0,0,0,.10);
        }}
        body {{ font-family: 'Noto Sans KR', sans-serif; background: var(--bg); color: var(--text-dark); -webkit-font-smoothing: antialiased; }}
        .site-header {{ background: linear-gradient(135deg, #0d47a1, #1976d2); padding: 0; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 20px rgba(13,71,161,.35); }}
        .header-inner {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 64px; }}
        .logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; color: #fff; }}
        .logo-icon {{ width: 36px; height: 36px; background: rgba(255,255,255,.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; }}
        .logo-text {{ font-size: 1.1rem; font-weight: 700; }}
        .header-nav a {{ color: rgba(255,255,255,.85); text-decoration: none; font-size: .9rem; font-weight: 500; padding: 6px 14px; border-radius: var(--radius-sm); transition: background .2s; }}
        .header-nav a:hover {{ background: rgba(255,255,255,.15); color: #fff; }}
        .page-hero {{ background: linear-gradient(135deg, #1a237e, #283593); padding: 80px 24px 60px; text-align: center; color: #fff; }}
        .page-hero h1 {{ font-size: clamp(1.8rem, 4vw, 2.8rem); font-weight: 700; margin-bottom: 12px; }}
        .page-hero p {{ opacity: .8; font-size: 1rem; }}
        .post-count {{ display: inline-block; background: var(--accent); color: #fff; padding: 4px 14px; border-radius: 20px; font-size: .8rem; font-weight: 700; margin-top: 16px; }}
        .posts-grid {{ max-width: 1100px; margin: 0 auto; padding: 56px 24px 80px; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 28px; }}
        .post-card {{ background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow-sm); overflow: hidden; cursor: pointer; transition: transform .25s, box-shadow .25s; display: flex; flex-direction: column; }}
        .post-card:hover {{ transform: translateY(-6px); box-shadow: var(--shadow-md); }}
        .card-img {{ height: 210px; overflow: hidden; background: #e8eaf0; }}
        .card-img img {{ width: 100%; height: 100%; object-fit: cover; transition: transform .4s ease; }}
        .post-card:hover .card-img img {{ transform: scale(1.05); }}
        .card-img-placeholder {{ display: flex; align-items: center; justify-content: center; font-size: 3rem; color: var(--text-light); }}
        .card-body {{ padding: 22px 24px 24px; flex: 1; display: flex; flex-direction: column; gap: 8px; }}
        .card-badge {{ display: inline-block; background: #e8f0fe; color: var(--primary); padding: 3px 10px; border-radius: 20px; font-size: .72rem; font-weight: 700; }}
        .card-title {{ font-size: 1.05rem; font-weight: 700; color: var(--text-dark); line-height: 1.4; }}
        .card-desc {{ font-size: .87rem; color: var(--text-mid); line-height: 1.7; flex: 1; }}
        .card-meta {{ display: flex; justify-content: space-between; align-items: center; font-size: .8rem; color: var(--text-light); margin-top: 8px; }}
        .card-read {{ color: var(--primary); font-weight: 600; }}
        .empty-state {{ text-align: center; padding: 80px 24px; color: var(--text-light); grid-column: 1/-1; }}
        .site-footer {{ background: #1a1a2e; color: rgba(255,255,255,.55); text-align: center; padding: 32px 24px; font-size: .82rem; line-height: 1.8; }}
        .site-footer strong {{ color: rgba(255,255,255,.85); }}
        @media (max-width: 768px) {{ .posts-grid {{ padding: 32px 16px 60px; gap: 20px; }} .header-nav {{ display: none; }} }}
    </style>
</head>
<body>
<header class="site-header">
    <div class="header-inner">
        <a href="../index.html" class="logo">
            <div class="logo-icon">🔧</div>
            <span class="logo-text">하수구수사대</span>
        </a>
        <nav class="header-nav">
            <a href="../index.html">홈</a>
            <a href="index.html">블로그</a>
            <a href="../index.html#contact">상담문의</a>
        </nav>
    </div>
</header>
<section class="page-hero">
    <h1>📋 시공 후기 & 블로그</h1>
    <p>하수구수사대의 실제 현장 시공 후기를 확인하세요</p>
    <span class="post-count">총 {len(posts)}개 포스트</span>
</section>
<div class="posts-grid">
    {cards_html if cards_html else '<div class="empty-state"><p>아직 블로그 포스트가 없습니다.</p></div>'}
</div>
<footer class="site-footer">
    <strong>하수구수사대</strong><br>
    용인·수원·화성 하수구 막힘 전문 청소업체<br>
    © {datetime.now().year} 하수구수사대. All rights reserved.
</footer>
</body>
</html>"""

    index_path = os.path.join(BLOG_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  [INDEX] blog/index.html 갱신 ({len(posts)}개 포스트)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print()
        print("사용법: python blog_crawler.py [블로그 포스트 번호 또는 URL]")
        print("예시 : python blog_crawler.py 224300839005")
        print("       python blog_crawler.py https://m.blog.naver.com/hasugu2118/223789808499")
        print()
        sys.exit(1)

    input_arg = sys.argv[1]
    log_no = extract_log_no(input_arg)
    run(log_no)
