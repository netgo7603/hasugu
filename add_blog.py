#!/usr/bin/env python3
"""
하수구수사대 블로그 크롤링 & 배포 파이프라인
사용법: python3 add_blog.py <네이버블로그URL> [옵션]
예시: python3 add_blog.py https://m.blog.naver.com/hasugu2118/224300839005
"""

import sys
import os
import re
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ============================================================
# 설정
# ============================================================
PROJECT_DIR = Path("/Users/lee/projects/hasugu")
BLOG_DIR = PROJECT_DIR / "blog"
IMAGES_DIR = BLOG_DIR / "images"
SITEMAP_FILE = PROJECT_DIR / "sitemap.xml"
DOMAIN = "https://lymin80.shop"

COMPANY_NAME = "하수구수사대"
COMPANY_PHONE = "010-5615-2118"
SERVICE_AREAS = ["서울", "경기도", "인천"]
NAVER_BLOG_BASE = "https://m.blog.naver.com"

# ============================================================
# 1. URL에서 블로그 ID 추출
# ============================================================
def extract_blog_id(url: str) -> str:
    """URL에서 블로그 포스트 ID 추출"""
    # https://m.blog.naver.com/hasugu2118/224300839005 → 224300839005
    # https://blog.naver.com/hasugu2118/224300839005 → 224300839005
    match = re.search(r'/(\d+)/?$', url)
    if match:
        return match.group(1)
    raise ValueError(f"블로그 ID를 추출할 수 없습니다: {url}")

def extract_blog_author(url: str) -> str:
    """URL에서 블로그 작성자 ID 추출"""
    match = re.search(r'naver\.com/([^/]+)/\d', url)
    if match:
        return match.group(1)
    return "hasugu2118"

# ============================================================
# 2. web_extract로 블로그 콘텐츠 크롤링
# ============================================================
def crawl_blog(url: str) -> dict:
    """web_extract를 사용하여 블로그 콘텐츠 크롤링"""
    print(f"📡 크롤링 시작: {url}")
    
    # web_extract는 도구 호출이므로, 여기서는 curl로 대체
    # 실제 환경에서는 Hermes web_extract 도구 사용
    result = subprocess.run(
        ["python3", "-c", f"""
import sys
sys.path.insert(0, '/Users/lee/.hermes/scripts')
try:
    from hermes_tools import web_extract
    result = web_extract(['{url}'])
    print(json.dumps(result))
except ImportError:
    # fallback: 직접 HTTP 요청
    import urllib.request
    req = urllib.request.Request('{url}', headers={{
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.read().decode('utf-8'))
"""],
        capture_output=True, text=True, timeout=60
    )
    
    if result.returncode != 0:
        print(f"⚠️ 크롤링 실패: {result.stderr[:200]}")
        return None
    
    return result.stdout

# ============================================================
# 3. HTML 파싱하여 메타데이터 추출
# ============================================================
def parse_blog_content(raw_text: str, url: str, blog_id: str) -> dict:
    """크롤링한 텍스트에서 메타데이터 추출"""
    
    # 제목 추출
    title_match = re.search(r'제목[:\s]+(.+)', raw_text) or re.search(r'^#\s+(.+)', raw_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else f"시공사례 {blog_id}"
    
    # 날짜 추출
    date_match = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', raw_text)
    if date_match:
        date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    # 지역 추출 (용인, 수지구, 풍덕천동 등)
    area_patterns = [
        r'([가-힣]+시)\s+([가-힣]+구)\s+([가-힣]+동)',
        r'([가-힣]+구)\s+([가-힣]+동)',
        r'([가-힣]+시)\s+([가-힣]+동)',
        r'([가-힣]+동)',
    ]
    
    areas = []
    for pattern in area_patterns:
        matches = re.findall(pattern, raw_text)
        for match in matches:
            if isinstance(match, tuple):
                areas.extend([m for m in match if len(m) > 1])
            else:
                areas.append(match)
    
    # 중복 제거 및 정리
    areas = list(dict.fromkeys(areas))
    primary_area = areas[0] if areas else "수원"
    
    # 서비스 유형 감지
    service_types = []
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
    
    for service, keywords in service_keywords.items():
        for kw in keywords:
            if kw in raw_text:
                service_types.append(service)
                break
    
    service_types = list(dict.fromkeys(service_types))
    primary_service = service_types[0] if service_types else "배관막힘"
    
    # 본문 텍스트 정리
    # 불필요한 줄 제거
    lines = raw_text.split('\n')
    clean_lines = []
    skip_patterns = [
        r'^📌', r'^Source:', r'^Date:', r'^Author:', r'^---',
        r'^##', r'^#', r'^\*\*', r'^\*', r'^```',
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        skip = False
        for pattern in skip_patterns:
            if re.match(pattern, line):
                skip = True
                break
        if not skip:
            clean_lines.append(line)
    
    body_text = '\n'.join(clean_lines)
    
    # 태그 추출
    tag_matches = re.findall(r'#([가-힣a-zA-Z0-9_]+)', raw_text)
    tags = list(dict.fromkeys(tag_matches))
    
    return {
        "blog_id": blog_id,
        "url": url,
        "title": title,
        "date": date_str,
        "areas": areas,
        "primary_area": primary_area,
        "service_types": service_types,
        "primary_service": primary_service,
        "body_text": body_text,
        "tags": tags,
        "slug": f"{primary_area}-{primary_service}-{blog_id}",
    }

# ============================================================
# 4. SEO/GEO 최적화 HTML 생성
# ============================================================
def generate_seo_html(meta: dict) -> str:
    """SEO/GEO 최적화된 HTML 생성"""
    
    slug = meta["slug"]
    title = meta["title"]
    date = meta["date"]
    areas = meta["areas"]
    primary_area = meta["primary_area"]
    service_types = meta["service_types"]
    primary_service = meta["primary_service"]
    body_text = meta["body_text"]
    tags = meta["tags"]
    blog_id = meta["blog_id"]
    
    # SEO 키워드 생성
    seo_keywords = [
        f"{primary_area} {primary_service}",
        f"{' '.join(areas[:2])} {primary_service}",
        f"{primary_area} 배관",
        f"{primary_area} 하수구",
        f"{' '.join(areas[:2])} 배관 전문",
        f"{primary_service} 전문업체",
    ] + [f"{area} {primary_service}" for area in areas[:3]]
    seo_keywords = list(dict.fromkeys(seo_keywords))
    
    # description 생성
    desc = f"{' '.join(areas[:2])} {primary_service} 전문업체 {COMPANY_NAME}. {title}. {COMPANY_PHONE} 24시간 긴급 출동."
    
    # 본문을 섹션으로 분할
    sections = split_into_sections(body_text, areas, service_types)
    
    # 이미지 경로 (블로그 ID별 폴더)
    img_prefix = f"/blog/images/{blog_id}"
    
    # FAQ 생성 (GEO 최적화)
    faqs = generate_faqs(meta, areas, service_types)
    
    # 태그 HTML
    tag_html = '\n'.join([f'      <span>#{tag}</span>' for tag in tags]) if tags else ''
    
    # 이전글 / 다음글 링크 체크 및 계산 (posts.json 활용)
    prev_nav_html = '<div style="visibility: hidden;"></div>'
    next_nav_html = '<div style="visibility: hidden;"></div>'
    
    posts_json_path = BLOG_DIR / "posts.json"
    if posts_json_path.exists():
        try:
            with open(posts_json_path, 'r', encoding='utf-8') as f:
                all_posts = json.load(f)
            if all_posts:
                # 가장 최신 포스트(첫 번째)를 이전 포스트로 연결
                latest_p = all_posts[0]
                prev_nav_html = f'''<a href="{latest_p['slug']}" class="nav-card">
      <span class="nav-label">◀ 이전 시공사례</span>
      <span class="nav-title">{latest_p['title']}</span>
    </a>'''
    area_keyword = ' '.join(areas[:2]) if areas else primary_area

    html = f'''<!DOCTYPE html>


<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | {COMPANY_NAME}</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{', '.join(seo_keywords)}">
  <link rel="canonical" href="{DOMAIN}/blog/{slug}">

  <!-- Open Graph -->
  <meta property="og:title" content="{title} | {COMPANY_NAME}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{img_prefix}/title.jpg">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{DOMAIN}/blog/{slug}">

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
    "datePublished": "{date}",
    "dateModified": "{datetime.now().strftime('%Y-%m-%d')}",
    "image": "{img_prefix}/title.jpg",
    "publisher": {{
      "@type": "Organization",
      "name": "{COMPANY_NAME}"
    }},
    "mainEntityOfPage": {{
      "@type": "WebPage",
      "@id": "{DOMAIN}/blog/{slug}"
    }}
  }}
  </script>

  <!-- Schema.org: FAQ -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
{faqs['schema']}
    ]
  }}
  </script>

  <!-- Schema.org: LocalBusiness -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "{COMPANY_NAME}",
    "description": "{area_keyword} {primary_service} 전문업체",
    "telephone": "{COMPANY_PHONE}",
    "areaServed": [{', '.join([f'{{"@type": "City", "name": "{a}"}}' for a in areas[:5]])}],
    "serviceType": [{', '.join([f'"{s}"' for s in service_types])}],
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
    .prev-next-nav {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 30px 0; }}
    .nav-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; text-decoration: none; color: #333; transition: all 0.2s ease; display: flex; flex-direction: column; }}
    .nav-card:hover {{ border-color: #2980b9; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(41,128,185,0.15); }}
    .nav-card .nav-label {{ font-size: 13px; color: #2980b9; font-weight: bold; margin-bottom: 6px; }}
    .nav-card .nav-title {{ font-size: 15px; font-weight: 600; line-height: 1.4; color: #1a5276; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }}
    .footer {{ text-align: center; padding: 20px; color: #888; font-size: 13px; }}
    .breadcrumb {{ font-size: 14px; color: #888; margin-bottom: 15px; }}
    .breadcrumb a {{ color: #2980b9; text-decoration: none; }}
    @media (max-width: 600px) {{
      .container {{ padding: 10px; }}
      .header h1 {{ font-size: 22px; }}
      .section {{ padding: 20px; }}
      .image-grid {{ grid-template-columns: 1fr; }}
      .cta .phone {{ font-size: 26px; }}
      .prev-next-nav {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>

<div class="container">

  <!-- 브레드크럼 -->
  <div class="breadcrumb">
    <a href="/">홈</a> &gt; <a href="/blog/">시공사례</a> &gt; <span>{primary_area} {primary_service}</span>
  </div>

  <!-- 헤더 -->
  <div class="header">
    <h1>🏠 {title}</h1>
    <p>{area_keyword} {primary_service} 전문업체 시공 사례</p>
  </div>

  <!-- 메타 정보 -->
  <div class="meta">
    📅 작성일: {date} | 📍 현장: {' '.join(areas[:3])} | 🏢 {COMPANY_NAME} | 🔄 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d')}
  </div>

  <!-- 타이틀 이미지 -->
  <div class="image-box">
    <img src="{img_prefix}/title.jpg" alt="{title} 현장 사진" onerror="this.style.display='none'">
    <div class="caption">{' '.join(areas[:2])} {primary_service} 현장</div>
  </div>

  <!-- 작업 개요 -->
  <div class="section">
    <h2>📋 작업 개요</h2>
    <ul style="padding-left: 20px;">
      <li style="margin-bottom: 8px;"><strong>위치:</strong> {' '.join(areas[:3])}</li>
      <li style="margin-bottom: 8px;"><strong>서비스:</strong> {', '.join(service_types)}</li>
      <li style="margin-bottom: 8px;"><strong>작업일:</strong> {date}</li>
      <li style="margin-bottom: 8px;"><strong>업체:</strong> {COMPANY_NAME}</li>
    </ul>
  </div>

  <!-- 본문 섹션 -->
{sections['html']}

  <!-- FAQ -->
  <div class="section">
    <h2>❓ 자주 묻는 질문 (FAQ)</h2>
{faqs['html']}
  </div>

  <!-- CTA -->
  <div class="cta">
    <h3>🚨 {primary_area} {primary_service} 문제로 고민이신가요?</h3>
    <p>정확한 원인 진단과 확실한 시공으로 재발 없는 해결을 약속드립니다.</p>
    <div class="phone">📞 {COMPANY_PHONE}</div>
    <p>24시간 긴급 출동 | {' / '.join(SERVICE_AREAS)} 전지역 | 1년 내 재발 시 무상 A/S</p>
  </div>

  <!-- 태그 -->
  <div class="section">
    <div class="tag-list">
{tag_html}
    </div>
  </div>

  <!-- 이전글 / 다음글 네비게이션 -->
  <div class="prev-next-nav">
    {prev_nav_html}
    {next_nav_html}
  </div>

  <!-- 푸터 -->
  <div class="footer">
    <p>© {datetime.now().year} {COMPANY_NAME}. All rights reserved.</p>
    <p>본 콘텐츠는 실제 현장 작업 사례를 기반으로 작성되었습니다.</p>
    <p>마지막 업데이트: {datetime.now().strftime('%Y년 %m월 %d일')}</p>
  </div>

</div>

</body>
</html>'''
    
    return html


def split_into_sections(body_text: str, areas: list, service_types: list) -> dict:
    """본문 텍스트를 섹션으로 분할하여 HTML 생성"""
    
    lines = body_text.split('\n')
    sections_html = []
    current_section = []
    section_count = 0
    
    # 주요 섹션 키워드
    section_keywords = {
        "문제 상황": ["문제", "상황", "증상", "발생", "연락", "출동", "다급"],
        "원인 분석": ["원인", "분석", "확인", "발견", "상태", "손상", "노후", "막힘"],
        "작업 과정": ["작업", "과정", "단계", "시작", "진행", "설치", "철거", "정리", "밀봉", "형성"],
        "작업 완료": ["완료", "테스트", "배수", "확인", "만족", "안심", "해결"],
        "주의사항": ["주의", "주의사항", "예방", "관리", "사용", "습관", "정기"],
        "핵심 정리": ["핵심", "정리", "요약", "핵심 조언", "조언", "인사이트"],
    }
    
    current_heading = "현장 후기"
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        # 섹션 키워드 감지
        new_heading = None
        for heading, keywords in section_keywords.items():
            for kw in keywords:
                if kw in line and len(line) < 30:
                    new_heading = heading
                    break
            if new_heading:
                break
        
        if new_heading and new_heading != current_heading:
            # 이전 섹션 저장
            if current_section:
                section_count += 1
                sections_html.append(f'''
  <div class="section">
    <h2>{'🔍' if section_count == 1 else '🔧' if section_count == 2 else '✅'} {current_heading}</h2>
    {''.join([f'<p>{l}</p>' for l in current_section])}
  </div>''')
            current_heading = new_heading
            current_section = []
        else:
            current_section.append(line)
    
    # 마지막 섹션 저장
    if current_section:
        section_count += 1
        sections_html.append(f'''
  <div class="section">
    <h2>{'🔍' if section_count == 1 else '🔧' if section_count == 2 else '✅'} {current_heading}</h2>
    {''.join([f'<p>{l}</p>' for l in current_section])}
  </div>''')
    
    # 섹션이 없으면 전체를 하나로
    if not sections_html:
        sections_html.append(f'''
  <div class="section">
    <h2>🔍 현장 후기</h2>
    {''.join([f'<p>{l}</p>' for l in lines if l.strip()])}
  </div>''')
    
    return {
        'html': '\n'.join(sections_html)
    }

def generate_faqs(meta: dict, areas: list, service_types: list) -> dict:
    """FAQ 생성 (SEO/GEO 최적화)"""
    
    primary_area = meta['primary_area']
    primary_service = meta['primary_service']
    area_keyword = ' '.join(areas[:2]) if areas else primary_area
    
    faq_list = [
        {
            "q": f"{primary_area} {primary_service} 비용은 얼마인가요?",
            "a": f"현장 상태에 따라 다릅니다. 단순 점검은 5만원~10만원, 본격적인 작업은 15만원~50만원이 일반적입니다. 정확한 비용은 무료 방문 견적 후 안내드립니다. ({datetime.now().year}년 기준)"
        },
        {
            "q": f"{area_keyword}에서 {primary_service} 서비스 가능한가요?",
            "a": f"네, 가능합니다. {COMPANY_NAME}은 {' / '.join(SERVICE_AREAS)} 전지역에서 24시간 긴급 출동 서비스를 제공합니다. {area_keyword} 지역은 평균 30분 내 도착합니다."
        },
        {
            "q": f"{primary_service} 작업 후 재발 방지 방법은?",
            "a": f"정기적인 배관 점검과 올바른 사용 습관이 가장 중요합니다. {COMPANY_NAME}은 작업 후 1년 내 재발 시 무상 A/S를 제공하며, 정기 점검 프로그램도 운영하고 있습니다."
        },
    ]
    
    # 서비스별 추가 FAQ
    if "음식물처리기" in service_types:
        faq_list.append({
            "q": "음식물처리기 사용 시 배관 막힘을 예방하는 방법은?",
            "a": "① 기름기가 많은 음식은 피하기 ② 한 번에 많은 양 투입하지 않기 ③ 충분한 물과 함께 사용하기 ④ 정기적으로 베이킹소다+식초로 배관 세척하기"
        })
    
    if "누수" in ' '.join(service_types) or "방수" in ' '.join(service_types):
        faq_list.append({
            "q": "비 올 때만 누수가 생기면 어떤 문제인가요?",
            "a": "우수관 주변 마감 노후, 방수층 손상, 배관 연결부 밀봉 불량 등이 주요 원인입니다. 정확한 원인 진단을 위해 전문 업체 방문 점검을 권장합니다."
        })
    
    # Schema JSON
    schema_entries = []
    for faq in faq_list:
        schema_entries.append(f'''      {{
        "@type": "Question",
        "name": "{faq['q']}",
        "acceptedAnswer": {{
          "@type": "Answer",
          "text": "{faq['a']}"
        }}
      }}''')
    
    # HTML
    html_entries = []
    for faq in faq_list:
        html_entries.append(f'''    <div class="faq-item">
      <div class="question">Q. {faq['q']}</div>
      <div class="answer">A. {faq['a']}</div>
    </div>''')
    
    return {
        'schema': ',\n'.join(schema_entries),
        'html': '\n'.join(html_entries)
    }

# ============================================================
# 5. 이미지 다운로드
# ============================================================
def download_images(blog_id: str, image_urls: list) -> list:
    """이미지 다운로드"""
    
    save_dir = IMAGES_DIR / blog_id
    save_dir.mkdir(parents=True, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://m.blog.naver.com/'
    }
    
    downloaded = []
    
    for i, url in enumerate(image_urls):
        # 파일명 결정
        if i == 0:
            filename = "title.jpg"
        else:
            filename = f"img{i+1}.jpg"
        
        filepath = save_dir / filename
        
        # 이미 존재하면 스킵
        if filepath.exists() and filepath.stat().st_size > 1000:
            print(f"  ⏭️  이미 존재: {filename}")
            downloaded.append(filename)
            continue
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if len(data) < 500:  # 너무 작으면 에러 페이지
                    continue
                with open(filepath, 'wb') as f:
                    f.write(data)
                size_kb = len(data) / 1024
                print(f"  ✅ {filename}: {size_kb:.1f}KB")
                downloaded.append(filename)
        except Exception as e:
            print(f"  ❌ {filename}: {e}")
    
    return downloaded

# ============================================================
# 6. sitemap.xml 갱신
# ============================================================
def update_sitemap(meta: dict, image_files: list):
    """sitemap.xml에 새 URL 추가"""
    
    slug = meta['slug']
    blog_id = meta['blog_id']
    date = meta['date']
    title = meta['title']
    
    # 기존 sitemap 읽기
    if SITEMAP_FILE.exists():
        with open(SITEMAP_FILE, 'r', encoding='utf-8') as f:
            sitemap_content = f.read()
    else:
        sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
</urlset>'''
    
    # 이미 존재하는지 확인
    if f"/blog/{slug}" in sitemap_content or f"/blog/{slug}.html" in sitemap_content:
        print(f"  ⏭️  sitemap에 이미 존재: {slug}")
        return
    
    # 이미지 엔트리
    image_entries = []
    for img_file in image_files[:5]:  # 최대 5개
        img_url = f"{DOMAIN}/blog/images/{blog_id}/{img_file}"
        image_entries.append(f'''    <image:image>
      <image:loc>{img_url}</image:loc>
      <image:title>{title}</image:title>
      <image:caption>{COMPANY_NAME} 시공사례 - {title}</image:caption>
    </image:image>''')
    
    image_block = '\n'.join(image_entries) if image_entries else ''
    
    # 새 URL 엔트리
    new_entry = f'''
  <!-- 시공사례: {title} -->
  <url>
    <loc>{DOMAIN}/blog/{slug}</loc>
    <lastmod>{date}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
{image_block}
  </url>'''
    
    # </urlset> 앞에 삽입
    sitemap_content = sitemap_content.replace('</urlset>', f'{new_entry}\n</urlset>')
    
    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    
    print(f"  ✅ sitemap.xml 갱신: /blog/{slug}")

    # RSS 갱신
    update_rss(slug, title, meta.get('description', title), date)

def update_rss(slug: str, title: str, desc: str, date: str):
    """rss.xml에 신규 포스트 삽입"""
    rss_file = PROJECT_DIR / "rss.xml"
    if not rss_file.exists():
        return

    try:
        with open(rss_file, 'r', encoding='utf-8') as f:
            content = f.read()

        link = f"{DOMAIN}/blog/{slug}"

        escaped_title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        escaped_desc = desc.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        new_item = f'''    <item>
      <title>{escaped_title}</title>
      <link>{link}</link>
      <description>{escaped_desc}</description>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{date}</pubDate>
    </item>'''

        if link not in content:
            content = content.replace('<channel>', f'<channel>\n{new_item}')
            with open(rss_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ rss.xml 갱신: /blog/{slug}")
    except Exception as e:
        print(f"  ⚠️ rss.xml 갱신 중 에러: {e}")


# ============================================================
# 7. Docker 배포
# ============================================================
def deploy_to_docker():
    """Docker 컨테이너에 파일 복사"""
    
    print("🐳 Docker 배포 중...")
    
    commands = [
        # blog 폴더 전체 복사
        f"docker cp {BLOG_DIR}/. memo-app:/usr/share/nginx/html/blog/",
        # nginx 리로드
        "docker exec memo-app nginx -s reload",
    ]
    
    for cmd in commands:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  ⚠️ 명령 실패: {cmd}")
            print(f"  에러: {result.stderr[:200]}")
        else:
            print(f"  ✅ {cmd[:60]}...")
    
 