import time
import json
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from zoneinfo import ZoneInfo

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
        except:
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
        content = get_article_content_by_selenium(driver, summary["link"])
        results.append({
            "title": summary["title"],
            "link": summary["link"],
            "date": summary["date"],
            "content": content
        })

    # 저장
    file_name = f"cointelegraph_yesterday_{yesterday_str}.json"
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(results)}개의 뉴스를 저장했습니다: {file_name}")

finally:
    driver.quit()