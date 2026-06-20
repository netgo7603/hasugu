import os
import glob
import re
from datetime import datetime

blog_files = glob.glob('blog/*.html')
posts = []

for fpath in blog_files:
    try:
        mtime = os.path.getmtime(fpath)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
            title = match.group(1) if match else os.path.basename(fpath)
            title = title.replace(' - 하수구수사대', '').replace(' | 하수구수사대', '').strip()
            posts.append({'path': fpath, 'title': title, 'mtime': mtime})
    except Exception as e:
        print(f"Error reading {fpath}: {e}")

# Sort by modification time descending
posts.sort(key=lambda x: x['mtime'], reverse=True)

html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>시공사례 전체보기 | 하수구수사대</title>
    <meta name="description" content="하수구수사대의 다양한 시공사례 전체 목록입니다. 수원, 용인 등 각 지역의 하수구막힘, 누수탐지, 고압세척 작업 결과를 확인하세요.">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --dark: #111827;
            --gray-100: #f3f4f6;
            --gray-300: #d1d5db;
            --gray-500: #6b7280;
            --white: #ffffff;
        }
        body { font-family: 'Noto Sans KR', sans-serif; background: var(--gray-100); margin: 0; padding: 0; color: var(--dark); line-height: 1.6; }
        .header { background: var(--white); padding: 16px 24px; border-bottom: 1px solid var(--gray-300); text-align: center; }
        .header a { text-decoration: none; color: var(--dark); font-weight: 700; font-size: 1.2rem; }
        .container { max-width: 800px; margin: 40px auto; padding: 24px; background: var(--white); border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        h1 { font-size: 1.8rem; margin-bottom: 24px; text-align: center; border-bottom: 2px solid var(--primary); padding-bottom: 16px; }
        .post-list { list-style: none; padding: 0; margin: 0; }
        .post-list li { border-bottom: 1px solid var(--gray-100); padding: 16px 0; }
        .post-list li:last-child { border-bottom: none; }
        .post-list a { text-decoration: none; color: var(--primary); font-size: 1.1rem; font-weight: 500; transition: color 0.2s; display: block; }
        .post-list a:hover { color: #1d4ed8; text-decoration: underline; }
        .date { font-size: 0.85rem; color: var(--gray-500); margin-top: 4px; }
        .pagination { display: flex; justify-content: center; gap: 8px; margin-top: 32px; flex-wrap: wrap; }
        .page-btn { padding: 8px 12px; border: 1px solid var(--gray-300); background: var(--white); cursor: pointer; border-radius: 6px; }
        .page-btn.active { background: var(--primary); color: var(--white); border-color: var(--primary); }
        .page-btn:hover:not(.active) { background: var(--gray-100); }
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <header class="header">
        <a href="index.html">← 하수구수사대 홈으로 돌아가기</a>
    </header>
    <div class="container">
        <h1>시공사례 전체보기</h1>
        <!-- 구글 봇은 아래의 1300개 <li>를 모두 한 번에 크롤링합니다. -->
        <ul class="post-list" id="postList">
{LI_ITEMS}
        </ul>
        <div class="pagination" id="pagination"></div>
    </div>

    <script>
        const itemsPerPage = 30;
        const listItems = document.querySelectorAll('#postList li');
        const totalPages = Math.ceil(listItems.length / itemsPerPage);
        const paginationContainer = document.getElementById('pagination');

        function showPage(page) {
            listItems.forEach((li, index) => {
                li.classList.add('hidden');
                if (index >= (page - 1) * itemsPerPage && index < page * itemsPerPage) {
                    li.classList.remove('hidden');
                }
            });
            renderPagination(page);
            window.scrollTo(0, 0);
        }

        function renderPagination(currentPage) {
            paginationContainer.innerHTML = '';
            
            let startPage = Math.max(1, currentPage - 2);
            let endPage = Math.min(totalPages, startPage + 4);
            
            if (endPage - startPage < 4) {
                startPage = Math.max(1, endPage - 4);
            }

            if (currentPage > 1) {
                const prev = document.createElement('button');
                prev.className = 'page-btn';
                prev.innerText = '이전';
                prev.onclick = () => showPage(currentPage - 1);
                paginationContainer.appendChild(prev);
            }

            for (let i = startPage; i <= endPage; i++) {
                const btn = document.createElement('button');
                btn.className = 'page-btn' + (i === currentPage ? ' active' : '');
                btn.innerText = i;
                btn.onclick = () => showPage(i);
                paginationContainer.appendChild(btn);
            }

            if (currentPage < totalPages) {
                const next = document.createElement('button');
                next.className = 'page-btn';
                next.innerText = '다음';
                next.onclick = () => showPage(currentPage + 1);
                paginationContainer.appendChild(next);
            }
        }

        if(totalPages > 0) {
            showPage(1);
        }
    </script>
</body>
</html>
"""

li_items = []
for post in posts:
    date_str = datetime.fromtimestamp(post['mtime']).strftime('%Y-%m-%d')
    li = f"            <li><a href=\"{post['path']}\">{post['title']}</a><div class=\"date\">작성일: {date_str}</div></li>"
    li_items.append(li)

final_html = html_template.replace('{LI_ITEMS}', '\n'.join(li_items))

with open('blog_index.html', 'w', encoding='utf-8') as f:
    f.write(final_html)

print(f"Successfully generated blog_index.html with {len(posts)} posts.")
