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
    """이미지 다운로드 - 썸네일 대신 원본 이미지 다운로드"""
    base_url = img_url.split("?")[0]
    
    # 썸네일 도메인을 원본 이미지 도메인(postfiles)으로 변경하고 고화질 파라미터 적용
    orig_url = base_url
    orig_url = orig_url.replace("mblogthumb-phinf.pstatic.net", "postfiles.pstatic.net")
    orig_url = orig_url.replace("blogthumb.phinf.naver.net", "postfiles.pstatic.net")
    orig_url = orig_url.replace("blogthumb.phinf.pstatic.net", "postfiles.pstatic.net")
    orig_url = orig_url.replace("blogthumb.pstatic.net", "postfiles.pstatic.net")
    
    # 고화질(type=w966) 파라미터 추가
    download_url = orig_url + "?type=w966"
    
    req = urllib.request.Request(download_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            with open(save_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        # 실패하면 w800 크기로 재시도
        try:
            fallback_url1 = orig_url + "?type=w800"
            req2 = urllib.request.Request(fallback_url1, headers=HEADERS)
            with urllib.request.urlopen(req2, timeout=15) as resp:
                with open(save_path, "wb") as f:
                    f.write(resp.read())
            return True
        except Exception as e2:
            # 그것도 실패하면 base_url만 시도 (파라미터 없음)
            try:
                req3 = urllib.request.Request(base_url, headers=HEADERS)
                with urllib.request.urlopen(req3, timeout=15) as resp:
                    with open(save_path, "wb") as f:
                        f.write(resp.read())
                return True
            except Exception as e3:
                print(f"  [경고] 이미지 다운로드 실패 ({download_url}): {e3}")
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

    target_html = content_html if content_html else html
    lazy_imgs = re.findall(r'data-lazy-src="(https://mblogthumb[^"]+)"', target_html)
    for url in lazy_imgs:
        base = url.split("?")[0]
        if base not in seen:
            seen.add(base)
            image_urls.append(base)

    # data-linkdata src 에서도 보완 수집
    link_data_imgs = re.findall(r'"src"\s*:\s*"(https://mblogthumb[^"]+)"', target_html)
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


TRANSLATIONS = {
    # Areas
    "용인": "yongin", "수지": "suji", "풍덕천": "pungdeokcheon", "기흥": "giheung", "처인": "cheoinggu", "역북": "yeokbuk", "김량장": "gimryangjang",
    "수원": "suwon", "영통": "yeongtong", "이의": "uiui", "권선": "gwonseon", "팔달": "paldal", "장안": "jangan",
    "화성": "hwaseong", "향남": "hyangnam", "상신": "sangshin", "하길": "hagil", "새솔": "saesol", "병점": "byeongjeom", "동탄": "dongtan",
    "오산": "osan", "가수": "gasu", "수청": "sucheong",
    "안산": "ansan", "해양": "haeyang",
    "서울": "seoul", "경기": "gyeonggi", "인천": "incheon",
    
    # Services
    "배관막힘": "drain-clogged", "하수구막힘": "sewer-clogged", "싱크대막힘": "sink-clogged", "변기막힘": "toilet-clogged",
    "하수구청소": "sewer-cleaning", "배관청소": "drain-cleaning", "하수관청소": "sewer-cleaning",
    "누수수리": "leakage-repair", "누수탐지": "leakage-detection", "방수공사": "waterproofing", "우수관교체": "rainpipe-replacement",
    "배관수리": "pipe-repair", "고압세척": "high-pressure-flushing", "내시경점검": "camera-inspection", "음식물처리기": "food-waste-disposer",
    "싱크리더": "sinkleader", "웰릭스": "welix", "베란다누수": "balcony-leakage"
}

def generate_slug_from_korean(primary_area: str, primary_service: str, log_no: str) -> str:
    words = re.findall(r'[가-힣a-zA-Z0-9]+', f"{primary_area} {primary_service}")
    slug_parts = []
    for w in words:
        matched = False
        for ko, en in TRANSLATIONS.items():
            if ko in w:
                slug_parts.append(en)
                matched = True
                break
        if not matched:
            pass
    slug_parts = list(dict.fromkeys(slug_parts))
    if not slug_parts:
        slug_parts = ["sewer", "clogged"]
    return f"{'-'.join(slug_parts)}-{log_no}"

def format_date(date_str: str) -> str:
    m = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', date_str)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return datetime.now().strftime("%Y-%m-%d")

def clean_html_to_text(html_content: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_geo_seo_info(title: str, body_text: str) -> dict:
    area_candidates = {
        "수원시 영통구 이의동": ["영통구", "이의동", "수원 영통"],
        "용인시 수지구 풍덕천동": ["수지구", "풍덕천동", "용인 수지"],
        "오산시 가수동": ["오산", "가수동"],
        "오산시 수청동": ["수청동"],
        "화성시 새솔동": ["새솔동"],
        "안산시 상록구 해양동": ["해양동", "안산 해양"],
        "용인시 기흥구": ["기흥구", "용인 기흥"],
        "수원시 권선구": ["권선구", "수원 권선"],
        "화성시 향남읍 상신리": ["향남", "상신리"],
        "화성시 향남읍 하길리": ["하길리"],
        "용인시 처인구": ["처인구", "용인 처인"]
    }
    
    found_areas = []
    for full_name, kws in area_candidates.items():
        for kw in kws:
            if kw in title:
                found_areas.append(full_name)
                break
                
    for full_name, kws in area_candidates.items():
        if full_name not in found_areas:
            for kw in kws:
                if kw in body_text:
                    found_areas.append(full_name)
                    break
                    
    found_areas = list(dict.fromkeys(found_areas))
    if not found_areas:
        found_areas = ["용인시 처인구", "수원시 영통구", "화성시 동탄"]
        
    primary_area = found_areas[0].split(" ")[-1] if found_areas else "용인"
    if "구" in primary_area or "동" in primary_area or "리" in primary_area:
        parts = found_areas[0].split(" ")
        if len(parts) >= 2:
            primary_area = f"{parts[0]} {parts[1]}"
        else:
            primary_area = parts[0]
            
    service_keywords = {
        "배관막힘": ["배관막힘", "배관 막힘", "막힘", "하수구막힘", "하수구 막힘"],
        "하수구청소": ["하수구청소", "하수구 청소", "청소작업", "청소 작업"],
        "누수수리": ["누수", "누수수리", "누수 수리", "빗물누수"],
        "방수공사": ["방수공사", "방수 공사", "방수작업", "방수 작업"],
        "우수관교체": ["우수관교체", "우수관 교체", "우수관"],
        "배관수리": ["배관수리", "배관 수리", "수리작업"],
        "고압세척": ["고압세척", "고압 세척", "세척"],
        "내시경점검": ["내시경", "내시경 점검", "내시경점검"],
        "음식물처리기": ["음식물처리기", "음식물 처리기"],
    }
    
    found_services = []
    for svc, kws in service_keywords.items():
        for kw in kws:
            if kw in title or kw in body_text:
                found_services.append(svc)
                break
    if not found_services:
        found_services = ["배관막힘"]
        
    primary_service = found_services[0]
    
    return {
        "areas": found_areas,
        "primary_area": primary_area,
        "service_types": found_services,
        "primary_service": primary_service
    }

def generate_html(data, log_no, img_map, cover_image_local):
    """네이버 SEO/GEO 최적화 및 프리미엄 스타일 HTML 생성"""
    title = data["title"]
    description = data["description"]
    post_date = data["date"]
    category = data["category"]
    
    COMPANY_NAME = "하수구수사대"
    COMPANY_PHONE = "010-5615-2118"
    DOMAIN = "https://www.lymin80.shop"
    
    # 텍스트 추출 및 정제
    content_html = clean_content_for_website(data["content_html"], log_no, img_map)
    raw_text = clean_html_to_text(content_html)
    
    # GEO/SEO 메타 정보 추출
    geo_seo = extract_geo_seo_info(title, raw_text)
    primary_area = geo_seo["primary_area"]
    primary_service = geo_seo["primary_service"]
    areas = geo_seo["areas"]
    service_types = geo_seo["service_types"]
    
    slug = generate_slug_from_korean(primary_area, primary_service, log_no)
    
    # 대표 이미지 경로 확보 (상대 경로 및 절대 경로 구분)
    cover_image_relative = cover_image_local
    if cover_image_relative.startswith("/blog/"):
        cover_image_relative = cover_image_relative[6:]
    elif cover_image_relative.startswith("/"):
        cover_image_relative = cover_image_relative[1:]
    if cover_image_relative.startswith("blog/"):
        cover_image_relative = cover_image_relative[5:]
        
    cover_image_absolute = f"{DOMAIN}/blog/{cover_image_relative}"

    # GEO Coordinates
    geo_coords = {
        "수원": "37.2635;127.0286",
        "용인": "37.2410;127.1779",
        "화성": "37.1995;126.8312",
        "오산": "37.1502;127.0789",
        "안산": "37.3219;126.8308",
        "서울": "37.5665;126.9780",
        "인천": "37.4563;126.7052"
    }
    
    geo_pos = "37.2410;127.1779"  # default Yongin
    for k, v in geo_coords.items():
        if k in primary_area:
            geo_pos = v
            break
        
    # SEO 키워드 추출
    seo_keywords = [
        f"{primary_area} {primary_service}",
        f"{' '.join(areas[:2])} {primary_service}",
        f"{primary_area} 배관",
        f"{primary_area} 하수구",
        f"{' '.join(areas[:2])} 배관 전문",
        f"{primary_service} 전문업체",
        "하수구수사대"
    ] + [f"{area} {primary_service}" for area in areas[:3]]
    seo_keywords = list(dict.fromkeys(seo_keywords))
    
    # Description 생성
    desc = f"{' '.join(areas[:2])} {primary_service} 전문업체 {COMPANY_NAME}. {title}. {COMPANY_PHONE} 24시간 긴급 출동."
    
    # 문단 추출
    paragraphs = []
    p_pattern = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
    for p_content in p_pattern.findall(content_html):
        txt = re.sub(r'<[^>]+>', '', p_content).strip()
        txt = txt.replace('&amp;quot;', '"').replace('&quot;', '"').replace('&nbsp;', ' ')
        if txt and len(txt) > 2:
            if txt not in paragraphs and not txt.startswith("📝 네이버 원문 보기"):
                paragraphs.append(txt)
                
    N = len(paragraphs)
    if N < 4:
        paragraphs = paragraphs + ["하수구수사대는 항상 최선을 다해 정확한 원인을 규명하고 해결해 드립니다."] * (4 - N)
        N = len(paragraphs)
        
    sec1_p = paragraphs[:int(N*0.25)]
    sec2_p = paragraphs[int(N*0.25):int(N*0.5)]
    sec3_p = paragraphs[int(N*0.5):int(N*0.9)]
    sec4_p = paragraphs[int(N*0.9):]
    
    # 이미지 목록 (img_map에서 로컬 경로 수집 - 상대 경로 형식)
    images = []
    for img_src in img_map.values():
        img_path = img_src
        if img_path.startswith("/blog/"):
            img_path = img_path[6:]
        elif img_path.startswith("/"):
            img_path = img_path[1:]
        if img_path.startswith("blog/"):
            img_path = img_path[5:]
        if img_path not in images:
            images.append(img_path)
            
    # 대표 이미지는 바디 리스트에서 제외 (상대 경로로 비교)
    body_images = [img for img in images if img != cover_image_relative]
    
    img_sec1 = f'<div class="image-box"><img src="{body_images[0]}" alt="{title} 현장 상황" loading="lazy"></div>' if len(body_images) > 0 else ""
    img_sec2 = f'<div class="image-box"><img src="{body_images[1]}" alt="{title} 원인 분석" loading="lazy"></div>' if len(body_images) > 1 else ""
    
    img_sec3 = ""
    if len(body_images) > 3:
        img_sec3 = f'''
        <div class="image-grid">
          <img src="{body_images[2]}" alt="작업 과정 사진 1" loading="lazy">
          <img src="{body_images[3]}" alt="작업 과정 사진 2" loading="lazy">
        </div>'''
    elif len(body_images) > 2:
        img_sec3 = f'<div class="image-box"><img src="{body_images[2]}" alt="작업 과정 사진" loading="lazy"></div>'
        
    extra_images = body_images[4:] if len(body_images) > 4 else []
    img_sec4 = ""
    if extra_images:
        img_sec4 = '<div class="image-grid">'
        for idx, img in enumerate(extra_images[:4]):
            img_sec4 += f'<img src="{img}" alt="추가 시공 사진 {idx+1}" loading="lazy">'
        img_sec4 += '</div>'
        
    # 인용구 추출
    quotes = []
    quote_pattern = re.compile(r'<blockquote[^>]*>(.*?)</blockquote>', re.DOTALL)
    for q_content in quote_pattern.findall(content_html):
        txt = re.sub(r'<[^>]+>', '', q_content).strip()
        if txt and txt not in quotes:
            quotes.append(txt)
    diag_quote = quotes[0] if quotes else "정밀 진단 장비를 사용하여 슬러지의 고착 여부를 판명하고 타격/세척 작업을 실시했습니다."
    
    # 예방법 생성
    precaution_title = "하수구 배관 막힘 예방 및 관리 가이드"
    precaution_list = [
        "머리카락, 비닐, 물티슈 등 물에 분해되지 않는 이물질은 절대 흘려보내지 마세요.",
        "기름기 많은 식기는 설거지 전 키친타올로 먼저 기름때를 닦아내세요.",
        "주기적으로 배수구에 뜨거운 물을 가득 부어주어 유지방 고착을 방지하세요.",
        "작업 후 1년 이내 재발 시 무상 A/S 보증 서비스를 제공합니다."
    ]
    
    service_joined = " ".join(service_types)
    if "음식물처리기" in service_joined:
        precaution_title = "음식물처리기 올바른 사용법"
        precaution_list = [
            "기름기가 많은 음식(지방류, 육류 비계 등)은 하수구 고착의 주원인이 되므로 투입하지 마세요.",
            "작동 시 충분한 양의 물을 동시에 흘려보내 잘게 갈린 찌꺼기가 배관 끝까지 흘러가게 하세요.",
            "부피가 크거나 질긴 채소류는 일반 쓰레기로 분리수거해 주세요.",
            "배수가 느려지는 느낌이 들면 화학 세정제보다 신속히 내시경 점검을 받으십시오."
        ]
        
    precaution_html = "".join([f'<li style="margin-bottom: 8px;">✅ {item}</li>' for item in precaution_list])
    
    # FAQ
    faq_items = [
        {
            "q": f"{primary_area} {primary_service} 비용은 얼마인가요?",
            "a": f"현장 상태와 배관 막힘의 원인에 따라 다릅니다. 단순 점검 및 통수는 5만원~15만원 선이며, 고압 세척이나 방수/교체 공사 등은 15만원~50만원 이상이 발생할 수 있습니다. 방문 후 상세 견적을 투명하게 안내해 드립니다."
        },
        {
            "q": f"{primary_area} 지역 출동 시간은 얼마나 걸리나요?",
            "a": f"하수구수사대는 서울, 경기, 인천 전 지역에 24시간 긴급 대기 중입니다. {primary_area} 지역은 연락 주시면 평균 30분에서 1시간 이내에 신속하게 현장에 도착합니다."
        },
        {
            "q": "작업 후 사후 관리나 A/S 보증이 되나요?",
            "a": "네, 저희 하수구수사대는 확실한 시공을 약속드리며, 작업 완료 후 동일 부위에서 1년 내에 다시 막히거나 누수가 재발할 경우 100% 무상 A/S를 제공해 드립니다."
        }
    ]
    
    faq_schema_entries = []
    faq_html_entries = []
    for faq in faq_items:
        faq_schema_entries.append(f'''      {{
        "@type": "Question",
        "name": "{faq['q']}",
        "acceptedAnswer": {{
          "@type": "Answer",
          "text": "{faq['a']}"
        }}
      }}''')
        faq_html_entries.append(f'''    <div class="faq-item">
      <div class="question">Q. {faq['q']}</div>
      <div class="answer">A. {faq['a']}</div>
    </div>''')
        
    faq_schema = ",\n".join(faq_schema_entries)
    faq_html = "\n".join(faq_html_entries)
    
    area_served_entries = []
    for a in areas[:5]:
        area_served_entries.append(f'{{"@type": "City", "name": "{a}"}}')
    area_served_schema = ",\n      ".join(area_served_entries)
    
    service_type_schema = ", ".join([f'"{s}"' for s in service_types])
    tag_html = "\n".join([f"      <span>#{tag}</span>" for tag in seo_keywords])
    
    iso_date = format_date(post_date)

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | {COMPANY_NAME}</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{', '.join(seo_keywords)}">
  <link rel="canonical" href="{DOMAIN}/blog/{slug}.html">

  <!-- Naver SEO & GEO Tags -->
  <meta name="geo.region" content="KR-41">
  <meta name="geo.placename" content="{primary_area}">
  <meta name="geo.position" content="{geo_pos}">
  <meta name="ICBM" content="{geo_pos}">

  <!-- Open Graph -->
  <meta property="og:title" content="{title} | {COMPANY_NAME}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{cover_image_absolute}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{DOMAIN}/blog/{slug}.html">

  <!-- Schema.org: Article -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "description": "{desc}",
    "author": {{
      "@type": "Organization",
      "name": "{COMPANY_NAME}"
    }},
    "datePublished": "{iso_date}",
    "dateModified": "{datetime.now().strftime('%Y-%m-%d')}",
    "image": "{cover_image_absolute}",
    "publisher": {{
      "@type": "Organization",
      "name": "{COMPANY_NAME}"
    }},
    "mainEntityOfPage": {{
      "@type": "WebPage",
      "@id": "{DOMAIN}/blog/{slug}.html"
    }}
  }}
  </script>

  <!-- Schema.org: FAQ -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
{faq_schema}
    ]
  }}
  </script>

  <!-- Schema.org: LocalBusiness -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "{COMPANY_NAME}",
    "description": "{primary_area} {primary_service} 전문업체",
    "telephone": "{COMPANY_PHONE}",
    "areaServed": [
      {area_served_schema}
    ],
    "serviceType": [{service_type_schema}],
    "openingHours": "Mo-Su 00:00-24:00"
  }}
  </script>

  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif; line-height: 1.8; color: #333; background: #f5f5f5; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
    .header {{ background: linear-gradient(135deg, #1a5276, #2980b9); color: white; padding: 40px 20px; text-align: center; border-radius: 12px; margin-bottom: 30px; }}
    .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
    .header p {{ font-size: 16px; opacity: 0.9; }}
    .meta {{ color: #666; font-size: 14px; margin-bottom: 20px; padding: 10px 15px; background: #fff; border-radius: 8px; border-left: 4px solid #2980b9; }}
    .section {{ background: #fff; padding: 30px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .section h2 {{ font-size: 22px; color: #1a5276; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}
    .section h3 {{ font-size: 18px; color: #2980b9; margin: 20px 0 10px; }}
    .section p {{ margin-bottom: 12px; font-size: 16px; }}
    .highlight {{ background: #fff3cd; padding: 2px 6px; border-radius: 4px; font-weight: 600; }}
    .blockquote {{ background: #f8f9fa; border-left: 4px solid #2980b9; padding: 15px 20px; margin: 15px 0; border-radius: 0 8px 8px 0; }}
    .blockquote strong {{ color: #1a5276; }}
    .image-box {{ margin: 20px 0; text-align: center; }}
    .image-box img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .image-box .caption {{ font-size: 13px; color: #888; margin-top: 8px; }}
    .image-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 20px 0; }}
    .image-grid img {{ width: 100%; height: auto; border-radius: 8px; }}
    .faq-item {{ margin-bottom: 20px; padding: 20px; background: #f0f7ff; border-radius: 8px; }}
    .faq-item .question {{ font-weight: bold; color: #1a5276; margin-bottom: 8px; }}
    .faq-item .answer {{ color: #444; }}
    .cta {{ background: linear-gradient(135deg, #1a5276, #2980b9); color: white; padding: 30px; border-radius: 12px; text-align: center; margin: 30px 0; }}
    .cta h3 {{ color: white; font-size: 22px; margin-bottom: 10px; }}
    .cta .phone {{ font-size: 32px; font-weight: bold; margin: 15px 0; }}
    .cta p {{ opacity: 0.9; }}
    .tag-list {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }}
    .tag-list span {{ background: #e8f4fd; color: #2980b9; padding: 4px 12px; border-radius: 20px; font-size: 13px; }}
    .footer {{ text-align: center; padding: 20px; color: #888; font-size: 13px; }}
    .breadcrumb {{ font-size: 14px; color: #888; margin-bottom: 15px; }}
    .breadcrumb a {{ color: #2980b9; text-decoration: none; }}
    @media (max-width: 600px) {{
      .container {{ padding: 10px; }}
      .header h1 {{ font-size: 22px; }}
      .section {{ padding: 20px; }}
      .image-grid {{ grid-template-columns: 1fr; }}
      .cta .phone {{ font-size: 26px; }}
    }}
  </style>
  <link rel="icon" type="image/png" sizes="32x32" href="/images/favicon.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png">
</head>
<body>

<div class="container">

  <!-- 브레드크럼 -->
  <div class="breadcrumb">
    <a href="../index.html">홈</a> &gt; <a href="index.html">시공사례</a> &gt; <span>{primary_area} {primary_service}</span>
  </div>

  <!-- 헤더 -->
  <div class="header">
    <h1>🏠 {title}</h1>
    <p>{primary_area} {primary_service} 전문 시공 후기</p>
  </div>

  <!-- 메타 정보 -->
  <div class="meta">
    📅 시공일: {post_date} | 📍 현장: {areas[0]} | 🏢 {COMPANY_NAME} | 🔄 업데이트: {datetime.now().strftime('%Y-%m-%d')}
  </div>

  <!-- 대표 이미지 -->
  {f'<div class="image-box"><img src="{cover_image_relative}" alt="{title} 대표 이미지"><div class="caption">{primary_area} {primary_service} 현장</div></div>' if cover_image_relative else ''}

  <!-- 작업 개요 -->
  <div class="section">
    <h2>📋 작업 개요</h2>
    <ul style="padding-left: 20px;">
      <li style="margin-bottom: 8px;"><strong>위치:</strong> {", ".join(areas[:3])}</li>
      <li style="margin-bottom: 8px;"><strong>서비스 유형:</strong> {", ".join(service_types)}</li>
      <li style="margin-bottom: 8px;"><strong>작업 일시:</strong> {post_date}</li>
      <li style="margin-bottom: 8px;"><strong>업체명:</strong> {COMPANY_NAME} ({COMPANY_PHONE})</li>
    </ul>
  </div>

  <!-- 문제 상황 -->
  <div class="section">
    <h2>🔍 문제 상황</h2>
    {"".join([f"<p>{p}</p>" for p in sec1_p])}
    {img_sec1}
  </div>

  <!-- 원인 분석 -->
  <div class="section">
    <h2>🔎 원인 분석</h2>
    <div class="blockquote">
      <p><strong>💡 전문가 진단:</strong> {diag_quote}</p>
    </div>
    {"".join([f"<p>{p}</p>" for p in sec2_p])}
    {img_sec2}
  </div>

  <!-- 작업 과정 -->
  <div class="section">
    <h2>🔧 작업 과정</h2>
    {"".join([f"<p>{p}</p>" for p in sec3_p])}
    {img_sec3}
  </div>

  <!-- 작업 완료 및 추가 사진 -->
  <div class="section">
    <h2>✅ 작업 완료</h2>
    {"".join([f"<p>{p}</p>" for p in sec4_p])}
    {img_sec4}
  </div>

  <!-- 예방법 및 주의사항 -->
  <div class="section">
    <h2>⚠️ {precaution_title}</h2>
    <ul style="padding-left: 20px; list-style: none;">
      {precaution_html}
    </ul>
  </div>

  <!-- 핵심 정리 -->
  <div class="section">
    <h2>💡 핵심 정리</h2>
    <ul style="padding-left: 20px;">
      <li style="margin-bottom: 8px;">확실한 장비 작업(내시경 점검 및 샤프트 스케일링)으로 원인을 뿌리 뽑습니다.</li>
      <li style="margin-bottom: 8px;">작업 후 1년 이내에 동일한 부위 재발 시 100% 무상 A/S 서비스를 보장합니다.</li>
      <li style="margin-bottom: 8px;">서울 · 경기 · 인천 전 지역에 24시간 언제든 긴급 출동할 수 있도록 항시 대기 중입니다.</li>
    </ul>
  </div>

  <!-- FAQ -->
  <div class="section">
    <h2>❓ 자주 묻는 질문 (FAQ)</h2>
    {faq_html}
  </div>

  <!-- CTA -->
  <div class="cta">
    <h3>🚨 {primary_area} {primary_service} 문제로 고민이신가요?</h3>
    <p>정확한 원인 진단과 확실한 시공으로 재발 없는 해결을 약속드립니다.</p>
    <div class="phone">📞 {COMPANY_PHONE}</div>
    <p>24시간 긴급 출동 | 서울 · 경기 · 인천 전지역 | 1년 내 재발 시 무상 A/S</p>
  </div>

  <!-- 태그 -->
  <div class="section">
    <div class="tag-list">
      {tag_html}
    </div>
  </div>

  <!-- 푸터 -->
  <div class="footer">
    <p>© {datetime.now().year} {COMPANY_NAME}. All rights reserved.</p>
    <p>본 콘텐츠는 실제 현장 시공 사례를 기반으로 작성되었습니다.</p>
    <p>마지막 업데이트: {datetime.now().strftime('%Y년 %m월 %d일')}</p>
  </div>

</div>

</body>
</html>'''
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

    # GEO/SEO 정보 추출 및 슬러그 결정
    body_text_clean = clean_html_to_text(data["content_html"])
    geo_seo = extract_geo_seo_info(data["title"], body_text_clean)
    slug = generate_slug_from_korean(geo_seo["primary_area"], geo_seo["primary_service"], log_no)

    # HTML 생성
    output_html = generate_html(data, log_no, img_map, cover_image_local)
    html_path = os.path.join(BLOG_DIR, f"{slug}.html")
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
        "html_file": f"{slug}.html",
        "images_count": downloaded,
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "naver_url": f"https://blog.naver.com/{blog_id}/{log_no}",
        "slug": slug
    }
    meta_path = os.path.join(BLOG_DIR, f"{log_no}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"{'='*60}")
    print(f"  [완료] 생성 완료!")
    print(f"{'='*60}")
    print(f"  HTML  : blog/{slug}.html")
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
        # 로컬 열기와 Nginx 서버 서빙 모두 깨지지 않도록 상대 경로 형식("images/...")으로 정상화
        if cover.startswith("/blog/"):
            cover = cover[6:]
        elif cover.startswith("/"):
            cover = cover[1:]
            
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
    <link rel="icon" type="image/png" sizes="32x32" href="/images/favicon.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png">
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
    
    # URL에서 블로그 ID 추출하여 전역 변수 BLOG_ID 업데이트
    if "blog.naver.com" in input_arg:
        m = re.search(r'blog\.naver\.com/([a-zA-Z0-9_-]+)/(\d+)', input_arg)
        if m:
            BLOG_ID = m.group(1)
            
    log_no = extract_log_no(input_arg)
    run(log_no)
