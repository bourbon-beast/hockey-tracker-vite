def poll_recent_results():
    """Poll for game results from the past week plus upcoming 2 weeks."""
    # Define date range (past week + upcoming 2 weeks)
    today = datetime.now()
    start_date = today - timedelta(days=7)
    end_date = today + timedelta(days=14)

    logger.info(f"Polling for results between {start_date.date()} and {end_date.date()}")

    # Get all Mentone teams
    mentone_teams = get_mentone_teams()

    if not mentone_teams:
        logger.warning("No Mentone teams found, exiting")
        return

    # Process each team separately
    all_updated_games = []
    total_games_created = 0
    total_games_updated = 0

    for team_name, team_data in mentone_teams.items():
        # Process results for this team
        updated_games, games_created, games_updated = process_team_results(
            team_data, start_date, end_date
        )

        # Add to totals
        if updated_games:
            all_updated_games.extend(updated_games)
            total_games_created += games_created
            total_games_updated += games_updated

    # Update games in Firestore
    if all_updated_games:
        update_games_in_firestore(all_updated_games)

        # Update summaries
        update_summaries(mentone_teams, all_updated_games)

    logger.info(f"Results polling completed: {len(all_updated_games)} games processed, "
                f"{total_games_created} created, {total_games_updated} updated")

def update_games_in_firestore(games):
    """Update games in Firestore using batch operations."""
    if not games:
        logger.info("No games to update")
        return 0, 0

    logger.info(f"Updating {len(games)} games in Firestore")

    # Transform function to prepare games for Firestore
    def transform_game(game):
        # Ensure timestamps
        game["updated_at"] = firestore.SERVER_TIMESTAMP
        game["last_polled_at"] = firestore.SERVER_TIMESTAMP

        if "created_at" not in game:
            game["created_at"] = firestore.SERVER_TIMESTAMP

        # Remove any reference objects that might have been added
        ref_fields = ["team_ref", "club_ref", "competition_ref", "grade_ref"]
        for field in ref_fields:
            if field in game:
                del game[field]

        return game

    # Use batch writing
    creates, updates = batch_write_to_firestore(db, games, "games", transform_game)

    logger.info(f"Created {creates} new games, updated {updates} existing games")
    return creates, updates

def update_summaries(mentone_teams, all_games):
    """Update team and club summaries based on games."""
    # Group games by team
    team_games = {}
    for game in all_games:
        # Process home team
        home_team_id = game["home_team"].get("id")
        if home_team_id and "Mentone" in game["home_team"].get("name", ""):
            if home_team_id not in team_games:
                team_games[home_team_id] = []
            team_games[home_team_id].append(game)

        # Process away team
        away_team_id = game["away_team"].get("id")
        if away_team_id and "Mentone" in game["away_team"].get("name", ""):
            if away_team_id not in team_games:
                team_games[away_team_id] = []
            team_games[away_team_id].append(game)

    # Generate team summaries
    team_summaries = generate_team_summaries(team_games)

    if team_summaries:
        # Update in Firestore
        creates, updates = batch_write_to_firestore(db, team_summaries, "team_summaries")
        logger.info(f"Updated {len(team_summaries)} team summaries ({creates} created, {updates} updated)")

        # Generate and update club summaries
        club_summaries = generate_club_summaries(team_summaries)
        if club_summaries:
            creates, updates = batch_write_to_firestore(db, club_summaries, "club_summaries")
            logger.info(f"Updated {len(club_summaries)} club summaries ({creates} created, {updates} updated)")
    else:
        logger.info("No team summaries to update")

def main():
    """Main function to run the results poller."""
    start_time = time.time()
    logger.info(f"=== Mentone Hockey Club Results Poller ===")

    # Check if we're in dry run mode
    if is_dry_run():
        logger.info("Running in DRY RUN mode - no Firestore changes will be made")

    try:
        # Poll for recent results
        poll_recent_results()

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

    elapsed_time = time.time() - start_time
    logger.info(f"Results polling completed in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()