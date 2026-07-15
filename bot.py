import discord
from discord import app_commands
import logging
import os

from config import (
    BOT_TOKEN, GUILD_ID,
    COD_ROLE_ID, LIBRARY_PASS_ROLE_ID, LIBRARY_CHANNEL_ID,
    DICTIONARIES, LISAN_DB, QAMUS_DB,
    ENGLISH_DICTS,
    EJTAAL_DB, EJTAAL_IMAGE_BASE, EJTAAL_DEFAULT_DICTS,
    EMBED_COLOR, ENGLISH_EMBED_COLOR, SCAN_EMBED_COLOR, EMBED_LIMIT
)
from database import lookup_root, fuzzy_lookup, search_nearby_roots
from root_extractor import extract_root
from text_utils import normalize
from ejtaal_db import search_all, build_image_url

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
GUILD = discord.Object(id=GUILD_ID)

RED  = 0xC0392B
GREY = 0x2C3E50

# Footer branding — appears on every embed
POWERED_BY = "Powered by 𝐓𝐡𝐞𝐨𝐥𝐨𝐠𝐢𝐜𝐚𝐥 𝐃𝐢𝐬𝐜𝐨𝐮𝐫𝐬𝐞🎙"

# Flag labels for the scan summary embed
LANG_FLAGS = {
    'ur': '🇵🇰 Urdu',
    'en': '🇬🇧 English',
    'ar': '🇸🇦 Arabic',
    'id': '🇮🇩 Indonesian',
    'fr': '🇫🇷 French',
    'ms': '🇲🇾 Malay',
    'de': '🇩🇪 German',
}


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

def check_access(interaction: discord.Interaction) -> tuple[bool, str]:
    """
    Returns (allowed, reason).
    COD role       → allowed everywhere.
    Library Pass   → allowed only in LIBRARY_CHANNEL_ID.
    Neither role   → denied.
    """
    member = interaction.user
    role_ids = {r.id for r in getattr(member, 'roles', [])}

    has_cod = COD_ROLE_ID in role_ids
    has_library_pass = LIBRARY_PASS_ROLE_ID in role_ids

    if has_cod:
        return True, ""

    if has_library_pass:
        if interaction.channel_id == LIBRARY_CHANNEL_ID:
            return True, ""
        return False, (
            f"❌  **Library Pass** holders can only use this command "
            f"in <#{LIBRARY_CHANNEL_ID}>."
        )

    return False, (
        "❌  You need the **COD** role or **Library Pass** role to use this bot."
    )


async def deny(interaction: discord.Interaction, reason: str):
    await interaction.response.send_message(
        embed=discord.Embed(description=reason, color=RED),
        ephemeral=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def truncate(text: str, limit: int = EMBED_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + '\n\n*… [text truncated — see source for full entry]*'


_LTR = '\u200E'


def fix_bidi(text: str) -> str:
    """Prefix every line with an LTR mark — fixes Arabic/English BiDi in Discord."""
    return '\n'.join(_LTR + line for line in text.split('\n'))


def add_powered_by(existing: str) -> str:
    """Append POWERED_BY to an existing footer string."""
    if existing:
        return f"{existing}  |  {POWERED_BY}"
    return POWERED_BY


# ═══════════════════════════════════════════════════════════════════════════════
# EMBED BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def make_arabic_embed(dict_name: str, entry: dict, root: str, fuzzy: bool) -> discord.Embed:
    embed = discord.Embed(
        title=f"📖  {dict_name}",
        description=truncate(entry['entry_text']),
        color=EMBED_COLOR
    )
    parts = [f"Root: {root}"]
    if entry.get('page_num'):
        parts.append(f"p. {entry['page_num']}")
    if entry.get('title'):
        parts.append(entry['title'])
    if fuzzy:
        parts.append("(approximate match)")
    embed.set_footer(text=add_powered_by("  |  ".join(parts)))
    return embed


def make_english_embed(dict_name: str, entry: dict, root: str, fuzzy: bool) -> discord.Embed:
    embed = discord.Embed(
        title=f"📖  {dict_name}",
        description=fix_bidi(truncate(entry['entry_text'])),
        color=ENGLISH_EMBED_COLOR
    )
    parts = [f"Root: {root}"]
    if entry.get('page_num'):
        parts.append(f"p. {entry['page_num']}")
    if entry.get('title') and entry['title'] != root:
        parts.append(entry['title'])
    if fuzzy:
        parts.append("(approximate match)")
    embed.set_footer(text=add_powered_by("  |  ".join(parts)))
    return embed


# ═══════════════════════════════════════════════════════════════════════════════
# LOOKUP HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def lookup_single(db_path: str, root: str) -> tuple[dict | None, bool]:
    """Exact then fuzzy lookup in one DB. Returns (entry, is_fuzzy)."""
    if not os.path.exists(db_path):
        return None, False
    hits = lookup_root(db_path, root)
    if hits:
        return hits[0], False
    hits = fuzzy_lookup(db_path, root)
    if hits:
        return hits[0], True
    return None, False


def lookup_all(dicts: dict, root: str) -> tuple[dict, dict]:
    results, fuzzy = {}, {}
    for name, path in dicts.items():
        entry, is_fuzzy = lookup_single(path, root)
        if entry:
            results[name] = entry
            if is_fuzzy:
                fuzzy[name] = True
    return results, fuzzy


def no_root_embed(word: str) -> discord.Embed:
    return discord.Embed(
        title="⚠️  Could not extract root",
        description=(
            f"Unable to analyze **{word}** morphologically.\n\n"
            "• Try `/lughat-root` and enter the trilateral root directly.\n"
            "• Example: for **يُقاتِلُ** the root is **قتل**\n"
            "• Example: for **الكاتب** the root is **كتب**"
        ),
        color=RED
    )


def not_found_embed(root: str, db_paths: list[str],
                    title: str = "❌  No results found") -> discord.Embed:
    suggestions = []
    for p in db_paths:
        if os.path.exists(p):
            suggestions += search_nearby_roots(p, root)
    suggestions = list(dict.fromkeys(suggestions))[:6]
    desc = f"Root **{root}** was not found in the available dictionaries."
    if suggestions:
        desc += "\n\nNearby roots: " + "  |  ".join(f"**{s}**" for s in suggestions)
    return discord.Embed(title=title, description=desc, color=RED)


# ═══════════════════════════════════════════════════════════════════════════════
# EJTAAL SCAN — Discord UI
# ═══════════════════════════════════════════════════════════════════════════════

class ScanDictView(discord.ui.View):
    """
    Dropdown shown after /lughat-scan.
    User picks up to 3 dictionaries → bot sends those page images.
    Expires after 5 minutes.
    """

    def __init__(self, results: list[dict], root: str):
        super().__init__(timeout=300)
        self.results = results
        self.root = root

        options = [
            discord.SelectOption(
                label=r['name'][:100],
                value=r['code'],
                description=f"p. {r['page_num']}  •  {LANG_FLAGS.get(r['lang'], r['lang'].upper())}"
            )
            for r in results[:25]   # Discord max = 25 options
        ]

        select = discord.ui.Select(
            placeholder="Choose dictionaries to view (up to 3) …",
            min_values=1,
            max_values=min(3, len(options)),
            options=options
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        await interaction.response.defer()

        chosen = interaction.data['values']
        result_map = {r['code']: r for r in self.results}
        embeds = []

        for code in chosen:
            r = result_map[code]
            lang = LANG_FLAGS.get(r['lang'], r['lang'].upper())

            # Build the direct ejtaal.net image URL
            ejtaal_url = build_image_url(
                r['img_prefix'], r['page_num'], EJTAAL_IMAGE_BASE
            )

            # Route through wsrv.nl — free image proxy.
            # Discord CDN → wsrv.nl → ejtaal.net (bypasses ejtaal hotlink block
            # and KeritCloud's outbound restrictions in one step).
            bare_url = ejtaal_url.replace("https://", "").replace("http://", "")
            proxy_url = f"https://wsrv.nl/?url={bare_url}&referer=https://ejtaal.net/aa/&ua=Mozilla/5.0+(Windows+NT+10.0;+Win64;+x64)+AppleWebKit/537.36"

            embed = discord.Embed(
                title=f"📖  {r['name']}",
                description=f"Root **{self.root}**  •  {lang}",
                color=r['color']
            )
            embed.set_image(url=proxy_url)
            embed.set_footer(text=f"Page {r['page_num']}  •  {POWERED_BY}")
            embeds.append(embed)

        await interaction.followup.send(embeds=embeds)

    async def on_timeout(self):
        self.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

# ── /lisan — Lisan al-Arab only ───────────────────────────────────────────────

@tree.command(
    name="lisan",
    description="Search Lisan al-Arab (لسان العرب) — enter any Arabic word or root",
    guild=GUILD
)
@app_commands.describe(word="Arabic word or root — e.g. الله | يُقاتِلُ | قتل")
async def lisan(interaction: discord.Interaction, word: str):
    allowed, reason = check_access(interaction)
    if not allowed:
        return await deny(interaction, reason)

    await interaction.response.defer()
    word = word.strip()
    root = extract_root(word)

    if root is None:
        return await interaction.followup.send(embed=no_root_embed(word))

    entry, is_fuzzy = lookup_single(LISAN_DB, root)

    if not entry:
        return await interaction.followup.send(
            embed=not_found_embed(root, [LISAN_DB])
        )

    root_display = root if normalize(word) == root else f"{word}  →  {root}"
    embeds = [
        discord.Embed(
            title=f"🔍  {root_display}",
            description="Result from **Lisan al-Arab**",
            color=GREY
        ),
        make_arabic_embed("Lisan al-Arab (لسان العرب)", entry, root, is_fuzzy)
    ]
    await interaction.followup.send(embeds=embeds)


# ── /qamus — Qamus al-Muhit only ─────────────────────────────────────────────

@tree.command(
    name="qamus",
    description="Search Qamus al-Muhit (القاموس المحيط) — enter any Arabic word or root",
    guild=GUILD
)
@app_commands.describe(word="Arabic word or root — e.g. الله | يُقاتِلُ | قتل")
async def qamus(interaction: discord.Interaction, word: str):
    allowed, reason = check_access(interaction)
    if not allowed:
        return await deny(interaction, reason)

    await interaction.response.defer()
    word = word.strip()
    root = extract_root(word)

    if root is None:
        return await interaction.followup.send(embed=no_root_embed(word))

    entry, is_fuzzy = lookup_single(QAMUS_DB, root)

    if not entry:
        return await interaction.followup.send(
            embed=not_found_embed(root, [QAMUS_DB])
        )

    root_display = root if normalize(word) == root else f"{word}  →  {root}"
    embeds = [
        discord.Embed(
            title=f"🔍  {root_display}",
            description="Result from **Qamus al-Muhit**",
            color=GREY
        ),
        make_arabic_embed("Qamus al-Muhit (القاموس المحيط)", entry, root, is_fuzzy)
    ]
    await interaction.followup.send(embeds=embeds)


# ── /lughat — all Arabic dicts ────────────────────────────────────────────────

@tree.command(
    name="lughat",
    description="Search all Arabic dictionaries (Lisan al-Arab + Qamus al-Muhit)",
    guild=GUILD
)
@app_commands.describe(word="Arabic word or root — e.g. الله | يُقاتِلُ | قتل")
async def lughat(interaction: discord.Interaction, word: str):
    allowed, reason = check_access(interaction)
    if not allowed:
        return await deny(interaction, reason)

    await interaction.response.defer()
    word = word.strip()
    root = extract_root(word)

    if root is None:
        return await interaction.followup.send(embed=no_root_embed(word))

    results, fuzzy = lookup_all(DICTIONARIES, root)

    if not results:
        return await interaction.followup.send(
            embed=not_found_embed(root, list(DICTIONARIES.values()))
        )

    root_display = root if normalize(word) == root else f"{word}  →  {root}"
    embeds = [discord.Embed(
        title=f"🔍  {root_display}",
        description=f"Found in **{len(results)}** Arabic {'dictionary' if len(results) == 1 else 'dictionaries'}",
        color=GREY
    )] + [
        make_arabic_embed(name, entry, root, name in fuzzy)
        for name, entry in results.items()
    ]
    await interaction.followup.send(embeds=embeds[:10])


# ── /lughat-root — direct root search all Arabic dicts ───────────────────────

@tree.command(
    name="lughat-root",
    description="Search all Arabic dictionaries by root directly (skip morphology)",
    guild=GUILD
)
@app_commands.describe(root="Trilateral root — e.g. قتل | علم | كتب")
async def lughat_root(interaction: discord.Interaction, root: str):
    allowed, reason = check_access(interaction)
    if not allowed:
        return await deny(interaction, reason)

    await interaction.response.defer()
    root = root.strip()
    results, fuzzy = lookup_all(DICTIONARIES, root)

    if not results:
        return await interaction.followup.send(
            embed=not_found_embed(root, list(DICTIONARIES.values()), "❌  Root not found")
        )

    embeds = [discord.Embed(
        title=f"📚  Root: {root}",
        description=f"Found in **{len(results)}** Arabic {'dictionary' if len(results) == 1 else 'dictionaries'}",
        color=GREY
    )] + [
        make_arabic_embed(name, entry, root, name in fuzzy)
        for name, entry in results.items()
    ]
    await interaction.followup.send(embeds=embeds[:10])


# ── /lane — Lane's Lexicon (English) ─────────────────────────────────────────

@tree.command(
    name="lane",
    description="Search Lane's Lexicon — English definitions for Arabic roots",
    guild=GUILD
)
@app_commands.describe(word="Arabic word or root — e.g. كتب | يُقاتِلُ | الله")
async def lane(interaction: discord.Interaction, word: str):
    allowed, reason = check_access(interaction)
    if not allowed:
        return await deny(interaction, reason)

    await interaction.response.defer()
    word = word.strip()
    root = extract_root(word)

    if root is None:
        return await interaction.followup.send(embed=no_root_embed(word))

    results, fuzzy = lookup_all(ENGLISH_DICTS, root)

    if not results:
        return await interaction.followup.send(
            embed=not_found_embed(root, list(ENGLISH_DICTS.values()),
                                  "❌  Not found in Lane's Lexicon")
        )

    root_display = root if normalize(word) == root else f"{word}  →  {root}"
    embeds = [discord.Embed(
        title=f"🔍  {root_display}",
        description="Result from **Lane's Lexicon**",
        color=GREY
    )] + [
        make_english_embed(name, entry, root, name in fuzzy)
        for name, entry in results.items()
    ]
    await interaction.followup.send(embeds=embeds[:10])


# ── /lughat-scan — ejtaal page images ────────────────────────────────────────

SCAN_LANG_CHOICES = [
    app_commands.Choice(name="Urdu  (Al-Munjid, Qaamoos Waheed, Mufradat…)", value="ur"),
    app_commands.Choice(name="English  (Hans Wehr, Lane's Lexicon, Steingass…)", value="en"),
    app_commands.Choice(name="Arabic  (Lisan al-Arab, al-Munjid Arabic…)", value="ar"),
    app_commands.Choice(name="All dictionaries", value="all"),
]


@tree.command(
    name="lughat-scan",
    description="Get scanned page images from 22+ dictionaries (Urdu, English, Arabic)",
    guild=GUILD
)
@app_commands.describe(
    word="Arabic word or root — e.g.  كتب  |  يُقاتِلُ  |  الله",
    lang="Filter by language — default shows your top picks from config"
)
@app_commands.choices(lang=SCAN_LANG_CHOICES)
async def lughat_scan(
    interaction: discord.Interaction,
    word: str,
    lang: app_commands.Choice[str] | None = None
):
    allowed, reason = check_access(interaction)
    if not allowed:
        return await deny(interaction, reason)

    await interaction.response.defer()
    word = word.strip()

    # ── Step 1: extract root ──────────────────────────────────────────────────
    root = extract_root(word)
    if root is None:
        return await interaction.followup.send(embed=no_root_embed(word))

    # ── Step 2: check DB ─────────────────────────────────────────────────────
    if not os.path.exists(EJTAAL_DB):
        return await interaction.followup.send(embed=discord.Embed(
            title="⚠️  Ejtaal index not found",
            description=(
                "The ejtaal index database has not been set up yet.\n\n"
                "**Admin:** upload `ejtaal_index.db` to the data folder."
            ),
            color=RED
        ))

    # ── Step 3: search index ──────────────────────────────────────────────────
    lang_val = lang.value if lang else None
    filter_lang = None if (lang_val == 'all' or lang_val is None) else lang_val
    all_results = search_all(EJTAAL_DB, root, filter_lang)

    # If no language filter chosen → reorder so default dicts come first
    if lang_val is None and EJTAAL_DEFAULT_DICTS:
        pinned = {r['code']: r for r in all_results if r['code'] in EJTAAL_DEFAULT_DICTS}
        rest = [r for r in all_results if r['code'] not in EJTAAL_DEFAULT_DICTS]
        ordered = [pinned[c] for c in EJTAAL_DEFAULT_DICTS if c in pinned]
        all_results = ordered + rest

    if not all_results:
        lang_note = f" in **{lang.name}**" if lang else ""
        return await interaction.followup.send(embed=discord.Embed(
            title="❌  No results found",
            description=(
                f"Root **{root}** was not found in the ejtaal index{lang_note}.\n\n"
                "• Try a different language filter\n"
                "• Verify the root with `/lughat-root`"
            ),
            color=RED
        ))

    # ── Step 4: summary embed + dropdown ─────────────────────────────────────
    root_display = root if normalize(word) == root else f"{word}  →  {root}"

    # Group by language for the summary field
    by_lang: dict[str, list[str]] = {}
    for r in all_results:
        by_lang.setdefault(r['lang'], []).append(r['name'])

    lang_lines = '\n'.join(
        f"{LANG_FLAGS.get(lg, lg.upper())}: "
        + ', '.join(names[:3])
        + (' …' if len(names) > 3 else '')
        for lg, names in by_lang.items()
    )

    summary = discord.Embed(
        title=f"🔍  {root_display}",
        description=(
            f"Found in **{len(all_results)}** ejtaal "
            f"{'dictionary' if len(all_results) == 1 else 'dictionaries'}\n\n"
            f"{lang_lines}"
        ),
        color=SCAN_EMBED_COLOR
    )
    summary.set_footer(text=f"Select dictionaries below to view their scanned pages ↓  |  {POWERED_BY}")

    view = ScanDictView(all_results, root)
    await interaction.followup.send(embed=summary, view=view)


# ── /lughat-help ──────────────────────────────────────────────────────────────

@tree.command(
    name="lughat-help",
    description="How to use the Arabic Dictionary Bot",
    guild=GUILD
)
async def lughat_help(interaction: discord.Interaction):
    allowed, reason = check_access(interaction)
    if not allowed:
        return await deny(interaction, reason)

    embed = discord.Embed(
        title="📚  Arabic Dictionary Bot — Commands",
        description="All commands auto-extract the Arabic root from any word you type.",
        color=EMBED_COLOR
    )

    # ── Arabic (text) ─────────────────────────────────────────────────────────
    embed.add_field(
        name="🟢  Arabic Dictionaries  (text)",
        value="─────────────────────────────────",
        inline=False
    )
    embed.add_field(
        name="/lisan [word or root]",
        value=(
            "Search **Lisan al-Arab** (لسان العرب) — classical Arabic text.\n"
            "Example: `/lisan قتل`  |  `/lisan يُقاتِلُ`"
        ),
        inline=False
    )
    embed.add_field(
        name="/qamus [word or root]",
        value=(
            "Search **Qamus al-Muhit** (القاموس المحيط) — classical Arabic text.\n"
            "Example: `/qamus علم`  |  `/qamus الكاتب`"
        ),
        inline=False
    )
    embed.add_field(
        name="/lughat [word or root]",
        value=(
            "Search **all Arabic dictionaries** at once (Lisan + Qamus).\n"
            "Example: `/lughat الله`"
        ),
        inline=False
    )
    embed.add_field(
        name="/lughat-root [root]",
        value=(
            "Search all Arabic dicts by **root directly** — skips morphology.\n"
            "Use this when auto-extraction fails.\n"
            "Example: `/lughat-root قتل`  |  `/lughat-root كتب`"
        ),
        inline=False
    )

    # ── English (text) ────────────────────────────────────────────────────────
    embed.add_field(
        name="🔵  English Dictionaries  (text)",
        value="─────────────────────────────────",
        inline=False
    )
    embed.add_field(
        name="/lane [word or root]",
        value=(
            "Search **Lane's Lexicon** — comprehensive English definitions.\n"
            "Example: `/lane كتب`  →  full English entry for root **كتب**"
        ),
        inline=False
    )

    # ── ejtaal scan (images) ──────────────────────────────────────────────────
    embed.add_field(
        name="🟣  ejtaal Scanned Pages  (images)",
        value="─────────────────────────────────",
        inline=False
    )
    embed.add_field(
        name="/lughat-scan [word or root]  [lang]",
        value=(
            "Returns **scanned page images** from 22+ dictionaries.\n"
            "After the command, a **dropdown menu** appears — pick up to **3 dictionaries** to view.\n\n"
            "**Language filter options:**\n"
            "• _(no filter)_ → shows your default picks (Al-Munjid, Qaamoos Waheed, Hans Wehr…)\n"
            "• `Urdu` → Al-Munjid, Qaamoos ul Waheed, Mufradat al-Quran, Lughat ul Quran…\n"
            "• `English` → Hans Wehr, Lane's Lexicon, Steingass, Hava, Brill…\n"
            "• `Arabic` → Lisan al-Arab, al-Munjid Arabic, Asaas al-Balaghah…\n"
            "• `All` → every indexed dictionary\n\n"
            "Example: `/lughat-scan كتب`  |  `/lughat-scan يُقاتِلُ lang:Urdu`"
        ),
        inline=False
    )

    # ── Tips ──────────────────────────────────────────────────────────────────
    embed.add_field(
        name="💡  Tips",
        value=(
            "• All commands accept full words, inflected forms, or bare roots.\n"
            "• If a word fails, use `/lughat-root` to enter the root directly.\n"
            "• `/lughat-scan` images come from ejtaal.net — same pages you see on the website.\n"
            "• `/lane` returns searchable English text; `/lughat-scan` returns the actual book scan."
        ),
        inline=False
    )

    # ── Sources ───────────────────────────────────────────────────────────────
    ar_sources = "\n".join(f"• {n}" for n in DICTIONARIES) or "_(none)_"
    en_sources = "\n".join(f"• {n}" for n in ENGLISH_DICTS) or "_(none)_"
    scan_sources = "22+ dictionaries\n(Urdu, English, Arabic, French, Indonesian…)"

    embed.add_field(name="Arabic sources",  value=ar_sources,   inline=True)
    embed.add_field(name="English sources", value=en_sources,   inline=True)
    embed.add_field(name="Scan sources",    value=scan_sources, inline=True)

    embed.set_footer(text=POWERED_BY)
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

@client.event
async def on_ready():
    await tree.sync(guild=GUILD)
    logger.info(f"Ready: {client.user} | Guild: {GUILD_ID}")
    logger.info(f"Arabic dicts : {list(DICTIONARIES.keys())}")
    logger.info(f"English dicts: {list(ENGLISH_DICTS.keys())}")
    logger.info(f"Ejtaal DB    : {EJTAAL_DB}  (exists={os.path.exists(EJTAAL_DB)})")
    logger.info(f"COD role: {COD_ROLE_ID} | Library Pass: {LIBRARY_PASS_ROLE_ID} | Channel: {LIBRARY_CHANNEL_ID}")


client.run(BOT_TOKEN)