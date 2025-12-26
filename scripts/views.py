import discord
from discord import ui
from scripts.modals import DescricaoModal, atualizar_embed_questao
from scripts.nivel_etiqueta import NivelView, EtiquetaModal

# Mapeamento de matérias para IDs de canais
MATERIAS_CANAIS = {
    "Matemática": 1437144074779099328,
    "Física": 1437144607426084894,
    "Química": 1431724171607412920,
    "Humanas": 1437144849110532219,
    "Linguagens": 1450565544620200067,
    "Outros": 1450565643983126558
}
