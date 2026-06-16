# 블로그 자동화 시스템 기획서

## 1. 개요
- **목적**: 네이버 블로그 링크를 입력하면 자동으로 SEO 최적화된 HTML 페이지를 생성하고 Docker에 배포
- **도메인**: hasugu2.lymin80.shop (하수구수사대)
- **담당**: planning 프로필 → development 프로필로 개발 위임

## 2. 시스템 아키텍처

```
[CEO 네이버 블로그 링크 입력]
        ↓
[1단계: 크롤링] Python 스크립트
  - 네이버 블로그 본문/이미지/제목 추출
  - 블로그 ID 추출 (URL에서)
        ↓
[2단계: HTML 생성] 템플릿 엔진
  - 기존 blog-sample.html 템플릿 재사용
  - SEO 메타태그 자동 생성
  - Schema.org (Article + FAQ + LocalBusiness)
  - OG 태그, 메타 키워드
  - 이미지 경로: /blog/images/{blog_id}/
        ↓
[3단계: Docker 배포] docker cp + nginx reload
  - memo-app 컨테이너에 HTML 복사
  - 이미지 폴더 복사
  - nginx 권한 설정 (644, nginx:nginx)
  - nginx -s reload
        ↓
[4단계: sitemap 갱신] XML 파싱
  - sitemap.xml에 새 URL 추가
  - git commit & push
```

## 3. 파일 구조

```
/Users/lee/projects/hasugu/
├── add_blog.py              # 메인 스크립트 (진입점)
├── blog_template.html       # HTML 템플릿
├── sitemap.xml              # 사이트맵
├── blog/                    # 생성된 블로그 HTML
│   └── {blog_id}.html
├── blog/images/             # 블로그 이미지
│   └── {blog_id}/
│       ├── title.jpg
│       ├── img1.jpg
│       └── ...
└── nginx/
    └── blog.conf            # nginx 블로그 설정
```

## 4. 크롤링 대상
- 네이버 블로그 (blog.naver.com)
- 추출 항목: 제목, 본문, 이미지, 작성일, 지역 키워드
- 지역 키워드 자동 추출 (제목/본문에서 지명 파싱)

## 5. SEO 최적화 규칙
- **제목**: 40자 이내, 지역명 + 서비스명 포함
- **설명**: 80자 이내, 핵심 키워드 포함
- **Schema.org**: Article + FAQ + LocalBusiness
- **OG 태그**: title, description, image, url
- **메타 키워드**: 지역명, 서비스명, 브랜드명
- **내부 링크**: 기존 블로그 상호 연결

## 6. 명령어
```bash
# 블로그 추가
python3 add_blog.py "https://blog.naver.com/hasugu2118/224304522855"

# 수동 배포 (필요시)
docker cp blog/{id}.html memo-app:/usr/share/nginx/html/blog/
docker cp blog/images/{id}/. memo-app:/usr/share/nginx/html/blog/images/{id}/
docker exec memo-app nginx -s reload
```

## 7. 우선순위
1. P1: 크롤링 + HTML 생성 스크립트
2. P2: Docker 자동 배포 연동
3. P3: sitemap.xml 자동 갱신
4. P4: 지역 키워드 자동 추출

## 8. 참고
- 기존 템플릿: /Users/lee/docker-stack/memo-app/blog-sample.html
- 기존 블로그: /Users/lee/projects/hasugu/blog/
- 배포 도메인: hasugu2.lymin80.shop
- 이미지 경로: /blog/images/{blog_id}/
