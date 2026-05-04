#!/usr/bin/env python3
"""
Instagram Follower Tracker
- 사용자 목록에서 프로필 정보를 가져와 HTML 파일 생성
- 프로필 사진을 로컬 assets 폴더에 다운로드
- GitHub Pages 배포용
"""

import instaloader
import requests
import time
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


def load_users(filepath: str = "users.txt") -> list[str]:
    """users.txt에서 사용자 목록을 읽어옵니다."""
    users = []
    
    if not os.path.exists(filepath):
        print(f"⚠️ {filepath} 파일이 없습니다. 샘플 파일을 생성해주세요.")
        return users
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 빈 줄과 주석(#으로 시작) 무시
            if line and not line.startswith("#"):
                # @로 시작하면 제거
                username = line.lstrip("@")
                users.append(username)
    
    return users


def download_image(url: str, save_path: str) -> bool:
    """이미지를 다운로드하여 로컬에 저장합니다."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"  └─ 이미지 다운로드 실패: {e}")
        return False


def create_default_image(assets_dir: str):
    """기본 프로필 이미지(SVG)를 생성합니다."""
    default_path = os.path.join(assets_dir, "default.svg")
    
    if os.path.exists(default_path):
        return
    
    # 심플한 기본 프로필 SVG 생성
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="50" fill="#e0e0e0"/>
  <circle cx="50" cy="38" r="18" fill="#bdbdbd"/>
  <ellipse cx="50" cy="85" rx="30" ry="25" fill="#bdbdbd"/>
</svg>'''
    
    print("📥 기본 이미지 생성 중...")
    with open(default_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("  └─ 완료!")



def fetch_user_data(username: str, L: instaloader.Instaloader, assets_dir: str, cache: dict, cache_file: str) -> tuple[dict, bool]:
    """단일 사용자 정보를 가져오거나 캐시에서 로드합니다. (반환값: 정보 dict, 캐시사용여부 bool)"""
    user_info = {
        "username": username,
        "success": False,
        "full_name": "",
        "is_private": False,
    }
    
    # 캐시 확인
    if username in cache:
        # 이미지 파일도 실제로 존재하는지 확인
        img_path = os.path.join(assets_dir, f"{username}.jpg")
        # 성공했던 기록(success is True)이고 이미지가 있는 경우만 캐시 사용 (실패했던 건은 재시도)
        if cache[username].get('success') is True and os.path.exists(img_path):
             print(f"  └─ 📦 캐시 사용")
             return cache[username], True
    
    try:
        # 프로필 정보 가져오기
        profile = instaloader.Profile.from_username(L.context, username)
        
        user_info["success"] = True
        user_info["full_name"] = profile.full_name
        user_info["is_private"] = profile.is_private
        
        # 프로필 사진 다운로드 (이미 존재하면 스킵)
        img_path = os.path.join(assets_dir, f"{username}.jpg")
        if os.path.exists(img_path):
            print(f"  └─ ✅ 성공 (이미지 이미 존재)")
        elif download_image(profile.profile_pic_url, img_path):
            print(f"  └─ ✅ 성공 (이미지 저장됨)")
        else:
            print(f"  └─ ✅ 성공 (이미지 저장 실패, 기본 이미지 사용)")
        
    except Exception as e:
        # Instaloader 실패 시 원시 HTTP 요청(fallback) 시도
        try:
            import re
            import html
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            res = requests.get(f"https://www.instagram.com/{username}/", headers=headers, timeout=10)
            res.raise_for_status()
            html_content = res.text
            
            title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_content)
            img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html_content)
            
            if title_match and img_match:
                title_text = html.unescape(title_match.group(1))
                full_name = title_text.split("(@")[0].strip() if "(@" in title_text else username
                pic_url = html.unescape(img_match.group(1))
                
                private_match = re.search(r'"is_private":\s*(true|false)', html_content)
                is_private = (private_match.group(1) == 'true') if private_match else False
                
                user_info["success"] = True
                user_info["full_name"] = full_name
                user_info["is_private"] = is_private
                
                img_path = os.path.join(assets_dir, f"{username}.jpg")
                if os.path.exists(img_path):
                    print(f"  └─ ✅ 성공 (Fallback, 이미지 이미 존재)")
                elif download_image(pic_url, img_path):
                    print(f"  └─ ✅ 성공 (Fallback, 이미지 저장됨)")
                else:
                    print(f"  └─ ✅ 성공 (Fallback, 이미지 저장 실패)")
            else:
                print(f"  └─ ❌ 실패: {str(e)[:50]}")
        except Exception as fallback_e:
            print(f"  └─ ❌ 실패: {str(e)[:50]}")
    
    # 캐시 업데이트 및 저장
    cache[username] = user_info
    
    # 중간 저장 (실행 중단 대비)
    try:
        import json
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️ 캐시 저장 실패: {e}")
        
    return user_info, False


def load_config(filepath: str = "config.json") -> dict:
    """config.json에서 페이지 설정을 읽어옵니다."""
    import json
    defaults = {"title": "Insta List", "heading": "Insta List"}
    if not os.path.exists(filepath):
        return defaults
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**defaults, **data}
    except Exception as e:
        print(f"⚠️ {filepath} 로드 실패, 기본값 사용: {e}")
        return defaults


def generate_html(developer_data: list[dict], users_data: list[dict], sponsors_data: list[dict], total_count: int, config: dict) -> str:
    """HTML 컨텐츠를 생성합니다."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = config.get("title", "Insta List")
    heading = config.get("heading", title)
    
    # 사용자 카드 HTML 생성 헬퍼 함수
    def create_user_cards(data_list):
        cards_html = ""
        for user in data_list:
            if user["success"]:
                privacy_tag = '<span class="tag private">비공개</span>' if user["is_private"] else ''
                cards_html += f"""
                <div class="user-card">
                    <div class="avatar-ring">
                        <img src="assets/{user['username']}.jpg" onerror="this.src='assets/default.svg'" alt="{user['username']}">
                    </div>
                    <div class="info">
                        <div class="username">{user['username']}{privacy_tag}</div>
                        <div class="fullname">{user['full_name'] or ' '}</div>
                    </div>
                    <a href="https://www.instagram.com/{user['username']}/" target="_blank" rel="noopener" class="btn">팔로우</a>
                </div>
    """
            else:
                cards_html += f"""
                <div class="user-card failed">
                    <div class="avatar-ring muted">
                        <img src="assets/default.svg" alt="{user['username']}">
                    </div>
                    <div class="info">
                        <div class="username">{user['username']}<span class="tag failed">조회 실패</span></div>
                        <div class="fullname">정보를 가져올 수 없습니다</div>
                    </div>
                    <a href="https://www.instagram.com/{user['username']}/" target="_blank" rel="noopener" class="btn secondary">확인</a>
                </div>
    """
        return cards_html

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg: #fafafa;
            --surface: #ffffff;
            --border: #dbdbdb;
            --text: #262626;
            --text-muted: #8e8e8e;
            --primary: #0095f6;
            --primary-hover: #1877f2;
            --secondary: #efefef;
            --danger: #ed4956;
            --ig-gradient: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%);
            --ig-gradient-soft: linear-gradient(135deg, #fde2c4 0%, #fcd0c0 25%, #f8c1d0 50%, #e8c5dc 75%, #d8c2e3 100%);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard", "Noto Sans KR", Roboto, sans-serif;
            background: var(--ig-gradient-soft);
            background-attachment: fixed;
            color: var(--text);
            min-height: 100vh;
            padding: 32px 16px 64px;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 720px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.35);
            backdrop-filter: blur(18px) saturate(160%);
            -webkit-backdrop-filter: blur(18px) saturate(160%);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 24px;
            padding: 8px 16px 24px;
            box-shadow: 0 20px 60px rgba(80, 40, 100, 0.12);
        }}

        header {{
            text-align: center;
            padding: 28px 24px;
            margin-bottom: 20px;
            background: rgba(255, 255, 255, 0.88);
            backdrop-filter: blur(14px) saturate(150%);
            -webkit-backdrop-filter: blur(14px) saturate(150%);
            border: 1px solid rgba(255, 255, 255, 0.6);
            border-radius: 20px;
            box-shadow:
                0 1px 2px rgba(80, 40, 100, 0.06),
                0 6px 16px rgba(80, 40, 100, 0.08),
                0 16px 40px rgba(80, 40, 100, 0.06);
        }}

        header h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 6px;
        }}

        header .subtitle {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        .stats {{
            display: inline-flex;
            gap: 8px;
            margin-top: 14px;
        }}

        .stat-item {{
            background: var(--secondary);
            color: var(--text);
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .section-title {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin: 8px 4px 16px;
        }}

        .user-list {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .user-card {{
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.88);
            backdrop-filter: blur(14px) saturate(150%);
            -webkit-backdrop-filter: blur(14px) saturate(150%);
            border: 1px solid rgba(255, 255, 255, 0.6);
            padding: 12px 14px;
            border-radius: 16px;
            box-shadow:
                0 1px 2px rgba(80, 40, 100, 0.06),
                0 6px 16px rgba(80, 40, 100, 0.08),
                0 16px 40px rgba(80, 40, 100, 0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .user-card:hover {{
            transform: translateY(-3px);
            box-shadow:
                0 2px 4px rgba(80, 40, 100, 0.08),
                0 10px 24px rgba(80, 40, 100, 0.14),
                0 24px 56px rgba(80, 40, 100, 0.10);
        }}

        .user-card.failed {{
            opacity: 0.6;
        }}

        .avatar-ring {{
            width: 56px;
            height: 56px;
            border-radius: 50%;
            padding: 2px;
            background: var(--ig-gradient);
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .avatar-ring.muted {{
            background: var(--border);
        }}

        .avatar-ring img {{
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--surface);
            background: var(--surface);
        }}

        .info {{
            flex-grow: 1;
            margin-left: 12px;
            min-width: 0;
        }}

        .username {{
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .tag {{
            font-size: 0.65rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 999px;
            background: var(--secondary);
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .tag.private {{
            background: #fff0f0;
            color: var(--danger);
        }}

        .tag.failed {{
            background: var(--secondary);
            color: var(--text-muted);
        }}

        .fullname {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .btn {{
            text-decoration: none;
            background: var(--primary);
            color: white;
            padding: 7px 14px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.85rem;
            flex-shrink: 0;
            transition: background-color 0.15s ease;
        }}

        .btn:hover {{
            background: var(--primary-hover);
        }}

        .btn.secondary {{
            background: var(--secondary);
            color: var(--text);
        }}

        .btn.secondary:hover {{
            background: #e5e5e5;
        }}

        footer {{
            text-align: center;
            margin-top: 48px;
            color: rgba(60, 40, 70, 0.55);
            font-size: 0.75rem;
        }}

        @media (max-width: 480px) {{
            body {{
                padding: 16px 8px 48px;
            }}

            .user-card {{
                padding: 8px 6px;
            }}

            .avatar-ring {{
                width: 48px;
                height: 48px;
            }}

            .btn {{
                padding: 6px 12px;
                font-size: 0.8rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{heading}</h1>
            <p class="subtitle">마지막 업데이트 · {now}</p>
            <div class="stats">
                <div class="stat-item">참여자 {total_count}</div>
            </div>
        </header>
        <main>
            <h2 class="section-title">참여자 · {len(users_data)}</h2>
            <div class="user-list">
                {create_user_cards(users_data)}
            </div>
        </main>
        <footer>
            <p>Powered by Instagram Follower Tracker</p>
        </footer>
    </div>
</body>
</html>
"""
    return html


def main():
    print("=" * 50)
    print("🔍 Instagram Follower Tracker")
    print("=" * 50)
    
    # assets 폴더 생성
    assets_dir = "assets"
    Path(assets_dir).mkdir(exist_ok=True)
    
    # 기본 이미지 준비
    create_default_image(assets_dir)
    
    # 목록 로드
    target_list = load_users("users.txt")
    # sponsors_list = load_users("sponsors.txt")
    # developers_list = load_users("developers.txt")
    
    print(f"\n📋 사용자: {len(target_list)}명\n")
    
    # 환경 변수 로드
    load_dotenv(".env.local")
    ig_username = os.getenv("IG_USERNAME")
    ig_password = os.getenv("IG_PASSWORD")

    # Instaloader 인스턴스 생성
    L = instaloader.Instaloader()
    
    if ig_username and ig_password and ig_username != "your_username_here":
        try:
            print(f"🔑 {ig_username} 계정으로 로그인 시도 중...")
            L.login(ig_username, ig_password)
            print("✅ 인스타그램 로그인 성공!")
        except Exception as e:
            print(f"⚠️ 로그인 실패: {e}")
    else:
        print("⚠️ .env.local에 계정 정보가 설정되지 않아 로그인 없이 진행합니다.")

    # 캐시 로드
    cache_file = "cache.json"
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                import json
                cache = json.load(f)
            print(f"📦 캐시된 데이터 {len(cache)}개를 로드했습니다.")
        except Exception:
            print("⚠️ 캐시 파일 로드 중 오류 발생, 새로 시작합니다.")
            cache = {}

    users_data = []
    sponsors_data = []
    developer_data = []
    
    # # 협찬사 처리
    # print("\n[1] 협찬사 정보 수집 중...")
    # for i, username in enumerate(sponsors_list, 1):
    #     print(f"[{i}/{len(sponsors_list)}] {username} 처리 중...")
    #     info, is_cached = fetch_user_data(username, L, assets_dir, cache, cache_file)
    #     sponsors_data.append(info)
    #     if not is_cached:
    #         time.sleep(5) # 캐시가 아닐 때만 대기

    # 사용자 처리
    print("\n[1] 사용자 정보 수집 중...")
    for i, username in enumerate(target_list, 1):
        print(f"[{i}/{len(target_list)}] {username} 처리 중...")
        info, is_cached = fetch_user_data(username, L, assets_dir, cache, cache_file)
        users_data.append(info)
        
        # 마지막 요청이 아니면 대기 (캐시 미사용 시에만)
        if i < len(target_list) and not is_cached:
            time.sleep(5)
    
    # # 개발자 정보 수집
    # print("\n[2] 개발자 정보 수집 중...")
    # for i, username in enumerate(developers_list, 1):
    #     print(f"[{i}/{len(developers_list)}] {username} 처리 중...")
    #     info, is_cached = fetch_user_data(username, L, assets_dir, cache, cache_file)
    #     developer_data.append(info)
    #     if i < len(developers_list) and not is_cached:
    #         time.sleep(5)

    # HTML 생성
    print("\n📝 HTML 파일 생성 중...")
    
    total_count = len(target_list)  # + len(sponsors_list) + len(developers_list)
    
    config = load_config("config.json")
    html_content = generate_html(developer_data, users_data, sponsors_data, total_count, config)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # 결과 요약
    total_success = sum(1 for u in users_data if u["success"]) + sum(1 for s in sponsors_data if s["success"])
    total_fail = (len(users_data) + len(sponsors_data)) - total_success
    
    print("\n" + "=" * 50)
    print("✨ 완료!")
    print(f"   - 성공: {total_success}명")
    print(f"   - 실패: {total_fail}명")
    print(f"   - 결과 파일: index.html")
    print(f"   - 이미지 폴더: {assets_dir}/")
    print("=" * 50)


if __name__ == "__main__":
    main()

