"""
Scraping configuration — league mappings, source URLs, rate limits.
Maps each in-scope league to identifiers used by every data source.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# League registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LeagueMapping:
    """Unified league identifier with per-source keys."""
    code: str
    name: str
    country: str

    # FBref  (comp id + url slug)
    fbref_id: Optional[str] = None
    fbref_slug: Optional[str] = None

    # Football-Data.co.uk (country code + division id)
    fd_country: Optional[str] = None
    fd_division: Optional[str] = None

    # Understat (league slug — only top 6 leagues supported)
    understat_slug: Optional[str] = None

    # Transfermarkt (competition path segment)
    tm_slug: Optional[str] = None
    tm_id: Optional[str] = None

    # ClubElo (country code used in the API)
    clubelo_country: Optional[str] = None

    # The Odds API (sport key)
    odds_api_key: Optional[str] = None

    # SofaScore (tournament id)
    sofascore_id: Optional[int] = None

    # API-Football (league id)
    api_football_id: Optional[int] = None


LEAGUES: dict[str, LeagueMapping] = {
    # ── England ─────────────────────────────────────────────
    "EPL": LeagueMapping(
        code="EPL", name="Premier League", country="England",
        fbref_id="9", fbref_slug="Premier-League",
        fd_country="E0", fd_division="E0",
        understat_slug="EPL",
        tm_slug="premier-league", tm_id="GB1",
        clubelo_country="ENG",
        odds_api_key="soccer_epl",
        sofascore_id=17, api_football_id=39,
    ),
    # ── Spain ───────────────────────────────────────────────
    "LALIGA": LeagueMapping(
        code="LALIGA", name="La Liga", country="Spain",
        fbref_id="12", fbref_slug="La-Liga",
        fd_country="SP1", fd_division="SP1",
        understat_slug="La_liga",
        tm_slug="laliga", tm_id="ES1",
        clubelo_country="ESP",
        odds_api_key="soccer_spain_la_liga",
        sofascore_id=8, api_football_id=140,
    ),
    # ── Germany ─────────────────────────────────────────────
    "BUNDESLIGA": LeagueMapping(
        code="BUNDESLIGA", name="Bundesliga", country="Germany",
        fbref_id="20", fbref_slug="Bundesliga",
        fd_country="D1", fd_division="D1",
        understat_slug="Bundesliga",
        tm_slug="1-bundesliga", tm_id="L1",
        clubelo_country="GER",
        odds_api_key="soccer_germany_bundesliga",
        sofascore_id=35, api_football_id=78,
    ),
    # ── Italy ───────────────────────────────────────────────
    "SERIEA": LeagueMapping(
        code="SERIEA", name="Serie A", country="Italy",
        fbref_id="11", fbref_slug="Serie-A",
        fd_country="I1", fd_division="I1",
        understat_slug="Serie_A",
        tm_slug="serie-a", tm_id="IT1",
        clubelo_country="ITA",
        odds_api_key="soccer_italy_serie_a",
        sofascore_id=23, api_football_id=135,
    ),
    # ── France ──────────────────────────────────────────────
    "LIGUE1": LeagueMapping(
        code="LIGUE1", name="Ligue 1", country="France",
        fbref_id="13", fbref_slug="Ligue-1",
        fd_country="F1", fd_division="F1",
        understat_slug="Ligue_1",
        tm_slug="ligue-1", tm_id="FR1",
        clubelo_country="FRA",
        odds_api_key="soccer_france_ligue_one",
        sofascore_id=34, api_football_id=61,
    ),
    # ── Netherlands ─────────────────────────────────────────
    "EREDIVISIE": LeagueMapping(
        code="EREDIVISIE", name="Eredivisie", country="Netherlands",
        fbref_id="23", fbref_slug="Eredivisie",
        fd_country="N1", fd_division="N1",
        tm_slug="eredivisie", tm_id="NL1",
        clubelo_country="NED",
        odds_api_key="soccer_netherlands_eredivisie",
        sofascore_id=37, api_football_id=88,
    ),
    # ── Portugal ────────────────────────────────────────────
    "PRIMEIRALIGA": LeagueMapping(
        code="PRIMEIRALIGA", name="Primeira Liga", country="Portugal",
        fbref_id="32", fbref_slug="Primeira-Liga",
        fd_country="P1", fd_division="P1",
        tm_slug="liga-portugal", tm_id="PO1",
        clubelo_country="POR",
        odds_api_key="soccer_portugal_primeira_liga",
        sofascore_id=238, api_football_id=94,
    ),
    # ── Turkey ──────────────────────────────────────────────
    "SUPERLIG": LeagueMapping(
        code="SUPERLIG", name="Süper Lig", country="Turkey",
        fbref_id="26", fbref_slug="Super-Lig",
        fd_country="T1", fd_division="T1",
        tm_slug="super-lig", tm_id="TR1",
        clubelo_country="TUR",
        odds_api_key="soccer_turkey_super_league",
        sofascore_id=52, api_football_id=203,
    ),
    # ── Belgium ─────────────────────────────────────────────
    "JUPILERPROLEAGUE": LeagueMapping(
        code="JUPILERPROLEAGUE", name="Jupiler Pro League", country="Belgium",
        fbref_id="37", fbref_slug="Belgian-Pro-League",
        fd_country="B1", fd_division="B1",
        tm_slug="jupiler-pro-league", tm_id="BE1",
        clubelo_country="BEL",
        odds_api_key="soccer_belgium_first_div",
        sofascore_id=38, api_football_id=144,
    ),
    # ── Scotland ────────────────────────────────────────────
    "SCOTTISHPREM": LeagueMapping(
        code="SCOTTISHPREM", name="Scottish Premiership", country="Scotland",
        fbref_id="40", fbref_slug="Scottish-Premiership",
        fd_country="SC0", fd_division="SC0",
        tm_slug="scottish-premiership", tm_id="SC1",
        clubelo_country="SCO",
        odds_api_key="soccer_spl",
        sofascore_id=36, api_football_id=179,
    ),
    # ── Morocco ─────────────────────────────────────────────
    "BOTOLAPRO": LeagueMapping(
        code="BOTOLAPRO", name="Botola Pro", country="Morocco",
        fbref_id="115", fbref_slug="Botola-Pro",
        tm_slug="botola-pro", tm_id="MAR1",
        odds_api_key="soccer_morocco_botola_pro",
        sofascore_id=937, api_football_id=200,
    ),
    # ── UEFA Champions League ───────────────────────────────
    "UCL": LeagueMapping(
        code="UCL", name="UEFA Champions League", country="Europe",
        fbref_id="8", fbref_slug="Champions-League",
        tm_slug="uefa-champions-league", tm_id="CL",
        odds_api_key="soccer_uefa_champs_league",
        sofascore_id=7, api_football_id=2,
    ),
    # ── UEFA Europa League ──────────────────────────────────
    "UEL": LeagueMapping(
        code="UEL", name="UEFA Europa League", country="Europe",
        fbref_id="19", fbref_slug="Europa-League",
        tm_slug="uefa-europa-league", tm_id="EL",
        odds_api_key="soccer_uefa_europa_league",
        sofascore_id=679, api_football_id=3,
    ),
    # ── International tournaments ───────────────────────────
    "WORLDCUP": LeagueMapping(
        code="WORLDCUP", name="FIFA World Cup", country="International",
        fbref_id="1", fbref_slug="World-Cup",
        tm_slug="weltmeisterschaft", tm_id="WM",
        odds_api_key="soccer_fifa_world_cup",
        sofascore_id=16, api_football_id=1,
    ),
    "EURO": LeagueMapping(
        code="EURO", name="UEFA European Championship", country="International",
        fbref_id="676", fbref_slug="European-Championship",
        tm_slug="europameisterschaft", tm_id="EM",
        odds_api_key="soccer_uefa_european_championship",
        sofascore_id=1, api_football_id=4,
    ),
}


# ---------------------------------------------------------------------------
# Source base URLs
# ---------------------------------------------------------------------------

FBREF_BASE_URL = "https://fbref.com/en"
UNDERSTAT_BASE_URL = "https://understat.com"
TRANSFERMARKT_BASE_URL = "https://www.transfermarkt.com"
FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk"
CLUBELO_API_URL = "http://api.clubelo.com"
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
SOFASCORE_API_URL = "https://api.sofascore.com/api/v1"
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"


# ---------------------------------------------------------------------------
# Rate-limit defaults (seconds between requests per source)
# ---------------------------------------------------------------------------

RATE_LIMITS: dict[str, float] = {
    "fbref": 6.0,          # FBref is very strict — 6s minimum to avoid 403s
    "understat": 2.0,
    "transfermarkt": 4.0,
    "football_data": 1.0,  # CSV downloads, lenient
    "clubelo": 1.0,        # Simple API
    "odds_api": 1.0,       # Rate-limited by monthly quota
    "sofascore": 2.0,
    "api_football": 1.0,   # Rate-limited by daily quota
}


# ---------------------------------------------------------------------------
# Season helpers
# ---------------------------------------------------------------------------

def get_seasons(start_year: int = 2018, end_year: int = 2026) -> list[str]:
    """Return season strings like '2024-2025'."""
    return [f"{y}-{y + 1}" for y in range(start_year, end_year)]


def get_current_season() -> str:
    from datetime import date
    today = date.today()
    year = today.year if today.month >= 8 else today.year - 1
    return f"{year}-{year + 1}"
