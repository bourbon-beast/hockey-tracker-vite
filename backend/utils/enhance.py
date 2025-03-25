from datetime import datetime
from firebase_admin import firestore

def enhance_game_metadata(game):
    """Add useful metadata fields to games for filtering."""
    if "date" in game and isinstance(game["date"], datetime):
        # Add day of week as string (Monday, Tuesday, etc.)
        game["day_of_week"] = game["date"].strftime("%A")

        # Flag for weekend games (Saturday/Sunday)
        game["is_weekend_game"] = game["date"].weekday() >= 5

        # ISO week number for grouping by week
        game["week_number"] = game["date"].isocalendar()[1]

        # Month name for monthly filtering
        game["month"] = game["date"].strftime("%B")

        # Time of day category
        hour = game["date"].hour
        if hour < 12:
            game["time_category"] = "Morning"
        elif hour < 17:
            game["time_category"] = "Afternoon"
        else:
            game["time_category"] = "Evening"

    # Add Mentone-specific fields for dashboard filtering
    mentone_is_home = "Mentone" in game.get("home_team", {}).get("name", "")
    mentone_is_away = "Mentone" in game.get("away_team", {}).get("name", "")
    game["mentone_is_home"] = mentone_is_home
    game["mentone_is_away"] = mentone_is_away
    game["is_mentone_game"] = mentone_is_home or mentone_is_away

    # Add match result from Mentone perspective
    if game.get("status") == "completed":
        home_score = game.get("home_team", {}).get("score")
        away_score = game.get("away_team", {}).get("score")

        if home_score is not None and away_score is not None:
            if mentone_is_home:
                if home_score > away_score:
                    game["mentone_result"] = "win"
                elif home_score < away_score:
                    game["mentone_result"] = "loss"
                else:
                    game["mentone_result"] = "draw"
            elif mentone_is_away:
                if away_score > home_score:
                    game["mentone_result"] = "win"
                elif away_score < home_score:
                    game["mentone_result"] = "loss"
                else:
                    game["mentone_result"] = "draw"

    # Track freshness
    game["last_polled_at"] = firestore.SERVER_TIMESTAMP

    return game

def generate_team_summaries(team_games):
    """
    Generate summary documents for each team.

    Args:
        team_games: Dict mapping team_id to list of games

    Returns:
        List of summary documents
    """
    summaries = []

    for team_id, games in team_games.items():
        # Skip if no games
        if not games:
            continue

        # Get sample game for metadata
        sample_game = games[0]
        team_name = None
        team_type = None
        team_gender = None

        # Find team data from either home or away
        if "mentone_is_home" in sample_game and sample_game["mentone_is_home"]:
            team_name = sample_game.get("home_team", {}).get("name")
        elif "mentone_is_away" in sample_game and sample_game["mentone_is_away"]:
            team_name = sample_game.get("away_team", {}).get("name")

        team_type = sample_game.get("type", "Unknown")
        team_gender = sample_game.get("gender", "Unknown")

        # Group games by round
        rounds = {}
        for game in games:
            round_num = game.get("round")
            if not round_num:
                continue

            if round_num not in rounds:
                rounds[round_num] = {
                    "games": [],
                    "games_played": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                    "status_counts": {"completed": 0, "scheduled": 0, "in_progress": 0}
                }

            rounds[round_num]["games"].append(game)

            # Count by status
            status = game.get("status", "scheduled")
            rounds[round_num]["status_counts"][status] = rounds[round_num]["status_counts"].get(status, 0) + 1

            # Only count completed games for stats
            if status != "completed":
                continue

            rounds[round_num]["games_played"] += 1

            # Get scores based on mentone perspective
            mentone_is_home = game.get("mentone_is_home", False)
            mentone_score = game.get("home_team", {}).get("score", 0) if mentone_is_home else game.get("away_team", {}).get("score", 0)
            opponent_score = game.get("away_team", {}).get("score", 0) if mentone_is_home else game.get("home_team", {}).get("score", 0)

            rounds[round_num]["goals_for"] += mentone_score or 0
            rounds[round_num]["goals_against"] += opponent_score or 0

            # Count results
            mentone_result = game.get("mentone_result")
            if mentone_result == "win":
                rounds[round_num]["wins"] += 1
            elif mentone_result == "loss":
                rounds[round_num]["losses"] += 1
            elif mentone_result == "draw":
                rounds[round_num]["draws"] += 1

        # Create summary documents for each round
        from utils.ids import make_summary_id
        for round_num, data in rounds.items():
            summary_id = make_summary_id(team_id, round_num)
            summary = {
                "id": summary_id,
                "team_id": team_id,
                "team_name": team_name,
                "round": round_num,
                "type": team_type,
                "gender": team_gender,
                "games_played": data["games_played"],
                "goals_for": data["goals_for"],
                "goals_against": data["goals_against"],
                "goal_difference": data["goals_for"] - data["goals_against"],
                "wins": data["wins"],
                "losses": data["losses"],
                "draws": data["draws"],
                "points": (data["wins"] * 3) + data["draws"],
                "status_counts": data["status_counts"],
                "updated_at": firestore.SERVER_TIMESTAMP
            }

            summaries.append(summary)

    return summaries

def generate_club_summaries(summaries):
    """
    Generate club-level summary documents from team summaries.

    Args:
        summaries: List of team summary documents

    Returns:
        List of club summary documents
    """
    # Group summaries by type and gender
    grouped = {}

    for summary in summaries:
        key = f"{summary.get('type', 'Unknown')}_{summary.get('gender', 'Unknown')}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(summary)

    club_summaries = []

    for key, group in grouped.items():
        type_str, gender_str = key.split('_')

        # Calculate totals
        total_games_played = sum(s.get("games_played", 0) for s in group)
        total_wins = sum(s.get("wins", 0) for s in group)
        total_losses = sum(s.get("losses", 0) for s in group)
        total_draws = sum(s.get("draws", 0) for s in group)
        total_goals_for = sum(s.get("goals_for", 0) for s in group)
        total_goals_against = sum(s.get("goals_against", 0) for s in group)

        # Win percentage
        win_percentage = 0
        if total_games_played > 0:
            win_percentage = (total_wins / total_games_played) * 100

        # Create club summary
        from utils.ids import make_club_summary_id
        summary_id = make_club_summary_id("mentone", type_str, gender_str)

        club_summary = {
            "id": summary_id,
            "club_id": "mentone",
            "division": type_str,
            "gender": gender_str,
            "total_teams": len(set(s.get("team_id") for s in group)),
            "total_games_played": total_games_played,
            "wins": total_wins,
            "losses": total_losses,
            "draws": total_draws,
            "win_percentage": win_percentage,
            "goals_for": total_goals_for,
            "goals_against": total_goals_against,
            "goal_difference": total_goals_for - total_goals_against,
            "updated_at": firestore.SERVER_TIMESTAMP
        }

        club_summaries.append(club_summary)

    return club_summaries