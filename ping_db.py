# ping_db.py
import os
from supabase import create_client, Client

# GitHub Actions의 Secrets에서 주입된 환경 변수를 가져옵니다.
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ 환경 변수(SUPABASE_URL 또는 SUPABASE_KEY)가 설정되지 않았습니다.")
    exit(1)

try:
    supabase: Client = create_client(url, key)
    response = supabase.table('characters').select('id').limit(1).execute()
    print(f"✅ Supabase DB Ping 성공! 서버가 정상적으로 깨어있습니다. (데이터 응답: {response.data})")
except Exception as e:
    print(f"❌ DB Ping 실패: {e}")
    exit(1)