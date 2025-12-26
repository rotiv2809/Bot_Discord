import discord
from discord import ui

class DescricaoModal(ui.Modal, title="Descrição da Questão"):
    """Modal para inserir a descrição da questão"""
    
    descricao = ui.TextInput(
        label="Descrição",
        placeholder="Digite a descrição da questão aqui...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        super().__init__()
        self.user_id = user_id
        self.questoes_em_criacao = questoes_em_criacao
    
    async def on_submit(self, interaction: discord.Interaction):
        # Salva a descrição no dicionário
        if self.user_id not in self.questoes_em_criacao:
            self.questoes_em_criacao[self.user_id] = {}
        
        self.questoes_em_criacao[self.user_id]['descricao'] = self.descricao.value
        
        await interaction.response.send_message(
            f"✅ Descrição salva com sucesso!\n\n**Preview:**\n{self.descricao.value[:100]}...",
            ephemeral=True
        )
        
        # Atualiza o embed principal
        await atualizar_embed_questao(interaction, self.user_id, self.questoes_em_criacao)


async def atualizar_embed_questao(interaction: discord.Interaction, user_id: int, questoes_em_criacao: dict):
    """Atualiza o embed com os dados preenchidos"""
    dados = questoes_em_criacao.get(user_id, {})
    
    embed = discord.Embed(
        title="📋 Criar Nova Questão",
        description="Preencha os campos abaixo para criar uma questão:",
        color=discord.Color.blue()
    )
    
    # Adiciona os campos preenchidos
    descricao_preview = dados.get('descricao', '*Não preenchido*')
    if descricao_preview != '*Não preenchido*' and len(descricao_preview) > 100:
        descricao_preview = descricao_preview[:100] + "..."
    
    embed.add_field(
        name="📝 Descrição",
        value=descricao_preview,
        inline=False
    )
    
    # Campo de imagem
    imagem_status = "*Não preenchido*"
    if dados.get('imagem'):
        imagem_status = "✅ Imagem anexada"
    elif dados.get('aguardando_imagem'):
        imagem_status = "⏳ Aguardando envio..."
    
    embed.add_field(
        name="🖼️ Imagem",
        value=imagem_status,
        inline=True
    )
    
    embed.add_field(
        name="📚 Matéria",
        value=dados.get('materia', '*Não preenchido*'),
        inline=True
    )
    
    embed.add_field(
        name="⭐ Nível",
        value=dados.get('nivel', '*Não preenchido*'),
        inline=True
    )
    
    embed.add_field(
        name="🏷️ Etiqueta",
        value=dados.get('etiqueta', '*Não preenchido*'),
        inline=True
    )
    
    # Adiciona preview da imagem se existir
    if dados.get('imagem'):
        embed.set_thumbnail(url=dados['imagem'])
    
    embed.set_footer(text="Clique nos botões abaixo para preencher cada campo")
    
    # Busca a mensagem original e atualiza
    try:
        # Tenta usar o message_id salvo
        message_id = dados.get('message_id')
        if message_id:
            message = await interaction.channel.fetch_message(message_id)
            await message.edit(embed=embed)
        else:
            # Fallback para o método antigo
            message = await interaction.channel.fetch_message(interaction.message.id)
            await message.edit(embed=embed)
    except Exception as e:
        print(f"Erro ao atualizar embed: {e}")