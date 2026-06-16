#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하수구수사대 블로그 SEO/GEO 일괄 처리 및 사이트맵 갱신 스크립트
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

# ============================================================
# 설정
# ============================================================
PROJECT_DIR = Path("/Users/lee/projects/hasugu")
BLOG_DIR = PROJECT_DIR / "blog"
SITEMAP_FILE = PROJECT_DIR / "sitemap.xml"
ROBOTS_FILE = PROJECT_DIR / "robots.txt"

DOMAIN = "https://hasugu2.lymin80.shop"
COMPANY_NAME = "하수구수사대"
COMPANY_PHONE = "010-5615-2118"
SERVICE_AREAS = ["서울", "경기도", "인천"]

# 각 포스트별 SEO/GEO 최적화 메타데이터 수동 매핑 (100% 품질 보장)
POSTS_METADATA = {
    "224304522855": {
        "slug": "suwon-yeongtong-balcony-leakage-224304522855",
        "primary_area": "수원 영통",
        "primary_service": "베란다누수 우수관교체",
        "areas": ["수원시 영통구 이의동", "수원 영통", "이의동", "수원", "영통구"],
        "service_types": ["베란다누수 수리", "우수관교체", "방수공사"],
        "keywords": ["영통구 베란다누수", "이의동 우수관교체", "수원 방수공사", "아파트 우수관교체", "베란다 방수", "하수구수사대"]
    },
    "224300839005": {
        "slug": "yongin-pungdeokcheon-food-waste-disposer-drain-cleaning-224300839005",
        "primary_area": "용인 풍덕천",
        "primary_service": "음식물처리기 배관막힘",
        "areas": ["용인시 수지구 풍덕천동", "용인 수지구", "풍덕천동", "용인", "수지구"],
        "service_types": ["음식물처리기 배관막힘", "하수관 청소", "배관 청소", "내시경 점검", "고압세척"],
        "keywords": ["용인 풍덕천동 음식물처리기 배관막힘", "풍덕천동 싱크대 배관막힘", "용인 음식물처리기 막힘", "풍덕천동 싱크대 막힘", "수지구 하수관 청소", "용인 배관 청소", "하수구수사대"]
    },
    "224013046491": {
        "slug": "osan-gasudong-sink-drain-clogged-sewer-backflow-224013046491",
        "primary_area": "오산 가수동",
        "primary_service": "싱크대배수관막힘 하수도역류",
        "areas": ["오산시 가수동", "오산시 수청동", "오산", "가수동", "수청동"],
        "service_types": ["싱크대배수관막힘", "하수도역류", "배관 뚫는업체", "배관 청소", "내시경 점검"],
        "keywords": ["오산 가수동 싱크대막힘", "수청동 하수도역류", "오산 싱크대배수관막힘", "수청동 싱크대막힘", "오산 하수구 뚫는업체", "오산 배관설비", "하수구수사대"]
    },
    "223976249977": {
        "slug": "saesoldong-haeyangdong-sink-drain-clogged-kitchen-pipe-backflow-223976249977",
        "primary_area": "새솔동 해양동",
        "primary_service": "싱크대배수관막힘 주방배관역류",
        "areas": ["화성시 새솔동", "안산시 상록구 해양동", "새솔동", "해양동", "화성 새솔동", "안산 해양동"],
        "service_types": ["싱크대배수관막힘", "주방배관역류", "하수구업체", "배관 청소", "내시경 점검"],
        "keywords": ["새솔동 싱크대막힘", "해양동 주방배관역류", "새솔동 싱크대배수관막힘", "해양동 싱크대막힘", "안산 하수구업체", "화성 하수구전문", "하수구수사대"]
    },
    "223789808499": {
        "slug": "welix-food-waste-disposer-drain-clogged-repair-223789808499",
        "primary_area": "용인 기흥구",
        "primary_service": "웰릭스 음식물처리기 배관막힘",
        "areas": ["용인시 기흥구", "용인 기흥", "수원 영통", "화성 동탄", "기흥구"],
        "service_types": ["웰릭스 음식물처리기", "음식물처리기 배관막힘", "배관 수리", "하수구막힘", "내시경 점검"],
        "keywords": ["웰릭스 음식물처리기 막힘", "음식물처리기 배관 수리", "용인 음식물처리기 막힘", "기흥구 싱크대막힘", "웰릭스 배관막힘", "싱크대 하수구 수리", "하수구수사대"]
    },
    "223039921838": {
        "slug": "welix-sinkleader-food-waste-disposer-clogged-223039921838",
        "primary_area": "수원 권선구",
        "primary_service": "웰릭스 싱크리더 음식물처리기막힘",
        "areas": ["수원시 권선구", "수원 권선", "용인 수지", "화성 병점", "권선구"],
        "service_types": ["웰릭스 싱크리더", "음식물처리기막힘", "하수구막힘 해결", "싱크대막힘", "배관 청소"],
        "keywords": ["웰릭스 싱크리더 막힘", "싱크리더 음식물처리기막힘", "수원 음식물처리기 막힘", "권선구 싱크대막힘", "싱크리더 배관청소", "하수구막힘 해결업체", "하수구수사대"]
    },
    "223023595407": {
        "slug": "hwaseong-hyangnam-sink-clogged-drain-cleaning-223023595407",
        "primary_area": "화성 향남",
        "primary_service": "싱크대막힘 하수구청소",
        "areas": ["화성시 향남읍 상신리", "화성시 향남읍 하길리", "화성 향남", "상신리", "하길리"],
        "service_types": ["싱크대막힘", "하수구막힘", "배관 청소", "싱크대 역류", "내시경 점검"],
        "keywords": ["화성 향남싱크대막힘", "향남 상신리 싱크대막힘", "향남 하길리 하수구막힘", "화성 싱크대역류", "향남 하수구뚫는업체", "향남 배관청소", "하수구수사대"]
    },
    "222634871204": {
        "slug": "yongin-cheoinggu-sewer-clogged-drain-cleaning-222634871204",
        "primary_area": "용인 처인구",
        "primary_service": "하수구막힘 배관청소",
        "areas": ["용인시 처인구 역북동", "용인시 처인구 김량장동", "용인 처인구", "역북동", "김량장동"],
        "service_types": ["하수구막힘", "싱크대하수구배관", "변기막힘", "배관 뚫음", "고압세척"],
        "keywords": ["용인 처인구 하수구막힘", "처인구 역북동 하수구막힘", "처인구 김량장동 변기막힘", "용인 처인구 싱크대막힘", "처인구 하수구 뚫는업체", "처인구 배관청소", "하수구수사대"]
    }
}

def format_date(date_str: str) -> str:
    """날짜 문자열 (예: 2025. 9. 18. 16:19)을 YYYY-MM-DD 형식으로 변환"""
    m = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', date_str)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return datetime.now().strftime("%Y-%m-%d")

def clean_html_to_text(html_content: str) -> str:
    """HTML 태그를 완전히 제거하고 텍스트 정제"""
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_original_content(blog_id: str) -> dict:
    """원본 Naver HTML에서 문단, 이미지, 인용구를 추출"""
    html_file = BLOG_DIR / f"{blog_id}.html"
    if not html_file.exists():
        return {"paragraphs": [], "images": [], "quotes": []}
        
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
        
    # blog-body 영역 추출
    start_idx = html.find('<div class="blog-body">')
    if start_idx == -1:
        start_idx = 0
    body = html[start_idx:]
    
    end_idx = body.find('</article>')
    if end_idx != -1:
        body = body[:end_idx]
        
    # 1. 문단(p) 추출
    paragraphs = []
    p_pattern = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
    for p_content in p_pattern.findall(body):
        txt = re.sub(r'<[^>]+>', '', p_content).strip()
        txt = txt.replace('&amp;quot;', '"').replace('&quot;', '"').replace('&nbsp;', ' ')
        if txt and len(txt) > 2:
            # 중복/노이즈 필터링
            if txt not in paragraphs and not txt.startswith("📝 네이버 원문 보기"):
                paragraphs.append(txt)
                
    # 2. 이미지(img) 추출 (로컬 경로)
    images = []
    img_pattern = re.compile(r'<img[^>]+src="([^"]+)"', re.DOTALL)
    for img_src in img_pattern.findall(body):
        if 'logo' not in img_src and 'avatar' not in img_src:
            # 파일명만 추출하여 표준 Nginx 경로 /blog/images/{blog_id}/{filename}로 저장
            filename = os.path.basename(img_src)
            img_path = f"/blog/images/{blog_id}/{filename}"
            # 중복 제거
            if img_path not in images:
                images.append(img_path)
                
    # 3. 인용구(blockquote) 추출
    quotes = []
    quote_pattern = re.compile(r'<blockquote[^>]*>(.*?)</blockquote>', re.DOTALL)
    for q_content in quote_pattern.findall(body):
        txt = re.sub(r'<[^>]+>', '', q_content).strip()
        if txt and txt not in quotes:
            quotes.append(txt)
            
    return {
        "paragraphs": paragraphs,
        "images": images,
        "quotes": quotes
    }

def get_best_cover_image(blog_id: str, found_images: list) -> str:
    """해당 포스트의 가장 적절한 대표 이미지 선정"""
    img_dir = BLOG_DIR / "images" / blog_id
    if not img_dir.exists():
        return found_images[0] if found_images else ""
        
    candidates = ["title.jpg", "title01.jpg", "cover.jpg", "cover.png", "cover.JPG", "image_1.jpg", "image_1.png", "image_1.JPG"]
    for c in candidates:
        if (img_dir / c).exists():
            return f"/blog/images/{blog_id}/{c}"
            
    if found_images:
        return found_images[0]
        
    return ""

def generate_seo_geo_html(meta: dict, content: dict, blog_id: str) -> str:
    """SEO/GEO 최적화된 새로운 HTML 본문 생성"""
    slug = meta["slug"]
    title = meta["title"]
    date_str = meta["date"]
    
    # GEO 매핑 정보
    map_info = POSTS_METADATA[blog_id]
    primary_area = map_info["primary_area"]
    primary_service = map_info["primary_service"]
    areas = map_info["areas"]
    service_types = map_info["service_types"]
    seo_keywords = map_info["keywords"]
    
    # 대표 이미지 지정
    cover_image = get_best_cover_image(blog_id, content["images"])
    
    # 본문 설명글 생성 (Description)
    desc = f"{' '.join(areas[:2])} {primary_service} 전문업체 {COMPANY_NAME}. {title}. {COMPANY_PHONE} 24시간 긴급 출동."
    
    # 문단 나누기
    paragraphs = content["paragraphs"]
    N = len(paragraphs)
    
    # 최소 문단 개수 보장
    if N < 4:
        paragraphs = paragraphs + ["하수구수사대는 항상 최선을 다해 정확한 원인을 규명하고 해결해 드립니다."] * (4 - N)
        N = len(paragraphs)
        
    sec1_p = paragraphs[:int(N*0.25)]
    sec2_p = paragraphs[int(N*0.25):int(N*0.5)]
    sec3_p = paragraphs[int(N*0.5):int(N*0.9)]
    sec4_p = paragraphs[int(N*0.9):]
    
    # 이미지 분배
    images = [img for img in content["images"] if img != cover_image]
    
    # 문제 상황 이미지
    img_sec1 = f'<div class="image-box"><img src="{images[0]}" alt="{title} 현장 상황" loading="lazy"></div>' if len(images) > 0 else ""
    # 원인 분석 이미지
    img_sec2 = f'<div class="image-box"><img src="{images[1]}" alt="{title} 원인 분석" loading="lazy"></div>' if len(images) > 1 else ""
    
    # 작업 과정 이미지 (최대 4개 활용)
    img_sec3 = ""
    if len(images) > 3:
        img_sec3 = f'''
        <div class="image-grid">
          <img src="{images[2]}" alt="작업 과정 사진 1" loading="lazy">
          <img src="{images[3]}" alt="작업 과정 사진 2" loading="lazy">
        </div>'''
    elif len(images) > 2:
        img_sec3 = f'<div class="image-box"><img src="{images[2]}" alt="작업 과정 사진" loading="lazy"></div>'
        
    # 추가 현장 이미지 그리드
    extra_images = images[4:] if len(images) > 4 else []
    img_sec4 = ""
    if extra_images:
        img_sec4 = '<div class="image-grid">'
        for idx, img in enumerate(extra_images[:4]): # 최대 4개
            img_sec4 += f'<img src="{img}" alt="추가 시공 사진 {idx+1}" loading="lazy">'
        img_sec4 += '</div>'
        
    # 전문가 진단 인용구
    diag_quote = content["quotes"][0] if content["quotes"] else "슬러지와 이물질이 통로를 꽉 막고 있어 배수가 불가능하며, 고압 세척과 샤프트 타격이 동반되어야 완벽한 해결이 가능합니다."
    
    # 예방법 및 주의사항 생성 (서비스 타입별 맞춤형)
    precaution_title = ""
    precaution_list = []
    
    service_joined = " ".join(service_types)
    if "음식물처리기" in service_joined:
        precaution_title = "음식물처리기 올바른 사용법"
        precaution_list = [
            "기름기가 많은 음식(지방류, 육류 비계 등)은 하수구 고착의 주원인이 되므로 투입하지 말아주세요.",
            "부피가 크거나 단단한 채소, 과일 껍질은 잘게 자르거나 일반 쓰레기로 분리해 주세요.",
            "작동 시 충분한 양의 물을 동시에 흘려보내 잘게 갈린 찌꺼기가 배관 끝까지 흘러가게 하세요.",
            "배수가 느려지는 느낌이 들면 화학 세정제에 의존하기보다 내시경 배관 점검을 권장합니다."
        ]
    elif "누수" in service_joined or "방수" in service_joined:
        precaution_title = "베란다 누수 및 방수 관리 방법"
        precaution_list = [
            "비가 많이 올 때 창틀 주변이나 아래층 천장에 얼룩이 생기는지 정기적으로 확인해 보세요.",
            "우수관 주변 실리콘 마감이 들뜨거나 깨진 틈새가 있는지 손상 여부를 수시로 체크하세요.",
            "베란다 바닥 타일의 줄눈(메지)이 소실되면 그 틈으로 물이 침투하여 누수가 유발됩니다.",
            "누수 의심 증상 발견 시 방치하면 아래층 손실이 커지므로 즉시 전문가의 진단을 받으십시오."
        ]
    elif "싱크대" in service_joined:
        precaution_title = "주방 싱크대 배관 막힘 예방 수칙"
        precaution_list = [
            "기름기가 묻은 식기나 프라이팬은 설거지 전 키친타올로 반드시 기름때를 닦아내세요.",
            "주기적으로 싱크대 개수대에 뜨거운 물을 가득 받아 한 번에 내려 배관 내부 기름을 씻어내세요.",
            "배수구 거름망을 미세한 필터로 사용하시고 음식물 찌꺼기가 틈으로 새어 들지 않게 관리하세요.",
            "베이킹소다와 식초를 뜨거운 물과 함께 일주일에 한 번씩 부어주면 배관 살균과 막힘 예방에 좋습니다."
        ]
    else:
        precaution_title = "하수구 배관 막힘 예방 및 관리 가이드"
        precaution_list = [
            "머리카락, 비닐, 물티슈 등 물에 분해되지 않는 이물질은 하수구 유입을 절대 금지해 주세요.",
            "하수구 거름망을 씌우고 모여진 이물질은 주기적으로 쓰레기통에 바로 비워주셔야 합니다.",
            "배관 노후가 심할 경우 이물질이 더 쉽게 걸리므로 주기적인 배관 세척(고압세척 등)을 권장합니다.",
            "작업 후 1년 이내 재발 시 하수구수사대에서 무상 A/S 보증 서비스를 제공합니다."
        ]
        
    precaution_html = "".join([f'<li style="margin-bottom: 8px;">✅ {item}</li>' for item in precaution_list])
    
    # FAQ 리스트 생성
    faq_items = [
        {
            "q": f"{primary_area} {primary_service} 비용은 얼마인가요?",
            "a": f"현장 상태와 배관 막힘의 원인에 따라 다릅니다. 단순 점검 및 통수는 5만원~15만원 선이며, 고압 세척이나 방수/교체 공사 등은 15만원~50만원 이상이 발생할 수 있습니다. 방문 후 상세 견적을 투명하게 안내해 드립니다."
        },
        {
            "q": f"{primary_area} 지역 출동 시간은 얼마나 걸리나요?",
            "a": f"{COMPANY_NAME}은 서울, 경기, 인천 전 지역에 24시간 긴급 대기 중입니다. {primary_area} 지역은 연락 주시면 평균 30분에서 1시간 이내에 신속하게 현장에 도착합니다."
        },
        {
            "q": "작업 후 사후 관리나 A/S 보증이 되나요?",
            "a": f"네, 저희 {COMPANY_NAME}은 확실한 시공을 약속드리며, 작업 완료 후 동일 부위에서 1년 내에 다시 막히거나 누수가 재발할 경우 100% 무상 A/S를 제공해 드립니다."
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
    
    # 지역 리스트 생성 (Schema.org LocalBusiness 용)
    area_served_entries = []
    for a in areas[:5]:
        area_served_entries.append(f'{{"@type": "City", "name": "{a}"}}')
    area_served_schema = ",\n      ".join(area_served_entries)
    
    # 서비스 리스트
    service_type_schema = ", ".join([f'"{s}"' for s in service_types])
    
    # 태그 HTML 생성
    tag_html = "\n".join([f"      <span>#{tag}</span>" for tag in seo_keywords])

    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | {COMPANY_NAME}</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{', '.join(seo_keywords)}">
  <link rel="canonical" href="{DOMAIN}/blog/{slug}.html">

  <!-- Open Graph -->
  <meta property="og:title" content="{title} | {COMPANY_NAME}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{cover_image}">
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
    "datePublished": "{format_date(date_str)}",
    "dateModified": "{datetime.now().strftime('%Y-%m-%d')}",
    "image": "{cover_image}",
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
  <link rel="icon" type="image/png" sizes="32x32" href="/images/logo.png">
</head>
<body>

<div class="container">

  <!-- 브레드크럼 -->
  <div class="breadcrumb">
    <a href="/">홈</a> &gt; <a href="/blog/index.html">시공사례</a> &gt; <span>{primary_area} {primary_service}</span>
  </div>

  <!-- 헤더 -->
  <div class="header">
    <h1>🏠 {title}</h1>
    <p>{primary_area} {primary_service} 전문 시공 후기</p>
  </div>

  <!-- 메타 정보 -->
  <div class="meta">
    📅 시공일: {date_str} | 📍 현장: {areas[0]} | 🏢 {COMPANY_NAME} | 🔄 업데이트: {datetime.now().strftime('%Y-%m-%d')}
  </div>

  <!-- 대표 이미지 -->
  {f'<div class="image-box"><img src="{cover_image}" alt="{title} 대표 이미지"><div class="caption">{primary_area} {primary_service} 현장</div></div>' if cover_image else ''}

  <!-- 작업 개요 -->
  <div class="section">
    <h2>📋 작업 개요</h2>
    <ul style="padding-left: 20px;">
      <li style="margin-bottom: 8px;"><strong>위치:</strong> {", ".join(areas[:3])}</li>
      <li style="margin-bottom: 8px;"><strong>서비스 유형:</strong> {", ".join(service_types)}</li>
      <li style="margin-bottom: 8px;"><strong>작업 일시:</strong> {date_str}</li>
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
    return html_content

def update_json_metadata(blog_id: str, slug: str) -> dict:
    """JSON 파일을 새 slug와 html_file 경로로 갱신"""
    json_path = BLOG_DIR / f"{blog_id}.json"
    if not json_path.exists():
        return {}
        
    with open(json_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
        
    meta["html_file"] = f"{slug}.html"
    meta["slug"] = slug
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        
    return meta

def rebuild_sitemap(posts: list):
    """sitemap.xml을 최신 상태로 처음부터 안전하게 다시 구축"""
    print("🕸️ sitemap.xml 재구축 중...")
    
    sitemap_entries = [f'''  <!-- 메인 페이지 -->
  <url>
    <loc>{DOMAIN}/</loc>
    <lastmod>2026-06-16</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
    <image:image>
      <image:loc>{DOMAIN}/images/Top_Bg_2.png</image:loc>
      <image:title>하수구수사대 배관케어 전문업체 메인</image:title>
      <image:caption>하수구수사대 - 하수구막힘, 누수탐지, 고압세척 전문업체</image:caption>
    </image:image>
    <image:image>
      <image:loc>{DOMAIN}/images/logo.png</image:loc>
      <image:title>하수구수사대 로고</image:title>
      <image:caption>하수구수사대 공식 로고</image:caption>
    </image:image>
  </url>
  
  <!-- 블로그 목록 페이지 -->
  <url>
    <loc>{DOMAIN}/blog/index.html</loc>
    <lastmod>2026-06-16</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>''']
  
    for p in posts:
        blog_id = p["log_no"]
        slug = POSTS_METADATA[blog_id]["slug"]
        date_str = format_date(p["date"])
        title = p["title"]
        cover_image = get_best_cover_image(blog_id, [])
        
        image_block = ""
        if cover_image:
            img_url = f"{DOMAIN}{cover_image}"
            image_block = f'''    <image:image>
      <image:loc>{img_url}</image:loc>
      <image:title>{title}</image:title>
      <image:caption>{COMPANY_NAME} 시공사례 - {title}</image:caption>
    </image:image>'''
            
        entry = f'''
  <!-- 시공사례: {title} -->
  <url>
    <loc>{DOMAIN}/blog/{slug}.html</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
{image_block}
  </url>'''
        sitemap_entries.append(entry)
        
    sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
{"".join(sitemap_entries)}
</urlset>
'''
    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    print("  ✅ sitemap.xml 재구축 완료!")

def rebuild_robots():
    """robots.txt 파일 생성/갱신"""
    print("🤖 robots.txt 갱신 중...")
    robots_content = f'''User-agent: *
Allow: /
Disallow: /index_files/

Sitemap: {DOMAIN}/sitemap.xml
'''
    with open(ROBOTS_FILE, 'w', encoding='utf-8') as f:
        f.write(robots_content)
    print("  ✅ robots.txt 갱신 완료!")

def update_blog_index(posts: list):
    """블로그 목록 페이지(blog/index.html)를 갱신"""
    print("📋 blog/index.html 갱신 중...")
    
    # 카드 HTML 생성
    cards_html = ""
    for p in posts:
        blog_id = p["log_no"]
        slug = POSTS_METADATA[blog_id]["slug"]
        cover = get_best_cover_image(blog_id, [])
        cover_html = (
            f'<div class="card-img"><img src="{cover}" alt="{p["title"]}" loading="lazy"></div>'
            if cover else
            '<div class="card-img card-img-placeholder">🔧</div>'
        )
        
        # 날짜 정제
        date_clean = p.get('date', '')
        
        cards_html += f"""
        <article class="post-card" onclick="location.href='{slug}.html'" role="button" tabindex="0">
            {cover_html}
            <div class="card-body">
                {"" if not p.get("category") else f'<span class="card-badge">{p["category"]}</span>'}
                <h2 class="card-title">{p['title']}</h2>
                <p class="card-desc">{p.get('description', '')[:80]}{"..." if len(p.get("description","")) > 80 else ""}</p>
                <div class="card-meta">
                    <span>📅 {date_clean}</span>
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
    index_path = BLOG_DIR / "index.html"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("  ✅ blog/index.html 갱신 완료!")

def main():
    print(f"🚀 블로그 SEO/GEO 일괄 최적화 및 갱신 프로세스 시작")
    print(f"   작업 경로: {BLOG_DIR}")
    
    posts = []
    
    # 1. 각 블로그 포스트 데이터 로드 및 새 HTML 생성
    for blog_id, map_info in POSTS_METADATA.items():
        json_path = BLOG_DIR / f"{blog_id}.json"
        if not json_path.exists():
            print(f"⚠️ 경고: {json_path}가 존재하지 않습니다. 건너뜁니다.")
            continue
            
        # JSON 갱신
        slug = map_info["slug"]
        meta = update_json_metadata(blog_id, slug)
        posts.append(meta)
        
        # 본문 파싱
        content = parse_original_content(blog_id)
        
        # 새 SEO/GEO HTML 생성
        new_html = generate_seo_geo_html(meta, content, blog_id)
        
        # 파일 저장
        output_file = BLOG_DIR / f"{slug}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(new_html)
            
        print(f"  ✨ {blog_id} -> blog/{slug}.html 생성 완료")
        
    # 날짜 역순 정렬
    posts.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # 2. blog/index.html 갱신
    update_blog_index(posts)
    
    # 3. sitemap.xml 갱신
    rebuild_sitemap(posts)
    
    # 4. robots.txt 갱신
    rebuild_robots()
    
    print(f"🎉 모든 작업이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()
