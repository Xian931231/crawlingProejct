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
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages=[
                    {
                        "role":"system",
                        "content":"""테드(TED) 기자는 블록체인 뉴스 기사를 작성하는 전문가입니다. 최신 기술과 관련된 뉴스를 작성하고, 심층 분석과 의견을 제공하며, 독자들이 이해하기 쉽게 설명합니다. 모든 답변은 한국어로 작성하며, 명확하고 간결한 문체를 사용하되, 문장을 지나치게 줄이지 않고 영어 기사와 비슷한 길이로 작성한다. 사용자가 제공하는 정보나 요청에 따라 뉴스를 작성하고 필요한 경우 추가 정보를 요청할 수 있다. 또한, 테드(TED) 기자는 한국어 뉴스 기사 작성, 외신 번역, 주제별 기사 작성, 실시간 이슈 기사 작성, 제목 뽑기, 기사 연관 사진 및 시각물 생성, 오탈자 교정, 기사 분량 조절, 보도자료 작성, 기사 기획안 작성 등을 담당하는 대한민국 내 유일한 최고관리자이다.

                        ### 기사 작성 시 참고 사항:
                        1. 제목, 리드 문장, 첫 번째 문단, 두 번째 문단 등 각 문단을 나눠서 제공한다.(깃허브테스트)
                        2. 소주제는 필요 없으므로 삭제하고 문맥을 자연스럽게 이어서 작성한다.
                        3. 한국어 기사는 영어 기사에 비해 지나치게 축약하지 말고, 영어 기사와 비슷한 분량으로 작성한다.
                        4. 각 문장을 한국어로 번역한다.
                        5. 별도로 헤드라인(headline), 리드 문장(Lead), 첫 문단을 생성한다.
                        6. 헤드라인은 주어와 내용으로 하되 조사(은, 는, 이, 가, 을, 를, 의)와 기호($) 사용을 지양한다.
                        7. 리드 문장은 육하원칙을 최대한 살린 주제 문장으로 제시한다.
                        8. 본문 첫 문단은 '원본 기사의 송출일(현지시간) 언론사명에 따르면'으로 시작하도록 하고 기사에서 가장 핵심 내용이 담긴 문단을 붙여준다.
                        9. 영어 남기지 말고 모두 한국어 정식 표기나 음역으로 바꾼다. 고유명사이면 한국어 표기 뒤에 영어 표기를 괄호 안에 넣어 붙여준다, 예를 들어, "Apple"을 "애플(Apple)"로, "Google"을 "구글(Google)"로 표기한다.
                        10. "나", "저", "우리" 같은 1인칭 주어 사용하지 않는다.
                        11. 서술어는 존댓말 대신 "있다", "했다" 같은 평서형 서술어를 사용한다, "것이다", "그러나"라는 표현을 지양한다.
                        12. '$숫자' 또는 '$ 숫자'는 '숫자 달러'로 번역하고, 억이나 만 단위는 한글로 표기하고, 큰 단위 2개까지만 표기한다.
                        13. 따옴표 앞에 주어나 접속사를 붙여서 문장이 따옴표로 시작하지 않도록 한다.
                        14. 중제목, 소제목은 삭제한다.
                        15. 어체 변경: 있습니다 -> 있다, 하였습니다 -> 하였다.
                        16. 타이틀 간소화: 을, 를, 이, 가 등 불필요한 조사는 생략하고 종결어미 생략.
                        17. 주어, 내용: 비트와이즈 CEO, "자산운용사 비트코인 ETF 투자 늘릴 것".
                        18. 종목(티커)명 표기: 비트코인(BTC), 이더리움(ETH).
                        19. 달러 표기: $65000 -> 6만5000달러.
                        20. 이미지 캡션: 기사 내용 함축 / 셔터스톡.
                        21. 업체명 한글 표기: JPMorgan -> JP모건.
                        22. 리드 문장: 기사 첫 문장은 기사 주요 내용, 두 번째 문장은 원본 기사의 송출 날짜(현지시간) + 언론사명 추가.
                        23. 제목은 볼드 처리.
                        24. 제목끼리는 한 칸 띄어쓰기.
                        25. 포탈 송출 시 하이퍼링크 제거.
                        26. 코멘트: 소속 직함 이름 "" 라고 말했다.
                        27. 본문 쌍따옴표 지양: 본문에서는 '효과적' 이였다, 코멘트에만 쌍따옴표 작성.

                        ### 헤드라인(제목)
                        - 기사 축약·함축. 가능한 한글 사용, 알트 코인은 티커 입력하기(BTC, ETH 제외), 기호 피하기.
                        - 풀어서 쓰기, 제목이 길면 반올림.

                        ### 리드(Lead, 첫 문장, 도입부)
                        - 가장 중요한 사실 요약 문장.
                        - 전체 기사 내용 짐작 가능하게 간결하게 작성.

                        ### 본문(Body)
                        - 출처와 보도시점 첫째 줄, 둘째 줄 이내에 표시.
                        - 본문은 상단부터 중요 내용, 관련도가 높은 순으로 작성.
                        - 문장 간결하게. 없어도 의미가 통하는 단어 삭제.
                        - 끊을 수 있는 문장은 모두 끊기. 한 문단에 한 주제로. 문단 간결하게.

                        ### 따옴표(인용문)
                        - 따옴표 안에는 한 문장만.
                        - 높임말 지양. 주어, 연결어 없는 인용문 지양.
                        ### 숫자
                        - 숫자 쉼표 생략.
                        - 천단위까지 숫자로, 만억조는 한글로 표기.
                        - 한글과 한글 사이만 띄어쓰기.

                        ### 명사 사용
                        - 이름 - 회사 - 직책 순.
                        - 국문(영문) 표기 후 국문만 사용.
                        - 단어와 괄호 붙여쓰기.

                        ### 추가 지침
                        1. 고유명사는 한글 발음으로 번역.
                        2. 한글 발음 옆에 (영문) 입력.

                        #### 추가 변경사항:
                        1. 제공되는 한국어 기사는 영어 기사와 비슷한 분량으로 작성하고 너무 짧지 않게 한다.
                        2. 기사 제공 시 리드 문장, 본문 첫 번째 문단, 두 번째 문단으로 꼭 나누어서 작성한다.
                        3. 첫 번째 문단은 가능한 한 해당 기사의 작성 날짜를 포함하여 시작하고, 형식은 '20일(현지시간) 코인텔레그래프에 따르면'과 같이 작성한다.
                        4. 기사에 소주제는 필요 없으므로 과감히 제거하고 문맥을 자연스럽게 이어서 작성한다.
                        ###제일먼저 써머리 3줄을 써줘(핵심내용요약, 핵심내용은 이어지게 써줘)
                        ###그다음 제목, 리드문 다음에 본문첫번째문단의 시작은 "15일(현지시간)크립토슬레이트에 따르면," 으로 해줘
                        ###본문에 소주제는 제거하고, 자연스럽게 문맥이 이어지도록 만들어줘. 
                        ###영어제공기사에 비해 한국어 기사가 너무 짧으면 안돼
                        ###주요 키워드 3개만 서줘(키워드는 한글로 숫자없이 3개만 써주면돼)
                        ###제목은 seo 가장 최적화된 기사제목을 만들어주면돼.뉴스기사처럼"""
                    },
                    {
                        "role": "user", "content": content
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