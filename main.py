import asyncio, json, os, re
from threading import Thread
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return 'Bot is running!'
def run_flask(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_flask).start()

GUILD_ID = 1462673426203545612
ADMIN_ROLE_ID = 1462814785392611368
TICKET_CATEGORY_ID = 1462814785392611368
STOCK_FILE, CONFIG_FILE, MESSAGES_FILE = 'stock.json', 'config.json', 'messages.json'
DEFAULT_PASSWORD = 'mhdg1122'

DEFAULT_CURRENCIES = {
    'credit': {'label': 'credit', 'enabled': True, 'amount': '0'},
    'crypto': {'label': 'crypto', 'enabled': True, 'amount': '0'},
    'robux': {'label': 'robux', 'enabled': True, 'amount': '0'},
    'real': {'label': 'real', 'enabled': True, 'amount': '0'},
    'uc': {'label': 'uc', 'enabled': True, 'amount': '0'},
    'vodafone': {'label': 'vodafone', 'enabled': True, 'amount': '0'},
    'nitro': {'label': 'نيترو جيفت', 'enabled': True, 'amount': '0'},
    'asia': {'label': 'asia', 'enabled': True, 'amount': '0'},
    'effects': {'label': 'effects', 'enabled': True, 'amount': '0'},
    'boosts': {'label': 'بوستات شهر', 'enabled': True, 'amount': '0'},
    'paypal': {'label': 'paypal', 'enabled': True, 'amount': '0'},
    'cliq': {'label': 'cliq cliq', 'enabled': True, 'amount': '0'},
}

DEFAULT_MESSAGES = {
    'verify_success': "✅ **تم التحقق من وجود الحساب بنجاح!**\n\n💵 **مجموعك الحسابي:** `{total_price}` ({currency_name})\n📦 **عدد الحسابات:** `{count}`\n\n📌 **سيتم تسليمك فور التأكيد.**",
    'ticket_welcome': "إرعررررحب\nاختار العملة التي تريد الاستلام بها.",
    'quantity_welcome': "اختار الكمية التي تريدها من القائمة بالأسفل.",
    'delivery_msg': "📦 **تم تسليم {amount} إيميل فوراً**\n\n**العملة:** {currency}\n**سعر القطعة:** `{unit_price}`\n**المجموع الكلي:** `{total_price}`\n\n**الحسابات:**\n{accounts_text}\n\n⚠️ اضغط على (فحص الحساب) بالأسفل للتأكد."
}

intents = discord.Intents.default()
intents.message_content = intents.members = intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

def load_json(fp, def_d):
    if not os.path.exists(fp):
        with open(fp, 'w', encoding='utf-8') as f: json.dump(def_d, f, indent=4, ensure_ascii=False)
    with open(fp, 'r', encoding='utf-8') as f: return json.load(f)

def save_json(fp, data):
    with open(fp, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

def load_stock(): return load_json(STOCK_FILE, [])
def save_stock(d): save_json(STOCK_FILE, d)
def load_config(): return load_json(CONFIG_FILE, DEFAULT_CURRENCIES)
def save_config(d): save_json(CONFIG_FILE, d)
def load_messages(): return load_json(MESSAGES_FILE, DEFAULT_MESSAGES)
def save_messages(d): save_json(MESSAGES_FILE, d)

def check_email_exists(email):
    if not re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email.strip()): return False
    u = email.split('@')[0]
    return 6 <= len(u) <= 30

def calculate_total(unit_str, count):
    nums = re.findall(r'\d+\.?\d*', str(unit_str))
    if nums:
        val = float(nums[0]) * count
        return str(int(val)) if val.is_integer() else f"{val:.2f}"
    return f"{unit_str} × {count}"

class EditMessageModal(discord.ui.Modal):
    def __init__(self, msg_key, title_name):
        super().__init__(title=f'تعديل: {title_name}')
        self.msg_key = msg_key
        self.text_input = discord.ui.TextInput(label='النص الجديد:', default=load_messages().get(msg_key, ''), style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.text_input)
    async def on_submit(self, inter):
        msgs = load_messages()
        msgs[self.msg_key] = self.text_input.value
        save_messages(msgs)
        await inter.response.send_message(f"✅ تم التحديث بنجاح!", ephemeral=True)

class MsgSettingsView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label='تعديل الفحص والتحقق 🔍', style=discord.ButtonStyle.primary)
    async def edit_verify(self, inter, btn): await inter.response.send_modal(EditMessageModal('verify_success', 'فحص الحساب'))
    @discord.ui.button(label='تعديل التسليم 📦', style=discord.ButtonStyle.primary)
    async def edit_delivery(self, inter, btn): await inter.response.send_modal(EditMessageModal('delivery_msg', 'التسليم'))
    @discord.ui.button(label='تعديل الترحيب 📝', style=discord.ButtonStyle.secondary)
    async def edit_welcomes(self, inter, btn): await inter.response.send_modal(EditMessageModal('quantity_welcome', 'الكمية'))

class EditAmountModal(discord.ui.Modal):
    def __init__(self, c_key, c_name):
        super().__init__(title=f'سعر: {c_name}')
        self.c_key = c_key
        self.amount_input = discord.ui.TextInput(label='السعر الجديد:', default=str(load_config().get(c_key, {}).get('amount', '')), required=True)
        self.add_item(self.amount_input)
    async def on_submit(self, inter):
        cfg = load_config()
        if self.c_key in cfg:
            cfg[self.c_key]['amount'] = self.amount_input.value
            cfg[self.c_key]['enabled'] = True
            save_config(cfg)
            await inter.response.send_message(f"✅ تم تحديث السعر إلى `{self.amount_input.value}`", ephemeral=True)

class AdminCurrencyControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for k, info in load_config().items():
            is_on = info.get('enabled', True)
            btn = discord.ui.Button(label=f"{'🟢' if is_on else '🔴'} {info['label']}", style=discord.ButtonStyle.success if is_on else discord.ButtonStyle.danger, custom_id=f'admin_btn_{k}')
            btn.callback = self.make_cb(k, info['label'])
            self.add_item(btn)
    def make_cb(self, key, name):
        async def cb(inter):
            class ChoiceView(discord.ui.View):
                @discord.ui.button(label='تعديل السعر ✏️', style=discord.ButtonStyle.primary)
                async def e(self, i, b): await i.response.send_modal(EditAmountModal(key, name))
                @discord.ui.button(label='تعطيل 🛑', style=discord.ButtonStyle.danger)
                async def d(self, i, b):
                    cfg = load_config()
                    cfg[key]['enabled'] = False
                    save_config(cfg)
                    await i.response.send_message(f"🔴 تم التعطيل", ephemeral=True)
            await inter.response.send_message(f"تحكم بعملة **{name}**:", view=ChoiceView(), ephemeral=True)
        return cb

class MoreAccountsView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label='طلب حسابات إضافية ➕', style=discord.ButtonStyle.primary, custom_id='more_accs_btn')
    async def request_more(self, inter, btn):
        embed = discord.Embed(title='نظام التوزيع', description=load_messages().get('ticket_welcome', ''), color=discord.Color.blue())
        await inter.response.send_message(embed=embed, view=CurrencySelectView(), ephemeral=True)

class AccountActionsView(discord.ui.View):
    def __init__(self, emails, c_name, unit, count):
        super().__init__(timeout=None)
        self.emails, self.c_name, self.unit, self.count = emails, c_name, unit, count
    @discord.ui.button(label='فحص الحساب والتحقق 🔍', style=discord.ButtonStyle.success, custom_id='check_emails_btn')
    async def check_emails(self, inter, btn):
        await inter.response.defer(ephemeral=True)
        working = [e for e in self.emails if check_email_exists(e)]
        bad = [e for e in self.emails if e not in working]
        msgs = load_messages()
        total = calculate_total(self.unit, self.count)
        if working:
            desc = msgs.get('verify_success', '').format(total_price=total, currency_name=self.c_name, count=self.count)
            desc += "\n\n**الحسابات:**\n" + "\n".join([f"✅ `{e}`" for e in working])
            if bad: desc += "\n\n❌ **غير صالحة:**\n" + '\n'.join([f'❌ `{e}`' for e in bad])
            await inter.followup.send(embed=discord.Embed(title='نتيجة التحقق', description=desc, color=discord.Color.green()), view=MoreAccountsView(), ephemeral=True)
        else:
            await inter.followup.send(embed=discord.Embed(title='❌ فشل التحقق', description='الحسابات غير صالحة.', color=discord.Color.red()), ephemeral=True)
    @discord.ui.button(label='نسخ الحسابات 📋', style=discord.ButtonStyle.secondary, custom_id='copy_emails_btn')
    async def copy_emails(self, inter, btn):
        raw = '\n'.join([f'{e}:{DEFAULT_PASSWORD}' for e in self.emails])
        await inter.response.send_message(embed=discord.Embed(title='📋 | نسخ سريع', description=f'```text\n{raw}\n```', color=discord.Color.light_grey()), ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label='إغلاق التذكرة 🔒', style=discord.ButtonStyle.danger, custom_id='close_ticket_btn')
    async def close_ticket(self, inter, btn):
        await inter.response.send_message(embed=discord.Embed(title='🔒 | جاري الإغلاق', description='سيتم الحذف...', color=discord.Color.red()))
        await asyncio.sleep(3)
        try: await inter.channel.delete()
        except: pass

class QuantitySelectMenu(discord.ui.Select):
    def __init__(self, c_name, unit):
        self.c_name, self.unit = c_name, unit
        opts = [discord.SelectOption(label=f'{i} حسابات' if i>1 else '1 حساب', value=str(i)) for i in [1, 3, 5, 10]]
        super().__init__(placeholder='اختار الكمية', options=opts)
    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        amt = int(self.values[0])
        stock = [s for s in load_stock() if isinstance(s, str) and s.strip().lower().endswith('@gmail.com')]
        if len(stock) < amt:
            return await inter.followup.send(embed=discord.Embed(title='❌ | الكمية غير كافية', description=f'المتوفر: {len(stock)}', color=discord.Color.red()), ephemeral=True)
        taken, remaining = stock[:amt], stock[amt:]
        save_stock(remaining)
        acc_text = "".join([f'**{i+1}.** `{e}`\n' for i, e in enumerate(taken)]) + f'الباسورد: `{DEFAULT_PASSWORD}`'
        desc = load_messages().get('delivery_msg', '').format(amount=amt, currency=self.c_name, unit_price=self.unit, total_price=calculate_total(self.unit, amt), accounts_text=acc_text)
        await inter.followup.send(embed=discord.Embed(title='📦 | تسليم الحسابات', description=desc, color=discord.Color.blue()), view=AccountActionsView(taken, self.c_name, self.unit, amt), ephemeral=True)

class QuantitySelectView(discord.ui.View):
    def __init__(self, c_name, unit):
        super().__init__(timeout=None)
        self.add_item(QuantitySelectMenu(c_name, unit))

class CurrencySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for k, info in load_config().items():
            en = info.get('enabled', True)
            btn = discord.ui.Button(label=info['label'], style=discord.ButtonStyle.success if en else discord.ButtonStyle.danger, custom_id=f'user_select_{k}')
            btn.callback = self.make_cb(info['label'], info.get('amount', '0'), en)
            self.add_item(btn)
    def make_cb(self, name, amount, en):
        async def cb(inter):
            if not en: return await inter.response.send_message(embed=discord.Embed(title='🛑', description='العملة مغلقة.', color=discord.Color.red()), ephemeral=True)
            embed = discord.Embed(title='اختر الكمية', description=load_messages().get('quantity_welcome', ''), color=discord.Color.blue())
            await inter.response.send_message(content=f'{inter.user.mention}', embed=embed, view=QuantitySelectView(name, amount), ephemeral=True)
        return cb

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label='اضغط لإنشاء حساب 🔓', style=discord.ButtonStyle.success, custom_id='open_ticket_btn')
    async def open_ticket(self, inter, btn):
        await inter.response.defer(ephemeral=True)
        g, cat = inter.guild, inter.guild.get_channel(TICKET_CATEGORY_ID)
        overwrites = {g.default_role: discord.PermissionOverwrite(view_channel=False), inter.user: discord.PermissionOverwrite(view_channel=True, send_messages=True), g.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        if r := g.get_role(ADMIN_ROLE_ID): overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        try:
            ch = await g.create_text_channel(name=f'ticket-{inter.user.name}', category=cat, overwrites=overwrites)
            await ch.send(content=inter.user.mention, embed=discord.Embed(title='نظام التوزيع', description=load_messages().get('ticket_welcome', ''), color=discord.Color.blue()), view=CurrencySelectView())
            await ch.send(view=CloseTicketView())
            await inter.followup.send(embed=discord.Embed(title='✅', description=f'تم فتح التذكرة: {ch.mention}', color=discord.Color.green()), ephemeral=True)
        except Exception as e: print(e)

@bot.tree.command(name='msgsettings', description='تعديل الرسائل')
async def msgsettings(inter):
    if not inter.user.guild_permissions.administrator: return await inter.response.send_message('❌ ليس لديك صلاحية.', ephemeral=True)
    await inter.response.send_message(embed=discord.Embed(title='⚙️ | تعديل الرسائل', color=discord.Color.gold()), view=MsgSettingsView(), ephemeral=True)

@bot.tree.command(name='settings', description='لوحة الأسعار')
async def settings(inter):
    if not inter.user.guild_permissions.administrator: return await inter.response.send_message('❌ ليس لديك صلاحية.', ephemeral=True)
    await inter.response.send_message(embed=discord.Embed(title='⚙️ | تحكم الأسعار', color=discord.Color.gold()), view=AdminCurrencyControlView(), ephemeral=True)

@bot.tree.command(name='addstock', description='إضافة إيميلات')
async def addstock(inter, text: str):
    if not inter.user.guild_permissions.administrator: return await inter.response.send_message('❌ ليس لديك صلاحية.', ephemeral=True)
    found = re.findall(r'[a-zA-Z0-9._%+-]+@gmail\.com', text, re.IGNORECASE)
    if not found: return await inter.response.send_message(embed=discord.Embed(title='❌', description='لم يتم العثور على إيميلات صالحة.', color=discord.Color.red()), ephemeral=True)
    stock = load_stock()
    stock.extend(found)
    save_stock(stock)
    await inter.response.send_message(embed=discord.Embed(title='✅', description=f'تم إضافة {len(found)} إيميل.', color=discord.Color.green()), ephemeral=True)

@bot.tree.command(name='setup', description='إرسال رسالة التكت')
async def setup(inter):
    if not inter.user.guild_permissions.administrator: return await inter.response.send_message("❌", ephemeral=True)
    await inter.channel.send(embed=discord.Embed(title="نظام توزيع الحسابات", description="اضغط لفتح تذكرة استلام.", color=discord.Color.blue()), view=TicketView())
    await inter.response.send_message("✅ تم الإرسال.", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    for v in [TicketView(), CloseTicketView(), AdminCurrencyControlView(), MoreAccountsView()]: bot.add_view(v)
    print(f'✅ Bot is ready! {bot.user}')

keep_alive()
bot.run("MTU0ODM3ODIyMjUxNTcyNDI4OA.GZj5f2.jsMK2U6a7ZJDPSQ01U-8BIy8uBGwbJca3BGO9s")

