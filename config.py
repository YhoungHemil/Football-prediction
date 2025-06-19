# config.py
"""Configuration file for the football prediction system"""

import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class APIConfig:
    """API configuration"""
    # Football-Data.org API
    football_data_api_key: str = "751bc97db5fa4f4ba08955bdda5a07d0"
    
    # The Odds API (free tier)
    odds_api_key: str = "0a37c3f215f3a61ba0ed12df8db98ed1"  # Get from https://the-odds-api.com/
    
    # Rate limiting
    request_delay: int = 3
    retry_delay: int = 30
    max_retries: int = 3

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "enhanced_football_data.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24

@dataclass
class LeagueConfig:
    """League configuration"""
    leagues: Dict[str, Dict] = None
    
    def __post_init__(self):
        if self.leagues is None:
            self.leagues = {
                # England
                'ENG-Premier League': {
                    'fbref_name': 'ENG-Premier League',
                    'odds_key': 'soccer_epl',
                    'priority': 1,
                    'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
                },
                'ENG-Championship': {
                    'fbref_name': 'ENG-Championship',
                    'odds_key': 'soccer_efl_champ',
                    'priority': 2,
                    'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
                },
                'ENG-League One': {
                    'fbref_name': 'ENG-League One',
                    'odds_key': None,
                    'priority': 3,
                    'seasons': ['2021-22', '2022-23', '2023-24']
                },
                'ENG-League Two': {
                    'fbref_name': 'ENG-League Two',
                    'odds_key': None,
                    'priority': 4,
                    'seasons': ['2021-22', '2022-23', '2023-24']
                },
                
                # Spain
                'ESP-La Liga': {
                    'fbref_name': 'ESP-La Liga',
                    'odds_key': 'soccer_spain_la_liga',
                    'priority': 1,
                    'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
                },
                'ESP-Segunda División': {
                    'fbref_name': 'ESP-Segunda División',
                    'odds_key': None,
                    'priority': 2,
                    'seasons': ['2021-22', '2022-23', '2023-24']
                },
                
                # Germany
                'GER-Bundesliga': {
                    'fbref_name': 'GER-Bundesliga',
                    'odds_key': 'soccer_germany_bundesliga',
                    'priority': 1,
                    'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
                },
                'GER-2. Bundesliga': {
                    'fbref_name': 'GER-2. Bundesliga',
                    'odds_key': None,
                    'priority': 2,
                    'seasons': ['2021-22', '2022-23', '2023-24']
                },
                
                # Italy
                'ITA-Serie A': {
                    'fbref_name': 'ITA-Serie A',
                    'odds_key': 'soccer_italy_serie_a',
                    'priority': 1,
                    'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
                },
                'ITA-Serie B': {
                    'fbref_name': 'ITA-Serie B',
                    'odds_key': None,
                    'priority': 2,
                    'seasons': ['2021-22', '2022-23', '2023-24']
                },
                
                # France
                'FRA-Ligue 1': {
                    'fbref_name': 'FRA-Ligue 1',
                    'odds_key': 'soccer_france_ligue_one',
                    'priority': 1,
                    'seasons': ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
                },
                'FRA-Ligue 2': {
                    'fbref_name': 'FRA-Ligue 2',
                    'odds_key': None,
                    'priority': 2,
                    'seasons': ['2021-22', '2022-23', '2023-24']
                }
            }

@dataclass
class ModelConfig:
    """Model configuration"""
    # Training parameters
    test_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 5
    
    # Model parameters
    rf_n_estimators: int = 100
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.1
    
    # Feature engineering
    form_window: int = 5  # Last N matches for form
    strength_window: int = 10  # Last N matches for strength calculation
    h2h_limit: int = 10  # Max H2H matches to consider

@dataclass
class PredictionConfig:
    """Prediction configuration"""
    # Confidence thresholds
    min_confidence: float = 0.6
    high_confidence: float = 0.8
    
    # Prediction types
    enabled_predictions: List[str] = None
    
    def __post_init__(self):
        if self.enabled_predictions is None:
            self.enabled_predictions = [
                'match_outcome',
                'over_under_2_5',
                'btts',
                'corners_over_9_5',
                'cards_over_3_5'
            ]

# Main configuration class
class Config:
    """Main configuration class"""
    def __init__(self):
        self.api = APIConfig()
        self.database = DatabaseConfig()
        self.leagues = LeagueConfig()
        self.models = ModelConfig()
        self.predictions = PredictionConfig()
    
    def update_from_env(self):
        """Update configuration from environment variables"""
        # API keys from environment
        self.api.odds_api_key = os.getenv('ODDS_API_KEY', self.api.odds_api_key)
        self.api.football_data_api_key = os.getenv('FOOTBALL_DATA_API_KEY', self.api.football_data_api_key)
        
        # Database path
        self.database.db_path = os.getenv('DB_PATH', self.database.db_path)
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary"""
        return {
            'api': self.api.__dict__,
            'database': self.database.__dict__,
            'models': self.models.__dict__,
            'predictions': self.predictions.__dict__
        }

# Create global config instance
config = Config()
config.update_from_env()
