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
    특정 RSS 피드에서 최신 기사 1개를 가져오는 함수
    
    Args:
        rss_url (str): RSS 피드 URL
        source_name (str): 뉴스 소스 이름
    
    Returns:
        list: 최신 기사 리스트
    """
    # RSS 피드 파싱
    feed = feedparser.parse(rss_url)
    
    # # 현재 시간을 UTC로 변환
    # now = datetime.now(pytz.UTC)
    # yesterday = now - timedelta(days=1)
    
    # 기사들을 저장할 리스트
    articles = []
    
    # 최신 기사 1개만 처리
    if len(feed.entries) > 0:
        entry = feed.entries[0]  # 첫 번째 기사만 선택
        try:
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
            
            # # 어제 날짜의 기사인지 확인
            # if yesterday.date() == pub_date.date():
            # 기사 전체 내용 가져오기
            try:
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
                    article_div = soup.find('div', {'class': ['post__content', 'post-content', 'content']})
                    if not article_div:
                        article_div = soup.find('div', {'data-role': 'article-content'})
                    if article_div:
                        # 불필요한 요소 제거
                        for div in article_div.find_all(['div', 'script', 'style']):
                            div.decompose()
                        # 본문 텍스트 추출
                        paragraphs = article_div.find_all('p')
                        article_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                
                elif source_name == 'CoinDesk':
                    # 메인 컨텐츠 영역 찾기
                    article_div = soup.find('div', {'class': ['article-body', 'article-body-text']})
                    if not article_div:
                        article_div = soup.find('div', {'data-article-content': True})
                    if article_div:
                        # 불필요한 요소 제거
                        for div in article_div.find_all(['div', 'script', 'style']):
                            div.decompose()
                        # 본문 텍스트 추출
                        paragraphs = article_div.find_all('p')
                        article_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                
                elif source_name == 'ThePieNews':
                    # 메인 컨텐츠 영역 찾기
                    article_div = soup.find('div', {'class': ['entry-content', 'article-content']})
                    if not article_div:
                        article_div = soup.find('article')
                    if article_div:
                        # 불필요한 요소 제거
                        for div in article_div.find_all(['div', 'script', 'style', 'aside']):
                            div.decompose()
                        # 본문 텍스트 추출
                        paragraphs = article_div.find_all('p')
                        article_content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                
                # 내용이 비어있으면 디버그 정보 출력
                if not article_content.strip():
                    print(f"Warning: 기사 내용을 찾을 수 없습니다. ({entry.link})")
                    print(f"페이지 HTML 구조: {soup.prettify()[:500]}...")
                
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
        with open(filename, 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(f"### 제목\n{article['title']}\n\n")
                f.write(f"### 링크\n{article['link']}\n\n")
                f.write(f"### 본문\n{article['content']}\n\n")
                f.write(f"### 발행일\n{article['published']}\n\n")
                f.write(f"### 출처\n{article['source']}\n\n")
                f.write("-" * 80 + "\n\n")
        print(f"기사가 {filename}에 저장되었습니다.")
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

def scrape_all_sources():
    """
    모든 뉴스 소스에서 어제 기사들을 스크랩하는 함수
    """
    # RSS 피드 URL 목록
    sources = {
        'CoinTelegraph': 'https://cointelegraph.com/rss',
        'CoinDesk': 'https://www.coindesk.com/arc/outboundfeeds/rss',
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