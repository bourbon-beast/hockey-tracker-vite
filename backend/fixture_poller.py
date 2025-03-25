def process_round_page(comp_id, fixture_id, round_num, mentone_teams):
    """Process a single round page and extract games."""
    round_url = f"{BASE_URL}{comp_id}/{fixture_id}/round/{round_num}"
    logger.info(f"Checking round URL: {round_url}")

    response = make_request(round_url)
    if not response:
        logger.warning(f"Failed to fetch round {round_num}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    game_elements = extract_game_elements(soup)

    logger.info(f"Found {len(game_elements)} game elements on round {round_num} page")
    games = []

    for game_el in game_elements:
        game = parse_game_element(game_el, fixture_id, comp_id, mentone_teams, round_num)

        if game:
            # Generate a proper game ID
            game["id"] = make_game_id(comp_id, fixture_id, round_num,
                                      game["home_team"]["name"],
                                      game["away_team"]["name"])

            # Apply metadata enhancements
            enhance_game_metadata(game)

            games.append(game)

    return games

def fetch_fixtures(mentone_teams):
    """Fetch all fixtures for Mentone teams."""
    logger.info("Fetching fixtures for all Mentone teams")

    all_games = []
    processed_count = 0

    # Process each team separately
    for team_name, team_data in mentone_teams.items():
        processed_count += 1
        comp_id = str(team_data.get("comp_id", ""))
        fixture_id = str(team_data.get("fixture_id", ""))

        if not comp_id or not fixture_id:
            logger.warning(f"Missing comp_id or fixture_id for team {team_name}, skipping")
            continue

        logger.info(f"[{processed_count}/{len(mentone_teams)}] Checking fixtures for {team_name}")

        # Check all rounds
        team_games = []
        for round_num in range(1, MAX_ROUNDS + 1):
            games = process_round_page(comp_id, fixture_id, round_num, {team_name: team_data})

            if games:
                team_games.extend(games)
                logger.info(f"Found {len(games)} games in round {round_num}")
            elif round_num > 1:
                # If we haven't found any games for this round, we might be at the end
                logger.info(f"No games found in round {round_num}, stopping search for {team_name}")
                break

            # Be nice to the server
            time.sleep(0.5)

        logger.info(f"Found {len(team_games)} total games for team {team_name}")
        all_games.extend(team_games)

    return all_games

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
    """Main function to run the fixture poller."""
    start_time = time.time()
    logger.info(f"=== Mentone Hockey Club Fixture Poller ===")

    # Check if we're in dry run mode
    if is_dry_run():
        logger.info("Running in DRY RUN mode - no Firestore changes will be made")

    try:
        # Get all Mentone teams
        mentone_teams = get_mentone_teams()

        if not mentone_teams:
            logger.warning("No Mentone teams found, exiting")
            return

        # Fetch all fixtures
        all_games = fetch_fixtures(mentone_teams)

        if not all_games:
            logger.warning("No games found, exiting")
            return

        # Update games in Firestore
        creates, updates = update_games_in_firestore(all_games)

        # Update summaries if any games were created or updated
        if creates > 0 or updates > 0:
            update_summaries(mentone_teams, all_games)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

    elapsed_time = time.time() - start_time
    logger.info(f"Fixture polling completed in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()