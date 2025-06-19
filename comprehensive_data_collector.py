import requests
import pandas as pd
import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import soccerdata as sd
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

class ComprehensiveFootballCollector:
    """Massive football data collector for 25,000+ matches across 12 leagues"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.setup_logging()
        self.setup_database()
        
        # API configurations
        self.football_data_api = config.get('football_data_api_key', '')
        self.odds_api_key = config.get('odds_api_key', '')
        
        # Rate limiting
        self.request_delay = config.get('request_delay', 2)
        self.batch_delay = config.get('batch_delay', 10)
        
        # Progress tracking
        self.total_target_matches = 0
        self.collected_matches = 0
        self.failed_collections = 0
        
        # Define comprehensive league structure
        self.league_structure = self.define_league_structure()
        
    def setup_logging(self):
        """Enhanced logging for large-scale collection"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('comprehensive_collector.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def define_league_structure(self) -> Dict:
        """Define all leagues and seasons to collect"""
        return {
            # ENGLAND - 4 Leagues (Premier League to League Two)
            'england': {
                'country_code': 'ENG',
                'leagues': {
                    'premier_league': {
                        'football_data_id': 2021,
                        'fbref_name': 'ENG-Premier League',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 380,
                        'priority': 1
                    },
                    'championship': {
                        'football_data_id': 2016,
                        'fbref_name': 'ENG-Championship',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 552,
                        'priority': 2
                    },
                    'league_one': {
                        'football_data_id': 2017,
                        'fbref_name': 'ENG-League One',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 552,
                        'priority': 3
                    },
                    'league_two': {
                        'football_data_id': 2018,
                        'fbref_name': 'ENG-League Two',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 552,
                        'priority': 4
                    }
                }
            },
            
            # SPAIN - 2 Leagues
            'spain': {
                'country_code': 'ESP',
                'leagues': {
                    'la_liga': {
                        'football_data_id': 2014,
                        'fbref_name': 'ESP-La Liga',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 380,
                        'priority': 1
                    },
                    'segunda_division': {
                        'football_data_id': 2017,  # May need adjustment
                        'fbref_name': 'ESP-Segunda División',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 462,
                        'priority': 2
                    }
                }
            },
            
            # GERMANY - 2 Leagues
            'germany': {
                'country_code': 'GER',
                'leagues': {
                    'bundesliga': {
                        'football_data_id': 2002,
                        'fbref_name': 'GER-Bundesliga',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 306,
                        'priority': 1
                    },
                    'bundesliga_2': {
                        'football_data_id': 2020,
                        'fbref_name': 'GER-2. Bundesliga',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 306,
                        'priority': 2
                    }
                }
            },
            
            # ITALY - 2 Leagues
            'italy': {
                'country_code': 'ITA',
                'leagues': {
                    'serie_a': {
                        'football_data_id': 2019,
                        'fbref_name': 'ITA-Serie A',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 380,
                        'priority': 1
                    },
                    'serie_b': {
                        'football_data_id': 2021,  # May need adjustment
                        'fbref_name': 'ITA-Serie B',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 380,
                        'priority': 2
                    }
                }
            },
            
            # FRANCE - 2 Leagues
            'france': {
                'country_code': 'FRA',
                'leagues': {
                    'ligue_1': {
                        'football_data_id': 2015,
                        'fbref_name': 'FRA-Ligue 1',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 380,
                        'priority': 1
                    },
                    'ligue_2': {
                        'football_data_id': 2016,  # May need adjustment
                        'fbref_name': 'FRA-Ligue 2',
                        'seasons': ['2020', '2021', '2022', '2023', '2024'],
                        'expected_matches_per_season': 380,
                        'priority': 2
                    }
                }
            }
        }
    
    def setup_database(self):
        """Enhanced database schema for comprehensive data"""
        self.conn = sqlite3.connect('comprehensive_football_data.db')
        cursor = self.conn.cursor()
        
        # Comprehensive matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comprehensive_matches (
                id TEXT PRIMARY KEY,
                country TEXT NOT NULL,
                league_name TEXT NOT NULL,
                competition_tier INTEGER,
                season TEXT NOT NULL,
                matchday INTEGER,
                
                -- Teams
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                
                -- Basic Results
                home_score INTEGER,
                away_score INTEGER,
                home_score_ht INTEGER,
                away_score_ht INTEGER,
                
                -- Match Info
                match_date TEXT,
                kickoff_time TEXT,
                venue TEXT,
                attendance INTEGER,
                referee TEXT,
                weather_conditions TEXT,
                
                -- Advanced Statistics
                home_possession REAL,
                away_possession REAL,
                
                -- Shots
                home_shots_total INTEGER,
                away_shots_total INTEGER,
                home_shots_on_target INTEGER,
                away_shots_on_target INTEGER,
                home_shots_off_target INTEGER,
                away_shots_off_target INTEGER,
                home_shots_blocked INTEGER,
                away_shots_blocked INTEGER,
                
                -- Expected Goals
                home_xg REAL,
                away_xg REAL,
                home_xg_ot REAL,  -- xG on target
                away_xg_ot REAL,
                
                -- Passing
                home_passes INTEGER,
                away_passes INTEGER,
                home_pass_accuracy REAL,
                away_pass_accuracy REAL,
                home_passes_final_third INTEGER,
                away_passes_final_third INTEGER,
                home_long_passes INTEGER,
                away_long_passes INTEGER,
                
                -- Set Pieces
                home_corners INTEGER,
                away_corners INTEGER,
                home_corner_accuracy REAL,
                away_corner_accuracy REAL,
                home_free_kicks INTEGER,
                away_free_kicks INTEGER,
                home_throw_ins INTEGER,
                away_throw_ins INTEGER,
                
                -- Disciplinary
                home_fouls INTEGER,
                away_fouls INTEGER,
                home_yellow_cards INTEGER,
                away_yellow_cards INTEGER,
                home_red_cards INTEGER,
                away_red_cards INTEGER,
                
                -- Defensive Actions
                home_tackles INTEGER,
                away_tackles INTEGER,
                home_interceptions INTEGER,
                away_interceptions INTEGER,
                home_clearances INTEGER,
                away_clearances INTEGER,
                home_blocks INTEGER,
                away_blocks INTEGER,
                
                -- Offsides and Other
                home_offsides INTEGER,
                away_offsides INTEGER,
                home_saves INTEGER,
                away_saves INTEGER,
                
                -- Tactical Data
                home_formation TEXT,
                away_formation TEXT,
                home_avg_position_x REAL,
                home_avg_position_y REAL,
                away_avg_position_x REAL,
                away_avg_position_y REAL,
                
                -- Data Quality and Sources
                data_completeness_score INTEGER,  -- 1-100 scale
                primary_data_source TEXT,
                secondary_data_source TEXT,
                last_updated TEXT,
                
                -- Indexes for fast queries
                UNIQUE(league_name, season, home_team, away_team, match_date)
            )
        ''')
        
        # Enhanced team statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_season_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                country TEXT NOT NULL,
                league_name TEXT NOT NULL,
                season TEXT NOT NULL,
                tier INTEGER,
                
                -- Basic Stats
                matches_played INTEGER,
                wins INTEGER,
                draws INTEGER,
                losses INTEGER,
                points INTEGER,
                
                -- Goals
                goals_for INTEGER,
                goals_against INTEGER,
                goal_difference INTEGER,
                goals_for_home INTEGER,
                goals_for_away INTEGER,
                goals_against_home INTEGER,
                goals_against_away INTEGER,
                
                -- Advanced Metrics
                avg_possession REAL,
                avg_shots_for REAL,
                avg_shots_against REAL,
                avg_shots_on_target_for REAL,
                avg_shots_on_target_against REAL,
                
                -- Expected Goals
                total_xg_for REAL,
                total_xg_against REAL,
                avg_xg_for REAL,
                avg_xg_against REAL,
                
                -- Set Pieces
                total_corners_for INTEGER,
                total_corners_against INTEGER,
                corner_conversion_rate REAL,
                
                -- Disciplinary
                total_cards INTEGER,
                yellow_cards INTEGER,
                red_cards INTEGER,
                fouls_committed INTEGER,
                fouls_suffered INTEGER,
                
                -- Form Indicators
                last_5_form TEXT,
                last_10_form TEXT,
                home_form TEXT,
                away_form TEXT,
                
                -- Strength Ratings
                attack_strength REAL,
                defense_strength REAL,
                overall_rating REAL,
                
                last_updated TEXT,
                
                UNIQUE(team_name, league_name, season)
            )
        ''')
        
        # Player statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_season_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                team_name TEXT NOT NULL,
                league_name TEXT NOT NULL,
                season TEXT NOT NULL,
                position TEXT,
                
                -- Appearance Data
                matches_played INTEGER,
                minutes_played INTEGER,
                starts INTEGER,
                substitute_appearances INTEGER,
                
                -- Scoring
                goals INTEGER,
                penalties_scored INTEGER,
                assists INTEGER,
                
                -- Shooting
                shots INTEGER,
                shots_on_target INTEGER,
                shot_accuracy REAL,
                
                -- Passing
                passes INTEGER,
                pass_accuracy REAL,
                key_passes INTEGER,
                crosses INTEGER,
                
                -- Defensive
                tackles INTEGER,
                interceptions INTEGER,
                clearances INTEGER,
                
                -- Disciplinary
                yellow_cards INTEGER,
                red_cards INTEGER,
                
                -- Advanced Metrics
                xg REAL,
                xa REAL,  -- Expected assists
                progressive_passes INTEGER,
                
                last_updated TEXT,
                
                UNIQUE(player_name, team_name, league_name, season)
            )
        ''')
        
        # Collection progress tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                league_name TEXT NOT NULL,
                season TEXT NOT NULL,
                collection_date TEXT,
                
                -- Progress metrics
                target_matches INTEGER,
                collected_matches INTEGER,
                success_rate REAL,
                
                -- Data quality
                detailed_stats_available INTEGER,
                basic_stats_only INTEGER,
                failed_collections INTEGER,
                
                -- Sources used
                primary_source TEXT,
                fallback_sources TEXT,
                
                collection_duration_minutes REAL,
                status TEXT,  -- 'completed', 'in_progress', 'failed'
                
                UNIQUE(league_name, season)
            )
        ''')
        
        self.conn.commit()
        self.logger.info(" Comprehensive database schema created successfully!")
    
    def calculate_total_target_matches(self) -> int:
        """Calculate total expected matches across all leagues and seasons"""
        total = 0
        for country_data in self.league_structure.values():
            for league_data in country_data['leagues'].values():
                matches_per_season = league_data['expected_matches_per_season']
                seasons = len(league_data['seasons'])
                total += matches_per_season * seasons
        
        self.total_target_matches = total
        self.logger.info(f" Target: {total:,} matches across {self.get_total_league_seasons()} league-seasons")
        return total
    
    def get_total_league_seasons(self) -> int:
        """Count total league-seasons to collect"""
        total = 0
        for country_data in self.league_structure.values():
            for league_data in country_data['leagues'].values():
                total += len(league_data['seasons'])
        return total
    
    def collect_football_data_org(self, league_id: int, season: str, league_name: str, country: str) -> List[Dict]:
        """Collect data from Football-Data.org API"""
        if not self.football_data_api:
            return []
        
        url = f"https://api.football-data.org/v4/competitions/{league_id}/matches"
        headers = {"X-Auth-Token": self.football_data_api}
        params = {"season": season}
        
        try:
            time.sleep(self.request_delay)
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                # Filter completed matches
                completed_matches = [m for m in matches if m['status'] == 'FINISHED']
                
                self.logger.info(f" Football-Data.org: {len(completed_matches)} matches for {league_name} {season}")
                
                # Convert to our format
                formatted_matches = []
                for match in completed_matches:
                    formatted_match = {
                        'id': f"fd_{match['id']}",
                        'country': country,
                        'league_name': league_name,
                        'season': season,
                        'home_team': match['homeTeam']['name'],
                        'away_team': match['awayTeam']['name'],
                        'home_score': match['score']['fullTime']['home'],
                        'away_score': match['score']['fullTime']['away'],
                        'match_date': match['utcDate'],
                        'venue': match.get('venue'),
                        'referee': ', '.join([ref.get('name', '') for ref in match.get('referees', [])]),
                        'data_completeness_score': 60,  # Football-Data.org has basic data
                        'primary_data_source': 'football-data.org'
                    }
                    formatted_matches.append(formatted_match)
                
                return formatted_matches
                
            else:
                self.logger.warning(f" Football-Data.org API error {response.status_code} for {league_name}")
                return []
                
        except Exception as e:
            self.logger.error(f" Football-Data.org collection failed for {league_name} {season}: {e}")
            return []
    
    def collect_fbref_data(self, fbref_name: str, season: str, league_name: str, country: str) -> List[Dict]:
        """Collect data from FBref via soccerdata (when available)"""
        try:
            # Only try FBref for leagues it supports
            supported_leagues = ['ENG-Premier League', 'ESP-La Liga', 'GER-Bundesliga', 'ITA-Serie A', 'FRA-Ligue 1']
            
            if fbref_name not in supported_leagues:
                return []
            
            self.logger.info(f" Attempting FBref collection for {fbref_name} {season}")
            
            # Convert season format (2023 -> 2023-24)
            season_formatted = f"{season}-{str(int(season)+1)[-2:]}"
            
            fbref = sd.FBref(leagues=fbref_name, seasons=season_formatted)
            
            # Get schedule data
            schedule = fbref.read_schedule()
            
            if schedule.empty:
                return []
            
            # Filter completed matches
            completed = schedule[schedule['home_score'].notna() & schedule['away_score'].notna()]
            
            if completed.empty:
                return []
            
            self.logger.info(f" FBref: {len(completed)} matches for {fbref_name} {season}")
            
            # Try to get additional stats
            try:
                team_stats = fbref.read_team_season_stats()
            except:
                team_stats = None
            
            # Convert to our format with enhanced data
            formatted_matches = []
            for idx, match in completed.iterrows():
                formatted_match = {
                    'id': f"fbref_{idx}",
                    'country': country,
                    'league_name': league_name,
                    'season': season,
                    'home_team': str(match.get('home_team', '')),
                    'away_team': str(match.get('away_team', '')),
                    'home_score': int(match['home_score']) if pd.notna(match['home_score']) else None,
                    'away_score': int(match['away_score']) if pd.notna(match['away_score']) else None,
                    'match_date': str(match.get('date', '')),
                    'data_completeness_score': 85,  # FBref has detailed data
                    'primary_data_source': 'fbref'
                }
                formatted_matches.append(formatted_match)
            
            return formatted_matches
            
        except Exception as e:
            self.logger.warning(f" FBref collection failed for {fbref_name} {season}: {e}")
            return []
    
    def store_matches(self, matches: List[Dict]):
        """Store matches in database with conflict resolution"""
        if not matches:
            return
        
        cursor = self.conn.cursor()
        stored_count = 0
        
        for match in matches:
            try:
                # Prepare data for insertion
                values = (
                    match.get('id'),
                    match.get('country'),
                    match.get('league_name'),
                    1,  # competition_tier - we'll update this later
                    match.get('season'),
                    match.get('matchday'),
                    match.get('home_team'),
                    match.get('away_team'),
                    match.get('home_score'),
                    match.get('away_score'),
                    match.get('home_score_ht'),
                    match.get('away_score_ht'),
                    match.get('match_date'),
                    match.get('kickoff_time'),
                    match.get('venue'),
                    match.get('attendance'),
                    match.get('referee'),
                    match.get('weather_conditions'),
                    match.get('home_possession'),
                    match.get('away_possession'),
                    match.get('home_shots_total'),
                    match.get('away_shots_total'),
                    match.get('home_shots_on_target'),
                    match.get('away_shots_on_target'),
                    match.get('home_corners'),
                    match.get('away_corners'),
                    match.get('home_fouls'),
                    match.get('away_fouls'),
                    match.get('home_yellow_cards'),
                    match.get('away_yellow_cards'),
                    match.get('home_red_cards'),
                    match.get('away_red_cards'),
                    match.get('home_offsides'),
                    match.get('away_offsides'),
                    match.get('data_completeness_score', 50),
                    match.get('primary_data_source'),
                    match.get('secondary_data_source'),
                    datetime.now().isoformat()
                )
                
                cursor.execute('''
                    INSERT OR REPLACE INTO comprehensive_matches 
                    (id, country, league_name, competition_tier, season, matchday,
                     home_team, away_team, home_score, away_score, home_score_ht, away_score_ht,
                     match_date, kickoff_time, venue, attendance, referee, weather_conditions,
                     home_possession, away_possession, home_shots_total, away_shots_total,
                     home_shots_on_target, away_shots_on_target, home_corners, away_corners,
                     home_fouls, away_fouls, home_yellow_cards, away_yellow_cards,
                     home_red_cards, away_red_cards, home_offsides, away_offsides,
                     data_completeness_score, primary_data_source, secondary_data_source, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', values)
                
                stored_count += 1
                
            except Exception as e:
                self.logger.error(f"Error storing match: {e}")
                continue
        
        self.conn.commit()
        self.collected_matches += stored_count
        self.logger.info(f" Stored {stored_count} matches in database")
    
    def collect_league_season(self, country: str, league_key: str, league_data: Dict) -> Dict:
        """Collect all data for a specific league and season"""
        league_name = league_data.get('fbref_name', league_key)
        results = {
            'country': country,
            'league_key': league_key,
            'league_name': league_name,
            'seasons_collected': [],
            'total_matches': 0,
            'sources_used': []
        }
        
        for season in league_data['seasons']:
            season_start_time = time.time()
            season_matches = []
            
            self.logger.info(f" Starting collection: {country.upper()} - {league_name} - {season}")
            
            # Try multiple data sources
            sources_attempted = []
            
            # 1. Try Football-Data.org API first (most reliable)
            if 'football_data_id' in league_data:
                fd_matches = self.collect_football_data_org(
                    league_data['football_data_id'], 
                    season, 
                    league_name, 
                    country
                )
                if fd_matches:
                    season_matches.extend(fd_matches)
                    sources_attempted.append('football-data.org')
            
            # 2. Try FBref for enhanced data (for top leagues)
            if league_data.get('priority') == 1:  # Only for tier 1 leagues
                fbref_matches = self.collect_fbref_data(
                    league_data['fbref_name'],
                    season,
                    league_name,
                    country
                )
                if fbref_matches:
                    # Merge or supplement existing data
                    season_matches.extend(fbref_matches)
                    sources_attempted.append('fbref')
            
            # Store matches for this season
            if season_matches:
                self.store_matches(season_matches)
                
                # Update progress
                season_duration = (time.time() - season_start_time) / 60
                self.update_collection_progress(
                    country, league_name, season, 
                    len(season_matches), sources_attempted, season_duration
                )
                
                results['seasons_collected'].append(season)
                results['total_matches'] += len(season_matches)
                results['sources_used'].extend(sources_attempted)
                
                self.logger.info(f" {league_name} {season}: {len(season_matches)} matches in {season_duration:.1f}m")
            else:
                self.logger.warning(f" No matches collected for {league_name} {season}")
                self.failed_collections += 1
            
            # Rate limiting between seasons
            time.sleep(self.batch_delay)
        
        return results
    
    def update_collection_progress(self, country: str, league_name: str, season: str, 
                                 matches_collected: int, sources_used: List[str], duration: float):
        """Update collection progress in database"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO collection_progress 
            (country, league_name, season, collection_date, collected_matches,
             primary_source, fallback_sources, collection_duration_minutes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            country, league_name, season, datetime.now().isoformat(),
            matches_collected, sources_used[0] if sources_used else 'none',
            ','.join(sources_used[1:]) if len(sources_used) > 1 else '',
            duration, 'completed' if matches_collected > 0 else 'failed'
        ))
        
        self.conn.commit()
    
    def run_comprehensive_collection(self):
        """Run the complete comprehensive data collection"""
        collection_start_time = time.time()
        
        self.logger.info(" STARTING COMPREHENSIVE FOOTBALL DATA COLLECTION")
        self.logger.info("=" * 80)
        
        # Calculate targets
        total_target = self.calculate_total_target_matches()
        total_league_seasons = self.get_total_league_seasons()
        
        self.logger.info(f" Collection Plan:")
        self.logger.info(f"   • Countries: 5 (England, Spain, Germany, Italy, France)")
        self.logger.info(f"   • Leagues: 12 total")
        self.logger.info(f"   • Seasons: 5 (2020-2024)")
        self.logger.info(f"   • League-seasons: {total_league_seasons}")
        self.logger.info(f"   • Target matches: {total_target:,}")
        self.logger.info("=" * 80)
        
        country_results = {}
        
        # Process each country
        for country_key, country_data in self.league_structure.items():
            country_start_time = time.time()
            self.logger.info(f"\n STARTING {country_key.upper()} COLLECTION")
            
            country_results[country_key] = {
                'leagues': {},
                'total_matches': 0,
                'completion_rate': 0
            }
            
            # Process each league in the country
            for league_key, league_data in country_data['leagues'].items():
                league_results = self.collect_league_season(country_key, league_key, league_data)
                country_results[country_key]['leagues'][league_key] = league_results
                country_results[country_key]['total_matches'] += league_results['total_matches']
            
            country_duration = (time.time() - country_start_time) / 60
            self.logger.info(f" {country_key.upper()} COMPLETED in {country_duration:.1f} minutes")
            self.logger.info(f"   Total matches: {country_results[country_key]['total_matches']}")
        
        # Final summary
        total_duration = (time.time() - collection_start_time) / 60
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info(" COMPREHENSIVE COLLECTION COMPLETED!")
        self.logger.info("=" * 80)
        self.logger.info(f" FINAL STATISTICS:")
        self.logger.info(f"   • Total duration: {total_duration:.1f} minutes ({total_duration/60:.1f} hours)")
        self.logger.info(f"   • Target matches: {total_target:,}")
        self.logger.info(f"   • Collected matches: {self.collected_matches:,}")
        self.logger.info(f"   • Success rate: {(self.collected_matches/total_target)*100:.1f}%")
        self.logger.info(f"   • Failed collections: {self.failed_collections}")
        
        # Country breakdown
        for country, results in country_results.items():
            self.logger.info(f"   • {country.upper()}: {results['total_matches']:,} matches")
        
        self.logger.info("=" * 80)
        
        # Generate final report
        self.generate_collection_report(country_results)
        
        return country_results
    
    def generate_collection_report(self, results: Dict):
        """Generate detailed collection report"""
        cursor = self.conn.cursor()
        
        # Get database statistics
        cursor.execute("SELECT COUNT(*) FROM comprehensive_matches")
        total_in_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM comprehensive_matches WHERE home_score IS NOT NULL")
        completed_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT league_name) FROM comprehensive_matches")
        leagues_collected = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT season) FROM comprehensive_matches")
        seasons_collected = cursor.fetchone()[0]
        
        # Create report
        report = f"""
COMPREHENSIVE FOOTBALL DATA COLLECTION REPORT
==============================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DATABASE STATISTICS:
• Total matches in database: {total_in_db:,}
• Completed matches with scores: {completed_matches:,}
• Leagues collected: {leagues_collected}
• Seasons covered: {seasons_collected}

COLLECTION BREAKDOWN BY COUNTRY:
"""
        
        for country, country_results in results.items():
            report += f"\n{country.upper()}:\n"
            for league_key, league_results in country_results['leagues'].items():
                report += f"  • {league_results['league_name']}: {league_results['total_matches']} matches\n"
                report += f"    Seasons: {', '.join(league_results['seasons_collected'])}\n"
                report += f"    Sources: {', '.join(set(league_results['sources_used']))}\n"
        
        report += f"""
NEXT STEPS:
1. Run model training with enhanced dataset
2. Implement advanced feature engineering
3. Add player statistics collection
4. Set up automated daily updates

Database file: comprehensive_football_data.db
Log file: comprehensive_collector.log
"""
        
        # Save report
        with open('collection_report.txt', 'w') as f:
            f.write(report)
        
        self.logger.info(" Collection report saved to 'collection_report.txt'")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info(" Database connection closed")

# Configuration for comprehensive collection
comprehensive_config = {
    'football_data_api_key': '751bc97db5fa4f4ba08955bdda5a07d0',  # Your existing key
    'odds_api_key': '',  # Optional - for future odds collection
    'request_delay': 2,  # 2 seconds between API calls
    'batch_delay': 5,    # 5 seconds between seasons
    'max_retries': 3
}

if __name__ == "__main__":
    print("🚀 COMPREHENSIVE FOOTBALL DATA COLLECTION")
    print("Target: 25,000+ matches across 12 leagues and 5 seasons")
    print("=" * 60)
    
    collector = ComprehensiveFootballCollector(comprehensive_config)
    
    try:
        results = collector.run_comprehensive_collection()
        
        print("\n✅ COLLECTION COMPLETED SUCCESSFULLY!")
        print("📊 Check 'collection_report.txt' for detailed results")
        print("💾 Database: 'comprehensive_football_data.db'")
        print("📋 Logs: 'comprehensive_collector.log'")
        
    except KeyboardInterrupt:
        print("\n⏹️ Collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        collector.close()