let allNews = [];
let currentPage = 1;
const itemsPerPage = 15;

// 폼 제출 시 실행
document.getElementById('crawl-form').addEventListener('submit', function(event) {
    event.preventDefault();

    // 초기화
    const newsResults = document.getElementById('news-results');
    const pagination = document.getElementById('pagination');
    newsResults.innerHTML = '';
    pagination.innerHTML = '';

    const loading = document.getElementById('loading');
    loading.style.display = 'block';

    // 입력값 수집
    const media = document.getElementById('media').value;
    const keyword = document.getElementById('keyword').value;
    const includeKeywords = document.getElementById('include_keywords').value;
    const excludeKeywords = document.getElementById('exclude_keywords').value;
    const pageCount = document.getElementById('page_count').value;

    // 서버 요청
    fetch('/crawl', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            media: media,
            keyword: keyword,
            include_keywords: includeKeywords,
            exclude_keywords: excludeKeywords,
            page_count: pageCount
        })
    })
    .then(response => response.json())
    .then(data => {
        loading.style.display = 'none';

        if (data.error) {
            newsResults.innerHTML = `<p>${data.error}</p>`;
        } else {
            // 최신순 정렬 추가 (날짜 기준 내림차순)
            allNews = data.sort((a, b) => new Date(b.date) - new Date(a.date));

            currentPage = 1;
            renderPage(currentPage);
            setupPagination();
            
            // 검색 결과 개수 표시
            const resultCount = document.createElement('div');
            resultCount.className = 'result-count';
            resultCount.innerHTML = `<p>총 ${allNews.length}개의 뉴스를 찾았습니다.</p>`;
            newsResults.insertBefore(resultCount, newsResults.firstChild);
        }
    })
    .catch(error => {
        loading.style.display = 'none';
        newsResults.innerHTML = `<p>검색 중 오류가 발생했습니다. 다시 시도해주세요.</p>`;
        console.error('Error:', error);
    });
});

// 뉴스 렌더링
function renderPage(page) {
    const newsResults = document.getElementById('news-results');
    
    // 결과 개수 표시는 유지하고 뉴스 리스트만 초기화
    const existingResultCount = newsResults.querySelector('.result-count');
    newsResults.innerHTML = '';
    if (existingResultCount) {
        newsResults.appendChild(existingResultCount);
    }

    const start = (page - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageItems = allNews.slice(start, end);

    const newsList = document.createElement('ul');
    pageItems.forEach(news => {
        const listItem = document.createElement('li');
        listItem.innerHTML = `
            <a href="${news.link}" target="_blank">${news.title}</a><br>
            <span>${news.press} | ${news.time_desc}</span>
        `;
        newsList.appendChild(listItem);
    });

    newsResults.appendChild(newsList);
}

// 페이지네이션 버튼 구성
function setupPagination() {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    const pageCount = Math.ceil(allNews.length / itemsPerPage);

    // 이전 버튼
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '이전';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderPage(currentPage);
            setupPagination();
        }
    });
    pagination.appendChild(prevBtn);

    // 페이지 숫자 버튼
    for (let i = 1; i <= pageCount; i++) {
        const button = document.createElement('button');
        button.textContent = i;
        button.className = (i === currentPage) ? 'active' : '';
        button.addEventListener('click', () => {
            currentPage = i;
            renderPage(currentPage);
            setupPagination();
        });
        pagination.appendChild(button);
    }

    // 다음 버튼
    const nextBtn = document.createElement('button');
    nextBtn.textContent = '다음';
    nextBtn.disabled = currentPage === pageCount;
    nextBtn.addEventListener('click', () => {
        if (currentPage < pageCount) {
            currentPage++;
            renderPage(currentPage);
            setupPagination();
        }
    });
    pagination.appendChild(nextBtn);
}
