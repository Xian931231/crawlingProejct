import time
import os
from openai import OpenAI
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# 기본 .env 파일 로드
load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
print("🔑 불러온 OPENAI_API_KEY:", openai_api_key)  # 디버깅용 출력
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

client = OpenAI(api_key=openai_api_key)

# 미국 뉴욕 기준 어제 날짜 계산
yesterday_str = (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=1)).strftime("%Y-%m-%d")
print("기준 날짜 (미국 기준 어제):", yesterday_str)

try:
    # prompt.txt 파일에서 시스템 프롬프트 읽기
    with open('prompt.txt', 'r', encoding='utf-8') as f:
        system_prompt = f.read()

    # news.txt 파일에서 뉴스 내용 읽기
    with open('news.txt', 'r', encoding='utf-8') as f:
        news_content = f.read()

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": news_content
            }
        ]
    )

    kr_content = completion.choices[0].message.content
    print("\n=== 번역 결과 ===")
    print(kr_content)

except Exception as e:
    print(f"프로그램 실행 중 오류 발생: {e}")