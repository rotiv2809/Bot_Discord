import json
from pathlib import Path

FAVORITOS_PATH = Path("questoes_data/favoritos.json")
FAVORITOS_PATH.parent.mkdir(exist_ok=True)

if not FAVORITOS_PATH.exists():
    FAVORITOS_PATH.write_text("{}", encoding="utf-8")


def carregar_favoritos() -> dict:
    return json.loads(FAVORITOS_PATH.read_text(encoding="utf-8"))


def salvar_favoritos(data: dict):
    FAVORITOS_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def adicionar_favorito(token: str, user_id: int):
    data = carregar_favoritos()
    data.setdefault(token, [])
    if user_id not in data[token]:
        data[token].append(user_id)
    salvar_favoritos(data)


def obter_favoritos(token: str) -> list[int]:
    data = carregar_favoritos()
    return data.get(token, [])


def remover_favoritos(token: str):
    data = carregar_favoritos()
    if token in data:
        del data[token]
        salvar_favoritos(data)
