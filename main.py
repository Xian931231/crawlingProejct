import os
from datetime import datetime
from dotenv import load_dotenv
from rss_scraper import scrape_all_sources
from openai import OpenAI
import requests
import time
import json
import re

# .env 파일 로드
load_dotenv()

# 환경 변수 로드
openai_api_key = os.getenv('OPENAI_API_KEY')
wp_url = os.getenv('WP_URL')
wp_user = os.getenv('WP_USER')
wp_pass = os.getenv('WP_APP_PASSWORD')

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=openai_api_key)

def validate_environment():
    """환경 변수 검증"""
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    if not all([wp_url, wp_user, wp_pass]):
        raise ValueError("WordPress 인증 정보가 .env 파일에 설정되어 있지 않습니다.")

def post_to_wordpress(title, content, lead, status='draft'):
    """WordPress에 포스트를 업로드하는 함수"""
    api_url = f"{wp_url}/wp-json/wp/v2/posts"
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    data = {
        'title': title,
        'content': content,
        'excerpt': lead,
        'status': status,
        'categories': [2],
        # 'meta_input': {
        #     'keyword': keyword
        # }
    }
    
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=headers,
            auth=(wp_user, wp_pass)
        )
        
        if response.status_code == 201:
            print(f"WordPress에 포스트가 성공적으로 업로드되었습니다. (상태: {status})")
            return response.json()
        else:
            print(f"WordPress 업로드 실패. 상태 코드: {response.status_code}")
            print(f"오류 메시지: {response.text}")
            return None
            
    except Exception as e:
        print(f"WordPress 업로드 중 오류 발생: {e}")
        return None

def translate_and_format(news_content):
    """뉴스 내용을 번역하고 포맷팅하는 함수"""
    try:
        # prompt.txt 파일에서 시스템 프롬프트 읽기
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            system_prompt = f.read()

        # GPT를 사용하여 번역 (GPT-4 대신)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": news_content
                }
            ],
            temperature=0.7,  # 번역의 창의성 조절
            max_tokens=4000   # 최대 토큰 수 제한
        )

        kr_content = completion.choices[0].message.content
        print(f"kr_content: {kr_content}")
        
        # 코드 블록(```json ... ```)이 있으면 제거
        if kr_content.strip().startswith("```"):
            kr_content = re.sub(r"^```[a-zA-Z]*\s*", "", kr_content.strip())
            if kr_content.strip().endswith("```"):
                kr_content = kr_content.strip()[:-3].strip()

        # JSON 형식인지 확인
        is_json = False
        try:
            # JSON 형식인지 시도
            article_json = json.loads(kr_content)
            is_json = True
        except json.JSONDecodeError:
            is_json = False

        title = ''
        lead = ''
        content = ''

        if is_json:
            # JSON 형식 처리
            title = article_json.get('title', '').strip()
            lead = article_json.get('lead', '').strip()
            content = article_json.get('content', '').strip()
        else:
            # 일반 문자열 형식 처리
            try:
                # title 추출
                if 'title:' in kr_content:
                    title_parts = kr_content.split('lead:')
                    title = title_parts[0].replace('title:', '').strip()
                elif '### 제목' in kr_content:
                    title_parts = kr_content.split('### 리드' if '### 리드' in kr_content else '### 본문')
                    title = title_parts[0].split('### 제목')[-1].strip()
                elif '**제목**' in kr_content:
                    title_parts = kr_content.split('**리드**' if '**리드**' in kr_content else '**본문**')
                    title = title_parts[0].split('**제목**')[-1].strip()
                # lead 추출
                if 'lead:' in kr_content:
                    lead_parts = kr_content.split('content:')
                    lead = lead_parts[0].split('lead:')[1].strip()
                elif '### 리드' in kr_content:
                    lead_parts = kr_content.split('### 본문')
                    lead = lead_parts[0].split('### 리드')[-1].strip()
                elif '**리드**' in kr_content:
                    lead_parts = kr_content.split('**본문**')
                    lead = lead_parts[0].split('**리드**')[-1].strip()
                # content 추출
                if 'content:' in kr_content:
                    content = kr_content.split('content:')[1].strip()
                elif '### 본문' in kr_content:
                    content_parts = kr_content.split('### 본문')
                    if len(content_parts) > 1:
                        content = content_parts[1].strip()
                        # 다음 섹션이 있다면 그 전까지만 추출
                        next_section = content.find('###')
                        if next_section != -1:
                            content = content[:next_section].strip()
                elif '**본문**' in kr_content:
                    content_parts = kr_content.split('**본문**')
                    if len(content_parts) > 1:
                        content = content_parts[1].strip()
                        # 다음 섹션이 있다면 그 전까지만 추출
                        next_section = content.find('**')
                        if next_section != -1:
                            content = content[:next_section].strip()
            except Exception as parsing_error:
                print(f"번역 결과 파싱 중 오류 발생: {parsing_error}")
                print(f"원본 번역 결과: {kr_content}")
                return None, None, None

        print("\n=== 파싱 결과 ===")


        if not all([title, lead, content]):
            print("경고: 일부 필드가 비어 있습니다.")
            print(f"비어있는 필드: {[field for field, value in {'title': title, 'lead': lead, 'content': content}.items() if not value]}")
            return None, None, None

        return title, lead, content
        
    except Exception as e:
        if 'insufficient_quota' in str(e):
            print("OpenAI API 할당량이 초과되었습니다. 계정의 사용량과 결제 상태를 확인해주세요.")
            print("https://platform.openai.com/account/usage 에서 현재 사용량을 확인할 수 있습니다.")
        else:
            print(f"번역 중 오류 발생: {e}")
        return None, None, None

def process_news():
    """뉴스 스크래핑, 번역, 포스팅을 처리하는 메인 함수"""
    try:
        # 환경 변수 검증
        validate_environment()
        
        # 뉴스 스크래핑
        print("\n1. 뉴스 스크래핑 시작...")
        scrape_all_sources()
        
        # news.txt 파일 읽기
        print("\n2. 스크래핑된 뉴스 읽기...")
        with open('news.txt', 'r', encoding='utf-8') as f:
            news_content = f.read()
        
        # 각 기사 분리 (구분자로 분리)
        articles = news_content.split("-" * 80)

        for article in articles:
            if not article.strip():
                continue
                
            print("\n3. 기사 번역 및 포맷팅 중...")
            title, lead, content = translate_and_format(article)

            # 예외 발생 등으로 하나라도 None이거나 비어있으면 건너뜀
            if not all([title, lead, content]):
                print("이 기사는 번역/파싱 오류로 건너뜁니다.")
                continue

            print(f"title: {title}")
            print(f"lead: {lead}")
            print(f"content: {content}")

            print("\n4. WordPress에 포스팅 중...")
            result = post_to_wordpress(title, content, lead)
            if result:
                print(f"포스트 ID: {result['id']}")
                print(f"포스트 링크: {result['link']}")
            time.sleep(5)
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")

# 테스트용 
def process_news_test():
    """뉴스 스크래핑, 번역, 포스팅을 처리하는 메인 함수"""
    try:
        # 환경 변수 검증
        validate_environment()
        
        # news.txt 파일 읽기
        print("\n2. 스크래핑된 뉴스 읽기...")
        with open('news.txt', 'r', encoding='utf-8') as f:
            news_content = f.read()
        
        # 각 기사 분리 (구분자로 분리)
        articles = news_content.split("-" * 80)

        for article in articles:
            if not article.strip():
                continue
                
            print("\n3. 기사 번역 및 포맷팅 중...")
            title, lead, content = translate_and_format(article)

            # 예외 발생 등으로 하나라도 None이거나 비어있으면 건너뜀
            if not all([title, lead, content]):
                print("이 기사는 번역/파싱 오류로 건너뜁니다.")
                continue

            print(f"title: {title}")
            print(f"lead: {lead}")
            print(f"content: {content}")

            print("\n4. WordPress에 포스팅 중...")
            result = post_to_wordpress(title, content, lead)
            if result:
                print(f"포스트 ID: {result['id']}")
                print(f"포스트 링크: {result['link']}")
            time.sleep(5)
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")

if __name__ == "__main__":
    process_news() 
    # process_news_test()