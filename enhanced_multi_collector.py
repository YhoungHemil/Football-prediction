import requests
import pandas as pd
import sqlite3
import json
import time
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import soccerdata as sd
from dataclasses import dataclass

@dataclass
class MatchData:
    """Standardized match data structure"""
    match_id: str
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    match_date: Optional[str] = None
    competition: Optional[str] = None
    season: Optional[str] = None
    # Advanced stats
    home_possession: Optional[float] = None
    away_possession: Optional[float] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_cards: Optional[int] = None
    away_cards: Optional[int] = None
    home_offsides: Optional[int] = None
    away_offsides: Optional[int] = None
    data_source: Optional[str] = None
    data_quality: Optional[str] = None

class MultiSourceFootballCollector:
    """Enhanced football data collector with multiple sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.setup_logging()
        self.setup_user_agents()
        self.setup_database()
        self.setup_data_sources()
        
        # Rate limiting
        self.request_delay = config.get('request_delay', 3)
        self.retry_delay = config.get('retry_delay', 30)
        self.max_retries = config.get('max_retries', 3)
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('multi_collector.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_user_agents(self):
        """Setup rotating user agents"""
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
    
    def get_random_headers(self) -> Dict[str, str]:
        """Get random headers for requests"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def setup_database(self):
        """Setup enhanced database schema"""
        self.conn = sqlite3.connect('enhanced_football_data.db')
        cursor = self.conn.cursor()
        
        # Enhanced matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_matches (
                id TEXT PRIMARY KEY,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                match_date TEXT,
                competition TEXT,
                season TEXT,
                matchday INTEGER,
                venue TEXT,
                referee TEXT,
                
                -- Advanced statistics
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
                
                -- Expected goals
                home_xg REAL,
                away_xg REAL,
                
                -- Tactical data
                home_passes INTEGER,
                away_passes INTEGER,
                home_pass_accuracy REAL,
                away_pass_accuracy REAL,
                home_crosses INTEGER,
                away_crosses INTEGER,
                
                -- Data metadata
                data_source TEXT,
                data_quality TEXT,
                last_updated TEXT,
                
                UNIQUE(home_team, away_team, match_date, competition)
            )
        ''')
        
        # Player statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                team TEXT NOT NULL,
                position TEXT,
                match_id TEXT,
                
                -- Basic stats
                minutes_played INTEGER,
                goals INTEGER,
                assists INTEGER,
                shots INTEGER,
                shots_on_target INTEGER,
                
                -- Passing
                passes INTEGER,
                pass_accuracy REAL,
                key_passes INTEGER,
                
                -- Defensive
                tackles INTEGER,
                interceptions INTEGER,
                clearances INTEGER,
                
                -- Disciplinary
                yellow_cards INTEGER,
                red_cards INTEGER,
                fouls_committed INTEGER,
                fouls_suffered INTEGER,
                
                -- Advanced metrics
                xg REAL,
                xa REAL,
                
                last_updated TEXT,
                FOREIGN KEY (match_id) REFERENCES enhanced_matches (id)
            )
        ''')
        
        # Team form table (enhanced)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_form_enhanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                competition TEXT NOT NULL,
                season TEXT NOT NULL,
                match_date TEXT,
                opponent TEXT,
                venue TEXT,
                
                -- Results
                goals_for INTEGER,
                goals_against INTEGER,
                result TEXT,
                points INTEGER,
                
                -- Advanced metrics
                xg_for REAL,
                xg_against REAL,
                possession REAL,
                shots_for INTEGER,
                shots_against INTEGER,
                corners_for INTEGER,
                corners_against INTEGER,
                cards_for INTEGER,
                cards_against INTEGER,
                
                -- Form indicators
                last_5_form TEXT,
                last_10_form TEXT,
                
                last_updated TEXT
            )
        ''')
        
        # Odds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_odds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                bookmaker TEXT NOT NULL,
                
                -- Main markets
                home_win_odds REAL,
                draw_odds REAL,
                away_win_odds REAL,
                
                -- Goal markets
                over_2_5_odds REAL,
                under_2_5_odds REAL,
                over_1_5_odds REAL,
                under_1_5_odds REAL,
                over_3_5_odds REAL,
                under_3_5_odds REAL,
                
                -- Other markets
                btts_yes_odds REAL,
                btts_no_odds REAL,
                
                -- First half markets
                fh_home_win_odds REAL,
                fh_draw_odds REAL,
                fh_away_win_odds REAL,
                fh_over_1_5_odds REAL,
                fh_under_1_5_odds REAL,
                
                odds_timestamp TEXT,
                last_updated TEXT,
                
                FOREIGN KEY (match_id) REFERENCES enhanced_matches (id)
            )
        ''')
        
        # Predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_version TEXT,
                
                -- Predictions
                home_win_prob REAL,
                draw_prob REAL,
                away_win_prob REAL,
                over_2_5_prob REAL,
                under_2_5_prob REAL,
                btts_prob REAL,
                
                -- Expected values
                predicted_home_score REAL,
                predicted_away_score REAL,
                predicted_total_goals REAL,
                
                -- Confidence metrics
                confidence_score REAL,
                prediction_date TEXT,
                
                FOREIGN KEY (match_id) REFERENCES enhanced_matches (id)
            )
        ''')
        
        self.conn.commit()
        self.logger.info("Enhanced database schema created successfully!")
    
    def setup_data_sources(self):
        """Initialize data sources"""
        self.sources = {}
        
        # Football-Data.org API
        if 'football_data_api_key' in self.config:
            self.sources['football_data'] = {
                'api_key': self.config['football_data_api_key'],
                'base_url': 'https://api.football-data.org/v4',
                'priority': 3
            }
        
        # The Odds API
        if 'odds_api_key' in self.config:
            self.sources['odds_api'] = {
                'api_key': self.config['odds_api_key'],
                'base_url': 'https://api.the-odds-api.com/v4',
                'priority': 1
            }
        
        # SoccerData (FBref, SofaScore, etc.)
        self.sources['soccerdata'] = {
            'priority': 1
        }
        
        self.logger.info(f"Initialized {len(self.sources)} data sources")
    
    def make_api_request(self, url: str, headers: Dict = None, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling and rate limiting"""
        if headers is None:
            headers = self.get_random_headers()
        
        self.total_requests += 1
        
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                time.sleep(self.request_delay)
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    self.successful_requests += 1
                    return response.json()
                elif response.status_code == 429:
                    self.logger.warning(f"Rate limit hit, waiting {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    self.logger.warning(f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        self.failed_requests += 1
        return None
    
    def get_fbref_data(self, league: str, season: str) -> List[MatchData]:
        """Get data from FBref via soccerdata"""
        try:
            self.logger.info(f"Collecting FBref data for {league} {season}")
            
            # Initialize FBref scraper
            fbref = sd.FBref(leagues=league, seasons=season)
            
            # Get schedule
            schedule = fbref.read_schedule()
            
            # Get team stats for context
            try:
                team_stats = fbref.read_team_season_stats()
            except:
                team_stats = None
            
            matches = []
            for _, match in schedule.iterrows():
                match_data = MatchData(
                    match_id=f"fbref_{match.get('game_id', '')}",
                    home_team=match.get('home_team', ''),
                    away_team=match.get('away_team', ''),
                    home_score=match.get('home_score'),
                    away_score=match.get('away_score'),
                    match_date=str(match.get('date', '')),
                    competition=league,
                    season=season,
                    data_source='fbref',
                    data_quality='detailed'
                )
                matches.append(match_data)
            
            self.logger.info(f"Collected {len(matches)} matches from FBref")
            return matches
            
        except Exception as e:
            self.logger.error(f"FBref data collection failed: {e}")
            return []
    
    def get_odds_data(self, sport='soccer_epl') -> Dict:
        """Get odds data from The Odds API"""
        if 'odds_api' not in self.sources:
            return {}
        
        try:
            url = f"{self.sources['odds_api']['base_url']}/sports/{sport}/odds"
            params = {
                'apiKey': self.sources['odds_api']['api_key'],
                'regions': 'uk,eu',
                'markets': 'h2h,totals',
                'oddsFormat': 'decimal'
            }
            
            data = self.make_api_request(url, params=params)
            if data:
                self.logger.info(f"Collected odds for {len(data)} matches")
                return data
            
        except Exception as e:
            self.logger.error(f"Odds data collection failed: {e}")
        
        return {}
    
    def store_match_data(self, match_data: MatchData):
        """Store match data in database"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO enhanced_matches 
            (id, home_team, away_team, home_score, away_score, match_date, 
             competition, season, home_corners, away_corners, home_yellow_cards, 
             away_yellow_cards, data_source, data_quality, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            match_data.match_id,
            match_data.home_team,
            match_data.away_team,
            match_data.home_score,
            match_data.away_score,
            match_data.match_date,
            match_data.competition,
            match_data.season,
            match_data.home_corners,
            match_data.away_corners,
            match_data.home_cards,
            match_data.away_cards,
            match_data.data_source,
            match_data.data_quality,
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
    
    def collect_league_data(self, league_config: Dict):
        """Collect data for a specific league"""
        league_name = league_config['name']
        seasons = league_config['seasons']
        
        self.logger.info(f"Starting collection for {league_name}")
        
        for season in seasons:
            # Primary: FBref data
            fbref_matches = self.get_fbref_data(league_name, season)
            for match in fbref_matches:
                self.store_match_data(match)
            
            # Secondary: Get odds if available
            if 'odds_sport_key' in league_config:
                odds_data = self.get_odds_data(league_config['odds_sport_key'])
                # Process and store odds...
            
            time.sleep(10)  # Pause between seasons
    
    def run_full_collection(self):
        """Run complete data collection"""
        # Define leagues to collect
        leagues_config = [
            {
                'name': 'ENG-Premier League',
                'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'],
                'odds_sport_key': 'soccer_epl'
            },
            {
                'name': 'ENG-Championship',
                'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'],
                'odds_sport_key': 'soccer_efl_champ'
            },
            {
                'name': 'GER-Bundesliga',
                'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'],
                'odds_sport_key': 'soccer_germany_bundesliga'
            },
            {
                'name': 'ITA-Serie A',
                'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'],
                'odds_sport_key': 'soccer_italy_serie_a'
            },
            {
                'name': 'ESP-La Liga',
                'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'],
                'odds_sport_key': 'soccer_spain_la_liga'
            },
            {
                'name': 'FRA-Ligue 1',
                'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'],
                'odds_sport_key': 'soccer_france_ligue_one'
            }
        ]
        
        start_time = time.time()
        
        for league_config in leagues_config:
            try:
                self.collect_league_data(league_config)
                self.logger.info(f"Completed collection for {league_config['name']}")
            except Exception as e:
                self.logger.error(f"Failed to collect {league_config['name']}: {e}")
                continue
        
        duration = (time.time() - start_time) / 60
        self.logger.info(f"Full collection completed in {duration:.2f} minutes")
        self.logger.info(f"API Statistics: {self.successful_requests} success, {self.failed_requests} failed")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

# Configuration
config = {
    'football_data_api_key': '751bc97db5fa4f4ba08955bdda5a07d0',  # Your existing key
    'odds_api_key': 'YOUR_ODDS_API_KEY',  # Get from the-odds-api.com
    'request_delay': 3,
    'retry_delay': 30,
    'max_retries': 3
}

if __name__ == "__main__":
    collector = MultiSourceFootballCollector(config)
    
    try:
        # Run full collection
        collector.run_full_collection()
        
        print("✅ Enhanced data collection completed!")
        print("📊 Database: 'enhanced_football_data.db'")
        print("📝 Logs: 'multi_collector.log'")
        
    except KeyboardInterrupt:
        print("\n⏹️ Collection stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        collector.close()