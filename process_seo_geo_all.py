#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하수구수사대 블로그 전체 포스트 SEO/GEO 일괄 마이그레이션 및 사이트맵/인덱스 갱신 스크립트
네트워크 요청 없이 로컬의 JSON과 HTML 파일을 파싱하여 올바른 지역 정보(Geo)와 서비스 정보(SEO)를 매핑하고
네이버 검색 최적화(Naver SEO/GEO Meta tags, Schema.org 구조화 데이터)를 반영한 HTML을 재생성합니다.
이전의 잘못 생성된 용인 처인구(yongin-cheoinggu) 파일들은 삭제하고 sitemap.xml, robots.txt, index.html을 갱신합니다.
"""

import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path

# ============================================================
# 설정
# ============================================================
PROJECT_DIR = Path("/Users/lee/projects/hasugu")
BLOG_DIR = PROJECT_DIR / "blog"
SITEMAP_FILE = PROJECT_DIR / "sitemap.xml"
ROBOTS_FILE = PROJECT_DIR / "robots.txt"

DOMAIN = "https://www.lymin80.shop"
COMPANY_NAME = "하수구수사대"
COMPANY_PHONE = "010-5615-2118"

# ============================================================
# 1. 지명 및 서비스 맵핑 데이터
# ============================================================
GEO_DATA = {
    # 경기도
    "동두천": {"en": "dongducheon", "coords": "37.9036;127.0607", "region": "KR-41", "placename": "동두천시"},
    "시흥": {"en": "siheung", "coords": "37.3801;126.8027", "region": "KR-41", "placename": "시흥시"},
    "고양": {"en": "goyang", "coords": "37.6584;126.8320", "region": "KR-41", "placename": "고양시"},
    "파주": {"en": "paju", "coords": "37.7600;126.7799", "region": "KR-41", "placename": "파주시"},
    "오산": {"en": "osan", "coords": "37.1502;127.0789", "region": "KR-41", "placename": "오산시"},
    "광주": {"en": "gwangju", "coords": "37.4087;127.2687", "region": "KR-41", "placename": "광주시"},
    "성남": {"en": "seongnam", "coords": "37.4201;127.1265", "region": "KR-41", "placename": "성남시"},
    "안성": {"en": "anseong", "coords": "37.0079;127.2798", "region": "KR-41", "placename": "안성시"},
    "평택": {"en": "pyeongtaek", "coords": "36.9922;127.1128", "region": "KR-41", "placename": "평택시"},
    "양주": {"en": "yangju", "coords": "37.7853;127.0458", "region": "KR-41", "placename": "양주시"},
    "용인": {"en": "yongin", "coords": "37.2410;127.1779", "region": "KR-41", "placename": "용인시"},
    "수원": {"en": "suwon", "coords": "37.2635;127.0286", "region": "KR-41", "placename": "수원시"},
    "화성": {"en": "hwaseong", "coords": "37.1995;126.8312", "region": "KR-41", "placename": "화성시"},
    "안양": {"en": "anyang", "coords": "37.3943;126.9568", "region": "KR-41", "placename": "안양시"},
    "안산": {"en": "ansan", "coords": "37.3219;126.8308", "region": "KR-41", "placename": "안산시"},
    # 충청남도
    "천안": {"en": "cheonan", "coords": "36.8151;127.1139", "region": "KR-44", "placename": "천안시"},
    "아산": {"en": "asan", "coords": "36.7844;127.0049", "region": "KR-44", "placename": "아산시"},
    # 서울/인천
    "서울": {"en": "seoul", "coords": "37.5665;126.9780", "region": "KR-11", "placename": "서울특별시"},
    "인천": {"en": "incheon", "coords": "37.4563;126.7052", "region": "KR-28", "placename": "인천광역시"}
}

SUB_AREA_MAP = {
    "동두천동": "dongducheon", "탑동동": "tapdong", "물왕동": "mulwang", "정왕동": "jeongwang",
    "화전동": "hwajeon", "동산동": "dongsan", "문발동": "munbal", "금릉동": "geumneung",
    "법곡동": "beopgok", "영인면": "yeongin", "갈곶동": "galgot", "세마동": "sema",
    "쌍령동": "ssangryeong", "오포읍": "opo", "회덕동": "hoedeok", "퇴촌면": "toechon",
    "용화동": "yonghwa", "인주면": "inju", "야탑동": "yatap", "대장동": "daejang",
    "신장동": "sinjang", "원동": "wondong", "성사동": "seongsa", "행신동": "haengsin",
    "정왕본동": "jeongwangbon", "금이동": "geumi", "검산동": "geomsan", "장단면": "jangdan",
    "분당동": "bundang", "어둔동": "eodun", "광적면": "gwangjeok", "연지동": "yeonji",
    "대덕면": "daedeok", "쌍용동": "ssangyong", "부성1동": "buseong", "부성동": "buseong",
    "화정동": "hwajeong", "지축동": "jichuk", "중앙동": "jungang", "비전동": "bijeon",
    "목현동": "mokhyeon", "목동": "mokdong", "장지동": "jangji", "남종면": "namjong",
    "풍기동": "punggi", "남동": "namdong", "송정동": "songjeong", "유양동": "yuyang",
    "고암동": "goam", "성환읍": "seonghwan", "불당2동": "buldang", "불당동": "buldang",
    "마전동": "majeon", "회암동": "hoeam", "금산동": "geumsan", "보개면": "bogae",
    "성거읍": "seonggeo", "입장면": "ipjang", "대흥동": "daeheung", "일봉동": "ilbong",
    "죽전": "jukjeon", "보정동": "bojeong", "병점": "byeongjeom", "우정읍": "ujeong",
    "장안면": "jangan", "처인구": "cheoinggu", "기흥": "giheung", "신봉동": "sinbong",
    "고기동": "gogi", "영천동": "yeongcheon", "산척동": "sancheok", "석우동": "seokwoo",
    "반송동": "bansong", "향남": "hyangnam", "보라동": "bora", "상하동": "sangha",
    "양감": "yanggam", "남양": "namyang", "팔탄": "paltan", "행궁동": "haenggung",
    "지동": "jidong", "와우리": "wau", "봉담": "bongdam", "호계동": "hogye",
    "갈산동": "galsan", "이의동": "uiui", "풍덕천동": "pungdeokcheon", "가수동": "gasu",
    "수청동": "sucheong", "새솔동": "saesol", "해양동": "haeyang", "상신리": "sangshin",
    "하길리": "hagil", "역북동": "yeokbuk", "김량장동": "gimryangjang",
    "곡반정동": "gokbanjeong", "모현읍": "mohyeon", "동천동": "dongcheon", "우만동": "uman",
    "매탄동": "maetan", "서천동": "seocheon", "망포동": "mangpo", "영덕동": "yeongdeok",
    "판교동": "pangyo", "고색동": "gosaek", "발안": "baran", "봉담읍": "bongdam",
    "정남면": "jeongnam", "양지면": "yangji", "마도면": "mado", "송산": "songsan",
    "천리": "cheonri"
}

# ============================================================
# 1-1. 서울 및 인천 행정구 데이터
# ============================================================
SEOUL_DISTRICTS = {
    "광진": "gwangjin", "노원": "nowon", "성북": "seongbuk", "강동": "gangdong", 
    "은평": "eunpyeong", "서초": "seocho", "중랑": "jungnang", "서대문": "seodaemun", 
    "금천": "geumcheon", "동대문": "dongdaemun", "동작": "dongjak", "영등포": "yeongdeungpo", 
    "관악": "gwanak", "강남": "gangnam", "송파": "songpa", "강서": "gangseo", 
    "양천": "yangcheon", "구로": "guro", "마포": "mapo", "용산": "yongsan", 
    "성동": "seongdong", "종로": "jongno", "도봉": "dobong", "강북": "gangbuk",
    "중구": "jung-gu"
}

INCHEON_DISTRICTS = {
    "부평": "bupyeong", "계양": "gyeyang", "미추홀": "michuhol", "연수": "yeonsu", 
    "남동": "namdong", "강화": "ganghwa", "옹진": "ongjin", "동구": "donggu",
    "서구": "seogu"
}

# 8개 초기 수동 매핑 포스트 정보 (기존 퀄리티 완전 보존)
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

# ============================================================
# 헬퍼 함수
# ============================================================
def format_date(date_str: str) -> str:
    """날짜 문자열을 YYYY-MM-DD 형식으로 변환"""
    m = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', date_str)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m2 = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if m2:
        return date_str
    return datetime.now().strftime("%Y-%m-%d")

def clean_html_to_text(html_content: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ============================================================
# 2. 신규 포스트의 지역 및 서비스 스마트 분석기
# ============================================================
def analyze_geo_seo(title: str, body_text: str) -> dict:
    """한글 제목과 본문에서 지명(Geo)과 서비스(SEO) 정보를 정밀 추출 (타이틀 우선 매칭)"""
    city_ko = ""
    sub_area_ko = ""
    
    # --- [1단계: 제목(Title) 매칭 - 최우선] ---
    # 1-1. 제목에서 기존 GEO_DATA 도시 매칭 (용인, 수원, 화성 등)
    for city in GEO_DATA.keys():
        if city in title:
            city_ko = city
            break
            
    # 1-2. 제목에서 서울 구 매칭
    if not city_ko:
        for dist in SEOUL_DISTRICTS.keys():
            if f"{dist}구" in title or dist in title:
                city_ko = "서울"
                sub_area_ko = f"{dist}구"
                break
                
    # 1-3. 제목에서 인천 구 매칭
    if not city_ko:
        for dist in INCHEON_DISTRICTS.keys():
            if dist in ["중구", "서구", "동구"]:
                if f"{dist}" in title:
                    if "인천" in title or "인천" in body_text:
                        city_ko = "인천"
                        sub_area_ko = f"{dist}"
                        break
            else:
                if f"{dist}구" in title or dist in title:
                    city_ko = "인천"
                    sub_area_ko = f"{dist}구"
                    break
                    
    # 1-4. 제목에서 세부 지명(동/읍/면) 매칭 및 시군 유추
    if not sub_area_ko:
        for sub in SUB_AREA_MAP.keys():
            if sub in title:
                sub_area_ko = sub
                if not city_ko:
                    eng = SUB_AREA_MAP[sub]
                    for city, info in GEO_DATA.items():
                        if info["en"] == eng:
                            city_ko = city
                            break
                break

    # --- [2단계: 본문(Body) 매칭 - 제목에서 매칭되지 않았을 때만] ---
    if not city_ko:
        # 2-1. 본문에서 기존 GEO_DATA 도시 매칭
        for city in GEO_DATA.keys():
            if city in body_text:
                city_ko = city
                break
                
    # 2-2. 본문에서 서울 구 매칭
    if not city_ko:
        for dist in SEOUL_DISTRICTS.keys():
            if f"{dist}구" in body_text or dist in body_text:
                city_ko = "서울"
                sub_area_ko = f"{dist}구"
                break
                
    # 2-3. 본문에서 인천 구 매칭
    if not city_ko:
        for dist in INCHEON_DISTRICTS.keys():
            if dist not in ["중구", "서구", "동구"]:
                if f"{dist}구" in body_text or dist in body_text:
                    city_ko = "인천"
                    sub_area_ko = f"{dist}구"
                    break
                    
    # 2-4. 본문에서 세부 지명(동/읍/면) 매칭 및 시군 유추
    if not sub_area_ko:
        for sub in SUB_AREA_MAP.keys():
            if sub in body_text:
                sub_area_ko = sub
                if not city_ko:
                    eng = SUB_AREA_MAP[sub]
                    for city, info in GEO_DATA.items():
                        if info["en"] == eng:
                            city_ko = city
                            break
                break

    # --- [3단계: 기본값 예외 처리] ---
    if not city_ko:
        city_ko = "용인"
        
    areas = []
    if sub_area_ko:
        areas.append(f"{city_ko} {sub_area_ko}")
        areas.append(sub_area_ko)
    areas.append(city_ko)
    
    service_types = []
    domain_map = {
        "싱크대": "싱크대막힘", "씽크대": "싱크대막힘",
        "변기": "변기막힘", "대변기": "변기막힘",
        "하수구": "하수구막힘", "하수도": "하수구막힘",
        "배관": "배관막힘", "배수관": "배관막힘", "오수관": "배관막힘", "배수구": "배관막힘", "맨홀": "맨홀막힘", "집수정": "집수정막힘",
        "누수": "누수수리", "물샘": "누수수리"
    }
    for kw, svc in domain_map.items():
        if kw in title or kw in body_text:
            service_types.append(svc)
            
    action_map = {
        "역류": "역류해결",
        "뚫": "뚫는업체",
        "청소": "배관청소",
        "세척": "고압세척",
        "공사": "설비공사",
        "보수": "배관보수",
        "차단": "악취차단"
    }
    for kw, act in action_map.items():
        if kw in title or kw in body_text:
            service_types.append(act)
            
    service_types = list(dict.fromkeys(service_types))
    if not service_types:
        service_types = ["배관막힘", "하수구역류"]
 
    primary_area = f"{city_ko} {sub_area_ko}" if sub_area_ko else city_ko
    primary_service = service_types[0] if service_types else "배관막힘"
 
    city_en = GEO_DATA[city_ko]["en"]
    
    # 영문 서브 지역명 동적 분석
    sub_en = ""
    if sub_area_ko:
        clean_sub = sub_area_ko.replace("구", "").replace("군", "").strip()
        if clean_sub in SEOUL_DISTRICTS:
            sub_en = SEOUL_DISTRICTS[clean_sub]
        elif clean_sub in INCHEON_DISTRICTS:
            sub_en = INCHEON_DISTRICTS[clean_sub]
        elif sub_area_ko in SUB_AREA_MAP:
            sub_en = SUB_AREA_MAP[sub_area_ko]
            
    service_en = "drain-clogged"
    if "싱크대" in title or "씽크대" in title or "싱크대" in body_text or "씽크대" in body_text:
        service_en = "sink-clogged"
    elif "변기" in title or "대변기" in title or "변기" in body_text or "대변기" in body_text:
        service_en = "toilet-clogged"
    elif "하수구역류" in title or "하수도역류" in title or "역류" in title:
        service_en = "sewer-backflow"
    elif "하수구" in title or "하수도" in title or "하수구" in body_text:
        service_en = "sewer-clogged"
    elif "고압세척" in title or "세척" in title:
        service_en = "high-pressure-flushing"
    elif "누수" in title or "물샘" in title:
        service_en = "leakage-repair"
    elif "맨홀" in title or "맨홀" in body_text:
        service_en = "manhole-clogged"
    elif "집수정" in title or "집수정" in body_text:
        service_en = "sump-cleaning"
        
    slug_parts = [city_en]
    if sub_en and sub_en != city_en:
        slug_parts.append(sub_en)
    slug_parts.append(service_en)
    
    slug = "-".join(slug_parts)
 
    seo_keywords = [
        f"{primary_area} {primary_service}",
        f"{city_ko} {primary_service}",
        f"{primary_area} 하수구막힘",
        f"{primary_area} 싱크대막힘",
        f"{primary_area} 변기막힘",
        f"{primary_area} 고압세척",
        "하수구수사대"
    ]
    if sub_area_ko:
        seo_keywords.append(f"{sub_area_ko} {primary_service}")
        seo_keywords.append(f"{sub_area_ko} 하수구역류")
 
    return {
        "city_ko": city_ko,
        "sub_area_ko": sub_area_ko,
        "primary_area": primary_area,
        "areas": areas,
        "primary_service": primary_service,
        "service_types": service_types,
        "slug": slug,
        "keywords": list(dict.fromkeys(seo_keywords))
    }

# ============================================================
# 3. HTML 파서 및 텍스트/이미지 복원기
# ============================================================
def extract_paragraphs_and_images_from_html(html_file_path: Path) -> dict:
    """기존 HTML 파일에서 본문 문단(p), 이미지(img), 전문가 인용구 추출"""
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    sections = {
        "sec1": [], # 문제 상황
        "sec2": [], # 원인 분석
        "sec3": [], # 작업 과정
        "sec4": []  # 작업 완료
    }
    
    idx_sec1 = html_content.find("<h2>🔍 문제 상황</h2>")
    idx_sec2 = html_content.find("<h2>🔎 원인 분석</h2>")
    idx_sec3 = html_content.find("<h2>🔧 작업 과정</h2>")
    idx_sec4 = html_content.find("<h2>✅ 작업 완료</h2>")
    idx_end = html_content.find("<h2>⚠️")
    
    if idx_end == -1:
        idx_end = len(html_content)
        
    p_pattern = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
    
    if idx_sec1 != -1 and idx_sec2 != -1:
        sec1_html = html_content[idx_sec1:idx_sec2]
        sections["sec1"] = [re.sub(r'<[^>]+>', '', p).strip() for p in p_pattern.findall(sec1_html)]
        
    if idx_sec2 != -1 and idx_sec3 != -1:
        sec2_html = html_content[idx_sec2:idx_sec3]
        sections["sec2"] = [
            re.sub(r'<[^>]+>', '', p).strip() 
            for p in p_pattern.findall(sec2_html)
            if "전문가 진단:" not in p
        ]
        
    if idx_sec3 != -1 and idx_sec4 != -1:
        sec3_html = html_content[idx_sec3:idx_sec4]
        sections["sec3"] = [re.sub(r'<[^>]+>', '', p).strip() for p in p_pattern.findall(sec3_html)]
        
    if idx_sec4 != -1:
        sec4_html = html_content[idx_sec4:idx_end]
        sections["sec4"] = [re.sub(r'<[^>]+>', '', p).strip() for p in p_pattern.findall(sec4_html)]
        
    quote = ""
    quote_match = re.search(r'<strong>💡 전문가 진단:</strong>\s*(.*?)</p>', html_content)
    if quote_match:
        quote = re.sub(r'<[^>]+>', '', quote_match.group(1)).strip()

    img_pattern = re.compile(r'<img[^>]+src="([^"]+)"', re.DOTALL)
    images = []
    for img in img_pattern.findall(html_content):
        if 'logo.png' not in img and 'Top_Bg_2.png' not in img:
            clean_img = img
            if clean_img.startswith("/blog/"):
                clean_img = clean_img[6:]
            elif clean_img.startswith("/"):
                clean_img = clean_img[1:]
            if clean_img.startswith("blog/"):
                clean_img = clean_img[5:]
            if clean_img not in images:
                images.append(clean_img)

    return {
        "sec1_p": [p for p in sections["sec1"] if p],
        "sec2_p": [p for p in sections["sec2"] if p],
        "sec3_p": [p for p in sections["sec3"] if p],
        "sec4_p": [p for p in sections["sec4"] if p],
        "quote": quote,
        "images": images
    }

# ============================================================
# 4. HTML 템플릿 제너레이터
# ============================================================
def generate_seo_geo_html(meta: dict, content: dict, geo_seo_info: dict, blog_id: str, prev_post: dict = None, next_post: dict = None) -> str:
    """완전한 Naver SEO/GEO 메타 태그와 Schema 구조화 데이터를 갖춘 프리미엄 HTML 리턴"""

    title = meta["title"]
    date_str = meta["date"]
    
    primary_area = geo_seo_info["primary_area"]
    primary_service = geo_seo_info["primary_service"]
    areas = geo_seo_info["areas"]
    service_types = geo_seo_info["service_types"]
    seo_keywords = geo_seo_info["keywords"]
    slug = geo_seo_info["slug"]
    
    city_ko = geo_seo_info["city_ko"]
    geo_pos = GEO_DATA[city_ko]["coords"]
    geo_region = GEO_DATA[city_ko]["region"]
    geo_placename = GEO_DATA[city_ko]["placename"]
    
    cover_image = meta.get("cover_image", "")
    if cover_image.startswith("/blog/"):
        cover_image = cover_image[6:]
    elif cover_image.startswith("/"):
        cover_image = cover_image[1:]
    if cover_image.startswith("blog/"):
        cover_image = cover_image[5:]
        
    cover_image_absolute = f"{DOMAIN}/blog/{cover_image}" if cover_image else ""
    desc = f"{' '.join(areas[:2])} {primary_service} 전문업체 {COMPANY_NAME}. {title}. {COMPANY_PHONE} 24시간 긴급 출동."
    
    sec1_p = content["sec1_p"]
    sec2_p = content["sec2_p"]
    sec3_p = content["sec3_p"]
    sec4_p = content["sec4_p"]
    
    images = [img for img in content["images"] if img != cover_image]
    
    img_sec1 = f'<div class="image-box"><img src="{images[0]}" alt="{title} 현장 상황" loading="lazy"></div>' if len(images) > 0 else ""
    img_sec2 = f'<div class="image-box"><img src="{images[1]}" alt="{title} 원인 분석" loading="lazy"></div>' if len(images) > 1 else ""
    
    img_sec3 = ""
    if len(images) > 3:
        img_sec3 = f'''
        <div class="image-grid">
          <img src="{images[2]}" alt="작업 과정 사진 1" loading="lazy">
          <img src="{images[3]}" alt="작업 과정 사진 2" loading="lazy">
        </div>'''
    elif len(images) > 2:
        img_sec3 = f'<div class="image-box"><img src="{images[2]}" alt="작업 과정 사진" loading="lazy"></div>'
        
    extra_images = images[4:] if len(images) > 4 else []
    img_sec4 = ""
    if extra_images:
        img_sec4 = '<div class="image-grid">'
        for idx, img in enumerate(extra_images[:4]):
            img_sec4 += f'<img src="{img}" alt="추가 시공 사진 {idx+1}" loading="lazy">'
        img_sec4 += '</div>'
        
    diag_quote = content["quote"] if content["quote"] else "슬러지와 이물질이 통로를 꽉 막고 있어 배수가 불가능하며, 정밀 타격 및 배관 세척이 동반되어야 해결 가능합니다."
    
    precaution_title = "하수구 배관 막힘 예방 및 관리 가이드"
    precaution_list = [
        "머리카락, 비닐, 물티슈 등 물에 분해되지 않는 이물질은 하수구 유입을 절대 금지해 주세요.",
        "하수구 거름망을 씌우고 모여진 이물질은 주기적으로 쓰레기통에 바로 비워주셔야 합니다.",
        "배관 노후가 심할 경우 이물질이 더 쉽게 걸리므로 주기적인 배관 세척(고압세척 등)을 권장합니다.",
        "작업 후 1년 이내 재발 시 하수구수사대에서 무상 A/S 보증 서비스를 제공합니다."
    ]
    
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
        
    precaution_html = "".join([f'<li style="margin-bottom: 8px;">✅ {item}</li>' for item in precaution_list])
    
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
    
    area_served_entries = []
    for a in areas[:5]:
        area_served_entries.append(f'{{"@type": "City", "name": "{a}"}}')
    area_served_schema = ",\n      ".join(area_served_entries)
    
    service_type_schema = ", ".join([f'"{s}"' for s in service_types])
    tag_html = "\n".join([f"      <span>#{tag}</span>" for tag in seo_keywords])

    prev_nav_html = f'''<a href="{prev_post['slug']}.html" class="nav-card">
      <span class="nav-label">◀ 이전 시공사례</span>
      <span class="nav-title">{prev_post['title']}</span>
    </a>''' if prev_post else '<div style="visibility: hidden;"></div>'

    next_nav_html = f'''<a href="{next_post['slug']}.html" class="nav-card" style="text-align: right;">
      <span class="nav-label">다음 시공사례 ▶</span>
      <span class="nav-title">{next_post['title']}</span>
    </a>''' if next_post else '<div style="visibility: hidden;"></div>'


    html_content = f'''<!DOCTYPE html>
<html lang="ko">


<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | {COMPANY_NAME}</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{', '.join(seo_keywords)}">
  <link rel="canonical" href="{DOMAIN}/blog/{slug}">

  <!-- Naver SEO & GEO Tags -->
  <meta name="geo.region" content="{geo_region}">
  <meta name="geo.placename" content="{geo_placename}">
  <meta name="geo.position" content="{geo_pos}">
  <meta name="ICBM" content="{geo_pos}">

  <!-- Open Graph -->
  <meta property="og:title" content="{title} | {COMPANY_NAME}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{cover_image_absolute}">
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
    "datePublished": "{format_date(date_str)}",
    "dateModified": "{datetime.now().strftime('%Y-%m-%d')}",
    "image": "{cover_image_absolute}",
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


  <link rel="icon" type="image/png" sizes="32x32" href="/images/favicon.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png">
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

  <!-- 이전글 / 다음글 네비게이션 -->
  <div class="prev-next-nav">
    {prev_nav_html}
    {next_nav_html}
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

# ============================================================
# 5. 글로벌 빌드 기능 (Sitemap, Index, Robots)
# ============================================================
def rebuild_sitemap(posts: list):
    """sitemap.xml을 최신 상태로 네이버/구글 서치어드바이저 표준 규격에 맞게 재구축"""
    print("🕸️ sitemap.xml 재구축 중...")
    
    sitemap_entries = [f'''  <url>
    <loc>{DOMAIN}/</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{DOMAIN}/blog/index.html</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>''']

    for p in posts:
        slug = p["slug"]
        date_str = format_date(p["date"])
        
        entry = f'''  <url>
    <loc>{DOMAIN}/blog/{slug}.html</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>'''
        sitemap_entries.append(entry)
        
    sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(sitemap_entries)}
</urlset>
'''
    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    print(f"  ✅ sitemap.xml 재구축 완료! ({len(posts)}개 포스트 반영)")


def format_rss_date(date_str: str) -> str:
    """날짜 문자열을 RFC 822 포맷(예: Wed, 29 Jul 2026 00:00:00 +0900)으로 변환"""
    clean_d = format_date(date_str)
    try:
        dt = datetime.strptime(clean_d, "%Y-%m-%d")
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0900")
    except Exception:
        return datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0900")

def rebuild_rss(posts: list):
    """rss.xml 파일 생성/갱신 (네이버 서치어드바이저 RSS 피드 가이드 정밀 준수)"""
    print("📡 rss.xml 갱신 중...")
    rss_items = []
    for p in posts[:50]:
        title = p.get('title', '').strip()
        slug = p.get('slug', '')
        link = f"{DOMAIN}/blog/{slug}.html"
        
        # 네이버 가이드: 본문 내용 포함 (CDATA 처리로 특수문자 및 HTML 안전성 확보)
        desc = p.get('description', '')
        html_file = BLOG_DIR / f"{slug}.html"
        if html_file.exists():
            try:
                with open(html_file, 'r', encoding='utf-8') as hf:
                    html_str = hf.read()
                    m_sec = re.findall(r'<div class="section">(.*?)</div>', html_str, re.DOTALL)
                    if m_sec:
                        clean_sec = " ".join([re.sub(r'<[^>]+>', ' ', s) for s in m_sec])
                        clean_sec = re.sub(r'\s+', ' ', clean_sec).strip()
                        if len(clean_sec) > 100:
                            desc = clean_sec
            except Exception:
                pass

        raw_date = p.get('date', '')
        pub_date = format_rss_date(raw_date)
        
        rss_items.append(f'''    <item>
      <title><![CDATA[{title}]]></title>
      <link>{link}</link>
      <description><![CDATA[{desc}]]></description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="true">{link}</guid>
    </item>''')

    rss_items_joined = "\n".join(rss_items)
    rss_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title><![CDATA[{COMPANY_NAME} 시공후기 & 블로그]]></title>
    <link>{DOMAIN}/blog/</link>
    <description><![CDATA[용인·수원·화성 하수구막힘, 누수탐지, 고압세척 전문업체 {COMPANY_NAME} 시공사례 피드]]></description>

    <language>ko-KR</language>
    <atom:link href="{DOMAIN}/rss.xml" rel="self" type="application/rss+xml" />
{rss_items_joined}
  </channel>
</rss>
'''

    rss_path = PROJECT_DIR / "rss.xml"
    with open(rss_path, 'w', encoding='utf-8') as f:
        f.write(rss_content)
    print(f"  ✅ rss.xml 갱신 완료! ({len(posts[:50])}개 포스트 반영)")


def rebuild_robots():

    """robots.txt 파일 생성/갱신"""
    print("🤖 robots.txt 갱신 중...")
    robots_content = f'''User-agent: *
Allow: /
Disallow: /index_files/

Sitemap: {DOMAIN}/sitemap.xml
Sitemap: {DOMAIN}/rss.xml
'''
    with open(ROBOTS_FILE, 'w', encoding='utf-8') as f:
        f.write(robots_content)
    print("  ✅ robots.txt 갱신 완료!")


def update_blog_index(posts: list):
    """블로그 목록 페이지(blog/index.html) 및 posts.json 갱신"""
    print("📋 blog/index.html 및 posts.json 갱신 중...")
    
    # 1. posts.json 파일 생성 (전체 목록)
    posts_json_data = []
    for p in posts:
        slug = p["slug"]
        cover = p.get("cover_image", "")
        if cover.startswith("/blog/"):
            cover = cover[6:]
        elif cover.startswith("/"):
            cover = cover[1:]
        if cover.startswith("blog/"):
            cover = cover[5:]
            
        posts_json_data.append({
            "title": p.get("title", ""),
            "slug": slug,
            "cover_image": cover,
            "category": p.get("category", ""),
            "description": p.get("description", ""),
            "date": p.get("date", "")
        })
        
    posts_json_path = BLOG_DIR / "posts.json"
    with open(posts_json_path, 'w', encoding='utf-8') as f:
        json.dump(posts_json_data, f, ensure_ascii=False, indent=2)
    print("  ✅ blog/posts.json 생성 완료!")

    # 2. 첫 24개 포스트만 정적 HTML 카드로 렌더링 (나머지는 JS로 비동기 로드)
    static_posts = posts[:24]
    cards_html = ""
    for p in static_posts:
        slug = p["slug"]
        cover = p.get("cover_image", "")
        
        if cover.startswith("/blog/"):
            cover = cover[6:]
        elif cover.startswith("/"):
            cover = cover[1:]
        if cover.startswith("blog/"):
            cover = cover[5:]

        cover_html = (
            f'<div class="card-img"><img src="{cover}" alt="{p["title"]}" loading="lazy"></div>'
            if cover else
            '<div class="card-img card-img-placeholder">🔧</div>'
        )
        
        date_clean = p.get('date', '')
        
        cards_html += f"""
        <a href="{slug}.html" class="post-card" style="text-decoration: none; color: inherit;">
            <article>
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
            </article>
        </a>"""

    index_html = f"""<!DOCTYPE html>

<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="하수구수사대 시공 후기 및 블로그 - 용인·수원·화성 하수구 막힘 전문 청소업체">
    <title>블로그 - 하수구수사대</title>
    <link rel="canonical" href="{DOMAIN}/blog/">
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
        .posts-grid {{ max-width: 1100px; margin: 0 auto; padding: 56px 24px 40px; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 28px; }}
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
        .load-more-container {{ text-align: center; margin: 20px 0 80px; }}
        .load-more-btn {{ background: var(--primary); color: white; border: none; padding: 12px 36px; font-size: 1rem; font-weight: 600; border-radius: var(--radius-sm); cursor: pointer; box-shadow: var(--shadow-sm); transition: background .2s, transform .2s; }}
        .load-more-btn:hover {{ background: var(--primary-dark); transform: translateY(-2px); }}
        .load-more-btn:active {{ transform: translateY(0); }}
        .site-footer {{ background: #1a1a2e; color: rgba(255,255,255,.55); text-align: center; padding: 32px 24px; font-size: .82rem; line-height: 1.8; }}
        .site-footer strong {{ color: rgba(255,255,255,.85); }}
        @media (max-width: 768px) {{ .posts-grid {{ padding: 32px 16px 40px; gap: 20px; }} .header-nav {{ display: none; }} }}
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
<div class="posts-grid" id="posts-container">
    {cards_html if cards_html else '<div class="empty-state"><p>아직 블로그 포스트가 없습니다.</p></div>'}
</div>
<div class="load-more-container">
    <button id="load-more-btn" class="load-more-btn">더 보기</button>
</div>
<footer class="site-footer">
    <strong>하수구수사대</strong><br>
    용인·수원·화성 하수구 막힘 전문 청소업체<br>
    © {datetime.now().year} 하수구수사대. All rights reserved.
</footer>

<script>
    let allPosts = [];
    let currentIndex = 24;
    const limit = 24;
    const container = document.getElementById('posts-container');
    const loadMoreBtn = document.getElementById('load-more-btn');

    // posts.json 파일 비동기 로드
    fetch('posts.json')
        .then(response => response.json())
        .then(data => {{
            allPosts = data;
            // 만약 전체 포스트가 24개 이하라면 더보기 버튼 숨김
            if (allPosts.length <= currentIndex) {{
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            }}
        }})
        .catch(err => console.error('Failed to load posts:', err));

    if (loadMoreBtn) {{
        loadMoreBtn.addEventListener('click', () => {{
            const nextPosts = allPosts.slice(currentIndex, currentIndex + limit);
            nextPosts.forEach(p => {{
                const card = document.createElement('a');
                card.href = p.slug.endsWith('.html') ? p.slug : p.slug + '.html';
                card.className = 'post-card';

                card.style.textDecoration = 'none';
                card.style.color = 'inherit';
                
                const coverHtml = p.cover_image ? 
                    `<div class="card-img"><img src="${{p.cover_image}}" alt="${{p.title}}" loading="lazy"></div>` :
                    `<div class="card-img card-img-placeholder">🔧</div>`;
                
                const categoryHtml = p.category ? `<span class="card-badge">${{p.category}}</span>` : '';
                const descTrunc = p.description.length > 80 ? p.description.slice(0, 80) + '...' : p.description;

                card.innerHTML = `
                    <article style="height: 100%; display: flex; flex-direction: column;">
                        \${{coverHtml}}
                        <div class="card-body" style="flex: 1; display: flex; flex-direction: column; gap: 8px;">
                            \${{categoryHtml}}
                            <h2 class="card-title">\${{p.title}}</h2>
                            <p class="card-desc">\${{descTrunc}}</p>
                            <div class="card-meta">
                                <span>📅 \${{p.date}}</span>
                                <span class="card-read">자세히 보기 →</span>
                            </div>
                        </div>
                    </article>
                `;
                container.appendChild(card);
            }});

            currentIndex += limit;
            if (currentIndex >= allPosts.length) {{
                loadMoreBtn.style.display = 'none';
            }}
        }});
    }}
</script>
</body>
</html>"""
    index_path = BLOG_DIR / "index.html"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("  ✅ blog/index.html 갱신 완료!")

# ============================================================
# 메인 마이그레이션 실행 루틴
# ============================================================
def main():
    print("🚀 블로그 SEO/GEO 일괄 복구 및 사이트맵 갱신 프로세스 시작")
    print(f"   블로그 경로: {BLOG_DIR}")

    json_files = sorted([f for f in os.listdir(BLOG_DIR) if f.endswith(".json") and f != "posts.json"])
    print(f"   수집된 JSON 메타데이터 개수: {len(json_files)}개")

    final_posts = []
    processed_log_nos = set()
    old_files_to_delete = []

    for idx, json_name in enumerate(json_files, 1):
        log_no = json_name[:-5]
        json_path = BLOG_DIR / json_name
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        except Exception as e:
            print(f"❌ [오류] {json_name} 로드 실패: {e}")
            continue

        title = meta.get("title", "")
        candidates = [
            meta.get("html_file"),
            f"yongin-cheoinggu-drain-clogged-{log_no}.html",
            f"yongin-cheoinggu-high-pressure-flushing-{log_no}.html",
            f"yongin-giheung-drain-clogged-{log_no}.html",
            f"yongin-suji-drain-clogged-{log_no}.html",
            f"hwaseong-hyangnam-drain-clogged-{log_no}.html",
            f"suwon-gwonseon-drain-clogged-{log_no}.html"
        ]
        
        html_path = None
        for cand in candidates:
            if cand:
                p = BLOG_DIR / cand
                if p.exists():
                    html_path = p
                    break
        
        if not html_path:
            pattern = re.compile(rf'-{log_no}\.html$')
            for f in os.listdir(BLOG_DIR):
                if pattern.search(f):
                    html_path = BLOG_DIR / f
                    break
                    
        if not html_path:
            print(f"⚠️ [{idx}/{len(json_files)}] {log_no} 에 해당하는 HTML 파일을 찾을 수 없습니다. 건너뜁니다.")
            continue

        print(f"⏳ [{idx}/{len(json_files)}] {log_no} 처리 중: {title[:30]}...")

        content = extract_paragraphs_and_images_from_html(html_path)
        body_text_clean = " ".join(content["sec1_p"] + content["sec2_p"] + content["sec3_p"] + content["sec4_p"])
        
        if log_no in POSTS_METADATA:
            info = POSTS_METADATA[log_no]
            city_ko = "용인"
            for city in GEO_DATA.keys():
                if city in info["areas"][-1] or city in info["areas"][-2] or city in info["areas"][0]:
                    city_ko = city
                    break
            geo_seo_info = {
                "city_ko": city_ko,
                "primary_area": info["primary_area"],
                "areas": info["areas"],
                "primary_service": info["primary_service"],
                "service_types": info["service_types"],
                "slug": info["slug"],
                "keywords": info["keywords"]
            }
        else:
            geo_seo_info = analyze_geo_seo(title, body_text_clean)
        
        slug = geo_seo_info["slug"]
        if not slug.endswith(f"-{log_no}"):
            slug = f"{slug}-{log_no}"
        geo_seo_info["slug"] = slug
        new_html_name = f"{slug}.html"

        meta["html_file"] = new_html_name
        meta["slug"] = slug


        meta["content"] = content
        meta["geo_seo_info"] = geo_seo_info
        meta["log_no"] = log_no
        meta["json_path"] = json_path
        meta["html_path"] = html_path

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "blog_id": meta.get("blog_id"),
                "title": meta.get("title"),
                "date": meta.get("date"),
                "category": meta.get("category"),
                "description": meta.get("description"),
                "cover_image": meta.get("cover_image"),
                "html_file": new_html_name,
                "slug": slug
            }, f, ensure_ascii=False, indent=2)

        if html_path.name != new_html_name:
            old_files_to_delete.append(html_path)

        final_posts.append(meta)
        processed_log_nos.add(log_no)

    # 날짜 역순 정렬 (최신글이 맨 앞)
    final_posts.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 2단계: 이전글/다음글 포함 HTML 최종 생성 및 저장
    print("\n🔗 이전글 / 다음글 체인 링크 렌더링 중...")
    total_len = len(final_posts)
    for idx, post in enumerate(final_posts):
        prev_post = final_posts[idx - 1] if idx > 0 else None
        next_post = final_posts[idx + 1] if idx < total_len - 1 else None
        
        slug = post["slug"]
        new_html_name = f"{slug}.html"
        new_html_path = BLOG_DIR / new_html_name
        
        new_html = generate_seo_geo_html(
            meta=post,
            content=post["content"],
            geo_seo_info=post["geo_seo_info"],
            blog_id=post["log_no"],
            prev_post=prev_post,
            next_post=next_post
        )
        with open(new_html_path, 'w', encoding='utf-8') as f:
            f.write(new_html)

    print(f"\n🗑️ 이전 오폭 파일 정리 중 (총 {len(old_files_to_delete)}개)...")

    for f in old_files_to_delete:
        try:
            if f.exists():
                os.remove(f)
                print(f"  ❌ 구 파일 삭제: {f.name}")
        except Exception as e:
            print(f"  ⚠️ 구 파일 삭제 실패: {f.name} ({e})")

    final_posts.sort(key=lambda x: x.get("date", ""), reverse=True)

    update_blog_index(final_posts)
    rebuild_sitemap(final_posts)
    rebuild_rss(final_posts)
    rebuild_robots()


    print(f"\n🎉 모든 작업이 성공적으로 완료되었습니다! 총 {len(final_posts)}개의 포스트가 올바르게 최적화 및 등록되었습니다.")

if __name__ == "__main__":
    main()
