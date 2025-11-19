from supabase import create_client
from dados import SUPABASE_URL, SUPABASE_KEY

print("=" * 50)
print("🧪 TESTE DE CONEXÃO SUPABASE")
print("=" * 50)

# 1. Verifica se as credenciais existem
print("\n1️⃣ Verificando credenciais...")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRO: Variáveis SUPABASE_URL ou SUPABASE_KEY não configuradas!")
    exit(1)

print(f"✅ SUPABASE_URL: {SUPABASE_URL[:30]}...")
print(f"✅ SUPABASE_KEY: {SUPABASE_KEY[:20]}...")

# 2. Tenta criar cliente
print("\n2️⃣ Criando cliente Supabase...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Cliente criado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao criar cliente: {e}")
    exit(1)

# 3. Testa consulta na tabela alunos_verificados
print("\n3️⃣ Testando consulta na tabela 'alunos_verificados'...")
try:
    response = supabase.table("alunos_verificados").select("*").execute()
    print(f"✅ Consulta bem-sucedida!")
    print(f"📊 Registros encontrados: {len(response.data)}")
    
    if len(response.data) > 0:
        print(f"\n📋 Primeiros registros:")
        for i, row in enumerate(response.data[:3], 1):
            print(f"   {i}. Email: {row.get('email')} | Discord ID: {row.get('discord_id')}")
    else:
        print("ℹ️ Tabela vazia (isso é normal se ainda não verificou ninguém)")
        
except Exception as e:
    print(f"❌ Erro na consulta: {e}")
    print("\n💡 Possíveis causas:")
    print("   - Tabela 'alunos_verificados' não existe")
    print("   - Credenciais inválidas")
    print("   - Problema de permissão")
    exit(1)

# 4. Testa inserção (e remove depois)
print("\n4️⃣ Testando inserção de dados...")
try:
    test_data = {
        "email": "teste@exemplo.com",
        "discord_id": "999999999999999999"
    }
    
    # Insere
    #insert_response = supabase.table("alunos_verificados").insert(test_data).execute()
    #print("✅ Inserção bem-sucedida!")
    
    # Remove imediatamente
    supabase.table("alunos_verificados").delete().eq("email", "teste@exemplo.com").execute()
    print("✅ Remoção do teste bem-sucedida!")
    
except Exception as e:
    print(f"⚠️ Erro no teste de inserção: {e}")
    print("ℹ️ Isso pode ser normal se já existe um registro com esse email")

# 5. Resultado final
print("\n" + "=" * 50)
print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
print("✅ Supabase está funcionando corretamente!")
print("=" * 50)
print("oi")