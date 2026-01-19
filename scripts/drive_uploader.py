import os
import json
import tempfile
import shutil
from typing import Optional
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload, MediaFileUpload

# =========================================
# CONFIGURAÇÕES
# =========================================

# 🔥 COLOQUE AQUI O ID DA PASTA QUE VOCÊ COMPARTILHOU COM O SERVICE ACCOUNT
PASTA_RAIZ_ID = "1reB6eFt7sS7RDVg39_G78ZHzMZwg_16o"

service = None


# =========================================
# FUNÇÕES AUXILIARES
# =========================================

def set_drive_service(drive_service):
    global service
    service = drive_service


def buscar_pasta(nome: str, parent_id: Optional[str]) -> Optional[str]:
    """
    Busca uma pasta pelo nome dentro de um parent.
    Retorna o ID se existir.
    """
    query = f"name='{nome}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    response = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    arquivos = response.get("files", [])
    if arquivos:
        return arquivos[0]["id"]

    return None


def criar_pasta(nome: str, parent_id: Optional[str]) -> str:
    metadata = {
        "name": nome,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    pasta = service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True
    ).execute()

    return pasta["id"]


def obter_ou_criar_pasta(nome: str, parent_id: Optional[str]) -> str:
    pasta_id = buscar_pasta(nome, parent_id)
    if pasta_id:
        return pasta_id

    return criar_pasta(nome, parent_id)


def upload_arquivo_bytes(file_content: bytes, filename: str, parent_id: str):
    """Upload direto de bytes para o Drive sem salvar localmente"""
    media = MediaInMemoryUpload(
        file_content,
        resumable=True
    )

    service.files().create(
        body={
            "name": filename,
            "parents": [parent_id]
        },
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()


def upload_arquivo(caminho_local: str, parent_id: str):
    """Upload de arquivo do sistema de arquivos"""
    nome = os.path.basename(caminho_local)

    media = MediaFileUpload(
        caminho_local,
        resumable=True
    )

    service.files().create(
        body={
            "name": nome,
            "parents": [parent_id]
        },
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()


# =========================================
# FUNÇÃO PRINCIPAL
# =========================================

def upload_questao_para_drive(pasta_temp: str, token: str, materia: str, subarea: str = "Geral"):
    """
    Faz upload da questão resolvida para o Google Drive
    
    Estrutura: Questoes_Discord / 2026 / Janeiro / Matemática / Q-ABC123
    
    Args:
        pasta_temp: Caminho da pasta temporária com os arquivos
        token: Token único da questão
        materia: Matéria da questão
        subarea: Subárea (não usado mais, mantido para compatibilidade)
    """
    if service is None:
        raise RuntimeError("❌ Drive service não configurado")

    if not os.path.exists(pasta_temp):
        print(f"❌ Pasta temporária não encontrada: {pasta_temp}")
        raise FileNotFoundError(f"Pasta {pasta_temp} não encontrada")

    # Verifica se há arquivos para upload
    arquivos = [f for f in os.listdir(pasta_temp) if os.path.isfile(os.path.join(pasta_temp, f))]
    if not arquivos:
        print(f"⚠️ Nenhum arquivo encontrado em {pasta_temp}")
        return

    print(f"📦 Preparando upload de {len(arquivos)} arquivo(s)...")

    try:
        # Pega ano e mês atual
        agora = datetime.now()
        ano = str(agora.year)
        meses = {
            1: "01 - Janeiro", 2: "02 - Fevereiro", 3: "03 - Março",
            4: "04 - Abril", 5: "05 - Maio", 6: "06 - Junho",
            7: "07 - Julho", 8: "08 - Agosto", 9: "09 - Setembro",
            10: "10 - Outubro", 11: "11 - Novembro", 12: "12 - Dezembro"
        }
        mes = meses[agora.month]

        # ✅ USA A PASTA COMPARTILHADA COMO RAIZ
        if PASTA_RAIZ_ID:
            print(f"📁 Usando pasta compartilhada: {PASTA_RAIZ_ID}")
            root_id = PASTA_RAIZ_ID
        else:
            print(f"⚠️ ATENÇÃO: PASTA_RAIZ_ID não definida!")
            raise RuntimeError("PASTA_RAIZ_ID não configurada")

        # 1️⃣ Ano
        print(f"📁 Criando/buscando pasta do ano: {ano}")
        ano_id = obter_ou_criar_pasta(ano, root_id)

        # 2️⃣ Mês
        print(f"📁 Criando/buscando pasta do mês: {mes}")
        mes_id = obter_ou_criar_pasta(mes, ano_id)

        # 3️⃣ Matéria
        print(f"📁 Criando/buscando pasta de matéria: {materia}")
        materia_id = obter_ou_criar_pasta(materia, mes_id)

        # 4️⃣ Pasta da questão
        print(f"📁 Criando/buscando pasta da questão: {token}")
        questao_id = obter_ou_criar_pasta(token, materia_id)

        # 5️⃣ Upload de todos os arquivos
        print(f"📤 Iniciando upload de arquivos...")
        for arquivo in arquivos:
            caminho = os.path.join(pasta_temp, arquivo)
            if os.path.isfile(caminho):
                print(f"   ↗️ Uploading: {arquivo}")
                upload_arquivo(caminho, questao_id)

        print(f"✅ Upload concluído no Drive: {token}")
        print(f"📂 Caminho: {ano}/{mes}/{materia}/{token}")
        
    except Exception as e:
        print(f"❌ Erro durante upload: {e}")
        import traceback
        traceback.print_exc()
        raise