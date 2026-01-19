import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GURU_API_TOKEN = os.getenv("GURU_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROLE_ID_ALUNO = int(os.getenv("ROLE_ID_ALUNO", "0"))

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Verificando variáveis carregadas:")
    print("=" * 50)
    print(f"DISCORD_TOKEN: {'✅ Carregado' if DISCORD_TOKEN else '❌ Faltando'}")
    print(f"SUPABASE_URL: {'✅ Carregado' if SUPABASE_URL else '❌ Faltando'}")
    print(f"SUPABASE_KEY: {'✅ Carregado' if SUPABASE_KEY else '❌ Faltando'}")
    print(f"GURU_API_TOKEN: {'✅ Carregado' if GURU_API_TOKEN else '❌ Faltando'}")
    print(f"ROLE_ID_ALUNO: {ROLE_ID_ALUNO if ROLE_ID_ALUNO != 0 else '❌ Faltando'}")
    print("=" * 50)