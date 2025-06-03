import time
import os
import requests
from openai import OpenAI
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import json

# 기본 .env 파일 로드
load_dotenv()

# 환경 변수 로드
openai_api_key = os.getenv('OPENAI_API_KEY')
wp_url = os.getenv('WP_URL')  # WordPress 사이트 URL (예: https://your-site.com)
wp_user = os.getenv('WP_USER')  # WordPress 사용자명
wp_pass = os.getenv('WP_APP_PASSWORD')  # WordPress 응용 프로그램 비밀번호

print("🔑 불러온 OPENAI_API_KEY:", openai_api_key)  # 디버깅용 출력
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

if not all([wp_url, wp_user, wp_pass]):
    raise ValueError("WordPress 인증 정보가 .env 파일에 설정되어 있지 않습니다.")

client = OpenAI(api_key=openai_api_key)

#WordPress에 포스트를 업로드하는 함수
def post_to_wordpress(title, content, lead,status='draft'):
    
    # status  = publish 면 즉시 개시
    # status  = draft 면 초안으로 저장
    # status  = private 면 비공개로 저장
    # status  = future 면 예약 개시
    # status  = pending 면 승인 대기
    # status  = trash 면 삭제
    # status  = auto-draft 면 자동 초안
    # status  = inherit 면 상속
    # status  = request-pending 면 요청 대기


    api_url = f"{wp_url}/wp-json/wp/v2/posts"
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    data = {
        'title': title,
        'content': content,
        'excerpt': lead,
        'status': status,  # 'draft' 또는 'publish'
    }
    
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=headers,
            auth=(wp_user, wp_pass)
        )
        
        if response.status_code == 201:  # 성공적으로 생성됨
            print(f"WordPress에 포스트가 성공적으로 업로드되었습니다. (상태: {status})")
            return response.json()
        else:
            print(f"WordPress 업로드 실패. 상태 코드: {response.status_code}")
            print(f"오류 메시지: {response.text}")
            return None
            
    except Exception as e:
        print(f"WordPress 업로드 중 오류 발생: {e}")
        return None

# 미국 뉴욕 기준 어제 날짜 계산
# yesterday_str = (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=1)).strftime("%Y-%m-%d")
# print("기준 날짜 (미국 기준 어제):", yesterday_str)

try:
    # prompt.txt 파일에서 시스템 프롬프트 읽기
    with open('prompt.txt', 'r', encoding='utf-8') as f:
        system_prompt = f.read()

    # news.txt 파일에서 뉴스 내용 읽기
    with open('news.txt', 'r', encoding='utf-8') as f:
        news_content = f.read()

    # GPT-4를 사용하여 번역
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": news_content
            },
            
        ]
    )

    kr_content = completion.choices[0].message.content
    print("\n=== 번역 결과 ===")
    print(kr_content)

    # 번역 결과를 각 부분으로 분리
    title = ''
    lead = ''
    content = ''
    
    # title 추출
    if 'title:' in kr_content:
        title_parts = kr_content.split('lead:')
        title = title_parts[0].replace('title:', '').strip()
    
    # lead 추출
    if 'lead:' in kr_content:
        lead_parts = kr_content.split('content:')
        lead = lead_parts[0].split('lead:')[1].strip()
    
    # content 추출 (content: 이후의 모든 내용)
    if 'content:' in kr_content:
        content = kr_content.split('content:')[1].strip()
    
    print("\n=== 파싱된 결과 ===")
    print("제목:", title)
    print("리드:", lead)
    print("본문:", content)

    #워드프로세스 포스트 업로드
    result = post_to_wordpress(title, f"{content}", lead)
    
    if result:
        print(f"포스트 ID: {result['id']}")
        print(f"포스트 링크: {result['link']}")

except Exception as e:
    print(f"프로그램 실행 중 오류 발생: {e}")