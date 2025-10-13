import os
from datetime import datetime
from dotenv import load_dotenv
from rss_scraper import scrape_all_sources
from openai import OpenAI
import requests
import time
import json
import re
import base64
from io import BytesIO
from PIL import Image

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

def validate_seo_optimization(title, lead, content):
    """SEO 최적화 점수 계산"""
    score = 0
    
    # 제목 길이 검증 (30-60자)
    if 30 <= len(title) <= 60:
        score += 20
    else:
        print(f" 제목 길이 부적절: {len(title)}자 (권장: 30-60자)")
    
    # 리드 길이 검증 (150-160자)
    if 150 <= len(lead) <= 160:
        score += 20
    else:
        print(f" 리드 길이 부적절: {len(lead)}자 (권장: 150-160자)")
    
    # 제목에 키워드 포함 여부
    if any(keyword in title.lower() for keyword in ['비트코인', '이더리움', '암호화폐', '블록체인', '코인']):
        score += 15
    
    # 리드에 키워드 포함 여부
    if any(keyword in lead.lower() for keyword in ['비트코인', '이더리움', '암호화폐', '블록체인', '코인']):
        score += 15
    
    # HTML 구조 검증
    if '<p>' in content and '<br>' in content:
        score += 10
    
    # 숫자 포함 여부 (신뢰도)
    if any(char.isdigit() for char in title):
        score += 10
    
    # 현재성 키워드 포함
    if any(keyword in title for keyword in ['2025', '최신', '오늘', '급상승', '돌파']):
        score += 10
    
    return min(score, 100)

def generate_meta_description(title, lead):
    """메타 설명 생성 (150-160자)"""
    # 리드가 적절한 길이면 사용, 아니면 제목 기반으로 생성
    if 150 <= len(lead) <= 160:
        return lead
    else:
        # 제목 + 간단한 설명으로 메타 설명 생성
        base_text = f"{title}. 최신 암호화폐 뉴스와 시장 분석을 제공합니다."
        if len(base_text) <= 160:
            return base_text
        else:
            return base_text[:157] + "..."

def extract_focus_keyword(title):
    """제목에서 포커스 키워드 추출"""
    keywords = ['비트코인', '이더리움', '암호화폐', '블록체인', '코인', '가격', '뉴스']
    for keyword in keywords:
        if keyword in title:
            return keyword
    return '암호화폐'

def optimize_content_structure(content):
    """콘텐츠 구조 SEO 최적화"""
    # H2, H3 태그 추가 (간단한 예시)
    optimized_content = content
    
    # 첫 번째 문단을 H2로 감싸기
    if '<p>' in content:
        first_p = content.split('<p>')[1].split('</p>')[0] if '</p>' in content else ""
        if first_p and len(first_p) > 20:
            # 첫 번째 문단을 H2로 변경
            optimized_content = content.replace(f'<p>{first_p}</p>', f'<h2>{first_p}</h2>', 1)
    
    return optimized_content

def generate_image_with_dalle(title, content, lead, return_url_only=False):
    """DALL-E를 사용하여 뉴스 기사에 맞는 이미지를 생성하는 함수"""
    try:
        # 이미지 생성을 위한 프롬프트 생성
        # 뉴스 기사 이미지: {title}
        
        # 기사 요약: ...
        
        # 전문적이고 신뢰할 수 있는 뉴스 이미지를 생성해주세요. 
        # - 기사 요약을 분석해서 관련된 이미지를 생성해주세요.
        # - 깔끔하고 현대적인 디자인
        # - 뉴스 매체에 적합한 색상 (주로 파란색, 회색, 흰색 톤)
        # - 관련 아이콘이나 그래픽 요소 포함
        # - 16:9 비율의 와이드 이미지

        image_prompt = f"""


        Create a high-quality, realistic editorial-style image that visually represents the following news topic:

        "{lead[:200]}"

        The image must have a 16:9 wide aspect ratio suitable for online news banners or thumbnails.
        Make it photojournalistic, realistic, and neutral in tone — like an image used by major global news outlets.
        Avoid any text, logos, watermarks, or overly stylized filters.
        Use natural lighting, balanced colors, and professional composition.


        """
        
        print("DALL-E를 사용하여 이미지 생성 중...")
        
        # DALL-E API 호출
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt.strip(),
            size="1792x1024",  # 16:9 비율
            quality="standard",
            n=1
        )
        
        # 생성된 이미지 URL 가져오기
        image_url = response.data[0].url
        print(f"이미지 생성 완료: {image_url}")
        
        # URL만 반환하는 경우
        if return_url_only:
            return image_url
        
        # 이미지 다운로드
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            return image_response.content
        else:
            print(f"이미지 다운로드 실패: {image_response.status_code}")
            return None
            
    except Exception as e:
        print(f"이미지 생성 중 오류 발생: {e}")
        return None

def upload_image_to_wordpress(image_data, filename="news_image.jpg"):
    """WordPress에 이미지를 업로드하는 함수"""
    try:
        # WordPress 미디어 업로드 API 엔드포인트
        media_url = f"{wp_url}/wp-json/wp/v2/media"
        
        # 파일명에 타임스탬프 추가하여 중복 방지 (영문만 사용)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_news_image.jpg"  # 한글 제거하고 영문만 사용
        
        # 멀티파트 폼 데이터로 이미지 업로드
        files = {
            'file': (safe_filename, image_data, 'image/jpeg')
        }
        
        # Content-Disposition 헤더에서 한글 제거
        headers = {
            'Content-Disposition': f'attachment; filename="{safe_filename}"'
        }
        
        print(f"이미지 업로드 시도 중... (파일명: {safe_filename})")
        
        response = requests.post(
            media_url,
            files=files,
            headers=headers,
            auth=(wp_user, wp_pass),
            timeout=30  # 타임아웃 설정
        )
        
        print(f"이미지 업로드 응답 상태: {response.status_code}")
        
        if response.status_code == 201:
            media_data = response.json()
            print(f"이미지 업로드 성공!")
            print(f"미디어 ID: {media_data['id']}")
            print(f"이미지 URL: {media_data['source_url']}")
            return media_data['id'], media_data['source_url']
        else:
            print(f"이미지 업로드 실패: {response.status_code}")
            print(f"오류 메시지: {response.text[:500]}...")  # 오류 메시지 길이 제한
            return None, None
            
    except Exception as e:
        print(f"이미지 업로드 중 오류 발생: {e}")
        return None, None

def post_to_wordpress(title, content, lead, status='draft', featured_media_id=None, image_url=None, tags=None):
    """WordPress에 포스트를 업로드하는 함수 (SEO 최적화)"""
    api_url = f"{wp_url}/wp-json/wp/v2/posts"
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }
    
    # HTML 태그를 보존하면서 안전하게 처리
    safe_title = title if title else ""
    safe_content = content if content else ""
    safe_lead = lead if lead else ""
    
    # SEO 최적화 검증
    seo_score = validate_seo_optimization(safe_title, safe_lead, safe_content)
    print(f"SEO 점수: {seo_score}/100")
    
    # 이미지 URL이 있으면 content에 이미지 추가 (SEO 최적화)
    if image_url:
        # 이미지 alt 텍스트를 제목 기반으로 생성
        image_alt = safe_title[:50] + "..." if len(safe_title) > 50 else safe_title
        image_title = f"{safe_title} - 관련 이미지"
        
        image_html = f'''<div class="featured-image" style="text-align: center; margin: 20px 0;">
            <img src="{image_url}" 
                 alt="{image_alt}" 
                 title="{image_title}"
                 style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
        </div>'''
        safe_content = image_html + safe_content
        print(f"SEO 최적화된 이미지가 content에 추가되었습니다: {image_url}")
    
    # SEO 최적화된 메타데이터 생성
    meta_description = generate_meta_description(safe_title, safe_lead)
    focus_keyword = extract_focus_keyword(safe_title)
    
    data = {
        'title': safe_title,
        'content': safe_content,
        'excerpt': safe_lead,
        'status': status,
        'categories': [2],
        'meta_input': {
            '_yoast_wpseo_title': safe_title,
            '_yoast_wpseo_metadesc': meta_description,
            '_yoast_wpseo_focuskw': focus_keyword,
            '_yoast_wpseo_canonical': '',
            '_yoast_wpseo_opengraph-title': safe_title,
            '_yoast_wpseo_opengraph-description': meta_description,
            '_yoast_wpseo_twitter-title': safe_title,
            '_yoast_wpseo_twitter-description': meta_description,
        }
    }
    
    # 태그가 있으면 추가
    if tags:
        data['tags'] = tags
    
    # 대표 이미지가 있으면 추가
    if featured_media_id:
        data['featured_media'] = featured_media_id
        print(f"대표 이미지 ID 설정: {featured_media_id}")
    else:
        print("대표 이미지 ID가 없습니다.")
    
    try:
        # JSON 데이터를 UTF-8로 인코딩하여 전송 (HTML 태그 보존)
        json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        
        print(f"포스트 데이터 전송 중... (대표이미지 ID: {featured_media_id})")
        print(f"Content 미리보기: {safe_content[:200]}...")  # HTML 태그 확인용
        
        response = requests.post(
            api_url,
            data=json_data,
            headers=headers,
            auth=(wp_user, wp_pass),
            timeout=30
        )
        
        if response.status_code == 201:
            post_data = response.json()
            print(f"WordPress에 포스트가 성공적으로 업로드되었습니다. (상태: {status})")
            print(f"포스트 ID: {post_data['id']}")
            
            # 대표 이미지 설정 확인
            if featured_media_id:
                print(f"대표 이미지 설정 확인 중... (미디어 ID: {featured_media_id})")
                # 포스트 정보를 다시 가져와서 대표 이미지 확인
                post_check_url = f"{wp_url}/wp-json/wp/v2/posts/{post_data['id']}"
                check_response = requests.get(post_check_url, auth=(wp_user, wp_pass))
                if check_response.status_code == 200:
                    post_info = check_response.json()
                    if post_info.get('featured_media') == featured_media_id:
                        print("✅ 대표 이미지가 성공적으로 설정되었습니다!")
                    else:
                        print(f"⚠️ 대표 이미지 설정 실패. 현재 설정된 미디어 ID: {post_info.get('featured_media')}")
                else:
                    print("포스트 정보 확인 실패")
            
            return post_data
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
        print(f"Content HTML 태그 확인: {'<br>' in content or '<p>' in content}")
        
        # SEO 최적화된 콘텐츠 구조 생성
        content = optimize_content_structure(content)
        
        # 태그 추출 (JSON에서 tags 필드가 있는 경우)
        tags = []
        if is_json and 'tags' in article_json:
            tags = article_json.get('tags', [])
        elif not is_json and 'tags:' in kr_content:
            try:
                tags_section = kr_content.split('tags:')[1].strip()
                if tags_section.startswith('[') and tags_section.endswith(']'):
                    import ast
                    tags = ast.literal_eval(tags_section)
                else:
                    # 간단한 태그 파싱
                    tags = [tag.strip() for tag in tags_section.split(',') if tag.strip()]
            except:
                tags = []

        if not all([title, lead, content]):
            print("경고: 일부 필드가 비어 있습니다.")
            print(f"비어있는 필드: {[field for field, value in {'title': title, 'lead': lead, 'content': content}.items() if not value]}")
            return None, None, None, None, None, None

        # 이미지 생성
        print("\n=== 이미지 생성 중 ===")
        featured_media_id = None
        image_url = None
        
        try:
            # DALL-E 이미지 생성
            dalle_image_url = generate_image_with_dalle(title, content, lead, return_url_only=True)
            
            if dalle_image_url:
                print(f"DALL-E 이미지 URL 획득: {dalle_image_url}")
                
                # 이미지 다운로드하여 WordPress에 업로드 시도
                image_data = generate_image_with_dalle(title, content, lead)
                
                if image_data:
                    # WordPress에 이미지 업로드
                    print("WordPress에 이미지 업로드 중...")
                    media_id, uploaded_image_url = upload_image_to_wordpress(image_data)
                    if media_id and uploaded_image_url:
                        featured_media_id = media_id
                        image_url = uploaded_image_url
                        print(f"대표 이미지 설정 완료 (ID: {media_id})")
                        print(f"이미지 URL: {image_url}")
                    else:
                        print("이미지 업로드 실패 - DALL-E URL을 직접 사용합니다.")
                        image_url = dalle_image_url
                        print(f"DALL-E 이미지 URL 사용: {image_url}")
                else:
                    print("이미지 다운로드 실패 - DALL-E URL을 직접 사용합니다.")
                    image_url = dalle_image_url
                    print(f"DALL-E 이미지 URL 사용: {image_url}")
            else:
                print("이미지 생성 실패 - 이미지 없이 포스트를 생성합니다.")
        except Exception as image_error:
            print(f"이미지 생성/업로드 중 오류 발생: {image_error}")
            print("이미지 없이 포스트를 생성합니다.")
            featured_media_id = None
            image_url = None

        return title, lead, content, featured_media_id, image_url, tags
        
    except Exception as e:
        if 'insufficient_quota' in str(e):
            print("OpenAI API 할당량이 초과되었습니다. 계정의 사용량과 결제 상태를 확인해주세요.")
            print("https://platform.openai.com/account/usage 에서 현재 사용량을 확인할 수 있습니다.")
        else:
            print(f"번역 중 오류 발생: {e}")
        return None, None, None, None, None, None

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
            title, lead, content, featured_media_id, image_url, tags = translate_and_format(article)

            # 예외 발생 등으로 하나라도 None이거나 비어있으면 건너뜀
            if not all([title, lead, content]):
                print("이 기사는 번역/파싱 오류로 건너뜁니다.")
                continue

            print(f"title: {title}")
            print(f"lead: {lead}")
            print(f"content: {content}")
            print(f"tags: {tags}")

            print("\n4. WordPress에 포스팅 중...")
            result = post_to_wordpress(title, content, lead, 'draft', featured_media_id, image_url, tags)
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
            title, lead, content, featured_media_id, image_url, tags = translate_and_format(article)

            # 예외 발생 등으로 하나라도 None이거나 비어있으면 건너뜀
            if not all([title, lead, content]):
                print("이 기사는 번역/파싱 오류로 건너뜁니다.")
                continue

            print(f"title: {title}")
            print(f"lead: {lead}")
            print(f"content: {content}")
            print(f"tags: {tags}")

            print("\n4. WordPress에 포스팅 중...")
            result = post_to_wordpress(title, content, lead, 'draft', featured_media_id, image_url, tags)
            if result:
                print(f"포스트 ID: {result['id']}")
                print(f"포스트 링크: {result['link']}")
            time.sleep(5)
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")

if __name__ == "__main__":
    process_news() 
    # process_news_test()