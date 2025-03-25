def create_competition(comp):
    """Create a competition in Firestore."""
    comp_id = comp["comp_id"]
    fixture_id = comp["fixture_id"]
    comp_name = comp.get("comp_heading", comp["name"])

    # Determine competition type
    comp_type = "Senior"  # Default type
    if "junior" in comp_name.lower() or any(f"u{i}" in comp_name.lower() for i in range(10, 19)):
        comp_type = "Junior"
    elif "masters" in comp_name.lower() or any(f"{i}+" in comp_name.lower() for i in [35, 45, 60]):
        comp_type = "Midweek/Masters"

    # Extract season info
    season = str(datetime.now().year)  # Default to current year
    if " - " in comp_name:
        parts = comp_name.split(" - ")
        if len(parts) > 1 and parts[1].strip().isdigit():
            season = parts[1].strip()

    # Create the Firestore document
    document_id = make_comp_id(comp_id)
    comp_ref = db.collection("competitions").document(document_id)

    comp_data = {
        "id": document_id,
        "original_id": comp_id,
        "name": comp_name,
        "type": comp_type,
        "season": season,
        "fixture_id": fixture_id,
        "start_date": firestore.SERVER_TIMESTAMP,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "active": True
    }

    if not is_dry_run():
        comp_ref.set(comp_data)
        logger.info(f"Created competition: {comp_name} ({document_id})")
    else:
        logger.info(f"DRY RUN: Would create competition: {comp_name} ({document_id})")

    return comp_ref, comp_data

def create_grade(comp, competition_ref, competition_data):
    """Create a grade (fixture) in Firestore."""
    fixture_id = comp["fixture_id"]
    comp_id = comp["comp_id"]
    comp_name = comp["name"]

    # Determine type and gender
    team_type, team_gender = classify_team(comp_name)

    # Generate grade ID
    document_id = make_grade_id(fixture_id)

    # Create grade data
    grade_data = {
        "id": document_id,
        "original_id": fixture_id,
        "name": comp_name,
        "comp_id": comp_id,
        "competition_name": competition_data.get("name", ""),
        "competition_id": competition_data.get("id", ""),
        "competition_ref": competition_ref,
        "type": team_type,
        "gender": team_gender,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }

    # Save to Firestore
    grade_ref = db.collection("grades").document(document_id)

    if not is_dry_run():
        grade_ref.set(grade_data)
        logger.info(f"Created grade: {comp_name} ({document_id})")
    else:
        logger.info(f"DRY RUN: Would create grade: {comp_name} ({document_id})")

    return grade_ref, grade_data

def find_and_create_teams(competitions):
    """Scan competitions to find teams and create in Firestore."""
    logger.info(f"Scanning {len(competitions)} competitions for teams...")
    teams = []
    seen = set()
    processed_count = 0

    # Create all competitions and grades first
    comp_refs = {}
    comp_data_map = {}
    grade_refs = {}
    grade_data_map = {}

    for comp in competitions:
        # Create competition
        comp_ref, comp_data = create_competition(comp)
        comp_id = comp["comp_id"]
        comp_refs[comp_id] = comp_ref
        comp_data_map[comp_id] = comp_data

        # Create grade
        grade_ref, grade_data = create_grade(comp, comp_ref, comp_data)
        fixture_id = comp["fixture_id"]
        grade_refs[fixture_id] = grade_ref
        grade_data_map[fixture_id] = grade_data

    # Process teams
    for comp in competitions:
        processed_count += 1
        comp_name = comp['name']
        comp_id = comp['comp_id']
        fixture_id = comp['fixture_id']
        round_url = f"https://www.hockeyvictoria.org.au/games/{comp_id}/{fixture_id}/round/1"

        logger.info(f"[{processed_count}/{len(competitions)}] Checking {comp_name} at {round_url}")

        response = make_request(round_url)
        if not response:
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract teams from the page
        team_info = {}
        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.text.strip()

            # Check if this is a team link
            team_match = TEAM_ID_REGEX.search(href)
            if team_match and is_valid_team(text):
                link_comp_id, team_id = team_match.groups()
                if link_comp_id == comp_id:
                    team_info[text] = team_id

        # Also look for teams in fixture details
        fixture_teams = set()
        for div in soup.select(".fixture-details-team-name"):
            text = div.text.strip()
            if text:
                fixture_teams.add(text)

        # Combine both sources
        all_teams = set(team_info.keys()) | fixture_teams

        # Get the competition type and gender
        comp_data = comp_data_map.get(comp_id, {})
        grade_data = grade_data_map.get(fixture_id, {})
        team_type = grade_data.get("type", comp_data.get("type", "Unknown"))
        team_gender = grade_data.get("gender", "Unknown")

        # Create/update teams
        for team_name in all_teams:
            # Extract club information
            club_name, club_id = extract_club_info(team_name)

            # Check if it's the home club
            is_home_club = club_id.lower() == HOME_CLUB_ID.lower()

            # Create a proper team name using the competition name
            competition_part = comp_name.split(' - ')[0] if ' - ' in comp_name else comp_name
            proper_team_name = f"{club_name} - {competition_part}"

            # Skip if we've already seen this team
            key = (proper_team_name, fixture_id)
            if key in seen:
                continue

            seen.add(key)

            # Get team ID from extracted info or generate one
            team_id = team_info.get(team_name, f"{team_type.lower()}_{fixture_id}")
            document_id = make_team_id(team_id)

            # Create or get club reference and data
            club_ref, club_data = create_or_get_club(club_name, club_id)

            # Create team data
            team_data = {
                "id": document_id,
                "original_id": team_id,
                "name": proper_team_name,
                "fixture_id": fixture_id,
                "comp_id": comp_id,
                "type": team_type,
                "gender": team_gender,
                "club": club_name,
                "club_id": club_id,
                "club_ref": club_ref,
                "is_home_club_team": is_home_club,
                "comp_name": comp_name,
                "competition_name": comp_data.get("name", ""),
                "competition_id": comp_data.get("id", ""),
                "competition_ref": comp_refs.get(comp_id),
                "grade_name": grade_data.get("name", ""),
                "grade_id": grade_data.get("id", ""),
                "grade_ref": grade_refs.get(fixture_id),
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "active": True
            }

            # Add to teams list
            teams.append(team_data)

            # Save to Firestore
            if not is_dry_run():
                db.collection("teams").document(document_id).set(team_data)

            # Log team discovery
            if is_home_club:
                logger.info(f"Found Mentone team: {proper_team_name} (ID: {document_id}, Type: {team_type}, Gender: {team_gender})")
            else:
                logger.debug(f"Found team: {proper_team_name} (ID: {document_id})")

    logger.info(f"Team discovery complete. Found {len(teams)} teams total.")
    return teams

def archive_old_teams():
    """Mark old teams as inactive."""
    current_year = datetime.now().year

    logger.info(f"Archiving teams from seasons before {current_year}")

    # Get all teams that don't have the current year as season
    if is_dry_run():
        logger.info("DRY RUN: Would archive old teams")
        return 0

    teams_ref = db.collection("teams")
    teams_query = teams_ref.where("season", "<", current_year).stream()

    count = 0
    for team in teams_query:
        team.reference.update({
            "active": False,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        count += 1

    logger.info(f"Archived {count} teams from previous seasons")
    return count

def save_teams_to_json(teams, output_file=OUTPUT_FILE):
    """Save discovered teams to a JSON file."""
    try:
        # Remove references as they're not JSON serializable
        cleaned_teams = []
        for team in teams:
            team_copy = team.copy()
            ref_fields = ['club_ref', 'competition_ref', 'grade_ref']
            for field in ref_fields:
                if field in team_copy:
                    del team_copy[field]
            cleaned_teams.append(team_copy)

        with open(output_file, "w") as f:
            json.dump(cleaned_teams, f, indent=2)
        logger.info(f"Successfully saved {len(teams)} teams to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save teams to {output_file}: {e}")

def create_settings():
    """Create default settings in Firestore."""
    logger.info("Creating settings...")

    settings_data = {
        "id": "email_settings",
        "version": 1,
        "pre_game_hours": 24,
        "weekly_summary_day": "Sunday",
        "weekly_summary_time": "20:00",
        "admin_emails": ["admin@mentone.com"],
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }

    if not is_dry_run():
        db.collection("settings").document("email_settings").set(settings_data)

    logger.info("Created email settings")

def main():
    """Main function to run the builder script."""
    start_time = time.time()
    logger.info(f"=== Mentone Hockey Club Season Builder ===")

    # Check if we're in dry run mode
    if is_dry_run():
        logger.info("Running in DRY RUN mode - no Firestore changes will be made")

    try:
        # Archive old teams
        archive_old_teams()

        # Get competitions
        comps = get_competition_blocks()
        if not comps:
            logger.error("No competitions found. Exiting.")
            return

        # Find and create teams
        teams = find_and_create_teams(comps)

        # Save teams to JSON for backup
        save_teams_to_json(teams)

        # Create settings
        create_settings()

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

    elapsed_time = time.time() - start_time
    logger.info(f"Script completed in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()