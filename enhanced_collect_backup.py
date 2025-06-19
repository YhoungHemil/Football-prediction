
import requests
import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
import time
import logging
from typing import Optional, Dict, Any

class EnhancedFootballCollector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": api_key}
        
        # Rate limiting configuration
        self.request_delay = 6  # 6 seconds between requests (10 requests/minute)
        self.retry_delay = 60   # 60 seconds when hitting 429 errors
        self.competition_break = 30  # 30 seconds between competitions
        self.max_retries = 3
        
        # Progress tracking
        self.total_requests = 0
        self.failed_requests = 0
        self.successful_requests = 0
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('football_collector.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create database connection
        self.conn = sqlite3.connect('enhanced_football_data.db')
        self.setup_enhanced_database()
    
    def setup_enhanced_database(self):
        """Create enhanced tables with detailed statistics"""
        cursor = self.conn.cursor()
        
        # Enhanced matches table with detailed stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_matches (
                id INTEGER PRIMARY KEY,
                competition_name TEXT,
                season TEXT,
                matchday INTEGER,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                home_score_ht INTEGER,
                away_score_ht INTEGER,
                match_date TEXT,
                status TEXT,
                winner TEXT,
                venue TEXT,
                referee TEXT,
                attendance INTEGER,
                
                -- Additional stats (when available from API)
                home_possession REAL,
                away_possession REAL,
                home_shots_total INTEGER,
                away_shots_total INTEGER,
                home_shots_on_target INTEGER,
                away_shots_on_target INTEGER,
                home_corners INTEGER,
                away_corners INTEGER,
                home_fouls INTEGER,
                away_fouls INTEGER,
                home_yellow_cards INTEGER,
                away_yellow_cards INTEGER,
                home_red_cards INTEGER,
                away_red_cards INTEGER,
                home_offsides INTEGER,
                away_offsides INTEGER,
                
                -- Data collection metadata
                data_completeness TEXT,
                last_updated TEXT
            )
        ''')
        
        # Team form tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_form (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT,
                competition_name TEXT,
                season TEXT,
                match_date TEXT,
                opponent TEXT,
                venue TEXT,
                goals_for INTEGER,
                goals_against INTEGER,
                result TEXT,
                points INTEGER,
                running_form TEXT,
                last_5_form TEXT,
                goals_for_last_5 INTEGER,
                goals_against_last_5 INTEGER
            )
        ''')
        
        # Head-to-head records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS head_to_head (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_a TEXT,
                team_b TEXT,
                competition_name TEXT,
                matches_played INTEGER,
                team_a_wins INTEGER,
                team_b_wins INTEGER,
                draws INTEGER,
                team_a_goals INTEGER,
                team_b_goals INTEGER,
                avg_goals_per_match REAL,
                over_2_5_count INTEGER,
                under_2_5_count INTEGER,
                last_updated TEXT
            )
        ''')
        
        # Team strength ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT,
                competition_name TEXT,
                season TEXT,
                matches_played INTEGER,
                
                -- Attacking metrics
                attack_strength REAL,
                avg_goals_scored REAL,
                goals_scored_home REAL,
                goals_scored_away REAL,
                
                -- Defensive metrics  
                defense_strength REAL,
                avg_goals_conceded REAL,
                goals_conceded_home REAL,
                goals_conceded_away REAL,
                
                -- Overall metrics
                overall_rating REAL,
                home_advantage REAL,
                recent_form_rating REAL,
                over_2_5_tendency REAL,
                
                last_updated TEXT
            )
        ''')
        
        # Match predictions table (for tracking our model performance)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                home_team TEXT,
                away_team TEXT,
                match_date TEXT,
                
                -- Predictions
                predicted_home_score REAL,
                predicted_away_score REAL,
                predicted_total_goals REAL,
                win_probability_home REAL,
                win_probability_draw REAL,
                win_probability_away REAL,
                over_2_5_probability REAL,
                
                -- Actual results (filled after match)
                actual_home_score INTEGER,
                actual_away_score INTEGER,
                actual_total_goals INTEGER,
                actual_result TEXT,
                
                prediction_accuracy TEXT,
                created_date TEXT
            )
        ''')
        
        # Collection statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_date TEXT,
                competition_name TEXT,
                total_matches INTEGER,
                successful_collections INTEGER,
                failed_collections INTEGER,
                detailed_data_available INTEGER,
                basic_data_only INTEGER,
                collection_duration_minutes REAL
            )
        ''')
        
        self.conn.commit()
        self.logger.info("Enhanced database tables created successfully!")
    
    def make_api_request(self, url: str, params: Dict = None, detailed: bool = False) -> Optional[Dict[Any, Any]]:
        """Make API request with rate limiting, retries, and error handling"""
        self.total_requests += 1
        
        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting
                if self.total_requests > 1:
                    self.logger.debug(f"Waiting {self.request_delay}s before request...")
                    time.sleep(self.request_delay)
                
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    self.successful_requests += 1
                    self.logger.debug(f"[SUCCESS] Request successful: {url}")
                    return response.json()
                
                elif response.status_code == 429:
                    self.logger.warning(f"[WARNING] Rate limit hit (429). Waiting {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
                
                elif response.status_code == 403:
                    self.logger.error("[ERROR] Access forbidden (403). Check API key permissions.")
                    if detailed:
                        self.logger.info("[RETRY] Falling back to basic data collection...")
                        return None  # Will trigger fallback to basic data
                    break
                
                elif response.status_code == 404:
                    self.logger.warning(f"[WARNING] Resource not found (404): {url}")
                    break
                
                else:
                    self.logger.warning(f"[WARNING] HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"[TIMEOUT] Request timeout (attempt {attempt + 1}/{self.max_retries})")
                
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"[NETWORK] Connection error (attempt {attempt + 1}/{self.max_retries})")
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"[ERROR] Request failed: {e}")
                
            # Wait before retry
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                self.logger.info(f"[WAIT] Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        self.failed_requests += 1
        self.logger.error(f"[ERROR] Failed to fetch data after {self.max_retries} attempts: {url}")
        return None
    
    def get_detailed_match_data(self, match_id: int) -> Optional[Dict[Any, Any]]:
        """Get detailed statistics for a specific match with fallback"""
        url = f"{self.base_url}/matches/{match_id}"
        
        # Try to get detailed data
        detailed_data = self.make_api_request(url, detailed=True)
        if detailed_data:
            return detailed_data
        
        # If detailed data fails, log and return None for fallback
        self.logger.warning(f"[WARNING] Could not get detailed data for match {match_id}")
        return None
    
    def collect_enhanced_matches(self, competition_id: int, season: int = 2024):
        """Collect matches with enhanced statistics and robust error handling"""
        collection_start = time.time()
        
        self.logger.info(f"[START] Starting enhanced data collection for competition {competition_id}, season {season}")
        
        url = f"{self.base_url}/competitions/{competition_id}/matches"
        params = {"season": season}
        
        # Get basic matches data
        matches_data = self.make_api_request(url, params)
        if not matches_data:
            self.logger.error("[ERROR] Failed to fetch matches list")
            return
        
        matches = matches_data.get('matches', [])
        competition_name = matches_data.get('competition', {}).get('name', 'Unknown')
        
        if not matches:
            self.logger.warning("[WARNING] No matches found")
            return
        
        self.logger.info(f"[INFO] Found {len(matches)} matches for {competition_name}")
        
        # Progress tracking variables
        processed = 0
        detailed_data_count = 0
        basic_data_count = 0
        failed_count = 0
        
        # Process each match
        for i, match in enumerate(matches):
            match_id = match['id']
            home_team = match['homeTeam']['name']
            away_team = match['awayTeam']['name']
            
            # Progress display
            processed += 1
            progress_percent = (processed / len(matches)) * 100
            
            self.logger.info(f"[PROGRESS] Progress: {processed}/{len(matches)} ({progress_percent:.1f}%) - "
                           f"Processing: {home_team} vs {away_team} (ID: {match_id})")
            
            try:
                # Try to get detailed match data
                detailed_match = self.get_detailed_match_data(match_id)
                
                if detailed_match:
                    # Store with detailed data
                    self.store_enhanced_match(detailed_match, competition_name, data_completeness="detailed")
                    detailed_data_count += 1
                    self.logger.debug(f"[SUCCESS] Stored detailed data for {home_team} vs {away_team}")
                else:
                    # Fallback to basic data from the matches list
                    self.store_enhanced_match(match, competition_name, data_completeness="basic")
                    basic_data_count += 1
                    self.logger.info(f"[BASIC] Stored basic data for {home_team} vs {away_team}")
                
            except Exception as e:
                failed_count += 1
                self.logger.error(f"[ERROR] Failed to process match {match_id} ({home_team} vs {away_team}): {e}")
                continue
            
            # Show intermediate progress every 10 matches
            if processed % 10 == 0:
                self.logger.info(f"[INFO] Intermediate Stats - Detailed: {detailed_data_count}, "
                               f"Basic: {basic_data_count}, Failed: {failed_count}")
        
        # Collection complete
        collection_duration = (time.time() - collection_start) / 60  # Convert to minutes
        
        # Store collection statistics
        self.store_collection_stats(
            competition_name, len(matches), processed - failed_count, 
            failed_count, detailed_data_count, basic_data_count, collection_duration
        )
        
        # Final summary
        self.logger.info(f"[SUCCESS] Collection completed for {competition_name}!")
        self.logger.info(f"[INFO] Final Statistics:")
        self.logger.info(f"   Total matches: {len(matches)}")
        self.logger.info(f"   Successfully processed: {processed - failed_count}")
        self.logger.info(f"   Detailed data: {detailed_data_count}")
        self.logger.info(f"   Basic data only: {basic_data_count}")
        self.logger.info(f"   Failed: {failed_count}")
        self.logger.info(f"   Collection time: {collection_duration:.2f} minutes")
        self.logger.info(f"   API requests: {self.total_requests} (Success: {self.successful_requests}, Failed: {self.failed_requests})")
        
        # Wait between competitions
        if processed > 0:
            self.logger.info(f"[PAUSE] Taking {self.competition_break}s break before next competition...")
            time.sleep(self.competition_break)
    
    def store_enhanced_match(self, match_data: Dict, competition_name: str, data_completeness: str = "basic"):
        """Store enhanced match data with fallback handling"""
        cursor = self.conn.cursor()
        
        match = match_data
        
        try:
            # Extract basic match info (always available)
            home_team = match['homeTeam']['name']
            away_team = match['awayTeam']['name']
            
            # Handle scores safely
            score = match.get('score', {})
            fulltime_score = score.get('fullTime', {})
            halftime_score = score.get('halfTime', {})
            
            home_score = fulltime_score.get('home') if fulltime_score.get('home') is not None else 0
            away_score = fulltime_score.get('away') if fulltime_score.get('away') is not None else 0
            home_score_ht = halftime_score.get('home') if halftime_score.get('home') is not None else 0
            away_score_ht = halftime_score.get('away') if halftime_score.get('away') is not None else 0
            
            # Extract additional statistics (may not be available)
            stats = match.get('statistics', {})
            
            cursor.execute('''
                INSERT OR REPLACE INTO enhanced_matches 
                (id, competition_name, season, matchday, home_team, away_team, 
                 home_score, away_score, home_score_ht, away_score_ht,
                 match_date, status, winner, venue, referee, attendance,
                 data_completeness, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match['id'],
                competition_name,
                match.get('season', {}).get('startDate', '2024')[:4],
                match.get('matchday'),
                home_team,
                away_team,
                home_score,
                away_score,
                home_score_ht,
                away_score_ht,
                match.get('utcDate'),
                match.get('status'),
                score.get('winner'),
                match.get('venue'),
                ', '.join([ref.get('name', '') for ref in match.get('referees', [])]),
                match.get('attendance'),
                data_completeness,
                datetime.now().isoformat()
            ))
            
            # Update team form after each finished match
            if match.get('status') == 'FINISHED':
                self.update_team_form(home_team, away_team, match, competition_name)
            
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error storing match data: {e}")
            raise
    
    def store_collection_stats(self, competition_name: str, total_matches: int, 
                             successful: int, failed: int, detailed: int, 
                             basic: int, duration: float):
        """Store collection statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO collection_stats 
            (collection_date, competition_name, total_matches, successful_collections,
             failed_collections, detailed_data_available, basic_data_only, collection_duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            competition_name,
            total_matches,
            successful,
            failed,
            detailed,
            basic,
            duration
        ))
        
        self.conn.commit()
    
    def update_team_form(self, home_team: str, away_team: str, match: Dict, competition_name: str):
        """Update team form records with error handling"""
        try:
            cursor = self.conn.cursor()
            
            score = match.get('score', {})
            fulltime_score = score.get('fullTime', {})
            
            home_score = fulltime_score.get('home', 0) or 0
            away_score = fulltime_score.get('away', 0) or 0
            match_date = match.get('utcDate')
            season = match.get('season', {}).get('startDate', '2024')[:4]
            
            # Determine results and points
            if home_score > away_score:
                home_result, away_result = 'W', 'L'
                home_points, away_points = 3, 0
            elif home_score < away_score:
                home_result, away_result = 'L', 'W'
                home_points, away_points = 0, 3
            else:
                home_result, away_result = 'D', 'D'
                home_points, away_points = 1, 1
            
            # Insert home team form
            cursor.execute('''
                INSERT INTO team_form 
                (team_name, competition_name, season, match_date, opponent, venue,
                 goals_for, goals_against, result, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (home_team, competition_name, season, match_date, away_team, 'H',
                  home_score, away_score, home_result, home_points))
            
            # Insert away team form
            cursor.execute('''
                INSERT INTO team_form 
                (team_name, competition_name, season, match_date, opponent, venue,
                 goals_for, goals_against, result, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (away_team, competition_name, season, match_date, home_team, 'A',
                  away_score, home_score, away_result, away_points))
            
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error updating team form: {e}")
    
    def calculate_team_ratings(self, competition_name: str, season: int = 2024):
        """Calculate team strength ratings"""
        self.logger.info("[CALC] Calculating team strength ratings...")
        
        cursor = self.conn.cursor()
        
        # Get all teams
        cursor.execute('''
            SELECT DISTINCT team_name FROM team_form 
            WHERE competition_name = ? AND season = ?
        ''', (competition_name, str(season)))
        
        teams = [row[0] for row in cursor.fetchall()]
        
        ratings_processed = 0
        for team in teams:
            try:
                rating = self.calculate_single_team_rating(team, competition_name, season)
                if rating:
                    self.store_team_rating(team, rating, competition_name, season)
                    ratings_processed += 1
                    
                    if ratings_processed % 5 == 0:
                        self.logger.info(f"[INFO] Processed ratings for {ratings_processed}/{len(teams)} teams")
                        
            except Exception as e:
                self.logger.error(f"[ERROR] Error calculating rating for {team}: {e}")
                continue
        
        self.logger.info(f"[SUCCESS] Calculated ratings for {ratings_processed}/{len(teams)} teams")
    
    def calculate_single_team_rating(self, team_name: str, competition_name: str, season: int):
        """Calculate comprehensive rating for a single team with proper type handling"""
        cursor = self.conn.cursor()
        
        # Get team's matches
        cursor.execute('''
            SELECT * FROM team_form 
            WHERE team_name = ? AND competition_name = ? AND season = ?
            ORDER BY match_date DESC
        ''', (team_name, competition_name, str(season)))
        
        matches = cursor.fetchall()
        
        if not matches:
            return {}
        
        # Helper function to safely convert to int
        def safe_int(value):
            if value is None or value == '':
                return 0
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        
        # Calculate basic metrics with type safety
        total_matches = len(matches)
        total_goals_for = sum(safe_int(match[6]) for match in matches)  # goals_for column
        total_goals_against = sum(safe_int(match[7]) for match in matches)  # goals_against column
        
        # Home/Away splits
        home_matches = [m for m in matches if m[5] == 'H']  # venue column
        away_matches = [m for m in matches if m[5] == 'A']
        
        home_goals_for = sum(safe_int(m[6]) for m in home_matches) if home_matches else 0
        away_goals_for = sum(safe_int(m[6]) for m in away_matches) if away_matches else 0
        home_goals_against = sum(safe_int(m[7]) for m in home_matches) if home_matches else 0
        away_goals_against = sum(safe_int(m[7]) for m in away_matches) if away_matches else 0
        
        # Recent form (last 5 matches)
        recent_matches = matches[:5]
        recent_goals_for = sum(safe_int(m[6]) for m in recent_matches)
        recent_goals_against = sum(safe_int(m[7]) for m in recent_matches)
        recent_points = sum(safe_int(m[9]) for m in recent_matches)  # points column
        
        # Over 2.5 tendency
        over_2_5_matches = sum(1 for m in matches if (safe_int(m[6]) + safe_int(m[7])) > 2.5)
        over_2_5_tendency = over_2_5_matches / total_matches if total_matches > 0 else 0
        
        # Calculate strength ratings (simplified version)
        league_avg_goals = 1.3  # Approximate Premier League average
        attack_strength = (total_goals_for / total_matches) / league_avg_goals if total_matches > 0 else 1
        defense_strength = league_avg_goals / (total_goals_against / total_matches) if total_matches > 0 and total_goals_against > 0 else 1
        
        return {
            'matches_played': total_matches,
            'attack_strength': round(attack_strength, 3),
            'avg_goals_scored': round(total_goals_for / total_matches, 2) if total_matches > 0 else 0,
            'goals_scored_home': round(home_goals_for / len(home_matches), 2) if home_matches else 0,
            'goals_scored_away': round(away_goals_for / len(away_matches), 2) if away_matches else 0,
            'defense_strength': round(defense_strength, 3),
            'avg_goals_conceded': round(total_goals_against / total_matches, 2) if total_matches > 0 else 0,
            'goals_conceded_home': round(home_goals_against / len(home_matches), 2) if home_matches else 0,
            'goals_conceded_away': round(away_goals_against / len(away_matches), 2) if away_matches else 0,
            'overall_rating': round((attack_strength + defense_strength) / 2, 3),
            'home_advantage': round((home_goals_for / len(home_matches)) - (away_goals_for / len(away_matches)), 2) if home_matches and away_matches else 0,
            'recent_form_rating': round(recent_points / len(recent_matches), 2) if recent_matches else 0,
            'over_2_5_tendency': round(over_2_5_tendency, 3)
        }
    
    def store_team_rating(self, team_name: str, rating: Dict, competition_name: str, season: int):
        """Store team rating in database"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO team_ratings 
            (team_name, competition_name, season, matches_played,
             attack_strength, avg_goals_scored, goals_scored_home, goals_scored_away,
             defense_strength, avg_goals_conceded, goals_conceded_home, goals_conceded_away,
             overall_rating, home_advantage, recent_form_rating, over_2_5_tendency, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            team_name, competition_name, str(season), rating['matches_played'],
            rating['attack_strength'], rating['avg_goals_scored'], 
            rating['goals_scored_home'], rating['goals_scored_away'],
            rating['defense_strength'], rating['avg_goals_conceded'],
            rating['goals_conceded_home'], rating['goals_conceded_away'],
            rating['overall_rating'], rating['home_advantage'],
            rating['recent_form_rating'], rating['over_2_5_tendency'],
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
    
    def calculate_head_to_head(self, competition_name: str, season: int = 2024):
        """Calculate head-to-head records between all teams"""
        self.logger.info("[H2H] Calculating head-to-head records...")
        
        cursor = self.conn.cursor()
        
        # Get all unique team pairs
        cursor.execute('''
            SELECT DISTINCT home_team, away_team FROM enhanced_matches 
            WHERE competition_name = ? AND season = ? AND status = 'FINISHED'
        ''', (competition_name, str(season)))
        
        pairs = cursor.fetchall()
        h2h_records = {}
        processed_pairs = 0
        
        for home_team, away_team in pairs:
            # Create bidirectional key
            key = tuple(sorted([home_team, away_team]))
            
            if key not in h2h_records:
                try:
                    h2h_record = self.calculate_h2h_record(key[0], key[1], competition_name)
                    if h2h_record:
                        h2h_records[key] = h2h_record
                        self.store_h2h_record(key[0], key[1], h2h_record, competition_name)
                        processed_pairs += 1
                        
                        if processed_pairs % 10 == 0:
                            self.logger.info(f"[INFO] Processed {processed_pairs} head-to-head records...")
                            
                except Exception as e:
                    self.logger.error(f"[ERROR] Error calculating H2H for {key[0]} vs {key[1]}: {e}")
                    continue
        
        self.logger.info(f"[SUCCESS] Calculated {len(h2h_records)} head-to-head records")
    
    def calculate_h2h_record(self, team_a: str, team_b: str, competition_name: str):
        """Calculate head-to-head record between two teams"""
        cursor = self.conn.cursor()
        
        # Get all matches between these teams (both home and away)
        cursor.execute('''
            SELECT home_team, away_team, home_score, away_score 
            FROM enhanced_matches 
            WHERE competition_name = ? AND status = 'FINISHED'
            AND ((home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?))
        ''', (competition_name, team_a, team_b, team_b, team_a))
        
        matches = cursor.fetchall()
        
        if not matches:
            return None
        
        team_a_wins = team_b_wins = draws = 0
        team_a_goals = team_b_goals = 0
        over_2_5 = under_2_5 = 0
        
        for home_team, away_team, home_score, away_score in matches:
            # Handle None values
            home_score = home_score or 0
            away_score = away_score or 0
            
            total_goals = home_score + away_score
            
            if total_goals > 2.5:
                over_2_5 += 1
            else:
                under_2_5 += 1
            
            if home_team == team_a:
                team_a_goals += home_score
                team_b_goals += away_score
                if home_score > away_score:
                    team_a_wins += 1
                elif home_score < away_score:
                    team_b_wins += 1
                else:
                    draws += 1
            else:  # away_team == team_a
                team_a_goals += away_score
                team_b_goals += home_score
                if away_score > home_score:
                    team_a_wins += 1
                elif away_score < home_score:
                    team_b_wins += 1
                else:
                    draws += 1
        
        return {
            'matches_played': len(matches),
            'team_a_wins': team_a_wins,
            'team_b_wins': team_b_wins,
            'draws': draws,
            'team_a_goals': team_a_goals,
            'team_b_goals': team_b_goals,
            'avg_goals_per_match': round((team_a_goals + team_b_goals) / len(matches), 2),
            'over_2_5_count': over_2_5,
            'under_2_5_count': under_2_5
        }
    
    def store_h2h_record(self, team_a: str, team_b: str, record: Dict, competition_name: str):
        """Store head-to-head record"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO head_to_head 
            (team_a, team_b, competition_name, matches_played,
             team_a_wins, team_b_wins, draws, team_a_goals, team_b_goals,
             avg_goals_per_match, over_2_5_count, under_2_5_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            team_a, team_b, competition_name, record['matches_played'],
            record['team_a_wins'], record['team_b_wins'], record['draws'],
            record['team_a_goals'], record['team_b_goals'],
            record['avg_goals_per_match'], record['over_2_5_count'],
            record['under_2_5_count'], datetime.now().isoformat()
        ))
        
        self.conn.commit()
    
    def show_team_ratings(self, competition_name: str = 'Premier League'):
        """Display team ratings"""
        self.logger.info(f"\n=== {competition_name.upper()} TEAM RATINGS ===")
        
        query = '''
        SELECT team_name, overall_rating, attack_strength, defense_strength,
               avg_goals_scored, avg_goals_conceded, over_2_5_tendency,
               recent_form_rating
        FROM team_ratings 
        WHERE competition_name = ?
        ORDER BY overall_rating DESC
        '''
        
        try:
            ratings_df = pd.read_sql_query(query, self.conn, params=(competition_name,))
            if not ratings_df.empty:
                print(ratings_df.round(3).to_string(index=False))
            else:
                self.logger.warning(f"No ratings found for {competition_name}")
        except Exception as e:
            self.logger.error(f"Error displaying ratings: {e}")
    
    def show_collection_summary(self):
        """Display collection statistics summary"""
        self.logger.info("\n=== COLLECTION SUMMARY ===")
        
        try:
            query = '''
            SELECT competition_name, collection_date, total_matches,
                   successful_collections, failed_collections, 
                   detailed_data_available, basic_data_only,
                   collection_duration_minutes
            FROM collection_stats
            ORDER BY collection_date DESC
            LIMIT 10
            '''
            
            summary_df = pd.read_sql_query(query, self.conn)
            if not summary_df.empty:
                print(summary_df.to_string(index=False))
                
                # Overall stats
                self.logger.info(f"\n=== OVERALL API USAGE ===")
                self.logger.info(f"Total API requests made: {self.total_requests}")
                self.logger.info(f"Successful requests: {self.successful_requests}")
                self.logger.info(f"Failed requests: {self.failed_requests}")
                self.logger.info(f"Success rate: {(self.successful_requests/self.total_requests)*100:.1f}%" if self.total_requests > 0 else "N/A")
            else:
                self.logger.info("No collection statistics available")
                
        except Exception as e:
            self.logger.error(f"Error displaying summary: {e}")
    
    def run_full_collection(self, competitions: Dict[int, str], season: int = 2024):
        """Run complete data collection for multiple competitions"""
        total_start_time = time.time()
        
        self.logger.info("[START] STARTING FULL ENHANCED FOOTBALL DATA COLLECTION")
        self.logger.info("=" * 80)
        self.logger.info(f"Season: {season}")
        self.logger.info(f"Competitions: {list(competitions.values())}")
        self.logger.info(f"Rate limiting: {self.request_delay}s between requests")
        self.logger.info("=" * 80)
        
        for competition_id, competition_name in competitions.items():
            self.logger.info(f"\n[COMPETITION] Starting collection for {competition_name} (ID: {competition_id})")
            
            try:
                # Step 1: Collect enhanced match data
                self.logger.info(f"[INFO] Collecting enhanced match data for {competition_name}...")
                self.collect_enhanced_matches(competition_id, season)
                
                # Step 2: Calculate team ratings
                self.logger.info(f"[CALC] Calculating team strength ratings for {competition_name}...")
                self.calculate_team_ratings(competition_name, season)
                
                # Step 3: Calculate head-to-head records
                self.logger.info(f"[H2H] Calculating head-to-head records for {competition_name}...")
                self.calculate_head_to_head(competition_name, season)
                
                # Step 4: Show team ratings
                self.show_team_ratings(competition_name)
                
                self.logger.info(f"[SUCCESS] Completed collection for {competition_name}")
                
            except Exception as e:
                self.logger.error(f"[ERROR] Failed to complete collection for {competition_name}: {e}")
                continue
        
        # Final summary
        total_duration = (time.time() - total_start_time) / 60
        self.logger.info(f"\n[COMPLETE] FULL COLLECTION COMPLETED!")
        self.logger.info(f"Total time: {total_duration:.2f} minutes")
        
        self.show_collection_summary()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("[DB] Database connection closed")

# Example usage and configuration
if __name__ == "__main__":
    # Replace with your API key
    API_KEY = "751bc97db5fa4f4ba08955bdda5a07d0"
    
    # Competition IDs (add more as needed)
    COMPETITIONS = {
        2021: "Premier League",
        2014: "La Liga", 
        2002: "Bundesliga",
        2019: "Serie A",
        2015: "Ligue 1"
    }
    
    collector = EnhancedFootballCollector(API_KEY)
    
    try:
        # Option 1: Run full collection for multiple competitions
        collector.run_full_collection(COMPETITIONS, 2024)
        
        # Option 2: Or run individual collections
        # collector.collect_enhanced_matches(2021, 2024)  # Premier League only
        # collector.calculate_team_ratings('Premier League', 2024)
        # collector.calculate_head_to_head('Premier League', 2024)
        # collector.show_team_ratings('Premier League')
        
    except KeyboardInterrupt:
        collector.logger.info("\n[STOP] Collection interrupted by user")
    except Exception as e:
        collector.logger.error(f"[ERROR] Unexpected error: {e}")
    finally:
        collector.close()
        
    print("\n[SUCCESS] Enhanced data collection completed!")
    print("[DB] Database: 'enhanced_football_data.db'")
    print("[LOG] Log file: 'football_collector.log'")