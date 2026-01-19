import json
import asyncio
from typing import Dict, Any
from openai import AsyncOpenAI
from dados import OPENAI_API_KEY

# =========================
# CONFIGURAÇÕES
# =========================

MODEL_NAME = "gpt-4.1-mini"  # custo baixo e ótimo pra texto
MAX_TOKENS = 1200
TEMPERATURE = 0.2  # baixo = menos alucinação

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Taxonomia controlada (importante!)
SUBAREAS = {
    "Matemática": [
        "Aritmética",
        "Álgebra",
        "Geometria Plana",
        "Geometria Espacial",
        "Geometria Analítica",
        "Análise Combinatória",
        "Probabilidade",
        "Funções",
        "Trigonometria",
        "Cálculo",
        "Outros"
    ],
    "Física": [
        "Cinemática",
        "Dinâmica",
        "Trabalho e Energia",
        "Quantidade de Movimento",
        "Gravitação",
        "Termodinâmica",
        "Ondulatória",
        "Óptica",
        "Eletrostática",
        "Eletrodinâmica",
        "Magnetismo",
        "Física Moderna",
        "Outros"
    ],
    "Química": [
        "Química Geral",
        "Estequiometria",
        "Soluções",
        "Termoquímica",
        "Cinética Química",
        "Equilíbrio Químico",
        "Eletroquímica",
        "Química Orgânica",
        "Funções Orgânicas",
        "Reações Orgânicas",
        "Química Inorgânica",
        "Outros"
    ]
}



# =========================
# PROMPT
# =========================

def montar_prompt(texto_questao: str) -> str:
    return f"""
Você é um professor experiente e criterioso.

Abaixo está o HISTÓRICO COMPLETO de uma questão resolvida, incluindo:
- enunciado
- mensagens de alunos
- mensagens de monitores
- tentativas e correções

TAREFAS:
1. Identifique a matéria principal
2. Classifique a subárea (use APENAS uma das opções fornecidas)
3. Determine o nível (Fundamental, Médio, Graduação)
4. Estime a dificuldade (fácil, média, difícil)
5. Gere um resumo didático e correto da resolução

Subáreas possíveis (use APENAS as correspondentes à matéria identificada):

Matemática:
{", ".join(SUBAREAS["Matemática"])}

Física:
{", ".join(SUBAREAS["Física"])}

Química:
{", ".join(SUBAREAS["Química"])}


REGRAS IMPORTANTES:
- Ignore mensagens irrelevantes (ex: "valeu", "ok", etc.)
- NÃO invente passos que não apareçam no histórico
- Se a solução estiver incompleta ou confusa, diga isso claramente
- Use linguagem clara e pedagógica
- Retorne APENAS um JSON válido
- O campo "resumo_md" deve estar em Markdown

IMPORTANTE:
Se partes da solução estiverem apenas em imagens anexadas
(e não descritas claramente em texto),
deixe isso explícito no resumo e NÃO invente passos.

FORMATO EXATO DE SAÍDA:

{{
  "materia": "",
  "subarea": "",
  "topicos": [],
  "nivel": "",
  "dificuldade": "",
  "resumo_md": ""
}}

==============================
HISTÓRICO DA QUESTÃO:
==============================

{texto_questao}
""".strip()


# =========================
# FUNÇÃO PRINCIPAL
# =========================

async def gerar_resumo_e_classificacao(
    texto_questao: str
) -> Dict[str, Any]:
    """
    Recebe o texto completo da questão (TXT)
    Retorna um dicionário com resumo + classificação
    """

    prompt = montar_prompt(texto_questao)

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Você responde apenas JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )

        conteudo = response.choices[0].message.content.strip()

        # Garante JSON limpo (remove ``` se vier)
        if conteudo.startswith("```"):
            conteudo = conteudo.strip("```").strip()
            if conteudo.startswith("json"):
                conteudo = conteudo[4:].strip()

        resultado = json.loads(conteudo)

        validar_resultado(resultado)

        return resultado

    except json.JSONDecodeError as e:
        print("❌ Erro ao decodificar JSON da IA")
        print(conteudo)
        raise e

    except Exception as e:
        print("❌ Erro ao gerar resumo com IA:", e)
        raise e


# =========================
# VALIDAÇÃO
# =========================

def validar_resultado(resultado: Dict[str, Any]):
    campos_obrigatorios = [
        "materia",
        "subarea",
        "topicos",
        "nivel",
        "dificuldade",
        "resumo_md"
    ]

    for campo in campos_obrigatorios:
        if campo not in resultado:
            raise ValueError(f"Campo ausente no resultado da IA: {campo}")

        materia = resultado.get("materia")

    if materia in SUBAREAS:
        if resultado["subarea"] not in SUBAREAS[materia]:
            resultado["subarea"] = "Outros"
    else:
        # Para Humanas, Linguagens, Outros etc.
        resultado["subarea"] = "Outros"


    if resultado["dificuldade"] not in ["fácil", "média", "difícil"]:
        resultado["dificuldade"] = "média"

    if resultado["nivel"] not in ["Fundamental", "Médio", "Graduação"]:
        resultado["nivel"] = "Médio"


# =========================
# TESTE LOCAL (opcional)
# =========================

if __name__ == "__main__":
    texto_fake = """
QUESTÃO:
Calcule a área de um triângulo retângulo com catetos 3 e 4.

DISCUSSÃO:
Aluno: como faz?
Monitor: usa pitágoras
Monitor: depois área = (base * altura)/2
"""

    async def testar():
        r = await gerar_resumo_e_classificacao(texto_fake)
        print(json.dumps(r, indent=2, ensure_ascii=False))

    asyncio.run(testar())
