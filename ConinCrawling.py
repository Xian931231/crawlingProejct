import time
import json
import os
from openai import OpenAI
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

# 미국 뉴욕 기준 어제 날짜
yesterday_str = (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=1)).strftime("%Y-%m-%d")
print("기준 날짜 (미국 기준 어제):", yesterday_str)

# 크롬 드라이버 옵션 설정
chrome_options = Options()
# chrome_options.add_argument("--headless")  # 필요 시 주석 해제
driver = webdriver.Chrome(options=chrome_options)

def get_article_content_by_selenium(driver, url):
    try:
        driver.get(url)
        time.sleep(1.5)

        content_div = driver.find_element(By.CSS_SELECTOR, "div.post-content.relative")
        content_elements = content_div.find_elements(By.XPATH, ".//*")

        content = []
        for elem in content_elements:
            class_attr = elem.get_attribute("class") or ""
            if "post-content__disclaimer" in class_attr:
                break
            tag = elem.tag_name.lower()
            if tag in ["p", "li", "blockquote"]:
                text = elem.text.strip()
                if text:
                    content.append(text)
        return "\n".join(content)
    except Exception as e:
        print(f"[본문 수집 실패] {url} | 에러: {e}")
        return ""

try:
    url = "https://cointelegraph.com/tags/markets"
    driver.get(url)
    time.sleep(2)

    # 스크롤 5번
    for _ in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(0.5)

    news_items = driver.find_elements(By.CSS_SELECTOR, "ul > li[data-testid='posts-listing__item']")

    # 1차로 제목/링크/날짜만 추출
    news_summaries = []
    for item in news_items:
        try:
            title = item.find_element(By.CSS_SELECTOR, ".post-card-inline__title").text.strip()
            link = item.find_element(By.CSS_SELECTOR, "a.post-card-inline__title-link").get_attribute("href")
            if link and link.startswith("/"):
                link = "https://cointelegraph.com" + link
            date = item.find_element(By.CSS_SELECTOR, "time.post-card-inline__date").get_attribute("datetime")
        except Exception as e:
            print(f"기사 정보 추출 실패: {e}")
            continue

        if date == yesterday_str:
            print(" 기사 수집 대상:", title)
            news_summaries.append({
                "title": title,
                "link": link,
                "date": date
            })

    # 2차로 본문 추가 수집
    results = []
    for summary in news_summaries:
        try:
            content = get_article_content_by_selenium(driver, summary["link"])

            system_content = """당신은 블록체인 뉴스 기사를 작성하는 전문가입니다. 최신 기술과 관련된 뉴스를 작성하고, 심층 분석과 의견을 제공하며, 독자들이 이해하기 쉽게 설명합니다.

            
            
### 기사 작성 요구사항:
1. 핵심 내용 요약:
   - 기사 맨 앞에 3줄로 핵심 내용을 요약
   - 요약은 서로 자연스럽게 이어지도록 작성
   - "###핵심내용요약" 제목으로 시작


   

   



   
2. 기사 구조:
   - SEO 최적화된 뉴스 기사 형식의 제목
   - 리드 문장 (전체 내용을 함축하는 첫 문장)
   - 본문 첫 문단은 "15일(현지시간) 크립토슬레이트에 따르면,"으로 시작
   - 소주제 없이 자연스러운 문맥 흐름
   - 영어 원문과 비슷한 분량 유지

3. 키워드:
   - 주요 키워드 3개 (한글로만 작성, 숫자 제외)
   - "###주요키워드" 제목으로 시작

4. 기타 지침:
   - 모든 답변은 한국어로 작성
   - 명확하고 간결한 문체 사용
   - 영어는 한국어 정식 표기나 음역으로 변환
   - 금액은 '숫자 달러'로 표기
   - 인용문 앞에 문맥 제공
   - 전문 용어는 설명 추가"""

            completion = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": system_content
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )

            kr_content = completion.choices[0].message.content
            print("번역 : ", kr_content)

            results.append({
                "title": summary["title"],
                "link": summary["link"],
                "date": summary["date"],
                "content": content,
                "kr_content": kr_content
            })
        except Exception as e:
            print(f"기사 처리 중 오류 발생: {e}")
            continue

    # 저장
    file_name = f"cointelegraph_yesterday_{yesterday_str}.json"
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(results)}개의 뉴스를 저장했습니다: {file_name}")

except Exception as e:
    print(f"프로그램 실행 중 오류 발생: {e}")

finally:
    driver.quit()