# ping_db.py
import os
from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# 🚀 무엇이 문제인지 정확히 알려주는 디버깅 출력
print("====================================")
print(f"🔍 URL 변수 인식 여부: {'✅ 정상' if url else '❌ 실패 (값이 비어있음)'}")
print(f"🔍 KEY 변수 인식 여부: {'✅ 정상' if key else '❌ 실패 (값이 비어있음)'}")
if url:
    print(f"🔍 URL 값 길이: {len(url)}글자, 시작: {url[:5]}...")
print("====================================")

if not url or not key:
    print("🚨 [에러] GitHub Secrets에서 변수를 불러오지 못했습니다. 깃허브 세팅을 확인해 주세요.")
    exit(1)

try:
    supabase: Client = create_client(url, key)
    response = supabase.table('characters').select('character_name').limit(1).execute()
    print(f"✅ Supabase DB Ping 성공! (응답 데이터: {response.data})")
except Exception as e:
    print(f"❌ DB Ping 실패: {e}")
    exit(1)