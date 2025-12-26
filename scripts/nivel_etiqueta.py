import discord
from discord import ui
from scripts.modals import atualizar_embed_questao

class NivelSelect(ui.Select):
    """Dropdown para seleção de nível da questão"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        self.user_id = user_id
        self.questoes_em_criacao = questoes_em_criacao
        
        options = [
            discord.SelectOption(
                label="Ensino Fundamental I",
                emoji="📚",
                description="1º ao 5º ano"
            ),
            discord.SelectOption(
                label="Ensino Fundamental II",
                emoji="📖",
                description="6º ao 9º ano"
            ),
            discord.SelectOption(
                label="Ensino Médio",
                emoji="🎓",
                description="1º ao 3º ano do Ensino Médio"
            ),
            discord.SelectOption(
                label="Pré-Vestibular",
                emoji="📝",
                description="Preparação para vestibulares e ENEM"
            ),
            discord.SelectOption(
                label="Ensino Superior",
                emoji="🎯",
                description="Graduação e Faculdade"
            ),
            discord.SelectOption(
                label="Pós-Graduação",
                emoji="🔬",
                description="Mestrado, Doutorado e especialização"
            ),
        ]
        
        super().__init__(
            placeholder="Selecione o nível de dificuldade...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_nivel"
        )
    
    async def callback(self, interaction: discord.Interaction):
        nivel_selecionado = self.values[0]
        
        # Salva o nível
        if self.user_id not in self.questoes_em_criacao:
            self.questoes_em_criacao[self.user_id] = {}
        
        self.questoes_em_criacao[self.user_id]['nivel'] = nivel_selecionado
        
        await interaction.response.send_message(
            f"✅ Nível selecionado: **{nivel_selecionado}**",
            ephemeral=True
        )
        
        # Atualiza o embed principal
        await atualizar_embed_questao(interaction, self.user_id, self.questoes_em_criacao)


class NivelView(ui.View):
    """View temporária para o dropdown de nível"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        super().__init__(timeout=60)
        self.add_item(NivelSelect(user_id, questoes_em_criacao))


class EtiquetaModal(ui.Modal, title="Etiquetas da Questão"):
    """Modal para inserir etiquetas da questão"""
    
    etiquetas = ui.TextInput(
        label="Etiquetas",
        placeholder="Ex: álgebra, equações, vestibular",
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        super().__init__()
        self.user_id = user_id
        self.questoes_em_criacao = questoes_em_criacao
    
    async def on_submit(self, interaction: discord.Interaction):
        # Salva as etiquetas no dicionário
        if self.user_id not in self.questoes_em_criacao:
            self.questoes_em_criacao[self.user_id] = {}
        
        # Processa as etiquetas (remove espaços extras)
        etiquetas_processadas = [tag.strip() for tag in self.etiquetas.value.split(',') if tag.strip()]
        etiquetas_formatadas = ', '.join(etiquetas_processadas)
        
        self.questoes_em_criacao[self.user_id]['etiqueta'] = etiquetas_formatadas
        
        await interaction.response.send_message(
            f"✅ Etiquetas salvas: **{etiquetas_formatadas}**",
            ephemeral=True
        )
        
        # Atualiza o embed principal
        await atualizar_embed_questao(interaction, self.user_id, self.questoes_em_criacao)