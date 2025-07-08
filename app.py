from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import mysql.connector
from sqlalchemy import create_engine, text
import re
import os

app = Flask(__name__)

# ---------------------------
# MySQL 연결 및 DB/테이블 설정
# ---------------------------
def create_connection_and_setup_db():
    # 환경 변수 디버깅
    print("🔍 환경 변수 디버깅:")
    print(f"  DB_HOST: {os.environ.get('DB_HOST', 'NOT_SET')}")
    print(f"  DB_USER: {os.environ.get('DB_USER', 'NOT_SET')}")
    print(f"  DB_PASSWORD: {os.environ.get('DB_PASSWORD', 'NOT_SET')}")
    print(f"  DB_NAME: {os.environ.get('DB_NAME', 'NOT_SET')}")
    print(f"  HOST: {os.environ.get('HOST', 'NOT_SET')}")
    print(f"  PORT: {os.environ.get('PORT', 'NOT_SET')}")
    
    # 환경 변수에서 데이터베이스 설정 가져오기
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', 'q1w2e3r4')
    db_name = os.environ.get('DB_NAME', 'news')
    
    print(f"🔗 데이터베이스 연결 시도: {db_user}@{db_host}/{db_name}")
    
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        print("✅ 데이터베이스 연결 성공!")
        
        # 테이블이 없으면 생성
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(500),
                link VARCHAR(1000),
                press VARCHAR(100),
                date DATE,
                time_desc VARCHAR(50)
            )
        """)
        connection.commit()
        print("✅ 뉴스 테이블 확인/생성 완료!")
        
        return connection
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        raise e

# ---------------------------
# 뉴스 삽입 함수
# ---------------------------
def insert_news(connection, title, link, press, date, time_desc):
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO news (title, link, press, date, time_desc) VALUES (%s, %s, %s, %s, %s);",
        (title, link, press, date, time_desc)
    )
    connection.commit()

# ---------------------------
# 기존 뉴스 삭제 함수 (검색할 때마다 삭제)
# ---------------------------
def delete_existing_news(connection):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM news;")  # 기존 뉴스 모두 삭제
    connection.commit()

# ---------------------------
# 키워드 필터링 함수
# ---------------------------
def filter_news_by_keywords(news_list, include_keywords=None, exclude_keywords=None):
    """
    뉴스 목록을 포함/제외 키워드에 따라 필터링
    """
    if not include_keywords and not exclude_keywords:
        return news_list
    
    filtered_news = []
    
    for news in news_list:
        title = news['title'].lower()
        
        # 제외 키워드 체크 (하나라도 포함되면 제외)
        if exclude_keywords:
            exclude_keywords_list = [kw.strip().lower() for kw in exclude_keywords.split(',') if kw.strip()]
            if any(keyword in title for keyword in exclude_keywords_list):
                print(f"❌ 제외됨: {news['title']} (제외 키워드: {[kw for kw in exclude_keywords_list if kw in title]})")
                continue
        
        # 포함 키워드 체크 (모든 키워드가 포함되어야 함)
        if include_keywords:
            include_keywords_list = [kw.strip().lower() for kw in include_keywords.split(',') if kw.strip()]
            missing_keywords = [kw for kw in include_keywords_list if kw not in title]
            if missing_keywords:
                print(f"❌ 제외됨: {news['title']} (누락된 키워드: {missing_keywords})")
                continue
            else:
                print(f"✅ 포함됨: {news['title']} (모든 키워드 포함)")
        
        filtered_news.append(news)
    
    return filtered_news

# ---------------------------
# Nate 뉴스 크롤링 함수
# ---------------------------
def nate_news(keyword, page_count, connection):
    for page in range(1, page_count + 1):
        url = f'https://news.nate.com/search?q={keyword}&page={page}'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select('#search-option > div.search-result > ul > li')

        for article in articles:
            try:
                title = article.select_one('a > div.info > span > h2').text.replace("'", "''")
                link = article.select_one('a')['href']
                time_info = article.select_one('span.time').text.split()
                press = time_info[0]
                raw_time = time_info[1]
                time_desc = raw_time

                # 날짜 처리
                if '전' in raw_time:
                    date = datetime.today().date()
                else:
                    date = datetime.strptime(raw_time, "%Y.%m.%d").date()

                insert_news(connection, title, link, press, date, time_desc)

            except Exception as e:
                print(f"⚠️ 네이트 뉴스 크롤링 중 에러 발생: {e}")
            continue

# ---------------------------
# Daum 뉴스 크롤링 함수
# ---------------------------
def daum_news(keyword, page_count, connection):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"}
    for page in range(1, page_count + 1):
        url = f'https://search.daum.net/search?w=news&nil_search=btn&DA=PGD&enc=utf8&cluster=y&cluster_page=1&q={keyword}&p={page}'
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select('li[data-docid]')  # 뉴스 개별 항목 선택

        for article in articles:
            try:
                title_tag = article.select_one('.item-title strong.tit-g a')
                title = title_tag.text.strip().replace("'", "''") if title_tag else '제목 없음'
                link = title_tag['href'] if title_tag else '#'

                press_tag = article.select_one('.area_tit a.item-writer strong.tit_item')
                if not press_tag:
                    press_tag = article.select_one('.area_tit a.item-writer span.txt_info')
                press = press_tag.text.strip() if press_tag else '언론사 없음'

                time_tag = article.select_one('.item-contents span.txt_info')
                time_desc = time_tag.text.strip() if time_tag else '시간 정보 없음'

                # 날짜 처리
                if '전' in time_desc:
                    date = datetime.today().date()
                else:
                    try:
                        date = datetime.strptime(time_desc, "%Y.%m.%d.").date()
                    except:
                        date = datetime.today().date()

                insert_news(connection, title, link, press, date, time_desc)

            except Exception as e:
                print(f"⚠️ 다음 뉴스 크롤링 중 에러 발생: {e}")

# ---------------------------
# Flask 라우트 (웹 페이지)
# ---------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/crawl', methods=['POST'])
def crawl():
    keyword = request.form['keyword']
    page_count = int(request.form['page_count'])
    media = request.form['media']
    include_keywords = request.form.get('include_keywords', '').strip()
    exclude_keywords = request.form.get('exclude_keywords', '').strip()

    connection = create_connection_and_setup_db()

    # 기존 뉴스 삭제
    delete_existing_news(connection)

    # 검색어 구성: 기본 검색어 + 포함 키워드
    search_keyword = keyword
    if include_keywords:
        include_list = [kw.strip() for kw in include_keywords.split(',') if kw.strip()]
        # 기본 검색어와 포함 키워드를 모두 포함하는 검색어 생성
        search_keyword = f"{keyword} {' '.join(include_list)}"
        print(f"🔍 실제 검색어: {search_keyword}")

    if media == '네이트':
        nate_news(search_keyword, page_count, connection)
    elif media == '다음':
        daum_news(search_keyword, page_count, connection)
    else:
        return jsonify({'error': '지원하지 않는 포털입니다.'})

    # 크롤링된 뉴스 출력 (pandas 대신 SQLAlchemy 사용)
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', 'q1w2e3r4')
    db_name = os.environ.get('DB_NAME', 'news')
    
    engine = create_engine(f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}')
    
    # pandas 대신 SQLAlchemy로 데이터 조회
    result = engine.execute(text('SELECT * FROM news ORDER BY date DESC'))
    news_list = []
    for row in result:
        news_list.append({
            'title': row.title,
            'link': row.link,
            'press': row.press,
            'date': row.date.isoformat() if row.date else None,
            'time_desc': row.time_desc
        })
    
    print(f"📊 크롤링된 총 뉴스 수: {len(news_list)}")
    
    # 키워드 필터링 적용
    filtered_news = filter_news_by_keywords(news_list, include_keywords, exclude_keywords)
    
    print(f"🔍 필터링 후 뉴스 수: {len(filtered_news)}")
    if include_keywords:
        print(f"✅ 포함 키워드: {include_keywords}")
    if exclude_keywords:
        print(f"❌ 제외 키워드: {exclude_keywords}")

    # JSON 응답으로 뉴스 전달
    return jsonify(filtered_news)

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🌐 서버 시작: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
