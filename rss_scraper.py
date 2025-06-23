import feedparser
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import json
import os
import requests
from bs4 import BeautifulSoup
import time

def get_yesterday_articles(rss_url, source_name):
    """
    특정 RSS 피드에서 전날의 모든 기사를 가져오는 함수
    
    Args:
        rss_url (str): RSS 피드 URL
        source_name (str): 뉴스 소스 이름
    
    Returns:
        list: 전날의 기사 리스트
    """
    # RSS 피드 파싱
    print(f"\n{source_name} RSS 피드 연결 중: {rss_url}")
    
    # User-Agent 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # feedparser에 headers 전달
    feed = feedparser.parse(rss_url, request_headers=headers)
    
    print(f"RSS 피드 상태: {feed.status if hasattr(feed, 'status') else 'Unknown'}")
    print(f"RSS 피드 제목: {feed.feed.title if hasattr(feed.feed, 'title') else 'Unknown'}")
    print(f"총 기사 수: {len(feed.entries)}")
    
    # 현재 시간을 UTC로 변환
    now = datetime.now(pytz.UTC)
    yesterday = now - timedelta(days=1)
    
    # 기존에 수집된 제목 목록 가져오기
    existing_titles = set()
    try:
        if os.path.exists('titles.txt'):
            with open('titles.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('- '):
                        existing_titles.add(line[2:].strip())
    except Exception as e:
        print(f"기존 제목 목록 읽기 실패: {e}")
    
    # 기사들을 저장할 리스트
    articles = []
    
    # 모든 기사 처리
    # for entry in feed.entries: # 전체
    for entry in feed.entries[:3]: # 각 사이트당 최신 기사 3개씩
        try:
            print(f"\n기사 처리 중: {entry.title}")
            print(f"기사 링크: {entry.link}")
            
            if 'published_parsed' in entry:
                pub_date = datetime.fromtimestamp(
                    datetime.timestamp(datetime(*entry.published_parsed[:6]))
                ).replace(tzinfo=pytz.UTC)
            elif 'updated_parsed' in entry:
                pub_date = datetime.fromtimestamp(
                    datetime.timestamp(datetime(*entry.updated_parsed[:6]))
                ).replace(tzinfo=pytz.UTC)
            else:
                pub_date = datetime.now(pytz.UTC)
            
            print(f"발행일: {pub_date}")
            print(f"기존 제목에 포함됨: {entry.title in existing_titles}")
            
            # 어제 날짜의 기사인지 확인하고, 기존에 수집되지 않은 기사인지 확인
            # if yesterday.date() == pub_date.date() and entry.title not in existing_titles:
            # 최신 기사 3개를 가져오되, 기존에 수집되지 않은 기사만 처리
            if entry.title not in existing_titles:
                try:
                    # 기사 전체 내용 가져오기
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(entry.link, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    article_content = ""
                    
                    # 각 뉴스 소스별 본문 추출 로직
                    if source_name == 'CoinTelegraph':
                        # 메인 컨텐츠 영역 찾기
                        article_div = soup.find('div', class_='post-content')
                        if not article_div:
                            article_div = soup.find('div', class_='post__content')
                        if not article_div:
                            article_div = soup.find('div', {'data-role': 'article-content'})
                        if article_div:
                            # 불필요한 요소 제거
                            for elem in article_div.find_all(['script', 'style', 'iframe', 'figure']):
                                elem.decompose()
                            # 본문 텍스트 추출
                            paragraphs = article_div.find_all(['p', 'h2', 'h3', 'blockquote'])
                            article_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                    
                    elif source_name == 'CoinDesk':
                        # 메인 컨텐츠 영역 찾기
                        article_content = ""
                        
                        print(f"CoinDesk 기사 처리 중: {entry.title}")
                        print(f"URL: {entry.link}")
                        
                        # 1. 먼저 article 태그 내에서 찾기
                        article_tag = soup.find('article')
                        if article_tag:
                            print("Article 태그 찾음")
                            # 2. 다양한 클래스명으로 본문 영역 찾기
                            content_selectors = [
                                'div[class*="article-body"]',
                                'div[class*="article-content"]', 
                                'div[class*="post-content"]',
                                'div[class*="entry-content"]',
                                'div[class*="content"]',
                                'div[class*="story-body"]',
                                'div[class*="article-text"]',
                                'main',
                                'article'
                            ]
                            
                            for selector in content_selectors:
                                content_div = soup.select_one(selector)
                                if content_div:
                                    print(f"선택자 '{selector}'로 내용 찾음")
                                    # 불필요한 요소 제거
                                    for elem in content_div.find_all(['script', 'style', 'iframe', 'figure', 'aside', 'nav', 'header', 'footer']):
                                        elem.decompose()
                                    
                                    # 본문 텍스트 추출
                                    paragraphs = content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'blockquote'])
                                    if paragraphs:
                                        article_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                                        print(f"본문 추출 완료: {len(article_content)} 문자")
                                        break
                        else:
                            print("Article 태그를 찾을 수 없음")
                        
                        # 3. article 태그에서 찾지 못한 경우 다른 방법 시도
                        if not article_content.strip():
                            print("다른 방법으로 본문 찾기 시도...")
                            # main 태그에서 직접 찾기
                            main_content = soup.find('main')
                            if main_content:
                                print("Main 태그 찾음")
                                paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'blockquote'])
                                article_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                            
                            # 여전히 없으면 모든 p 태그에서 찾기
                            if not article_content.strip():
                                print("모든 p 태그에서 찾기 시도...")
                                all_paragraphs = soup.find_all('p')
                                if all_paragraphs:
                                    article_content = '\n\n'.join([p.get_text().strip() for p in all_paragraphs if p.get_text().strip()])
                                    print(f"모든 p 태그에서 추출: {len(article_content)} 문자")
                        
                        # 4. 여전히 내용이 없으면 RSS 피드의 설명 사용
                        if not article_content.strip():
                            print("RSS 피드 설명 사용...")
                            if hasattr(entry, 'content') and entry.content:
                                article_content = entry.content[0].value
                                print("RSS content 사용")
                            elif hasattr(entry, 'description'):
                                article_content = entry.description
                                print("RSS description 사용")
                            elif hasattr(entry, 'summary'):
                                article_content = entry.summary
                                print("RSS summary 사용")
                        
                        # 5. 디버그 정보 출력 (내용이 없을 때만)
                        if not article_content.strip():
                            print(f"\nCoinDesk 기사 추출 실패: {entry.link}")
                            print("사용 가능한 태그들:")
                            for tag in soup.find_all(['article', 'main', 'div']):
                                if tag.get('class'):
                                    print(f"- {tag.name} with class: {tag.get('class')}")
                            print("HTML 구조 일부:")
                            print(soup.prettify()[:1000])
                        else:
                            print(f"CoinDesk 기사 추출 성공: {len(article_content)} 문자")
                    
                    elif source_name == 'ThePieNews':
                        # 메인 컨텐츠 영역 찾기
                        article_content = ""
                        
                        # 1. article 태그 찾기
                        article = soup.find('article')
                        if article:
                            # 2. article 내에서 entry-content 클래스를 가진 div 찾기
                            content_div = article.find('div', class_='entry-content')
                            
                            if content_div:
                                # 3. 불필요한 요소 제거
                                # 소셜 미디어 버튼 제거
                                for social in content_div.find_all('div', class_=['jp-relatedposts', 'sharedaddy', 'social-share']):
                                    social.decompose()
                                
                                # 광고 제거
                                for ad in content_div.find_all('div', class_=['advertisement', 'ad-container']):
                                    ad.decompose()
                                
                                # 관련 기사 섹션 제거
                                for related in content_div.find_all('div', class_=['related-posts', 'yarpp-related']):
                                    related.decompose()
                                
                                # 4. 본문 텍스트 추출
                                paragraphs = []
                                
                                # 모든 텍스트 컨테이너 찾기
                                for elem in content_div.find_all(['p', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol']):
                                    # 광고나 불필요한 텍스트 필터링
                                    text = elem.get_text().strip()
                                    if text and not any(skip in text.lower() for skip in [
                                        'advertisement', 
                                        'related articles', 
                                        'sponsored',
                                        'share this article',
                                        'follow us',
                                        'subscribe to our newsletter'
                                    ]):
                                        # ul/ol 태그의 경우 각 항목을 별도로 처리
                                        if elem.name in ['ul', 'ol']:
                                            items = [li.get_text().strip() for li in elem.find_all('li')]
                                            paragraphs.extend([f"• {item}" for item in items if item])
                                        else:
                                            paragraphs.append(text)
                                
                                article_content = '\n\n'.join(paragraphs)
                        
                        # 내용이 없으면 대체 방법 시도
                        if not article_content.strip():
                            # RSS 피드의 전체 내용 시도
                            if hasattr(entry, 'content') and entry.content:
                                article_content = entry.content[0].value
                            # description이나 summary 시도
                            elif hasattr(entry, 'description'):
                                article_content = entry.description
                            elif hasattr(entry, 'summary'):
                                article_content = entry.summary

                        # 디버그를 위한 정보 출력
                        if not article_content.strip():
                            print(f"\nThePieNews 기사 추출 실패: {entry.link}")
                            print("HTML 구조:")
                            if article:
                                print("Article 태그 찾음")
                                if content_div:
                                    print("Entry-content div 찾음")
                                    print("사용 가능한 태그들:")
                                    for tag in content_div.find_all(['p', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol']):
                                        print(f"- {tag.name}: {tag.get_text()[:100]}...")
                    
                    # 내용이 비어있으면 디버그 정보 출력
                    if not article_content.strip():
                        print(f"\nWarning: 기사 내용을 찾을 수 없습니다. ({entry.link})")
                        print(f"소스: {source_name}")
                        # HTML 구조 출력
                        print("\n페이지 HTML 구조 일부:")
                        print(soup.prettify()[:1500])
                        
                        # 대체 내용으로 RSS 피드의 설명 사용
                        article_content = entry.get('description', '') or entry.get('summary', '')
                    
                    # 과도한 요청 방지를 위한 딜레이
                    time.sleep(2)
                    
                    article = {
                        'title': entry.title,
                        'link': entry.link,
                        'content': article_content,
                        'published': pub_date.isoformat(),
                        'source': source_name
                    }
                    articles.append(article)
                    print(f"기사 스크랩 완료: {entry.title}")
                    
                except Exception as e:
                    print(f"기사 내용 가져오기 실패 ({entry.link}): {e}")
                    
        except Exception as e:
            print(f"기사 파싱 중 오류 발생: {e}")
    
    return articles

def save_articles_to_file(articles, filename='news.txt'):
    """
    스크랩한 기사들을 파일로 저장하는 함수
    
    Args:
        articles (list): 저장할 기사들의 리스트
        filename (str): 저장할 파일 이름
    """
    try:
        # 전체 기사 내용 저장
        with open(filename, 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(f"### 제목\n{article['title']}\n\n")
                f.write(f"### 링크\n{article['link']}\n\n")
                f.write(f"### 본문\n{article['content']}\n\n")
                f.write(f"### 발행일\n{article['published']}\n\n")
                f.write(f"### 출처\n{article['source']}\n\n")
                f.write("-" * 80 + "\n\n")
        print(f"기사가 {filename}에 저장되었습니다.")
        
        # 제목만 리스트로 추가 저장
        mode = 'a' if os.path.exists('titles.txt') else 'w'
        with open('titles.txt', mode, encoding='utf-8') as f:
            for article in articles:
                f.write(f"- {article['title']}\n")
        print(f"기사 제목이 titles.txt에 추가되었습니다.")
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

def scrape_all_sources():
    """
    모든 뉴스 소스에서 어제 기사들을 스크랩하는 함수
    """
    # RSS 피드 URL 목록
    sources = {
        'CoinTelegraph': 'https://cointelegraph.com/rss',
        'CoinDesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'ThePieNews': 'https://thepienews.com/feed/'
    }
    
    all_articles = []
    
    # 각 소스에서 기사 스크랩
    for source_name, url in sources.items():
        try:
            print(f"\n{source_name}에서 기사를 스크랩하는 중...")
            articles = get_yesterday_articles(url, source_name)
            all_articles.extend(articles)
            print(f"{source_name}에서 {len(articles)}개의 기사를 찾았습니다.")
        except Exception as e:
            print(f"{source_name} 스크랩 중 오류 발생: {e}")
    
    # 결과 저장
    if all_articles:
        save_articles_to_file(all_articles)
        print(f"\n총 {len(all_articles)}개의 기사를 스크랩했습니다.")
    else:
        print("\n어제 작성된 기사를 찾을 수 없습니다.")

if __name__ == "__main__":
    scrape_all_sources() 