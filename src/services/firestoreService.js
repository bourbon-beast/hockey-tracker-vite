// src/services/firestoreService.js
import {
    collection,
    getDocs,
    query,
    where,
    orderBy,
    limit,
    Timestamp,
    doc,
    getDoc
} from 'firebase/firestore';
import { db } from '../../firebase';


// Add this function to your existing file
export const testFirestoreConnection = async () => {
    try {
        // Get the first document from any collection to test access
        const testRef = collection(db, 'teams');
        const testQuery = query(testRef, limit(1));
        const snapshot = await getDocs(testQuery);

        if (snapshot.empty) {
            console.log("Connection successful but no documents found");
            return false;
        } else {
            console.log("Connection successful, documents exist");
            return true;
        }
    } catch (error) {
        console.error("Firestore connection test failed:", error);
        throw error; // This will help you see the exact error in the console
    }
};
/**
 * Fetch games for a specific date range
 * @param {Date} startDate - Start date for range
 * @param {Date} endDate - End date for range
 * @param {String} clubId - Optional club ID to filter games
 * @returns {Promise<Array>} Array of game objects
 */
export const fetchGamesByDateRange = async (startDate, endDate, clubId = null) => {
    try {
        console.log("Fetching games with dates:", startDate, endDate, "club:", clubId);

        // Create Firestore timestamp objects for our date range
        const startTimestamp = Timestamp.fromDate(startDate);
        const endTimestamp = Timestamp.fromDate(endDate);

        // Start building the query
        const gamesRef = collection(db, 'games');
        let gameQuery = query(
            gamesRef,
            where('date', '>=', startTimestamp),
            where('date', '<=', endTimestamp),
            orderBy('date', 'asc')
        );

        const querySnapshot = await getDocs(gameQuery);
        console.log("Query complete, got", querySnapshot.size, "results");

        const games = [];
        querySnapshot.forEach((doc) => {
            const data = doc.data();

            // Convert Firestore timestamp to JS Date
            const gameDate = data.date instanceof Timestamp ?
                data.date.toDate() :
                (data.date ? new Date(data.date) : new Date());

            // Create a complete game object with the date properly converted
            const gameObj = {
                id: doc.id,
                ...data,
                date: gameDate
            };

            // Filter by club if needed
            if (clubId) {
                // Extract the simple club name from clubId (removing "club_" prefix if it exists)
                const simpleClubName = clubId.replace('club_', '');

                // Check team details for the simple club name
                const homeClubId = data.home_team?.club_id?.toLowerCase() || '';
                const homeClubName = data.home_team?.club?.toLowerCase() || '';

                const awayClubId = data.away_team?.club_id?.toLowerCase() || '';
                const awayClubName = data.away_team?.club?.toLowerCase() || '';

                // Check if either home or away team matches the club
                if (homeClubId === simpleClubName ||
                    homeClubName === simpleClubName ||
                    awayClubId === simpleClubName ||
                    awayClubName === simpleClubName) {
                    games.push(gameObj);
                }
            } else {
                // No club filter, include all games
                games.push(gameObj);
            }
        });

        console.log("Returning", games.length, "filtered games");
        return games;
    } catch (error) {
        console.error('Error fetching games by date range:', error);
        throw error;
    }
};

/**
 * Group games by category (Men's, Women's, Juniors, Midweek)
 * @param {Array} games - Array of game objects
 * @returns {Object} Object with games grouped by category
 */
export const groupGamesByCategory = (games) => {
    return {
        "Men's": games.filter(game => {
            const homeTeamName = (game.home_team?.name || '').toLowerCase();
            const awayTeamName = (game.away_team?.name || '').toLowerCase();
            return homeTeamName.includes("men's") || awayTeamName.includes("men's");
        }),

        "Women's": games.filter(game => {
            const homeTeamName = (game.home_team?.name || '').toLowerCase();
            const awayTeamName = (game.away_team?.name || '').toLowerCase();
            return homeTeamName.includes("women's") || awayTeamName.includes("women's");
        }),

        "Juniors": games.filter(game => {
            const homeTeamName = (game.home_team?.name || '').toLowerCase();
            const awayTeamName = (game.away_team?.name || '').toLowerCase();
            return homeTeamName.includes("under") ||
                awayTeamName.includes("under") ||
                homeTeamName.includes("u12") ||
                awayTeamName.includes("u12") ||
                homeTeamName.includes("u14") ||
                awayTeamName.includes("u14") ||
                homeTeamName.includes("u16") ||
                awayTeamName.includes("u16") ||
                homeTeamName.includes("u18") ||
                awayTeamName.includes("u18");
        }),

        "Midweek": games.filter(game => {
            const homeTeamName = (game.home_team?.name || '').toLowerCase();
            const awayTeamName = (game.away_team?.name || '').toLowerCase();
            const isWeekend = game.date ? (game.date.getDay() === 0 || game.date.getDay() === 6) : false;
            return !isWeekend ||
                homeTeamName.includes("masters") ||
                awayTeamName.includes("masters") ||
                homeTeamName.includes("midweek") ||
                awayTeamName.includes("midweek");
        })
    };
};

/**
 * Fetch all clubs
 */
export const fetchAllClubs = async () => {
    try {
        const clubsRef = collection(db, 'clubs');
        const querySnapshot = await getDocs(clubsRef);

        const clubs = [];
        querySnapshot.forEach((doc) => {
            clubs.push({
                id: doc.id,
                ...doc.data(),
            });
        });

        return clubs;
    } catch (error) {
        console.error('Error fetching all clubs:', error);
        throw error;
    }
};

/**
 * Fetch a club by ID
 */
export const fetchClubById = async (clubId) => {
    try {
        const clubRef = doc(db, 'clubs', clubId);
        const clubDoc = await getDoc(clubRef);

        if (!clubDoc.exists()) {
            return null;
        }

        return {
            id: clubDoc.id,
            ...clubDoc.data()
        };
    } catch (error) {
        console.error(`Error fetching club with ID ${clubId}:`, error);
        throw error;
    }
};

/**
 * Fetch all teams from a specific club
 */
export const fetchTeamsByClubId = async (clubId) => {
    try {
        const teamsRef = collection(db, 'teams');
        const teamsQuery = query(teamsRef, where('club_id', '==', clubId));
        const querySnapshot = await getDocs(teamsQuery);

        const teams = [];
        querySnapshot.forEach((doc) => {
            teams.push({
                id: doc.id,
                ...doc.data(),
            });
        });

        return teams;
    } catch (error) {
        console.error(`Error fetching teams for club ${clubId}:`, error);
        throw error;
    }
};

/**
 * Fetch games for a specific club
 * This searches for games where either home_team.club_id or away_team.club_id matches
 */
export const fetchGamesByClubId = async (clubId) => {
    try {
        const gamesRef = collection(db, 'games');

        // Query for games where this club is home team
        const homeGamesQuery = query(
            gamesRef,
            where('home_team.club_id', '==', clubId),
            orderBy('date', 'desc')
        );

        // Query for games where this club is away team
        const awayGamesQuery = query(
            gamesRef,
            where('away_team.club_id', '==', clubId),
            orderBy('date', 'desc')
        );

        // Execute both queries
        const [homeGamesSnapshot, awayGamesSnapshot] = await Promise.all([
            getDocs(homeGamesQuery),
            getDocs(awayGamesQuery)
        ]);

        // Process results
        const homeGames = [];
        homeGamesSnapshot.forEach((doc) => {
            const data = doc.data();
            const gameDate = data.date instanceof Timestamp ? data.date.toDate() : new Date(data.date);

            homeGames.push({
                id: doc.id,
                ...data,
                date: gameDate
            });
        });

        const awayGames = [];
        awayGamesSnapshot.forEach((doc) => {
            const data = doc.data();
            const gameDate = data.date instanceof Timestamp ? data.date.toDate() : new Date(data.date);

            awayGames.push({
                id: doc.id,
                ...data,
                date: gameDate
            });
        });

        // Combine results and remove duplicates
        const allGames = [...homeGames];

        // Only add away games that aren't already in home games
        awayGames.forEach(awayGame => {
            if (!allGames.some(game => game.id === awayGame.id)) {
                allGames.push(awayGame);
            }
        });

        // Sort by date (newest first)
        return allGames.sort((a, b) => b.date - a.date);
    } catch (error) {
        console.error(`Error fetching games for club ${clubId}:`, error);
        throw error;
    }
};

/**
 * Get club statistics
 */
export const fetchClubStats = async (clubId) => {
    try {
        // Get teams
        const teams = await fetchTeamsByClubId(clubId);

        // Get games
        const games = await fetchGamesByClubId(clubId);

        // Calculate stats
        let wins = 0;
        let losses = 0;
        let draws = 0;
        let goalsFor = 0;
        let goalsAgainst = 0;
        const teamIds = teams.map(team => team.id);

        games.forEach(game => {
            const isHomeTeam = game.home_team && teamIds.includes(game.home_team.id);
            const isAwayTeam = game.away_team && teamIds.includes(game.away_team.id);

            if (game.status !== 'completed') {
                return; // Skip games that aren't completed
            }

            if (isHomeTeam) {
                const homeScore = game.home_team.score || 0;
                const awayScore = game.away_team.score || 0;

                goalsFor += homeScore;
                goalsAgainst += awayScore;

                if (homeScore > awayScore) wins++;
                else if (homeScore < awayScore) losses++;
                else draws++;
            }
            else if (isAwayTeam) {
                const homeScore = game.home_team.score || 0;
                const awayScore = game.away_team.score || 0;

                goalsFor += awayScore;
                goalsAgainst += homeScore;

                if (awayScore > homeScore) wins++;
                else if (awayScore < homeScore) losses++;
                else draws++;
            }
        });

        const completedGames = games.filter(game => game.status === 'completed').length;

        return {
            team_count: teams.length,
            games_played: completedGames,
            wins,
            losses,
            draws,
            goals_for: goalsFor,
            goals_against: goalsAgainst,
            goal_difference: goalsFor - goalsAgainst,
            win_percentage: completedGames > 0 ? (wins / completedGames) * 100 : 0,
            upcoming_games: games.filter(game => game.status === 'scheduled').length
        };
    } catch (error) {
        console.error(`Error fetching stats for club ${clubId}:`, error);
        throw error;
    }
};