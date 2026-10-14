import os
import random
import json
import time
import datetime
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Caricamento variabili d'ambiente (.env)
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configurazione Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# FILE E CONFIGURAZIONI GLOBALI
# ==========================================
ECONOMY_FILE = "economy.json"
LEVELS_FILE = "levels.json"

# ID dei canali (Sostituisci con gli ID reali del tuo server)
WELCOME_CHANNEL_ID = 123456789012345678
GOODBYE_CHANNEL_ID = 123456789012345678
AUTOROLE_ID = 123456789012345678  # Imposta 0 per disattivare

# Configurazione Verifica e Ticket
verification_config = {"role_id": 123456789012345678}
ticket_config = {
    "style": "menu",
    "title": "🎫 Supporto Ticket",
    "description": "Seleziona o clicca sulla categoria appropriata per aprire un ticket.",
    "categories": [
        {"label": "Supporto Generale", "description": "Richiedi assistenza generale", "emoji": "❓"},
        {"label": "Segnalazione Bug", "description": "Segnala un errore o un problema", "emoji": "🐛"},
        {"label": "Donazioni & VIP", "description": "Info su donazioni e pacchetti", "emoji": "💎"}
    ]
}

# Negozio Virtuale
SHOP_ITEMS = {
    "1": {"name": "👑 Ruolo VIP", "price": 5000, "role_id": 123456789012345678},
    "2": {"name": "💎 Ruolo Ricco", "price": 10000, "role_id": 123456789012345678},
    "3": {"name": "🏆 Trofeo Discord", "price": 1000, "role_id": None}
}

# Domande Quiz
QUIZ_QUESTIONS = [
    {"question": "Qual è la capitale della Francia?", "options": ["Berlino", "Parigi", "Madrid", "Roma"], "answer": "Parigi", "reward": 200},
    {"question": "Quanti pianeti ci sono nel sistema solare?", "options": ["7", "8", "9", "10"], "answer": "8", "reward": 150},
    {"question": "Chi ha dipinto la Gioconda?", "options": ["Leonardo da Vinci", "Michelangelo", "Raffaello", "Caravaggio"], "answer": "Leonardo da Vinci", "reward": 250}
]

# Tracciamento Anti-Raid
recent_joins = {}

# --- FUNZIONI UTILITÀ JSON ---
def load_data(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        return json.load(f)

def save_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


# ==========================================
# 1. PANNELLO AMMINISTRAZIONE (/admin_panel)
# ==========================================
class UserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Seleziona l'utente da gestire...", min_values=1, max_values=1)
    async def select_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        target_user = select.values[0]
        embed = discord.Embed(
            title=f"⚙️ Pannello Moderazione: {target_user.name}",
            description=f"Seleziona l'azione da eseguire su <@{target_user.id}>",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="ID Utente", value=f"`{target_user.id}`", inline=True)
        await interaction.response.send_message(embed=embed, view=AdminActionsView(target_user), ephemeral=True)


class AdminActionsView(discord.ui.View):
    def __init__(self, target_user: discord.User):
        super().__init__(timeout=180)
        self.target_user = target_user

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.guild.ban(self.target_user, reason=f"Bannato da {interaction.user.name}")
        await interaction.response.send_message(f"✅ <@{self.target_user.id}> è stato **bannato**.", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.orange, emoji="👢")
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.target_user.id)
        if member:
            await member.kick(reason=f"Espulso da {interaction.user.name}")
            await interaction.response.send_message(f"✅ <@{self.target_user.id}> è stato **espulso**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Utente non presente nel server.", ephemeral=True)

    @discord.ui.button(label="Mute (10m)", style=discord.ButtonStyle.secondary, emoji="🔇")
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.target_user.id)
        if member:
            await member.timeout(datetime.timedelta(minutes=10), reason=f"Mutato da {interaction.user.name}")
            await interaction.response.send_message(f"✅ <@{self.target_user.id}> mutato per 10 min.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Utente non presente nel server.", ephemeral=True)

    @discord.ui.button(label="Unmute", style=discord.ButtonStyle.success, emoji="🔊")
    async def unmute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.target_user.id)
        if member:
            await member.timeout(None)
            await interaction.response.send_message(f"✅ Unmute effettuato per <@{self.target_user.id}>", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Utente non presente nel server.", ephemeral=True)


# ==========================================
# 2. SISTEMA TICKET
# ==========================================
class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        select = discord.ui.Select(
            placeholder="Scegli una categoria...",
            custom_id="ticket_select_menu",
            options=[
                discord.SelectOption(label=cat["label"], description=cat.get("description", ""), emoji=cat.get("emoji", "🎟️"))
                for cat in ticket_config["categories"]
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        await create_ticket_channel(interaction, interaction.data["values"][0])


class TicketButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for cat in ticket_config["categories"]:
            btn = discord.ui.Button(label=cat["label"], emoji=cat.get("emoji", "🎟️"), style=discord.ButtonStyle.primary)
            btn.callback = self.make_callback(cat["label"])
            self.add_item(btn)

    def make_callback(self, category_name):
        async def callback(interaction: discord.Interaction):
            await create_ticket_channel(interaction, category_name)
        return callback


class TicketChannelControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="✋")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Non hai i permessi per questo comando.", ephemeral=True)
        await interaction.channel.send(embed=discord.Embed(description=f"✋ Ticket preso in carico da {interaction.user.mention}.", color=discord.Color.green()))
        await interaction.response.send_message("Ticket preso in carico!", ephemeral=True)

    @discord.ui.button(label="Chiudi", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=discord.Embed(description=f"🔒 Ticket in chiusura tra 5 secondi...", color=discord.Color.red()))
        await asyncio.sleep(5)
        await interaction.channel.delete()


async def create_ticket_channel(interaction: discord.Interaction, category_name: str):
    guild = interaction.guild
    user = interaction.user

    safe_name = user.name.lower().replace(" ", "-")
    existing = discord.utils.get(guild.channels, name=f"ticket-{safe_name}")
    if existing:
        return await interaction.response.send_message(f"❌ Hai già un ticket aperto in {existing.mention}!", ephemeral=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    channel = await guild.create_text_channel(name=f"ticket-{safe_name}", overwrites=overwrites)
    embed = discord.Embed(
        title=f"🎟️ Ticket: {category_name}",
        description=f"Benvenuto {user.mention}!\nDescrivi il tuo problema e uno staffer ti risponderà a breve.",
        color=discord.Color.blue()
    )
    await channel.send(content=f"{user.mention}", embed=embed, view=TicketChannelControlsView())
    await interaction.response.send_message(f"✅ Ticket aperto in {channel.mention}", ephemeral=True)


# ==========================================
# 3. VERIFICA E MODALE CANDIDATURE
# ==========================================
class VerificationButtons(discord.ui.View):
    def __init__(self, correct_number: int):
        super().__init__(timeout=300)
        numbers = [correct_number]
        while len(numbers) < 4:
            r = random.randint(10, 99)
            if r not in numbers:
                numbers.append(r)
        random.shuffle(numbers)

        for num in numbers:
            btn = discord.ui.Button(label=str(num), style=discord.ButtonStyle.secondary)
            btn.callback = self.create_callback(num, correct_number)
            self.add_item(btn)

    def create_callback(self, chosen, correct):
        async def callback(interaction: discord.Interaction):
            if chosen == correct:
                role = interaction.guild.get_role(verification_config["role_id"])
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message("✅ Verifica completata! Ruolo assegnato.", ephemeral=True)
                else:
                    await interaction.response.send_message("⚠️ Ruolo non configurato.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Numero errato, riprova!", ephemeral=True)
        return callback


class StaffApplicationModal(discord.ui.Modal, title="Candidatura Staff"):
    eta = discord.ui.TextInput(label="Quanti anni hai?", placeholder="Incolla età...", required=True, max_length=2)
    esperienza = discord.ui.TextInput(label="Esperienze precedenti", style=discord.TextStyle.paragraph, required=True)
    motivazione = discord.ui.TextInput(label="Perché te?", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"📋 Candidatura da {interaction.user.name}", color=discord.Color.purple())
        embed.add_field(name="Età", value=self.eta.value, inline=True)
        embed.add_field(name="Esperienza", value=self.esperienza.value, inline=False)
        embed.add_field(name="Motivazione", value=self.motivazione.value, inline=False)
        await interaction.response.send_message("✅ Candidatura inviata allo staff!", ephemeral=True)


class QuizView(discord.ui.View):
    def __init__(self, q_data, user_id):
        super().__init__(timeout=30)
        self.q_data = q_data
        self.user_id = user_id

        for opt in q_data["options"]:
            btn = discord.ui.Button(label=opt, style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(opt)
            self.add_item(btn)

    def make_callback(self, chosen):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ Quiz non tuo!", ephemeral=True)
            if chosen == self.q_data["answer"]:
                econ = load_data(ECONOMY_FILE)
                uid = str(interaction.user.id)
                econ[uid] = econ.get(uid, {"wallet": 0, "bank": 0})
                econ[uid]["wallet"] += self.q_data["reward"]
                save_data(ECONOMY_FILE, econ)
                await interaction.response.send_message(f"✅ Risposta corretta! +🪙 **{self.q_data['reward']} monete**", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Errato! La risposta era **{self.q_data['answer']}**.", ephemeral=True)
            self.stop()
        return callback


# ==========================================
# EVENTI DEL BOT (JOIN, REMOVE, MESSAGE)
# ==========================================
@bot.event
async def on_ready():
    print(f"🤖 Bot connesso come {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Sincronizzati {len(synced)} comandi slash.")
    except Exception as e:
        print(f"Errore sincronizzazione comandi: {e}")


@bot.event
async def on_member_join(member: discord.Member):
    if AUTOROLE_ID != 0:
        role = member.guild.get_role(AUTOROLE_ID)
        if role:
            await member.add_roles(role)

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="👋 Nuovo Arrivo!",
            description=f"GG👑 SEI ENTRATO SU **{member.guild.name}**, {member.mention}! Fatti un giro e vedi se ti piace.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    now = time.time()
    recent_joins.setdefault(member.guild.id, []).append(now)
    recent_joins[member.guild.id] = [t for t in recent_joins[member.guild.id] if now - t < 10]
    if len(recent_joins[member.guild.id]) > 5:
        sys_chan = member.guild.system_channel
        if sys_chan:
            await sys_chan.send("🚨 **ALLARME ANTI-RAID ATTIVATO!** Rilevati troppi accessi contemporanei.")


@bot.event
async def on_member_remove(member: discord.Member):
    channel = member.guild.get_channel(GOODBYE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="👋 Utente Uscito",
            description=f"NOOO🌹 **{member.name}**, è uscito da **{member.guild.name}**, ADDIO😢",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if not message.author.guild_permissions.administrator:
        if "discord.gg/" in message.content.lower() or "https://" in message.content.lower():
            try:
                await message.delete()
                msg = await message.channel.send(f"⚠️ {message.author.mention}, i link non sono consentiti!")
                await asyncio.sleep(4)
                await msg.delete()
                return
            except Exception:
                pass

    levels = load_data(LEVELS_FILE)
    uid = str(message.author.id)
    levels[uid] = levels.get(uid, {"xp": 0, "level": 1})
    levels[uid]["xp"] += random.randint(5, 15)

    needed = levels[uid]["level"] * 100
    if levels[uid]["xp"] >= needed:
        levels[uid]["level"] += 1
        levels[uid]["xp"] = 0
        await message.channel.send(f"🎉 {message.author.mention} è salito al **Livello {levels[uid]['level']}**!")

    save_data(LEVELS_FILE, levels)
    await bot.process_commands(message)


# ==========================================
# REGISTRAZIONE COMANDI SLASH (/...)
# ==========================================

@bot.tree.command(name="admin_panel", description="Apre il pannello di amministrazione.")
@app_commands.checks.has_permissions(administrator=True)
async def admin_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ Pannello Amministrazione", description="Seleziona un utente dal menu sottostante.", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, view=UserSelectView(), ephemeral=True)


@bot.tree.command(name="ticket_setup", description="Invia il pannello per aprire i ticket.")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction):
    embed = discord.Embed(title=ticket_config["title"], description=ticket_config["description"], color=discord.Color.gold())
    view = TicketSelectView() if ticket_config["style"] == "menu" else TicketButtonsView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Pannello inviato!", ephemeral=True)


@bot.tree.command(name="ticket_add", description="Aggiungi un utente al ticket.")
async def ticket_add(interaction: discord.Interaction, utente: discord.Member):
    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("❌ Usa questo comando solo nei canali ticket!", ephemeral=True)
    await interaction.channel.set_permissions(utente, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"✅ {utente.mention} aggiunto al ticket.")


@bot.tree.command(name="verify_setup", description="Invia il pannello di verifica.")
@app_commands.checks.has_permissions(administrator=True)
async def verify_setup(interaction: discord.Interaction):
    corr = random.randint(10, 99)
    embed = discord.Embed(title="🔒 Verifica", description=f"Clicca sul pulsante con il numero: **{corr}**", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=VerificationButtons(corr))
    await interaction.response.send_message("✅ Pannello verifica inviato!", ephemeral=True)


@bot.tree.command(name="balance", description="Controlla il tuo saldo o quello di un utente.")
async def balance(interaction: discord.Interaction, utente: discord.Member = None):
    target = utente or interaction.user
    data = load_data(ECONOMY_FILE).get(str(target.id), {"wallet": 100, "bank": 0})
    embed = discord.Embed(title=f"💰 Portafoglio di {target.name}", color=discord.Color.gold())
    embed.add_field(name="Contanti", value=f"🪙 `{data.get('wallet', 100)}`")
    embed.add_field(name="Banca", value=f"🏦 `{data.get('bank', 0)}`")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="work", description="Lavora per guadagnare monete.")
async def work(interaction: discord.Interaction):
    econ = load_data(ECONOMY_FILE)
    uid = str(interaction.user.id)
    econ[uid] = econ.get(uid, {"wallet": 100, "bank": 0})
    earn = random.randint(50, 300)
    econ[uid]["wallet"] += earn
    save_data(ECONOMY_FILE, econ)
    await interaction.response.send_message(f"💼 Hai guadagnato 🪙 **{earn} monete**!")


@bot.tree.command(name="daily", description="Raccogli il bonus giornaliero.")
async def daily(interaction: discord.Interaction):
    econ = load_data(ECONOMY_FILE)
    uid = str(interaction.user.id)
    user_data = econ.get(uid, {"wallet": 100, "bank": 0, "last_daily": None})
    now = datetime.datetime.now(datetime.timezone.utc)

    if user_data.get("last_daily"):
        try:
            last = datetime.datetime.fromisoformat(user_data["last_daily"])
        except Exception:
            last = None

        if last and (now - last) < datetime.timedelta(hours=24):
            remaining = datetime.timedelta(hours=24) - (now - last)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            return await interaction.response.send_message(f"⏳ Hai già riscattato il daily. Riprova tra {hours}h {minutes}m.", ephemeral=True)

    reward = random.randint(200, 800)
    user_data["wallet"] = user_data.get("wallet", 100) + reward
    user_data["last_daily"] = now.isoformat()
    econ[uid] = user_data
    save_data(ECONOMY_FILE, econ)
    await interaction.response.send_message(f"🎁 Hai raccolto il daily! +🪙 **{reward}**.", ephemeral=True)


@bot.tree.command(name="shop", description="Mostra gli oggetti disponibili nel negozio.")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Negozio", color=discord.Color.blurple())
    for item_id, info in SHOP_ITEMS.items():
        role_text = f" (ruolo ID: {info['role_id']})" if info.get("role_id") else ""
        embed.add_field(name=f"{item_id}. {info['name']}", value=f"Prezzo: 🪙 `{info['price']}`{role_text}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="buy", description="Acquista un oggetto dal negozio.")
async def buy(interaction: discord.Interaction, item_id: str):
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return await interaction.response.send_message("❌ Articolo non trovato.", ephemeral=True)

    econ = load_data(ECONOMY_FILE)
    uid = str(interaction.user.id)
    econ[uid] = econ.get(uid, {"wallet": 100, "bank": 0})
    if econ[uid]["wallet"] < item["price"]:
        return await interaction.response.send_message("❌ Non hai abbastanza monete.", ephemeral=True)

    econ[uid]["wallet"] -= item["price"]
    save_data(ECONOMY_FILE, econ)

    if item.get("role_id"):
        role = interaction.guild.get_role(item["role_id"])
        if role:
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                await member.add_roles(role)
                await interaction.response.send_message(f"✅ Acquistato **{item['name']}** e ruolo assegnato!", ephemeral=True)
                return

    await interaction.response.send_message(f"✅ Acquistato **{item['name']}**!", ephemeral=True)


@bot.tree.command(name="quiz", description="Partecipa al quiz e vinci monete.")
async def quiz(interaction: discord.Interaction):
    q = random.choice(QUIZ_QUESTIONS)
    embed = discord.Embed(title="❓ Quiz", description=q["question"], color=discord.Color.teal())
    for i, opt in enumerate(q["options"], start=1):
        embed.add_field(name=f"{i}.", value=opt, inline=False)
    view = QuizView(q, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)


# Avvia il bot
if __name__ == "__main__":
    if not TOKEN:
        print("ERRORE: DISCORD_TOKEN non impostato nel .env")
    else:
        bot.run(TOKEN)
