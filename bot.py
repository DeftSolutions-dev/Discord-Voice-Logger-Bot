import discord
from discord.ext import commands
from discord.ui import View, Button
from datetime import datetime, timezone
import aiosqlite
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TOKEN')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'voice_logs.db')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
GUILD_ID = int(os.getenv('GUILD_ID'))

if TOKEN is None:
    raise ValueError("Токен не найден. Пожалуйста, добавьте его в файл .env.")

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.user_voice_data = {}

def format_duration(duration):
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours} ч {minutes} м {seconds} с"

async def send_log(embed: discord.Embed):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)

async def save_log(user_id, username, event_type, channel_before, channel_after, timestamp, duration):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT INTO voice_logs (user_id, username, event_type, channel_before, channel_after, timestamp, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, event_type, channel_before, channel_after, timestamp, duration))
        await db.commit()

class LogButton(Button):
    def __init__(self, label: str, user_id: int, date_str: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"log_button_{date_str}")
        self.user_id = user_id
        self.date_str = date_str

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Вы не можете использовать эти кнопки.", ephemeral=True)
            return
        try:
            search_date = datetime.strptime(self.date_str, '%m/%d/%Y').date()
        except ValueError:
            await interaction.response.send_message("❌ Неверный формат даты.", ephemeral=True)
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute('''
                SELECT user_id, username, event_type, channel_before, channel_after, timestamp, duration
                FROM voice_logs 
                WHERE user_id = ? AND date(timestamp) = ?
                ORDER BY timestamp DESC LIMIT 25
            ''', (self.user_id, search_date.isoformat()))
            rows = await cursor.fetchall()
        if not rows:
            await interaction.response.send_message(f"🔍 Логи за дату {self.date_str} не найдены.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"📜 Голосовые логи за {self.date_str}",
            color=0x3498DB,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Запрошено пользователем {interaction.user}", icon_url=interaction.user.display_avatar.url)
        for row in rows:
            user_id, username, event_type, channel_before, channel_after, timestamp, duration = row
            user_tag = f"{username} (ID: {user_id})"
            try:
                timestamp_dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                timestamp_formatted = timestamp_dt.strftime('%m/%d/%Y %H:%M:%S UTC')
            except ValueError:
                timestamp_formatted = timestamp
            if event_type == "join":
                description = (
                    f"**Тип события**: Присоединение\n"
                    f"**Канал**: {channel_after}\n"
                    f"**Время**: {timestamp_formatted}"
                )
            elif event_type == "leave":
                description = (
                    f"**Тип события**: Покидание\n"
                    f"**Канал**: {channel_before}\n"
                    f"**Время выхода**: {timestamp_formatted}\n"
                    f"**Время пребывания**: {duration}"
                )
            elif event_type == "switch":
                description = (
                    f"**Тип события**: Переключение каналов\n"
                    f"**Исходный канал**: {channel_before}\n"
                    f"**Новый канал**: {channel_after}\n"
                    f"**Время переключения**: {timestamp_formatted}\n"
                    f"**Время в исходном канале**: {duration}"
                )
            else:
                description = "Неизвестное событие."
            embed.add_field(name=user_tag, value=description, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

class LogView(View):
    def __init__(self, user_id: int, available_dates: list):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.available_dates = available_dates
        self.current_page = 0
        self.max_page = (len(self.available_dates) - 1) // 25
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start = self.current_page * 25
        end = start + 25
        for date in self.available_dates[start:end]:
            self.add_item(LogButton(label=date, user_id=self.user_id, date_str=date))
        if self.max_page > 0:
            if self.current_page > 0:
                self.add_item(PaginationButton(label='⬅️', custom_id='prev'))
            if self.current_page < self.max_page:
                self.add_item(PaginationButton(label='➡️', custom_id='next'))

    async def on_timeout(self):
        self.clear_items()
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

class PaginationButton(Button):
    def __init__(self, label: str, custom_id: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        view: LogView = self.view
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("❌ Вы не можете использовать эти кнопки.", ephemeral=True)
            return
        if self.custom_id == 'prev' and view.current_page > 0:
            view.current_page -= 1
            view.update_buttons()
            await interaction.response.edit_message(view=view)
        elif self.custom_id == 'next' and view.current_page < view.max_page:
            view.current_page += 1
            view.update_buttons()
            await interaction.response.edit_message(view=view)
        else:
            await interaction.response.defer()

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} успешно запущен и готов к работе!')
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS voice_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                channel_before TEXT,
                channel_after TEXT,
                timestamp TEXT NOT NULL,
                duration TEXT
            )
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON voice_logs(user_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON voice_logs(timestamp)')
        await db.commit()

@bot.slash_command(
    name="log",
    description="Посмотреть голосовые логи",
    guild_ids=[GUILD_ID]
)
async def log(ctx: discord.ApplicationContext, member: discord.Member = None, date: str = None):
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.respond("❌ У вас нет прав для использования этой команды.", ephemeral=True)
        return
    query_user = member.id if member else None
    query_date = date
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if query_user:
            if query_date:
                try:
                    search_date = datetime.strptime(query_date, '%m/%d/%Y').date()
                except ValueError:
                    await ctx.respond("❌ Неверный формат даты. Пожалуйста, используйте формат `MM/DD/YYYY`.", ephemeral=True)
                    return
                cursor = await db.execute('''
                    SELECT user_id, username, event_type, channel_before, channel_after, timestamp, duration
                    FROM voice_logs 
                    WHERE user_id = ? AND date(timestamp) = ?
                    ORDER BY timestamp DESC LIMIT 25
                ''', (query_user, search_date.isoformat()))
                rows = await cursor.fetchall()
                if not rows:
                    await ctx.respond(f"🔍 Логи для пользователя {member} за дату {search_date.strftime('%m/%d/%Y')} не найдены.", ephemeral=True)
                    return
                embed = discord.Embed(
                    title=f"📜 Голосовые логи для {member} за {search_date.strftime('%m/%d/%Y')}",
                    color=0x3498DB,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                cursor = await db.execute('''
                    SELECT DISTINCT date(timestamp) as log_date
                    FROM voice_logs
                    WHERE user_id = ? AND date(timestamp) IS NOT NULL
                    ORDER BY log_date DESC
                ''', (query_user,))
                dates = await cursor.fetchall()
                if not dates:
                    await ctx.respond(f"📭 Пользователь {member} никогда не заходил ни в один голосовой канал.", ephemeral=True)
                    return
                date_list = []
                for row in dates:
                    if row[0]:
                        try:
                            formatted_date = datetime.strptime(row[0], '%Y-%m-%d').strftime('%m/%d/%Y')
                            date_list.append(formatted_date)
                        except ValueError:
                            continue
                if not date_list:
                    await ctx.respond("📭 Не удалось найти доступные даты.", ephemeral=True)
                    return
                embed = discord.Embed(
                    title=f"📅 Доступные даты для {member}",
                    description='\n'.join(date_list),
                    color=0x3498DB,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text="Пожалуйста, выберите дату для просмотра логов.")
                view = LogView(user_id=query_user, available_dates=date_list)
                view.message = await ctx.respond(embed=embed, view=view, ephemeral=False)
                return
        else:
            if query_date:
                try:
                    search_date = datetime.strptime(query_date, '%m/%d/%Y').date()
                except ValueError:
                    await ctx.respond("❌ Неверный формат даты. Пожалуйста, используйте формат `MM/DD/YYYY`.", ephemeral=True)
                    return
                cursor = await db.execute('''
                    SELECT user_id, username, event_type, channel_before, channel_after, timestamp, duration
                    FROM voice_logs 
                    WHERE date(timestamp) = ?
                    ORDER BY timestamp DESC LIMIT 25
                ''', (search_date.isoformat(),))
                rows = await cursor.fetchall()
                if not rows:
                    await ctx.respond(f"🔍 Логи за дату {search_date.strftime('%m/%d/%Y')} не найдены.", ephemeral=True)
                    return
                embed = discord.Embed(
                    title=f"📜 Голосовые логи за {search_date.strftime('%m/%d/%Y')}",
                    color=0x3498DB,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                cursor = await db.execute('''
                    SELECT user_id, username, event_type, channel_before, channel_after, timestamp, duration 
                    FROM voice_logs 
                    ORDER BY timestamp DESC LIMIT 25
                ''')
                rows = await cursor.fetchall()
                if not rows:
                    await ctx.respond("📭 Нет доступных логов.", ephemeral=True)
                    return
                embed = discord.Embed(
                    title="📜 Все голосовые логи",
                    color=0x3498DB,
                    timestamp=datetime.now(timezone.utc)
                )
        if (query_user and not query_date) or not query_user:
            if query_user and not query_date:
                await ctx.respond(
                    embed=embed,
                    view=LogView(user_id=query_user, available_dates=date_list) if 'date_list' in locals() else None,
                    ephemeral=False
                )
            else:
                await ctx.respond(embed=embed, ephemeral=False)
            return
        for row in rows:
            user_id, username, event_type, channel_before, channel_after, timestamp, duration = row
            user_tag = f"{username} (ID: {user_id})"
            try:
                timestamp_dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                timestamp_formatted = timestamp_dt.strftime('%m/%d/%Y %H:%M:%S UTC')
            except ValueError:
                timestamp_formatted = timestamp
            if event_type == "join":
                description = (
                    f"**Тип события**: Присоединение\n"
                    f"**Канал**: {channel_after}\n"
                    f"**Время**: {timestamp_formatted}"
                )
            elif event_type == "leave":
                description = (
                    f"**Тип события**: Покидание\n"
                    f"**Канал**: {channel_before}\n"
                    f"**Время выхода**: {timestamp_formatted}\n"
                    f"**Время пребывания**: {duration}"
                )
            elif event_type == "switch":
                description = (
                    f"**Тип события**: Переключение каналов\n"
                    f"**Исходный канал**: {channel_before}\n"
                    f"**Новый канал**: {channel_after}\n"
                    f"**Время переключения**: {timestamp_formatted}\n"
                    f"**Время в исходном канале**: {duration}"
                )
            else:
                description = "Неизвестное событие."
            embed.add_field(name=user_tag, value=description, inline=False)
        await ctx.respond(embed=embed, ephemeral=False)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    if before.channel is None and after.channel is not None:
        bot.user_voice_data[member.id] = {
            'channel': after.channel,
            'join_time': datetime.now(timezone.utc)
        }
        join_embed = discord.Embed(
            title="🔊 Присоединение к голосовому каналу",
            color=0x00FF00,
            timestamp=datetime.now(timezone.utc)
        )
        join_embed.add_field(name="Пользователь", value=member.mention, inline=False)
        join_embed.add_field(name="Канал", value=after.channel.name, inline=False)
        join_embed.add_field(name="Время присоединения", value=current_time, inline=False)
        await send_log(join_embed)
        await save_log(
            user_id=member.id,
            username=member.display_name,
            event_type="join",
            channel_before=None,
            channel_after=after.channel.name,
            timestamp=current_time,
            duration=None
        )
    elif before.channel is not None and after.channel is None:
        voice_info = bot.user_voice_data.pop(member.id, None)
        if voice_info:
            leave_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            duration = datetime.now(timezone.utc) - voice_info['join_time']
            duration_str = format_duration(duration)
            leave_embed = discord.Embed(
                title="🔊 Покидание голосового канала",
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )
            leave_embed.add_field(name="Пользователь", value=member.mention, inline=False)
            leave_embed.add_field(name="Канал", value=voice_info['channel'].name, inline=False)
            leave_embed.add_field(name="Время выхода", value=leave_time, inline=False)
            leave_embed.add_field(name="Время пребывания", value=duration_str, inline=False)
            await send_log(leave_embed)
            await save_log(
                user_id=member.id,
                username=member.display_name,
                event_type="leave",
                channel_before=voice_info['channel'].name,
                channel_after=None,
                timestamp=leave_time,
                duration=duration_str
            )
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        voice_info = bot.user_voice_data.get(member.id)
        if voice_info:
            switch_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            duration = datetime.now(timezone.utc) - voice_info['join_time']
            duration_str = format_duration(duration)
            switch_embed = discord.Embed(
                title="🔀 Переключение голосовых каналов",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )
            switch_embed.add_field(name="Пользователь", value=member.mention, inline=False)
            switch_embed.add_field(name="Исходный канал", value=before.channel.name, inline=True)
            switch_embed.add_field(name="Новый канал", value=after.channel.name, inline=True)
            switch_embed.add_field(name="Время переключения", value=switch_time, inline=False)
            switch_embed.add_field(name="Время в исходном канале", value=duration_str, inline=False)
            await send_log(switch_embed)
            await save_log(
                user_id=member.id,
                username=member.display_name,
                event_type="switch",
                channel_before=before.channel.name,
                channel_after=after.channel.name,
                timestamp=switch_time,
                duration=duration_str
            )
        bot.user_voice_data[member.id] = {
            'channel': after.channel,
            'join_time': datetime.now(timezone.utc)
        }

bot.run(TOKEN)