"""
renovar_redirect.py
Flask app que roda junto com o bot.
Quando o aluno clica no link de renovação da DM, esse endpoint:
  1. Busca email e nome do aluno pelo discord_id
  2. Dispara o webhook do Clint CRM com os dados
  3. Redireciona para a URL de renovação
"""

import threading
import requests
from flask import Flask, request, redirect
from supabase import create_client, Client
from dados import SUPABASE_URL, SUPABASE_KEY

# ─────────────────────────────────────────────
# CONFIGURAÇÕES — ajuste aqui
# ─────────────────────────────────────────────

# 🔗 URL da página de renovação do site
URL_RENOVACAO = "https://www.tropadoarcanjo.com.br/cursos/"  # ← trocar pela URL definitiva

# 🔔 Webhook do Clint CRM (fornecido pelo chefe)
CLINT_WEBHOOK_URL = "https://functions-api.clint.digital/endpoints/integration/webhook/5ae5e4da-de79-41bf-a788-9e8cbb71bafd"

# ─────────────────────────────────────────────

app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def disparar_webhook_clint(email: str, nome: str, discord_id: str, dias_restantes: int = None):
    """Dispara o webhook do Clint CRM com os dados do aluno"""
    try:
        payload = {
            "email": email,
            "nome": nome,
            "discord_id": discord_id,
            "origem": "discord_aviso_renovacao",
        }
        if dias_restantes is not None:
            payload["dias_restantes"] = dias_restantes

        response = requests.post(CLINT_WEBHOOK_URL, json=payload, timeout=10)
        print(f"📡 Webhook Clint disparado para {email} — status {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao disparar webhook Clint: {e}")


@app.route("/renovar")
def renovar():
    discord_id = request.args.get("discord_id")
    dias_restantes = request.args.get("dias")

    if not discord_id:
        return redirect(URL_RENOVACAO)

    try:
        # Busca email e nome pelo discord_id na tabela verificacoes
        response = supabase.table("verificacoes") \
            .select("email, username") \
            .eq("discord_id", str(discord_id)) \
            .execute()

        if response.data:
            email = response.data[0].get("email", "")
            nome = response.data[0].get("username", "")

            # Dispara webhook em thread separada para não travar o redirect
            threading.Thread(
                target=disparar_webhook_clint,
                args=(email, nome, discord_id),
                kwargs={"dias_restantes": int(dias_restantes) if dias_restantes else None},
                daemon=True
            ).start()

    except Exception as e:
        print(f"❌ Erro ao buscar dados do aluno {discord_id}: {e}")

    return redirect(URL_RENOVACAO)


@app.route("/health")
def health():
    """Endpoint de health check para a SquareCloud"""
    return {"status": "ok"}, 200


def iniciar_flask():
    """Inicia o Flask em thread separada"""
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


def start_web_server():
    thread = threading.Thread(target=iniciar_flask, daemon=True)
    thread.start()
    print("🌐 Servidor Flask iniciado na porta 8080")