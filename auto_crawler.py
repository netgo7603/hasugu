#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 RSS 피드를 주기적으로 조회하여
새로 작성된 블로그 글이 있으면 blog_crawler.py를 실행하여 자동으로 크롤링하고,
로컬 빌드 후 Docker 컨테이너(Nginx)로 배포하는 자동화 스크립트입니다.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import subprocess
from datetime import datetime

# ============================================================
# 설정
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = os.path.join(BASE_DIR, "blog")
RSS_URL = "https://rss.blog.naver.com/hasugu80.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ============================================================
# 1. RSS 피드 읽어오기
# ============================================================
def fetch_rss(url):
    print(f"📡 RSS 피드 가져오는 중: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"❌ [오류] RSS 피드 요청 실패: {e}")
        return None

# ============================================================
# 2. RSS XML 파싱하여 포스트 목록 추출
# ============================================================
def parse_rss_items(xml_data):
    if not xml_data:
        return []
    
    try:
        # UTF-8 디코딩 처리 (일부 특수문자나 인코딩 문제를 방지하기 위해 bytes 그대로 ET.fromstring에 입력하거나 string으로 디코딩)
        # XML 상단에 encoding="utf-8" 선언이 있으므로 bytes 전달이 권장됨
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"❌ [오류] XML 파싱 실패: {e}")
        return []
    
    items = []
    # RSS 2.0 표준 경로인 channel/item 탐색
    for item in root.findall(".//item"):
        title_elem = item.find("title")
        link_elem = item.find("link")
        guid_elem = item.find("guid")
        pub_date_elem = item.find("pubDate")
        
        title = title_elem.text if title_elem is not None else ""
        link = ""
        if link_elem is not None and link_elem.text:
            link = link_elem.text
        elif guid_elem is not None and guid_elem.text:
            link = guid_elem.text
            
        pub_date = pub_date_elem.text if pub_date_elem is not None else ""
        
        # link에서 log_no 추출
        log_no = ""
        if link:
            # 1. 경로 상의 포스트 번호 검색 (예: blog.naver.com/hasugu80/224013046491?fromRss=true)
            path_match = re.search(r'blog\.naver\.com/[a-zA-Z0-9_-]+/(\d+)', link)
            if path_match:
                log_no = path_match.group(1)
            else:
                # 2. 쿼리 파라미터 logNo=... 검색
                query_match = re.search(r'[?&]logNo=(\d+)', link)
                if query_match:
                    log_no = query_match.group(1)
                else:
                    # 3. 마지막 숫자 시퀀스 추출 시도
                    digits = re.findall(r'\d+', link)
                    if digits:
                        log_no = digits[-1]
        
        
        if log_no:
            items.append({
                "title": title,
                "link": link,
                "log_no": log_no,
                "pub_date": pub_date
            })
            
    return items

# ============================================================
# 3. Docker 배포
# ============================================================
def deploy_to_docker():
    print("\n🐳 Docker 배포 중...")
    sitemap_path = os.path.join(BASE_DIR, "sitemap.xml")
    robots_path = os.path.join(BASE_DIR, "robots.txt")
    
    commands = [
        # blog 폴더 전체를 컨테이너 내 Nginx 경로로 복사
        f"docker cp {BLOG_DIR}/. memo-app:/usr/share/nginx/html/blog/",
        # sitemap.xml 복사
        f"docker cp {sitemap_path} memo-app:/usr/share/nginx/html/",
        # robots.txt 복사
        f"docker cp {robots_path} memo-app:/usr/share/nginx/html/",
        # nginx 설정 재적용
        "docker exec memo-app nginx -s reload"
    ]
    
    success = True
    for cmd in commands:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠️ 명령 실패: {cmd}")
            print(f"  에러: {result.stderr.strip()[:200]}")
            success = False
        else:
            print(f"  ✅ {cmd[:50]}... 성공")
            
    return success

# ============================================================
# 메인 제어 루프
# ============================================================
def main():
    # RSS URL을 인자로 넘겨받았는지 확인 (없으면 기본값 RSS_URL 사용)
    rss_url = RSS_URL
    if len(sys.argv) > 1 and (sys.argv[1].startswith("http://") or sys.argv[1].startswith("https://")):
        rss_url = sys.argv[1].strip()
        print(f"ℹ️ 커스텀 RSS URL이 입력되었습니다: {rss_url}")
        
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 블로그 자동화 스크립트 실행 시작 (대상 RSS: {rss_url})")
    
    # RSS 피드 가져오기
    xml_data = fetch_rss(rss_url)
    posts = parse_rss_items(xml_data)
    
    if not posts:
        print("ℹ️ 가져온 포스트가 없거나 RSS 파싱에 실패했습니다.")
        return
        
    print(f"📝 RSS 피드에서 총 {len(posts)}개의 포스트 발견")
    
    new_crawled_count = 0
    
    for i, post in enumerate(posts, 1):
        log_no = post["log_no"]
        title = post["title"]
        
        # 이미 크롤링되었는지 확인 (blog/{log_no}.json 파일 검사)
        json_path = os.path.join(BLOG_DIR, f"{log_no}.json")
        
        if os.path.exists(json_path):
            print(f"[{i}/{len(posts)}]  ⏭️  이미 크롤링됨: {title} (log_no: {log_no})")
            continue
            
        # 새 포스트 발견 시 크롤러 실행
        print(f"[{i}/{len(posts)}] 🚀 새 포스트 발견! 크롤링 시작: {title} (log_no: {log_no})")
        
        crawler_script = os.path.join(BASE_DIR, "blog_crawler.py")
        cmd = ["python3", crawler_script, post["link"]]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"      ✅ 크롤링 성공")
            new_crawled_count += 1
        else:
            print(f"      ❌ 크롤링 실패 (Exit Code: {result.returncode})")
            print(f"      에러 로그: {result.stderr.strip()[:500]}")
            
    # 새로 크롤링한 포스트가 있다면 최적화 및 배포
    if new_crawled_count > 0:
        print(f"\n🎉 {new_crawled_count}개의 새로운 포스트가 추가되었습니다.")
        
        # 1. SEO/GEO 복구 및 사이트맵/목록 갱신 스크립트 실행
        print("\n🔄 SEO/GEO 최적화 및 사이트맵/목록 페이지 갱신 중...")
        seo_script = os.path.join(BASE_DIR, "process_seo_geo_all.py")
        seo_result = subprocess.run(["python3", seo_script], capture_output=True, text=True)
        if seo_result.returncode == 0:
            print("  ✅ SEO/GEO 최적화 및 사이트맵 갱신 완료!")
        else:
            print("  ❌ [오류] SEO/GEO 최적화 실패")
            print(seo_result.stderr)
            
        # 2. Docker 배포 수행
        deploy_to_docker()
    else:
        print("\n✨ 새로운 포스트가 없습니다. 최적화 및 배포 단계를 생략합니다.")
        
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 자동화 스크립트 실행 종료\n")

if __name__ == "__main__":
    main()
