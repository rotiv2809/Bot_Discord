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

class MateriaSelect(ui.Select):
    """Dropdown para seleção de matéria"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        self.user_id = user_id
        self.questoes_em_criacao = questoes_em_criacao
        
        options = [
            discord.SelectOption(label="Matemática", emoji="🔢", description="Questões de matemática"),
            discord.SelectOption(label="Física", emoji="⚛️", description="Questões de física"),
            discord.SelectOption(label="Química", emoji="🧪", description="Questões de química"),
            discord.SelectOption(label="Humanas", emoji="📖", description="História, Geografia, Filosofia, etc."),
            discord.SelectOption(label="Linguagens", emoji="📝", description="Português, Literatura, Inglês, etc."),
            discord.SelectOption(label="Outros", emoji="📚", description="Outras matérias"),
        ]
        
        super().__init__(
            placeholder="Selecione a matéria...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_materia"
        )
    
    async def callback(self, interaction: discord.Interaction):
        materia_selecionada = self.values[0]
        
        # Salva a matéria e o ID do canal
        if self.user_id not in self.questoes_em_criacao:
            self.questoes_em_criacao[self.user_id] = {}
        
        self.questoes_em_criacao[self.user_id]['materia'] = materia_selecionada
        self.questoes_em_criacao[self.user_id]['canal_id'] = MATERIAS_CANAIS[materia_selecionada]
        
        await interaction.response.send_message(
            f"✅ Matéria selecionada: **{materia_selecionada}**",
            ephemeral=True
        )
        
        # Atualiza o embed principal
        await atualizar_embed_questao(interaction, self.user_id, self.questoes_em_criacao)


class MateriaView(ui.View):
    """View temporária para o dropdown de matérias"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        super().__init__(timeout=60)
        self.add_item(MateriaSelect(user_id, questoes_em_criacao))


class BotoesQuestaoView(ui.View):
    """View com os botões para preencher os campos da questão"""
    
    def __init__(self, user_id: int, questoes_em_criacao: dict):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.questoes_em_criacao = questoes_em_criacao
    
    @ui.button(label="📝 Descrição", style=discord.ButtonStyle.primary, custom_id="btn_descricao")
    async def button_descricao(self, interaction: discord.Interaction, button: ui.Button):
        # Abre o modal de descrição
        modal = DescricaoModal(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🖼️ Imagem", style=discord.ButtonStyle.secondary, custom_id="btn_imagem")
    async def button_imagem(self, interaction: discord.Interaction, button: ui.Button):
        # Ativa o modo de espera de imagem
        if self.user_id not in self.questoes_em_criacao:
            self.questoes_em_criacao[self.user_id] = {}
        
        self.questoes_em_criacao[self.user_id]['aguardando_imagem'] = True
        self.questoes_em_criacao[self.user_id]['canal_imagem'] = interaction.channel_id
        
        await interaction.response.send_message(
            "📷 **Modo de captura de imagem ativado!**\n\n"
            "Por favor, envie uma imagem neste canal das seguintes formas:\n"
            "• Anexe uma imagem (arraste e solte ou clique no +)\n"
            "• Cole uma imagem diretamente no chat\n"
            "• Envie um link de imagem\n\n"
            "⏱️ Você tem 2 minutos para enviar a imagem.\n"
            "💡 Para pular, clique novamente no botão 🖼️ Imagem.",
            ephemeral=True
        )
    
    @ui.button(label="📚 Matéria", style=discord.ButtonStyle.secondary, custom_id="btn_materia")
    async def button_materia(self, interaction: discord.Interaction, button: ui.Button):
        view = MateriaView(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_message(
            "📚 **Selecione a matéria da questão:**",
            view=view,
            ephemeral=True
        )
    
    @ui.button(label="⭐ Nível", style=discord.ButtonStyle.secondary, custom_id="btn_nivel")
    async def button_nivel(self, interaction: discord.Interaction, button: ui.Button):
        view = NivelView(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_message(
            "⭐ **Selecione o nível de dificuldade da questão:**",
            view=view,
            ephemeral=True
        )
    
    @ui.button(label="🏷️ Etiqueta", style=discord.ButtonStyle.secondary, custom_id="btn_etiqueta")
    async def button_etiqueta(self, interaction: discord.Interaction, button: ui.Button):
        modal = EtiquetaModal(self.user_id, self.questoes_em_criacao)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✅ Finalizar", style=discord.ButtonStyle.success, custom_id="btn_finalizar", row=2)
    async def button_finalizar(self, interaction: discord.Interaction, button: ui.Button):
        dados = self.questoes_em_criacao.get(self.user_id, {})
        
        # Validação
        campos_obrigatorios = {
            'descricao': '📝 Descrição',
            'materia': '📚 Matéria'
        }
        
        faltando = [nome for campo, nome in campos_obrigatorios.items() if not dados.get(campo)]
        
        if faltando:
            await interaction.response.send_message(
                f"❌ **Campos obrigatórios faltando:**\n" + "\n".join(f"• {campo}" for campo in faltando),
                ephemeral=True
            )
            return
        
        # Defer para ter mais tempo
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Busca o canal da matéria
            canal_id = dados.get('canal_id')
            canal = interaction.guild.get_channel(canal_id)
            
            if not canal:
                await interaction.followup.send(
                    "❌ Erro: Canal da matéria não encontrado!",
                    ephemeral=True
                )
                return
            
            # Cria o embed da questão
            embed_questao = discord.Embed(
                title="❓ Nova Questão",
                description=dados['descricao'],
                color=discord.Color.blue()
            )
            
            embed_questao.add_field(
                name="📚 Matéria",
                value=dados['materia'],
                inline=True
            )
            
            if dados.get('nivel'):
                embed_questao.add_field(
                    name="⭐ Nível",
                    value=dados['nivel'],
                    inline=True
                )
            
            if dados.get('etiqueta'):
                embed_questao.add_field(
                    name="🏷️ Etiquetas",
                    value=dados['etiqueta'],
                    inline=True
                )
            
            embed_questao.set_footer(
                text=f"Criado por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            
            if dados.get('imagem'):
                embed_questao.set_image(url=dados['imagem'])
            
            # Cria o tópico no canal
            nome_topico = f"Questão - {dados['materia']}"
            if len(dados['descricao']) > 50:
                nome_topico = f"{dados['descricao'][:47]}..."
            else:
                nome_topico = dados['descricao']
            
            # Cria thread/tópico
            mensagem_inicial = await canal.send(embed=embed_questao)
            topico = await mensagem_inicial.create_thread(
                name=nome_topico[:100],  # Limite de 100 caracteres
                auto_archive_duration=1440  # 24 horas
            )
            
            await interaction.followup.send(
                f"✅ **Questão criada com sucesso!**\n\n"
                f"📍 Canal: {canal.mention}\n"
                f"🧵 Tópico: {topico.mention}\n"
                f"📚 Matéria: **{dados['materia']}**",
                ephemeral=True
            )
            
            # Remove a mensagem original
            try:
                await interaction.message.delete()
            except:
                pass
            
            # Limpa os dados
            self.questoes_em_criacao.pop(self.user_id, None)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao criar questão: {str(e)}",
                ephemeral=True
            )
            print(f"Erro ao criar questão: {e}")
    
    @ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, custom_id="btn_cancelar", row=2)
    async def button_cancelar(self, interaction: discord.Interaction, button: ui.Button):
        self.questoes_em_criacao.pop(self.user_id, None)
        await interaction.message.delete()
        await interaction.response.send_message(
            "🗑️ Criação de questão cancelada.",
            ephemeral=True
        )