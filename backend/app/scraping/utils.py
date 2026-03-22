"""
Scraping utilities — team name matching, proxy helpers, data cleaning.
"""

import re
import json
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Team name normalization & fuzzy matching
# ---------------------------------------------------------------------------

TEAM_NAME_ALIASES: dict[str, list[str]] = {
    # ── England ────────────────────────────────────────────────────────
    "Manchester United": ["Man United", "Man Utd", "Manchester Utd"],
    "Manchester City": ["Man City"],
    "Newcastle United": ["Newcastle Utd", "Newcastle"],
    "Wolverhampton Wanderers": ["Wolves", "Wolverhampton"],
    "Nottingham Forest": ["Nott'm Forest", "Nottingham", "Nott'ham Forest"],
    "West Ham United": ["West Ham", "West Ham Utd"],
    "Tottenham Hotspur": ["Tottenham", "Spurs"],
    "Brighton and Hove Albion": ["Brighton", "Brighton & Hove Albion", "Brighton Hove Albion"],
    "AFC Bournemouth": ["Bournemouth"],
    "Leicester City": ["Leicester"],
    "Sheffield United": ["Sheffield Utd", "Sheff Utd"],
    "Leeds United": ["Leeds", "Leeds Utd"],
    "Ipswich Town": ["Ipswich"],
    "Luton Town": ["Luton"],
    "Burnley FC": ["Burnley"],
    "Norwich City": ["Norwich"],
    "Watford FC": ["Watford"],
    "West Bromwich Albion": ["West Brom", "WBA", "West Bromwich"],
    "Crystal Palace": [],
    "Aston Villa": [],
    "Everton FC": ["Everton"],
    "Fulham FC": ["Fulham"],
    "Brentford FC": ["Brentford"],
    "Southampton FC": ["Southampton"],
    "Arsenal FC": ["Arsenal"],
    "Liverpool FC": ["Liverpool"],
    "Chelsea FC": ["Chelsea"],
    # ── Spain ──────────────────────────────────────────────────────────
    "Atletico Madrid": ["Atlético Madrid", "Atl. Madrid", "Atletico de Madrid", "Atlético de Madrid"],
    "Athletic Bilbao": ["Athletic Club", "Ath Bilbao", "Ath. Bilbao"],
    "Celta Vigo": ["Celta de Vigo", "RC Celta"],
    "Real Betis": ["Betis", "Real Betis Balompié"],
    "Real Sociedad": ["Sociedad", "Real Sociedad de Fútbol"],
    "Deportivo Alavés": ["Alavés", "Alaves", "Deportivo Alaves"],
    "Real Valladolid": ["Valladolid"],
    "RCD Espanyol": ["Espanyol"],
    "RCD Mallorca": ["Mallorca"],
    "Rayo Vallecano": ["Vallecano"],
    "Girona FC": ["Girona"],
    "Cadiz CF": ["Cadiz", "Cádiz"],
    "Getafe CF": ["Getafe"],
    "Osasuna": ["CA Osasuna"],
    "Villarreal CF": ["Villarreal"],
    "Real Madrid": ["Real Madrid CF"],
    "FC Barcelona": ["Barcelona", "Barça", "Barca"],
    "Sevilla FC": ["Sevilla"],
    "Valencia CF": ["Valencia"],
    "UD Almería": ["Almería", "Almeria", "UD Almeria"],
    "UD Las Palmas": ["Las Palmas"],
    "CD Leganés": ["Leganés", "Leganes"],
    "Elche CF": ["Elche"],
    "Granada CF": ["Granada"],
    "Real Zaragoza": ["Zaragoza"],
    "SD Huesca": ["Huesca"],
    "SD Eibar": ["Eibar"],
    "Levante UD": ["Levante"],
    # ── Germany ────────────────────────────────────────────────────────
    "Borussia Dortmund": ["Dortmund", "BVB", "Bor. Dortmund"],
    "Borussia Mönchengladbach": ["M'Gladbach", "Gladbach", "Bor. M'Gladbach", "Monchengladbach", "Borussia Monchengladbach"],
    "RB Leipzig": ["Leipzig", "RasenBallsport Leipzig"],
    "Bayer Leverkusen": ["Leverkusen", "Bayer 04 Leverkusen"],
    "Bayern Munich": ["Bayern München", "FC Bayern München", "Bayern", "FC Bayern Munich"],
    "Eintracht Frankfurt": ["Ein Frankfurt", "Frankfurt"],
    "VfB Stuttgart": ["Stuttgart"],
    "VfL Wolfsburg": ["Wolfsburg"],
    "SC Freiburg": ["Freiburg"],
    "1. FC Union Berlin": ["Union Berlin", "FC Union Berlin"],
    "1. FC Köln": ["FC Köln", "FC Koln", "Köln", "Koln", "1. FC Koln"],
    "1. FC Heidenheim": ["Heidenheim", "FC Heidenheim"],
    "FC Augsburg": ["Augsburg"],
    "SV Darmstadt 98": ["Darmstadt", "Darmstadt 98"],
    "TSG Hoffenheim": ["Hoffenheim", "TSG 1899 Hoffenheim"],
    "Werder Bremen": ["Bremen", "SV Werder Bremen"],
    "1. FSV Mainz 05": ["Mainz", "Mainz 05"],
    "VfL Bochum": ["Bochum"],
    "Hertha BSC": ["Hertha Berlin", "Hertha"],
    "Arminia Bielefeld": ["Bielefeld"],
    "SpVgg Greuther Fürth": ["Greuther Fürth", "Greuther Furth", "Fürth", "Furth"],
    "FC Schalke 04": ["Schalke", "Schalke 04"],
    "Holstein Kiel": ["Kiel"],
    "FC St. Pauli": ["St. Pauli"],
    # ── France ─────────────────────────────────────────────────────────
    "Paris Saint-Germain": ["PSG", "Paris SG", "Paris Saint Germain"],
    "Olympique Lyonnais": ["Lyon", "OL"],
    "Olympique de Marseille": ["Marseille", "OM"],
    "AS Monaco": ["Monaco"],
    "Stade Rennais": ["Rennes"],
    "LOSC Lille": ["Lille", "Lille OSC"],
    "OGC Nice": ["Nice"],
    "RC Lens": ["Lens"],
    "RC Strasbourg": ["Strasbourg", "RC Strasbourg Alsace"],
    "Stade Brestois 29": ["Brest", "Stade Brestois"],
    "Montpellier HSC": ["Montpellier"],
    "FC Nantes": ["Nantes"],
    "Toulouse FC": ["Toulouse"],
    "Le Havre AC": ["Le Havre"],
    "Clermont Foot": ["Clermont"],
    "FC Lorient": ["Lorient"],
    "FC Metz": ["Metz"],
    "Stade de Reims": ["Reims"],
    "Angers SCO": ["Angers"],
    "AS Saint-Étienne": ["Saint-Étienne", "Saint-Etienne", "St Etienne", "ASSE"],
    "AJ Auxerre": ["Auxerre"],
    "Girondins de Bordeaux": ["Bordeaux"],
    "Dijon FCO": ["Dijon"],
    "Nîmes Olympique": ["Nîmes", "Nimes"],
    # ── Italy ──────────────────────────────────────────────────────────
    "Inter Milan": ["Inter", "Internazionale", "FC Internazionale Milano", "FC Internazionale"],
    "AC Milan": ["Milan", "AC Milan 1899"],
    "AS Roma": ["Roma"],
    "SSC Napoli": ["Napoli"],
    "Juventus": ["Juve", "Juventus FC"],
    "SS Lazio": ["Lazio"],
    "ACF Fiorentina": ["Fiorentina"],
    "Atalanta BC": ["Atalanta", "Atalanta Bergamo"],
    "Torino FC": ["Torino"],
    "Bologna FC": ["Bologna"],
    "Udinese Calcio": ["Udinese"],
    "US Sassuolo": ["Sassuolo"],
    "Cagliari Calcio": ["Cagliari"],
    "Genoa CFC": ["Genoa"],
    "Hellas Verona": ["Verona", "Hellas Verona FC"],
    "US Lecce": ["Lecce"],
    "Empoli FC": ["Empoli"],
    "Monza": ["AC Monza"],
    "Frosinone Calcio": ["Frosinone"],
    "US Salernitana": ["Salernitana"],
    "Spezia Calcio": ["Spezia"],
    "Venezia FC": ["Venezia"],
    "Sampdoria": ["UC Sampdoria"],
    "Benevento Calcio": ["Benevento"],
    "FC Crotone": ["Crotone"],
    "Parma Calcio": ["Parma"],
    "Como 1907": ["Como"],
    # ── Netherlands (Eredivisie) ───────────────────────────────────────
    "Ajax Amsterdam": ["Ajax", "AFC Ajax"],
    "PSV Eindhoven": ["PSV"],
    "Feyenoord Rotterdam": ["Feyenoord"],
    "AZ Alkmaar": ["AZ"],
    "FC Twente": ["Twente"],
    "FC Utrecht": ["Utrecht"],
    "SC Heerenveen": ["Heerenveen"],
    "Vitesse Arnhem": ["Vitesse"],
    "NEC Nijmegen": ["NEC", "N.E.C."],
    "FC Groningen": ["Groningen"],
    "Sparta Rotterdam": ["Sparta"],
    "Go Ahead Eagles": ["Go Ahead"],
    "Fortuna Sittard": ["Fortuna"],
    "RKC Waalwijk": ["RKC"],
    "PEC Zwolle": ["Zwolle", "PEC"],
    "SC Cambuur": ["Cambuur"],
    "Willem II": [],
    "Heracles Almelo": ["Heracles"],
    "FC Volendam": ["Volendam"],
    "Excelsior Rotterdam": ["Excelsior"],
    "FC Emmen": ["Emmen"],
    "Almere City FC": ["Almere City"],
    # ── Portugal (Primeira Liga) ───────────────────────────────────────
    "Sporting CP": ["Sporting", "Sporting Lisbon", "Sporting Clube de Portugal"],
    "SL Benfica": ["Benfica"],
    "FC Porto": ["Porto"],
    "SC Braga": ["Braga", "Sporting Braga"],
    "Vitória SC": ["Vitória de Guimarães", "Guimaraes", "Vitória Guimarães", "Vitoria SC", "Vitoria de Guimaraes"],
    "Gil Vicente FC": ["Gil Vicente"],
    "CD Santa Clara": ["Santa Clara"],
    "CS Marítimo": ["Marítimo", "Maritimo"],
    "Boavista FC": ["Boavista"],
    "FC Famalicão": ["Famalicão", "Famalicao"],
    "FC Arouca": ["Arouca"],
    "Rio Ave FC": ["Rio Ave"],
    "Moreirense FC": ["Moreirense"],
    "GD Estoril Praia": ["Estoril", "Estoril Praia"],
    "FC Vizela": ["Vizela"],
    "CD Tondela": ["Tondela"],
    "Portimonense SC": ["Portimonense"],
    "CF Estrela da Amadora": ["Estrela Amadora", "Estrela da Amadora"],
    "Casa Pia AC": ["Casa Pia"],
    "CD Nacional": ["Nacional"],
    "SC Farense": ["Farense"],
    "Paços de Ferreira": ["Paços Ferreira", "Pacos de Ferreira", "Pacos Ferreira"],
    "Belenenses SAD": ["Belenenses"],
    # ── Turkey (Süper Lig) ────────────────────────────────────────────
    "Galatasaray": ["Galatasaray SK"],
    "Fenerbahçe": ["Fenerbahce", "Fenerbahçe SK"],
    "Beşiktaş": ["Besiktas", "Beşiktaş JK"],
    "Trabzonspor": [],
    "İstanbul Başakşehir": ["Istanbul Basaksehir", "Basaksehir", "İstanbul Başakşehir FK"],
    "Adana Demirspor": ["Adana Demir"],
    "Antalyaspor": [],
    "Konyaspor": [],
    "Alanyaspor": [],
    "Sivasspor": [],
    "Kayserispor": [],
    "Kasımpaşa": ["Kasimpasa"],
    "Gaziantep FK": ["Gaziantep"],
    "Hatayspor": [],
    "Fatih Karagümrük": ["Karagümrük", "Karagumruk", "Fatih Karagumruk"],
    "Giresunspor": [],
    "Rizespor": ["Çaykur Rizespor", "Caykur Rizespor"],
    "Samsunspor": [],
    "Pendikspor": [],
    "Ankaragücü": ["Ankaragucu", "MKE Ankaragücü"],
    "Eyüpspor": ["Eyupspor"],
    "Göztepe": ["Goztepe"],
    "Bodrum FK": ["Bodrumspor"],
    # ── Belgium (Jupiler Pro League) ──────────────────────────────────
    "Club Brugge": ["Club Brugge KV", "Club Bruges"],
    "RSC Anderlecht": ["Anderlecht"],
    "KRC Genk": ["Genk", "Racing Genk"],
    "Royal Antwerp FC": ["Antwerp", "Royal Antwerp"],
    "KAA Gent": ["Gent", "AA Gent"],
    "Standard Liège": ["Standard Liege", "Standard", "Standard de Liège"],
    "Royale Union Saint-Gilloise": ["Union SG", "Union Saint-Gilloise", "R. Union SG"],
    "Cercle Brugge": ["Cercle Bruges"],
    "KV Mechelen": ["Mechelen"],
    "Sint-Truidense VV": ["Sint-Truiden", "STVV", "St. Truiden"],
    "OH Leuven": ["Oud-Heverlee Leuven"],
    "Charleroi": ["Sporting Charleroi", "R. Charleroi SC"],
    "KV Kortrijk": ["Kortrijk"],
    "SV Zulte Waregem": ["Zulte Waregem"],
    "KV Oostende": ["Oostende"],
    "Westerlo": ["KVC Westerlo"],
    "KAS Eupen": ["Eupen"],
    "RFC Seraing": ["Seraing"],
    "Beerschot VA": ["Beerschot"],
    "FCV Dender EH": ["Dender"],
    "RWDM": ["RWD Molenbeek"],
    # ── Scotland (Scottish Premiership) ────────────────────────────────
    "Celtic FC": ["Celtic"],
    "Rangers FC": ["Rangers"],
    "Aberdeen FC": ["Aberdeen"],
    "Heart of Midlothian": ["Hearts", "Heart"],
    "Hibernian FC": ["Hibernian", "Hibs"],
    "St Mirren FC": ["St Mirren"],
    "Dundee United": ["Dundee Utd"],
    "Dundee FC": ["Dundee"],
    "Ross County": [],
    "Motherwell FC": ["Motherwell"],
    "Livingston FC": ["Livingston"],
    "Kilmarnock FC": ["Kilmarnock"],
    "St Johnstone FC": ["St Johnstone"],
    # ── Morocco (Botola Pro) ───────────────────────────────────────────
    "Raja Casablanca": ["Raja CA", "Raja Club Athletic"],
    "Wydad Casablanca": ["WAC", "Wydad AC"],
    "RS Berkane": ["Renaissance Berkane"],
    "AS FAR": ["FAR Rabat", "Forces Armées Royales"],
    "FUS Rabat": ["Fath Union Sport"],
    "Moghreb Tétouan": ["MAT Tétouan", "Moghreb Tetouan"],
    "Hassania Agadir": ["HUSA Agadir"],
    "Ittihad Tanger": [],
    "Olympic Safi": ["OC Safi"],
    "Difaa El Jadida": ["Difaa", "DHJ"],
    "MAS Fez": ["Mouloudia Fez"],
    "Chabab Mohammedia": ["SCCM"],
    "Youssoufia Berrechid": ["Youssoufia"],
    "Rapide Oued Zem": ["ROZ"],
    "Maghreb Fez": ["MAS Fès"],
    "Jeunesse Sportive Soualem": ["JSS"],
}

_ALIAS_MAP: dict[str, str] = {}
for _canonical, _aliases in TEAM_NAME_ALIASES.items():
    _ALIAS_MAP[_canonical.lower()] = _canonical
    for _alias in _aliases:
        _ALIAS_MAP[_alias.lower()] = _canonical

_ALIAS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "team_aliases.json"
if _ALIAS_FILE.exists():
    try:
        _extra = json.loads(_ALIAS_FILE.read_text(encoding="utf-8"))
        for _canon, _al_list in _extra.items():
            if _canon.lower() not in _ALIAS_MAP:
                _ALIAS_MAP[_canon.lower()] = _canon
            for _a in _al_list:
                if _a.lower() not in _ALIAS_MAP:
                    _ALIAS_MAP[_a.lower()] = _canon
    except Exception:
        pass


def normalize_team_name(name: str) -> str:
    """Map common aliases to a canonical team name."""
    if not name:
        return name
    cleaned = name.strip()
    return _ALIAS_MAP.get(cleaned.lower(), cleaned)


def fuzzy_match_team(name: str, candidates: list[str], threshold: float = 0.75) -> Optional[str]:
    """Find the closest matching team name from a list of candidates."""
    try:
        from thefuzz import fuzz, process
        norm = normalize_team_name(name)
        result = process.extractOne(norm, candidates, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= threshold * 100:
            return result[0]
        return None
    except ImportError:
        from difflib import SequenceMatcher
        norm = normalize_team_name(name)
        best_match = None
        best_score = 0.0
        for candidate in candidates:
            norm_candidate = normalize_team_name(candidate)
            score = SequenceMatcher(None, norm.lower(), norm_candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate
        return best_match if best_score >= threshold else None


# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------

def clean_numeric(value: str) -> Optional[float]:
    """Extract a numeric value from a string like '2.34' or '1,234'."""
    if not value or value == "-":
        return None
    cleaned = re.sub(r"[^\d.\-]", "", str(value).replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_score(score_str: str) -> tuple[Optional[int], Optional[int]]:
    """Parse '2-1' or '2–1' into (home_goals, away_goals)."""
    match = re.match(r"(\d+)\s*[-–:]\s*(\d+)", str(score_str))
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None
