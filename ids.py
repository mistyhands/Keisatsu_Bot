import discord


class Channels():
    """Named Discord channels to post to.
    """
    TESTING = 929365821908738080
    REDDIT_POSTS = 939616386962030592
    BOT_DEBUG = 939571508467073044
    MISTYHANDS = 240903336717582337
    BANS = 939598756523933777
    MOD_ONLY = 939615965140893766
    SUNBOARD = 940907916960075858


class Roles():
    MODERATOR = 939571086562050119

    TEAL_LIGHT = 940028543730065419
    TEAL_DARK = 940028657198592100
    GREEN_LIGHT = 940028689545044069
    GREEN_DARK = 940028795556094002
    BLURPLE = 940035562478391296
    BLUE_GRAY = 940035694942887976
    BLUE_LIGHT = 940028846768521237
    BLUE_DARK = 940032765091536896
    PURPLE_LIGHT = 940028880457203742
    PURPLE_DARK = 940029042059534406
    HOT_PINK_LIGHT = 940029078373822535
    HOT_PINK_DARK = 940029124150431794
    YELLOW_LIGHT = 940029181528506420
    YELLOW_DARK = 940029213455548466
    ORANGE_LIGHT = 940029248628986006
    ORANGE_DARK = 940029355525033986
    ORANGERED_LIGHT = 940029390581035099
    ORANGERED_DARK = 940029424219324446
    PASTEL_RED = 940029756823453727
    PASTEL_ORANGE = 940030201952366619
    PASTEL_YELLOW = 940030356764098662
    PASTEL_GREEN = 940030421314457600
    PASTEL_MINT = 940031614656872488
    PASTEL_PURPLE = 940031786061279233
    PASTEL_PINK = 940031894819569665
    SLATE = 940029476044144650

    HE_HIM = 940037330109100103
    THEY_THEM = 940037422807388160
    SHE_HER = 940037443007168554
    OTHER_PRONOUNS = 940037741327036478
    MY_BALS = 940037702131257425

    LGBT = 940059062970753044
    FURRY = 940359885072244736
    PROGRAMMING = 940360260705714247
    FOOD = 940365875486269480
    ANIME = 940383310109093978
    ART = 940385839152783370
    GAMES = 943487991400235078

    EVENTS_GAME = 943492576441425921


emoji_to_role = {
    # COLOURS
    discord.PartialEmoji(
        name="⚛️"
    ): Roles.TEAL_LIGHT,
    discord.PartialEmoji(
        name="🆔"
    ): Roles.TEAL_DARK,
    discord.PartialEmoji(
        name="☮️"
    ): Roles.GREEN_LIGHT,
    discord.PartialEmoji(
        name="♓"
    ): Roles.GREEN_DARK,
    discord.PartialEmoji(
        name="♒"
    ): Roles.BLURPLE,
    discord.PartialEmoji(
        name="♑"
    ): Roles.BLUE_GRAY,
    discord.PartialEmoji(
        name="♐"
    ): Roles.BLUE_LIGHT,
    discord.PartialEmoji(
        name="♏"
    ): Roles.BLUE_DARK,
    discord.PartialEmoji(
        name="♎"
    ): Roles.PURPLE_LIGHT,
    discord.PartialEmoji(
        name="♍"
    ): Roles.PURPLE_DARK,
    discord.PartialEmoji(
        name="♌"
    ): Roles.HOT_PINK_LIGHT,
    discord.PartialEmoji(
        name="♋"
    ): Roles.HOT_PINK_DARK,
    discord.PartialEmoji(
        name="♊"
    ): Roles.YELLOW_LIGHT,
    discord.PartialEmoji(
        name="♉"
    ): Roles.YELLOW_DARK,
    discord.PartialEmoji(
        name="♈"
    ): Roles.ORANGE_LIGHT,
    discord.PartialEmoji(
        name="⛎"
    ): Roles.ORANGE_DARK,
    discord.PartialEmoji(
        name="🛐"
    ): Roles.ORANGERED_LIGHT,
    discord.PartialEmoji(
        name="☦️"
    ): Roles.ORANGERED_DARK,
    discord.PartialEmoji(
        name="☯️"
    ): Roles.SLATE,
    discord.PartialEmoji(
        name="🕎"
    ): Roles.PASTEL_RED,
    discord.PartialEmoji(
        name="🔯"
    ): Roles.PASTEL_ORANGE,
    discord.PartialEmoji(
        name="✡️"
    ): Roles.PASTEL_YELLOW,
    discord.PartialEmoji(
        name="☸️"
    ): Roles.PASTEL_GREEN,
    discord.PartialEmoji(
        name="🕉"
    ): Roles.PASTEL_MINT,
    discord.PartialEmoji(
        name="☪️"
    ): Roles.PASTEL_PURPLE,
    discord.PartialEmoji(
        name="✝️"
    ): Roles.PASTEL_PINK,

    # PRONOUNS
    discord.PartialEmoji(
        name="🟥"
    ): Roles.HE_HIM,
    discord.PartialEmoji(
        name="🟧"
    ): Roles.THEY_THEM,
    discord.PartialEmoji(
        name="🟨"
    ): Roles.SHE_HER,
    discord.PartialEmoji(
        name="🟩"
    ): Roles.OTHER_PRONOUNS,
    discord.PartialEmoji(
        name="🟦"
    ): Roles.MY_BALS,

    # CHANNELS
    discord.PartialEmoji(
        name="1️⃣"
    ): Roles.LGBT,
    discord.PartialEmoji(
        name="2️⃣"
    ): Roles.FURRY,
    discord.PartialEmoji(
        name="3️⃣"
    ): Roles.PROGRAMMING,
    discord.PartialEmoji(
        name="4️⃣"
    ): Roles.FOOD,
    discord.PartialEmoji(
        name="5️⃣"
    ): Roles.ANIME,
    discord.PartialEmoji(
        name="6️⃣"
    ): Roles.ART,
    discord.PartialEmoji(
        name="7️⃣"
    ): Roles.GAMES,

    # EVENTS
    discord.PartialEmoji(
        name="🎮"
    ): Roles.EVENTS_GAME,
}
