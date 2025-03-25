import hashlib

def make_team_id(fixture_id):
    """Standardized team ID generator."""
    return f"team_{fixture_id}"

def make_club_id(club_name):
    """Standardized club ID generator."""
    club_id = club_name.lower().replace(" ", "_").replace("-", "_")
    return f"club_{club_id}"

def make_comp_id(comp_id):
    """Standardized competition ID generator."""
    return f"comp_{comp_id}"

def make_grade_id(fixture_id):
    """Standardized grade ID generator."""
    return f"grade_{fixture_id}"

def make_game_id(comp_id, fixture_id, round_num, home_team, away_team):
    """Generate consistent game ID using hash."""
    # Create a reproducible string
    base = f"{comp_id}_{fixture_id}_{round_num}_{home_team}_{away_team}"
    # Hash for uniqueness
    hash_object = hashlib.md5(base.encode())
    hash_str = hash_object.hexdigest()[:8]
    return f"game_{hash_str}"

def make_summary_id(team_id, round_num):
    """Generate summary document ID."""
    return f"summary_{team_id}_round_{round_num}"

def make_club_summary_id(club_id, division, gender):
    """Generate club summary document ID."""
    return f"club_summary_{club_id}_{division.lower()}_{gender.lower()}"