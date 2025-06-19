import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math
from dataclasses import dataclass

@dataclass
class FeatureWeights:
    """Dynamic feature weights based on match context"""
    home_advantage: float = 1.0
    recent_form: float = 1.0
    team_strength_gap: float = 1.0
    h2h_record: float = 1.0
    league_position: float = 1.0
    rest_days: float = 1.0
    motivation: float = 1.0
    tactical_formation: float = 1.0
    weather: float = 1.0
    crowd_size: float = 1.0

class AdvancedFootballFeatures:
    """Advanced weighted feature engineering for football predictions"""
    
    def __init__(self, db_path: str = 'comprehensive_football_data.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        
        # Feature weight configurations
        self.base_weights = {
            'home_advantage': 3.5,      # High impact
            'recent_form': 3.0,         # High impact  
            'team_strength_gap': 3.2,   # High impact
            'h2h_record': 2.8,          # High impact
            'league_position': 2.0,     # Medium impact
            'rest_days': 1.5,           # Medium impact
            'motivation': 1.8,          # Medium impact
            'tactical_formation': 0.8,  # Low impact
            'weather': 0.5,             # Low impact
            'crowd_size': 0.6           # Low impact
        }
        
        # ELO rating system parameters
        self.initial_elo = 1500
        self.k_factor = 30
        
        # Form calculation parameters
        self.form_matches = 5
        self.strength_matches = 10
        
    def calculate_elo_ratings(self) -> Dict[str, float]:
        """Calculate ELO ratings for all teams"""
        print("🎯 Calculating ELO ratings for all teams...")
        
        # Get all completed matches ordered by date
        query = '''
        SELECT home_team, away_team, home_score, away_score, match_date, league_name
        FROM comprehensive_matches 
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        ORDER BY match_date ASC
        '''
        
        matches_df = pd.read_sql_query(query, self.conn)
        
        # Initialize ELO ratings for all teams
        teams = set(matches_df['home_team'].unique()) | set(matches_df['away_team'].unique())
        elo_ratings = {team: self.initial_elo for team in teams}
        
        # Process matches chronologically
        for _, match in matches_df.iterrows():
            home_team = match['home_team']
            away_team = match['away_team']
            home_score = match['home_score']
            away_score = match['away_score']
            
            # Determine match result
            if home_score > away_score:
                result = 1  # Home win
            elif home_score < away_score:
                result = 0  # Away win
            else:
                result = 0.5  # Draw
            
            # Get current ratings
            home_elo = elo_ratings[home_team]
            away_elo = elo_ratings[away_team]
            
            # Expected score for home team
            expected_home = 1 / (1 + 10**((away_elo - home_elo) / 400))
            
            # Update ratings
            elo_ratings[home_team] += self.k_factor * (result - expected_home)
            elo_ratings[away_team] += self.k_factor * ((1 - result) - (1 - expected_home))
        
        print(f"✅ Calculated ELO ratings for {len(teams)} teams")
        return elo_ratings
    
    def calculate_recent_form(self, team: str, before_date: str, league: str, 
                            matches_count: int = 5) -> Dict[str, float]:
        """Calculate team's recent form before a specific date"""
        query = '''
        SELECT home_team, away_team, home_score, away_score, match_date
        FROM comprehensive_matches 
        WHERE (home_team = ? OR away_team = ?) 
        AND league_name = ? 
        AND match_date < ? 
        AND home_score IS NOT NULL
        ORDER BY match_date DESC 
        LIMIT ?
        '''
        
        cursor = self.conn.cursor()
        cursor.execute(query, (team, team, league, before_date, matches_count))
        recent_matches = cursor.fetchall()
        
        if not recent_matches:
            return {
                'points_per_game': 1.0,  # Neutral
                'goals_for_avg': 1.0,
                'goals_against_avg': 1.0,
                'win_rate': 0.33,
                'form_score': 1.0
            }
        
        points = 0
        goals_for = 0
        goals_against = 0
        wins = 0
        
        for home_team, away_team, home_score, away_score, match_date in recent_matches:
            if home_team == team:
                # Team played at home
                team_goals = home_score
                opponent_goals = away_score
            else:
                # Team played away
                team_goals = away_score
                opponent_goals = home_score
            
            goals_for += team_goals
            goals_against += opponent_goals
            
            # Calculate points
            if team_goals > opponent_goals:
                points += 3
                wins += 1
            elif team_goals == opponent_goals:
                points += 1
        
        matches_played = len(recent_matches)
        
        return {
            'points_per_game': points / matches_played,
            'goals_for_avg': goals_for / matches_played,
            'goals_against_avg': goals_against / matches_played,
            'win_rate': wins / matches_played,
            'form_score': (points / (matches_played * 3))  # Normalized 0-1
        }
    
    def calculate_h2h_record(self, home_team: str, away_team: str, 
                           before_date: str, matches_limit: int = 10) -> Dict[str, float]:
        """Calculate head-to-head record between two teams"""
        query = '''
        SELECT home_team, away_team, home_score, away_score, match_date
        FROM comprehensive_matches 
        WHERE ((home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?))
        AND match_date < ? 
        AND home_score IS NOT NULL
        ORDER BY match_date DESC 
        LIMIT ?
        '''
        
        cursor = self.conn.cursor()
        cursor.execute(query, (home_team, away_team, away_team, home_team, before_date, matches_limit))
        h2h_matches = cursor.fetchall()
        
        if not h2h_matches:
            return {
                'home_team_wins': 0.33,
                'away_team_wins': 0.33,
                'draws': 0.33,
                'home_advantage_h2h': 0.5,
                'avg_goals_total': 2.5,
                'h2h_strength': 0.5
            }
        
        home_wins = 0
        away_wins = 0
        draws = 0
        total_goals = 0
        home_team_goals_in_h2h = 0
        
        for h_team, a_team, h_score, a_score, date in h2h_matches:
            total_goals += h_score + a_score
            
            # From perspective of current home team
            if h_team == home_team:
                home_team_goals_in_h2h += h_score
                if h_score > a_score:
                    home_wins += 1
                elif h_score < a_score:
                    away_wins += 1
                else:
                    draws += 1
            else:
                home_team_goals_in_h2h += a_score
                if a_score > h_score:
                    home_wins += 1
                elif a_score < h_score:
                    away_wins += 1
                else:
                    draws += 1
        
        matches_count = len(h2h_matches)
        
        return {
            'home_team_wins': home_wins / matches_count,
            'away_team_wins': away_wins / matches_count,
            'draws': draws / matches_count,
            'home_advantage_h2h': home_wins / (home_wins + away_wins) if (home_wins + away_wins) > 0 else 0.5,
            'avg_goals_total': total_goals / matches_count,
            'h2h_strength': (home_wins + 0.5 * draws) / matches_count
        }
    
    def calculate_league_position_strength(self, team: str, league: str, 
                                         season: str, before_date: str) -> Dict[str, float]:
        """Calculate team's league position and relative strength"""
        # Get team's performance in current season before the date
        query = '''
        SELECT home_team, away_team, home_score, away_score
        FROM comprehensive_matches 
        WHERE (home_team = ? OR away_team = ?) 
        AND league_name = ? 
        AND season = ?
        AND match_date < ? 
        AND home_score IS NOT NULL
        '''
        
        cursor = self.conn.cursor()
        cursor.execute(query, (team, team, league, season, before_date))
        season_matches = cursor.fetchall()
        
        if not season_matches:
            return {
                'estimated_position': 10,  # Mid-table
                'points_total': 15,
                'goal_difference': 0,
                'position_strength': 0.5
            }
        
        points = 0
        goals_for = 0
        goals_against = 0
        
        for home_team, away_team, home_score, away_score in season_matches:
            if home_team == team:
                team_goals = home_score
                opponent_goals = away_score
            else:
                team_goals = away_score
                opponent_goals = home_score
            
            goals_for += team_goals
            goals_against += opponent_goals
            
            if team_goals > opponent_goals:
                points += 3
            elif team_goals == opponent_goals:
                points += 1
        
        goal_difference = goals_for - goals_against
        
        # Estimate position based on points per game (rough calculation)
        matches_played = len(season_matches)
        points_per_game = points / matches_played if matches_played > 0 else 1.0
        
        # Rough position estimation (higher points = lower position number = better)
        if points_per_game >= 2.5:
            estimated_position = min(1 + (3 - points_per_game) * 3, 4)
        elif points_per_game >= 2.0:
            estimated_position = 4 + (2.5 - points_per_game) * 8
        elif points_per_game >= 1.5:
            estimated_position = 8 + (2.0 - points_per_game) * 6
        else:
            estimated_position = 14 + (1.5 - points_per_game) * 6
        
        estimated_position = max(1, min(20, estimated_position))
        
        return {
            'estimated_position': estimated_position,
            'points_total': points,
            'goal_difference': goal_difference,
            'position_strength': (21 - estimated_position) / 20  # Normalized 0-1 (1 = 1st place)
        }
    
    def calculate_rest_days(self, team: str, match_date: str, league: str) -> int:
        """Calculate days since team's last match"""
        query = '''
        SELECT MAX(match_date) as last_match
        FROM comprehensive_matches 
        WHERE (home_team = ? OR away_team = ?) 
        AND league_name = ?
        AND match_date < ? 
        AND home_score IS NOT NULL
        '''
        
        cursor = self.conn.cursor()
        cursor.execute(query, (team, team, league, match_date))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return 7  # Default 1 week
        
        last_match_date = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
        current_match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
        
        return (current_match_date - last_match_date).days
    
    def calculate_motivation_factor(self, team_position: float, league_size: int = 20, 
                                  season_progress: float = 0.5) -> float:
        """Calculate team motivation based on league position and season stage"""
        # Higher motivation for:
        # - Top 4 (European qualification)
        # - Bottom 3 (relegation battle)
        # - Mid-season onwards (results matter more)
        
        if team_position <= 4:
            # Fighting for European spots
            motivation = 0.8 + (season_progress * 0.2)
        elif team_position >= (league_size - 3):
            # Fighting relegation
            motivation = 0.9 + (season_progress * 0.1)
        elif 4 < team_position <= 8:
            # Fighting for Europe
            motivation = 0.6 + (season_progress * 0.2)
        else:
            # Mid-table, less motivation
            motivation = 0.4 + (season_progress * 0.1)
        
        return min(1.0, motivation)
    
    def calculate_dynamic_weights(self, match_context: Dict) -> FeatureWeights:
        """Calculate dynamic feature weights based on match context"""
        weights = FeatureWeights()
        
        # Base weights
        weights.home_advantage = self.base_weights['home_advantage']
        weights.recent_form = self.base_weights['recent_form']
        weights.team_strength_gap = self.base_weights['team_strength_gap']
        weights.h2h_record = self.base_weights['h2h_record']
        weights.league_position = self.base_weights['league_position']
        weights.rest_days = self.base_weights['rest_days']
        weights.motivation = self.base_weights['motivation']
        
        # Dynamic adjustments based on context
        
        # 1. Derby matches - increase H2H weight
        if match_context.get('is_derby', False):
            weights.h2h_record *= 1.4
            weights.motivation *= 1.3
        
        # 2. End of season - increase motivation weight
        season_progress = match_context.get('season_progress', 0.5)
        if season_progress > 0.7:  # Last 30% of season
            weights.motivation *= 1.5
            weights.league_position *= 1.3
        
        # 3. Top team vs bottom team - increase strength gap weight
        position_gap = abs(match_context.get('position_gap', 0))
        if position_gap > 10:
            weights.team_strength_gap *= 1.3
            weights.motivation *= 1.2
        
        # 4. Short rest (< 3 days) - increase rest days weight
        home_rest = match_context.get('home_rest_days', 7)
        away_rest = match_context.get('away_rest_days', 7)
        if min(home_rest, away_rest) < 3:
            weights.rest_days *= 2.0
        
        # 5. Strong recent form difference - increase form weight
        form_gap = abs(match_context.get('form_gap', 0))
        if form_gap > 0.3:  # Significant form difference
            weights.recent_form *= 1.2
        
        return weights
    
    def create_weighted_features(self, home_team: str, away_team: str, 
                               match_date: str, league: str, season: str) -> Dict[str, float]:
        """Create comprehensive weighted features for a match"""
        
        # Calculate all base features
        elo_ratings = self.calculate_elo_ratings()
        
        home_form = self.calculate_recent_form(home_team, match_date, league)
        away_form = self.calculate_recent_form(away_team, match_date, league)
        
        h2h_record = self.calculate_h2h_record(home_team, away_team, match_date)
        
        home_position_data = self.calculate_league_position_strength(home_team, league, season, match_date)
        away_position_data = self.calculate_league_position_strength(away_team, league, season, match_date)
        
        home_rest = self.calculate_rest_days(home_team, match_date, league)
        away_rest = self.calculate_rest_days(away_team, match_date, league)
        
        # Calculate match context for dynamic weighting
        match_context = {
            'is_derby': self.is_derby_match(home_team, away_team),
            'season_progress': self.calculate_season_progress(match_date, season),
            'position_gap': abs(home_position_data['estimated_position'] - away_position_data['estimated_position']),
            'home_rest_days': home_rest,
            'away_rest_days': away_rest,
            'form_gap': abs(home_form['form_score'] - away_form['form_score'])
        }
        
        # Get dynamic weights
        weights = self.calculate_dynamic_weights(match_context)
        
        # Create weighted features
        features = {}
        
        # 1. Home Advantage (weighted)
        base_home_advantage = 0.55  # Historical home win rate
        features['home_advantage_weighted'] = base_home_advantage * weights.home_advantage
        
        # 2. Team Strength Gap (ELO-based, weighted)
        home_elo = elo_ratings.get(home_team, self.initial_elo)
        away_elo = elo_ratings.get(away_team, self.initial_elo)
        elo_diff = (home_elo - away_elo) / 400  # Normalized
        features['team_strength_gap_weighted'] = elo_diff * weights.team_strength_gap
        
        # 3. Recent Form (weighted)
        form_diff = home_form['form_score'] - away_form['form_score']
        features['recent_form_weighted'] = form_diff * weights.recent_form
        
        # 4. H2H Record (weighted)
        h2h_advantage = h2h_record['h2h_strength'] - 0.5  # Center around 0
        features['h2h_record_weighted'] = h2h_advantage * weights.h2h_record
        
        # 5. League Position (weighted)
        position_diff = (away_position_data['position_strength'] - home_position_data['position_strength'])
        features['league_position_weighted'] = position_diff * weights.league_position
        
        # 6. Rest Days (weighted)
        rest_advantage = (away_rest - home_rest) / 7  # Normalized by week
        features['rest_days_weighted'] = rest_advantage * weights.rest_days
        
        # 7. Motivation (weighted)
        home_motivation = self.calculate_motivation_factor(
            home_position_data['estimated_position'], 20, match_context['season_progress']
        )
        away_motivation = self.calculate_motivation_factor(
            away_position_data['estimated_position'], 20, match_context['season_progress']
        )
        motivation_diff = home_motivation - away_motivation
        features['motivation_weighted'] = motivation_diff * weights.motivation
        
        # 8. Additional unweighted features for model
        features['home_goals_for_avg'] = home_form['goals_for_avg']
        features['home_goals_against_avg'] = home_form['goals_against_avg']
        features['away_goals_for_avg'] = away_form['goals_for_avg']
        features['away_goals_against_avg'] = away_form['goals_against_avg']
        features['h2h_avg_goals'] = h2h_record['avg_goals_total']
        features['home_position'] = home_position_data['estimated_position']
        features['away_position'] = away_position_data['estimated_position']
        
        # 9. Composite weighted score
        features['composite_home_advantage'] = (
            features['home_advantage_weighted'] +
            features['team_strength_gap_weighted'] +
            features['recent_form_weighted'] +
            features['h2h_record_weighted'] +
            features['league_position_weighted'] +
            features['rest_days_weighted'] +
            features['motivation_weighted']
        )
        
        return features
    
    def is_derby_match(self, home_team: str, away_team: str) -> bool:
        """Determine if this is a derby match (same city/region)"""
        # Simplified derby detection - you can expand this
        city_teams = {
            'manchester': ['manchester united', 'manchester city'],
            'liverpool': ['liverpool', 'everton'],
            'london': ['arsenal', 'chelsea', 'tottenham', 'west ham', 'crystal palace', 'fulham', 'brentford'],
            'milan': ['inter', 'milan', 'ac milan', 'inter milan'],
            'madrid': ['real madrid', 'atletico madrid'],
            'turin': ['juventus', 'torino'],
            'rome': ['roma', 'lazio'],
            'munich': ['bayern munich', 'bayern'],
            'birmingham': ['aston villa', 'birmingham'],
            'sheffield': ['sheffield united', 'sheffield wednesday']
        }
        
        home_lower = home_team.lower()
        away_lower = away_team.lower()
        
        for city, teams in city_teams.items():
            home_in_city = any(team in home_lower for team in teams)
            away_in_city = any(team in away_lower for team in teams)
            if home_in_city and away_in_city:
                return True
        
        return False
    
    def calculate_season_progress(self, match_date: str, season: str) -> float:
        """Calculate how far through the season this match is (0-1)"""
        try:
            # Assume season starts in August and ends in May
            season_year = int(season)
            season_start = datetime(season_year, 8, 1)
            season_end = datetime(season_year + 1, 5, 31)
            
            current_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
            
            season_length = (season_end - season_start).days
            progress_days = (current_date - season_start).days
            
            return max(0.0, min(1.0, progress_days / season_length))
        except:
            return 0.5  # Default to mid-season
    
    def close(self):
        """Close database connection"""
        self.conn.close()

# Example usage and testing
if __name__ == "__main__":
    print("🚀 ADVANCED WEIGHTED FEATURE SYSTEM")
    print("=" * 50)
    
    feature_engine = AdvancedFootballFeatures()
    
    try:
        # Test with a sample match
        features = feature_engine.create_weighted_features(
            home_team="Arsenal",
            away_team="Manchester United",
            match_date="2024-01-01T15:00:00Z",
            league="ENG-Premier League",
            season="2023"
        )
        
        print("✅ Sample weighted features:")
        for feature, value in features.items():
            print(f"  • {feature}: {value:.3f}")
        
        print(f"\n🎯 Composite home advantage: {features['composite_home_advantage']:.3f}")
        print("🚀 Feature engineering system ready!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        feature_engine.close()