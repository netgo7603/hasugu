#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hasugu2118 전용 블로그 과거 글 수집 및 자동 배포기 (2개씩 수집)
사용법: python3 history_crawler_2118.py
네이버 비동기 목록 API를 호출하여 hasugu2118 블로그의 신규 글 2개를 크롤링하고
SEO/GEO 최적화 및 Git Commit & Push까지 수행합니다.
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import subprocess
from datetime import datetime

# ============================================================
# 설정
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = os.path.join(BASE_DIR, "blog")
BLOG_ID = "hasugu2118"
CRAWL_LIMIT = 2

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

# ============================================================
# Git Commit & Push
# ============================================================
def git_commit_and_push():
    print("\n🐙 Git Commit & Push 진행 중...")
    try:
        # git add
        subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=True)
        
        # git commit
        commit_message = f"auto(blog): crawl and process 2 posts for {BLOG_ID} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], cwd=BASE_DIR, check=True)
        
        # git push
        subprocess.run(["git", "push"], cwd=BASE_DIR, check=True)
        print("✅ Git Commit & Push 완료!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 작업 실패: {e}")
        return False

# ============================================================
# 메인 크롤링 루틴
# ============================================================
def main():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] hasugu2118 전용 블로그 수집기 시작")
    print(f"📡 대상 블로그 ID: {BLOG_ID}")
    print(f"🎯 목표 수집 수량: {CRAWL_LIMIT}개")

    page = 1
    seen_log_nos = set()
    new_crawled_count = 0
    consecutive_empty_or_duplicate_pages = 0

    while new_crawled_count < CRAWL_LIMIT:
        # 네이버 비동기 목록 API 호출 URL 조립
        list_url = f"https://blog.naver.com/PostTitleListAsync.naver?blogId={BLOG_ID}&viewdate=&currentPage={page}&categoryNo=&parentCategoryNo=&countPerPage=30"
        print(f"\n📄 페이지 {page} 조회 중: {list_url}")

        req = urllib.request.Request(list_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_data = resp.read().decode('utf-8', errors='replace')
        except urllib.error.URLError as e:
            print(f"❌ [오류] 목록 API 요청 실패: {e}")
            break

        # JSON 파싱
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            try:
                # 백슬래시 오동작 등 이스케이프 보정 후 재시도
                fixed_raw_data = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', raw_data)
                data = json.loads(fixed_raw_data)
            except Exception as re_err:
                print(f"❌ [오류] JSON 파싱 실패 (API 응답 에러 가능성): {e}")
                print(f"      (복구 재시도 실패: {re_err})")
                break

        post_list = data.get("postList", [])
        if not post_list:
            print("ℹ️ 더 이상 포스트가 존재하지 않습니다. 수집을 종료합니다.")
            break

        # 이번 페이지의 글 번호 수집 및 신규 발견 확인
        current_page_log_nos = []
        new_log_nos_on_page = []

        for post in post_list:
            log_no = post.get("logNo")
            if log_no:
                current_page_log_nos.append(log_no)
                if log_no not in seen_log_nos:
                    new_log_nos_on_page.append(post)
                    seen_log_nos.add(log_no)

        # 중복 검사
        if not new_log_nos_on_page:
            consecutive_empty_or_duplicate_pages += 1
            print(f"⚠️ 페이지 {page}의 모든 포스트가 이전 페이지들과 중복됩니다. (연속 중복: {consecutive_empty_or_duplicate_pages})")
            if consecutive_empty_or_duplicate_pages >= 2:
                print("ℹ️ 새로운 포스트가 더 이상 발견되지 않아 목록 조회를 중단합니다.")
                break
        else:
            consecutive_empty_or_duplicate_pages = 0

        print(f"📝 페이지 {page}: 총 {len(post_list)}개 중 {len(new_log_nos_on_page)}개의 새로운 글 감지")

        # 각 포스트에 대해 크롤링 실행
        for i, post in enumerate(new_log_nos_on_page, 1):
            log_no = post["logNo"]
            title_encoded = post.get("title", "")
            title = urllib.parse.unquote(title_encoded).replace("+", " ")
            post_date = post.get("addDate", "")
            post_url = f"https://blog.naver.com/{BLOG_ID}/{log_no}"

            # 로컬 JSON 메타데이터 실존 여부 확인
            json_path = os.path.join(BLOG_DIR, f"{log_no}.json")
            if os.path.exists(json_path):
                print(f"  [{i}/{len(new_log_nos_on_page)}] ⏭️  이미 크롤링됨: {title[:35]}... (log_no: {log_no})")
                continue

            print(f"  [{i}/{len(new_log_nos_on_page)}] 🚀 신규 발견 크롤링 시작: {title} ({post_date})")
            
            crawler_script = os.path.join(BASE_DIR, "blog_crawler.py")
            cmd = ["python3", crawler_script, post_url]
            
            # 딜레이를 주어 IP 블록을 사전에 차단
            time.sleep(0.8)
            result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"      ✅ 크롤링 성공")
                new_crawled_count += 1
                if new_crawled_count >= CRAWL_LIMIT:
                    print(f"\n🎯 목표 수량({CRAWL_LIMIT}개) 도달로 크롤링을 종료합니다.")
                    break
            else:
                print(f"      ❌ 크롤링 실패 (Exit Code: {result.returncode})")
                print(f"      에러 로그: {result.stderr.strip()[:300]}")

        # 다음 페이지로 이동
        page += 1
        time.sleep(1.0)

    # 3. 새로운 글이 하나라도 크롤링되었다면 SEO/GEO 최적화 및 Git Commit & Push, Docker 배포 수행
    if new_crawled_count > 0:
        print(f"\n🎉 총 {new_crawled_count}개의 새로운 포스트가 수집되었습니다.")
        
        # SEO/GEO 최적화 및 sitemap.xml / robots.txt / index.html 일괄 재생성
        print("\n🔄 전체 포스트 SEO/GEO 최적화 및 사이트맵/목록 페이지 갱신 중...")
        seo_script = os.path.join(BASE_DIR, "process_seo_geo_all.py")
        seo_result = subprocess.run(["python3", seo_script], cwd=BASE_DIR, capture_output=True, text=True)
        
        if seo_result.returncode == 0:
            print("  ✅ SEO/GEO 최적화 및 사이트맵 갱신 완료!")
            
            # Git Commit & Push 실행
            git_commit_and_push()
        else:
            print("  ❌ [오류] SEO/GEO 최적화 실패")
            print(seo_result.stderr)
            

    else:
        print("\n✨ 새로 수집된 포스트가 없습니다. 최적화 및 배포 단계를 생략합니다.")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] hasugu2118 전용 블로그 수집기 종료\n")

if __name__ == "__main__":
    main()
