import re
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def make_request(url, retry_count=0):
    """
    Make an HTTP request with retries and error handling.
    """
    try:
        logger.debug(f"Requesting: {url}")
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"Request to {url} failed: {e}. Retrying ({retry_count+1}/{MAX_RETRIES})...")
            import time
            time.sleep(RETRY_DELAY)
            return make_request(url, retry_count + 1)
        else:
            logger.error(f"Request to {url} failed after {MAX_RETRIES} attempts: {e}")
            return None

def parse_date_string(date_text):
    """Parse various date formats from Hockey Victoria site."""
    try:
        # Try format: "Monday, 14 April 2025 - 7:30 PM"
        if " - " in date_text:
            date_parts = date_text.split(" - ")
            date_str = date_parts[0]  # "Monday, 14 April 2025"
            time_str = date_parts[1] if len(date_parts) > 1 else "12:00 PM"  # "7:30 PM"
            return datetime.strptime(f"{date_str} {time_str}", "%A, %d %B %Y %I:%M %p")

        # Try alternative formats
        formats = [
            "%a %d %b %Y %I:%M %p",  # Sat 05 Apr 2025 7:30 PM
            "%a %d %b %Y %H:%M",     # Sat 05 Apr 2025 19:30
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_text}")
        return datetime.now()  # Fallback

    except Exception as e:
        logger.error(f"Error parsing date '{date_text}': {e}")
        return datetime.now()  # Fallback

def extract_club_info(team_name):
    """Extract club name and ID from team name."""
    if " - " in team_name:
        club_name = team_name.split(" - ")[0].strip()
    else:
        # Handle case where there's no delimiter
        club_name = team_name.split()[0]

    # Generate club_id
    from utils.ids import make_club_id
    club_id = make_club_id(club_name).replace("club_", "")  # Remove prefix for consistency

    return club_name, club_id

def find_best_team_match(team_name, fixture_id, mentone_teams):
    """Find the best matching Mentone team ID."""
    if "Mentone" not in team_name:
        return None

    # Try exact match first
    for name, data in mentone_teams.items():
        if name == team_name:
            return data["id"]

    # Try fixture ID match
    for name, data in mentone_teams.items():
        if str(data["fixture_id"]) == str(fixture_id):
            return data["id"]

    # Try partial match
    for name, data in mentone_teams.items():
        if name in team_name or team_name in name:
            return data["id"]

    return None

def classify_team(comp_name):
    """
    Classify a team by type and gender based on competition name.
    """
    comp_name_lower = comp_name.lower()

    # Gender/type classification based on naming
    GENDER_MAP = {
        "men": "Men",
        "women": "Women",
        "boys": "Boys",
        "girls": "Girls",
        "mixed": "Mixed"
    }

    TYPE_KEYWORDS = {
        "senior": "Senior",
        "junior": "Junior",
        "midweek": "Midweek",
        "masters": "Masters",
        "outdoor": "Outdoor",
        "indoor": "Indoor"
    }

    # Determine team type
    team_type = "Unknown"
    for keyword, value in TYPE_KEYWORDS.items():
        if keyword in comp_name_lower:
            team_type = value
            break

    # Special case handling
    if "premier league" in comp_name_lower or "vic league" in comp_name_lower or "pennant" in comp_name_lower:
        team_type = "Senior"
    elif "u12" in comp_name_lower or "u14" in comp_name_lower or "u16" in comp_name_lower or "u18" in comp_name_lower:
        team_type = "Junior"
    elif "masters" in comp_name_lower or "35+" in comp_name_lower or "45+" in comp_name_lower or "60+" in comp_name_lower:
        team_type = "Midweek"

    # Determine gender from competition name
    if "women's" in comp_name_lower or "women" in comp_name_lower:
        gender = "Women"
    elif "men's" in comp_name_lower or "men" in comp_name_lower:
        gender = "Men"
    else:
        # Fall back to keyword checking
        gender = "Unknown"
        for keyword, value in GENDER_MAP.items():
            if keyword in comp_name_lower:
                gender = value
                break

    return team_type, gender

def extract_game_elements(soup):
    """Extract game elements from HTML, trying different selectors."""
    game_elements = []

    # Try different selectors based on observed HTML structure
    selectors = [
        "div.fixture-details",
        "div.card-body.font-size-sm",
        "div.card.card-hover"
    ]

    for selector in selectors:
        elements = soup.select(selector)
        if elements:
            game_elements.extend(elements)
            break

    return game_elements

def parse_game_element(game_el, fixture_id, comp_id, mentone_teams, round_num):
    """Parse a game element and extract details."""
    from utils.ids import make_game_id

    try:
        # Extract teams from fixture
        team_els = []

        # Try different selectors for team names
        selectors = [
            ".fixture-details-team-name",
            "div.col-lg-3 a",
            ".text-center a"
        ]

        for selector in selectors:
            team_els = game_el.select(selector)
            if len(team_els) >= 2:
                break

        # Skip if we don't have at least two teams
        if len(team_els) < 2:
            logger.debug(f"Couldn't find two teams in game element")
            return None

        # Get team names
        home_team_name = team_els[0].text.strip()
        away_team_name = team_els[1].text.strip()

        # Check if Mentone is playing
        mentone_is_home = "Mentone" in home_team_name
        mentone_is_away = "Mentone" in away_team_name

        if not (mentone_is_home or mentone_is_away):
            return None

        logger.info(f"Found Mentone game: {home_team_name} vs {away_team_name}")

        # Create game object
        game = {}

        # Extract date and time
        date_el = game_el.select_one(".fixture-details-date-long")
        if date_el:
            game["date"] = parse_date_string(date_el.text.strip())
        else:
            # Try alternative date element
            datetime_el = game_el.select_one("div.col-md")
            if datetime_el:
                lines = datetime_el.get_text("\n", strip=True).split("\n")
                date_str = lines[0]
                time_str = lines[1] if len(lines) > 1 else "12:00"
                game["date"] = parse_date_string(f"{date_str} {time_str}")
            else:
                game["date"] = datetime.now()

        # Extract venue
        venue_el = game_el.select_one(".fixture-details-venue")
        if not venue_el:
            venue_el = game_el.select_one("div.col-md a")
        game["venue"] = venue_el.text.strip() if venue_el else "Unknown Venue"

        # Extract club info and team IDs
        home_club_name, home_club_id = extract_club_info(home_team_name)
        away_club_name, away_club_id = extract_club_info(away_team_name)

        # Find best matching team IDs
        home_team_id = find_best_team_match(home_team_name, fixture_id, mentone_teams) if mentone_is_home else None
        away_team_id = find_best_team_match(away_team_name, fixture_id, mentone_teams) if mentone_is_away else None

        # Set up team data
        game["home_team"] = {
            "name": home_team_name,
            "id": home_team_id,
            "club": home_club_name,
            "club_id": home_club_id
        }

        game["away_team"] = {
            "name": away_team_name,
            "id": away_team_id,
            "club": away_club_name,
            "club_id": away_club_id
        }

        # Extract scores
        score_els = game_el.select(".fixture-details-team-score")
        if len(score_els) >= 2:
            home_score_text = score_els[0].text.strip()
            away_score_text = score_els[1].text.strip()

            if home_score_text and home_score_text != "-":
                try:
                    game["home_team"]["score"] = int(home_score_text)
                except ValueError:
                    pass

            if away_score_text and away_score_text != "-":
                try:
                    game["away_team"]["score"] = int(away_score_text)
                except ValueError:
                    pass

        # Determine game status
        now = datetime.now()
        if game.get("date", now) < now:
            if ("score" in game["home_team"] and "score" in game["away_team"]):
                game["status"] = "completed"
            else:
                game["status"] = "in_progress"
        else:
            game["status"] = "scheduled"

        # Add metadata for dashboard filtering
        game["round"] = round_num
        game["comp_id"] = comp_id
        game["fixture_id"] = fixture_i