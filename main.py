"""BDO Party-Finder Discord Bot
v2.8 – on cancel: also deletes/archives the party thread
made by @koozy
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal

import discord
from discord import app_commands, PartialEmoji
from discord.ext import commands
from dotenv import load_dotenv

# ────────────  ENV  ────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID_LIST = [int(x) for x in os.getenv("GUILD_IDS", "").split(",") if x]

# ─────────── CONFIG ───────────
DOLUNS_ROLE_ID,  DOLUNS_ROLE_NAME   = 1202775580651561000, "doluns"
BOSS_ROLE_ID,    BOSS_ROLE_NAME     = 1285747877846716490, "bossblitzers"
DUNGEON_ROLE_ID, DUNGEON_ROLE_NAME  = 1202775939185115207, "dungeon"

CLASS_LIST = [
    "Warrior", "Ranger", "Sorceress", "Berserker", "Tamer", "Musa", "Maehwa",
    "Valkyrie", "Kunoichi", "Ninja", "Wizard", "Witch", "Dark Knight",
    "Striker", "Mystic", "Lahn", "Archer", "Shai", "Guardian", "Hashashin",
    "Nova", "Sage", "Corsair", "Drakania", "Woosa", "Maegu", "Scholar",
    "Dosa", "Deadeye",
]

CLASS_EMOJIS: dict[str, tuple[str, int]] = {
    "Warrior":   ("warrior", 1054117865432830012),
    "Ranger":    ("ranger", 1054117859145564210),
    "Sorceress": ("sorceress", 1054117862467444787),
    "Berserker": ("berserker", 937874380648771685),
    "Tamer":     ("tamer", 1152015018385231952),
    "Musa":      ("musa", 1054117854515048580),
    "Maehwa":    ("maehwa", 1054117810625855608),
    "Valkyrie":  ("valkyrie", 1054117906293719070),
    "Kunoichi":  ("kunoichi", 1054117767546159156),
    "Ninja":     ("ninja", 1054117856452816947),
    "Wizard":    ("wizard", 1261228964672962650),
    "Witch":     ("witch", 1261229011711950919),
    "Dark Knight": ("darkknight", 1054117762022244453),
    "Striker":   ("striker", 1054117903668105236),
    "Mystic":    ("mystic", 1054117855592984616),
    "Lahn":      ("lahn", 1223161513100185640),
    "Archer":    ("archer", 1054117757442068480),
    "Shai":      ("shai", 1054117861246906418),
    "Guardian":  ("guardian", 1054117807119417407),
    "Hashashin": ("hashashin", 1054117808184758413),
    "Nova":      ("nova", 1152014920947339264),
    "Sage":      ("sage", 1054117860085084230),
    "Corsair":   ("corsair", 859895710463295538),
    "Drakania":  ("drakania", 1054117763855159357),
    "Woosa":     ("woosa", 1261234794822631444),
    "Maegu":     ("maegu", 1223161515092475985),
    "Scholar":   ("scholar", 1210497845048774677),
    "Dosa":      ("dosa", 1254801633045385289),
    "Deadeye":   ("deadeye", 1321175340592267328),
}

MAX_OPTIONS   = 25
DEFAULT_COLOR = discord.Color.gold()

# ─────────── DATA ───────────
@dataclass
class Party:
    template: Literal["Doluns", "Boss Blitz", "Dungeon"]
    size: int
    owner_id: int
    members: Dict[int, str] = field(default_factory=dict)
    need_class: Optional[str] = None
    message_id: Optional[int] = None
    thread_id: Optional[int] = None            # ← new

    def add_member(self, uid: int, cls: str) -> bool:
        if uid in self.members or len(self.members) >= self.size:
            return False
        self.members[uid] = cls
        return True

    @property
    def is_full(self) -> bool:
        return len(self.members) >= self.size

# ─────────── BOT ───────────
class PartyFinder(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.parties: Dict[int, Party] = {}

    async def setup_hook(self):
        if GUILD_ID_LIST:
            g = discord.Object(id=GUILD_ID_LIST[0])
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        else:
            await self.tree.sync()

    async def get_msg(self, mid: int) -> discord.Message:
        for g in self.guilds:
            for ch in g.text_channels:
                try:
                    return await ch.fetch_message(mid)
                except (discord.NotFound, discord.Forbidden):
                    continue
        raise discord.NotFound("Message", mid)

    def party_embed(self, p: Party) -> discord.Embed:
        roster = "\n".join(f"<@{u}> — {c}" for u, c in p.members.items()) or "*No one yet*"
        extra  = f"Needed class to start: **{p.need_class}**\n" if p.need_class else ""
        return discord.Embed(
            title=f"{p.template} Party",
            description=f"{extra}**Size:** {len(p.members)}/{p.size}\n\n{roster}",
            color=DEFAULT_COLOR,
        )

bot = PartyFinder()

# ────────── HELPERS ──────────
def lookup_role(guild: discord.Guild, rid: int, name: str) -> Optional[discord.Role]:
    return guild.get_role(rid) if rid else discord.utils.find(lambda r: r.name.lower()==name.lower(), guild.roles)

TEMPLATE_ROLES = {
    "Doluns":     (DOLUNS_ROLE_ID,  DOLUNS_ROLE_NAME),
    "Boss Blitz": (BOSS_ROLE_ID,    BOSS_ROLE_NAME),
    "Dungeon":    (DUNGEON_ROLE_ID, DUNGEON_ROLE_NAME),
}

def emoji_for(cls: str) -> Optional[PartialEmoji]:
    if cls in CLASS_EMOJIS:
        n, eid = CLASS_EMOJIS[cls]
        return PartialEmoji(name=n, id=eid)
    return None

# ────────── COMMANDS ──────────
@bot.tree.command(name="party_create", description="Create a party")
@app_commands.choices(template=[app_commands.Choice(name=t, value=t) for t in ("Doluns","Boss Blitz","Dungeon")])
@app_commands.describe(size="Party size 1-20")
async def party_create(
    interaction: discord.Interaction,
    template: app_commands.Choice[str],
    size: app_commands.Range[int,1,20],
):
    party = Party(template.value, size, interaction.user.id)
    party.add_member(interaction.user.id, "TBD")

    view = SignUpView(bot, party)
    await interaction.response.send_message(embed=bot.party_embed(party), view=view)
    sent = await interaction.original_response()
    party.message_id = sent.id
    bot.parties[sent.id] = party

    rid,rname = TEMPLATE_ROLES[template.value]
    if (role := lookup_role(interaction.guild, rid, rname)):
        await sent.channel.send(f"{role.mention}  **{template.value}** party created!",
                                allowed_mentions=discord.AllowedMentions(roles=True))

# ──────────  UI ──────────
class CancelButton(discord.ui.Button):
    def __init__(self, v:"SignUpView"):
        super().__init__(label="Cancel Party",style=discord.ButtonStyle.danger)
        self.v=v
    async def callback(self,interaction:discord.Interaction):
        if interaction.user.id!=self.v.party.owner_id:
            return await interaction.response.send_message("Only creator.",ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await self.v.end_party()
        await interaction.followup.send("Party cancelled.",ephemeral=True)

class SignUpView(discord.ui.View):
    def __init__(self, bot:PartyFinder, party:Party):
        super().__init__(timeout=None)
        self.bot,self.party=bot,party
        self.add_item(CreatorClassSelect(self))
        if party.template=="Doluns":
            self.add_item(NeedClassSelect(self))
        for i in range(0,len(CLASS_LIST),MAX_OPTIONS):
            self.add_item(ClassSelect(self,CLASS_LIST[i:i+MAX_OPTIONS],f"Join class ({i//MAX_OPTIONS+1})"))
        self.add_item(CancelButton(self))

    # central finalize routine
    async def finalize(self, interaction:discord.Interaction):
        base = interaction.channel if not isinstance(interaction.channel, discord.Thread) else interaction.channel.parent
        mentions=" ".join(f"<@{u}>" for u in self.party.members)
        ready_msg = await base.send(f"{self.party.template} party is ready! {mentions}")
        try:
            thread = await base.create_thread(name=f"{self.party.template} party", message=ready_msg)
            self.party.thread_id = thread.id                # ← store thread id
            await thread.send("Coordinate here!")
        except discord.HTTPException as e:
            await base.send(f"⚠️ Could not create thread: {e}")
        for child in self.children:
            if isinstance(child,discord.ui.Select):
                child.disabled=True
        await (await base.fetch_message(self.party.message_id)).edit(view=self)

    async def end_party(self):
        # delete the original embed
        try:
            await (await self.bot.get_msg(self.party.message_id)).delete()
        except discord.NotFound:
            pass
        # delete or archive the thread if it exists
        if self.party.thread_id:
            try:
                thread = await self.bot.fetch_channel(self.party.thread_id)
                if isinstance(thread, discord.Thread):
                    await thread.delete()
            except discord.Forbidden:
                try:
                    await thread.edit(archived=True, locked=True)
                except Exception:
                    pass
            except discord.HTTPException:
                pass
        self.bot.parties.pop(self.party.message_id,None)

class CreatorClassSelect(discord.ui.Select):
    def __init__(self, v:SignUpView):
        opts=[discord.SelectOption(label=c,value=c,emoji=emoji_for(c)) for c in CLASS_LIST]
        super().__init__(placeholder="Pick your class (creator)",options=opts[:MAX_OPTIONS],min_values=1,max_values=1)
        self.v=v
    async def callback(self,interaction:discord.Interaction):
        if interaction.user.id!=self.v.party.owner_id:
            return await interaction.response.send_message("Creator only.",ephemeral=True)
        self.v.party.members[interaction.user.id]=self.values[0]
        await interaction.response.edit_message(embed=self.v.bot.party_embed(self.v.party),view=self.v)
        self.disabled=True
        await interaction.message.edit(view=self.v)
        if self.v.party.is_full or (self.v.party.need_class and self.v.party.need_class in self.v.party.members.values()):
            await self.v.finalize(interaction)

# ── replace the old NeedClassSelect class with this one ─────────────────────
class NeedClassSelect(discord.ui.Select):
    """Needed-class selector ­— Doluns only.

    Only two choices are allowed:
      • Shai  (actual support class)
      • DPS   (generic slot for any damage class)
    """

    # optional emoji mapping for these two “classes”
    _EMOJI_OVERRIDES = {
        "Shai": emoji_for("Shai"),                 # uses normal Shai icon
        "DPS":  PartialEmoji(name="⚔️")            # unicode sword
    }

    def __init__(self, v: SignUpView):
        opts = [
            discord.SelectOption(
                label=cls,
                value=cls,
                emoji=self._EMOJI_OVERRIDES.get(cls)
            )
            for cls in ("Shai", "DPS")
        ]
        super().__init__(
            placeholder="Needed role (Doluns)",
            options=opts,
            min_values=1,
            max_values=1,
        )
        self.v = v

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.v.party.owner_id:
            return await interaction.response.send_message(
                "Only the creator sets the needed role.", ephemeral=True
            )

        self.v.party.need_class = self.values[0]
        await interaction.response.edit_message(
            embed=self.v.bot.party_embed(self.v.party),
            view=self.v,
        )
        self.disabled = True
        await interaction.message.edit(view=self.v)


class ClassSelect(discord.ui.Select):
    def __init__(self,v:SignUpView,classes:List[str],placeholder:str):
        opts=[discord.SelectOption(label=c,value=c,emoji=emoji_for(c)) for c in classes]
        super().__init__(placeholder=placeholder,options=opts,min_values=1,max_values=1)
        self.v=v
    async def callback(self,interaction:discord.Interaction):
        if not self.v.party.add_member(interaction.user.id,self.values[0]):
            return await interaction.response.send_message("Party full or already joined.",ephemeral=True)
        await interaction.response.edit_message(embed=self.v.bot.party_embed(self.v.party),view=self.v)
        if self.v.party.is_full or (self.v.party.need_class and self.v.party.need_class in self.v.party.members.values()):
            await self.v.finalize(interaction)

# ────────── RUN ──────────
if not TOKEN:
    raise SystemExit("DISCORD_BOT_TOKEN env var not set")
bot.run(TOKEN)
