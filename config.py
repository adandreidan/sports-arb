# config.py — Central configuration for the sports arbitrage scanner

SPORT = "NBA"
PROP_TYPE = "points"

BANKROLL = 500

LOWER_LIMIT = 0.002
UPPER_LIMIT = 0.07

LOG_FILE = "arb_log.csv"

# Game-specific URLs (PHI 76ers @ NY Knicks)
DK_GAME_URL = "https://sportsbook.draftkings.com/event/phi-76ers-%2540-ny-knicks/34103684"
FD_GAME_URL = "https://on.sportsbook.fanduel.ca/basketball/nba/philadelphia-76ers-@-new-york-knicks-35564245"

# Legacy NBA lobby URLs (kept for reference)
DRAFTKINGS_NBA_URL = "https://sportsbook.draftkings.com/leagues/basketball/nba"
FANDUEL_NBA_URL = "https://sportsbook.fanduel.com/basketball/nba"

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1501469917373927506/lmPXTap1jtGlWj0uOlGwRdY4MIGxUHhzRoe-KkCon-JB-AxF-3Z9RGIPv15MRqwHwmfK"

SCAN_INTERVAL = 30

PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 10
