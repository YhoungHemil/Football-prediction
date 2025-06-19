import requests
import pandas as pd
import sqlite3
import json
from datetime import datetime
import time

class FootballDataCollector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": api_key}
        
        # Create database connection
        self.conn = sqlite3.connect('football_data.db')
        self.setup_database()
    
    def setup_database(self):
        """Create tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY,
                competition_name TEXT,
                season TEXT,
                matchday INTEGER,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                match_date TEXT,
                status TEXT,
                winner TEXT
            )
        ''')
        
        # Team standings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_name TEXT,
                season TEXT,
                team_name TEXT,
                position INTEGER,
                played_games INTEGER,
                won INTEGER,
                draw INTEGER,
                lost INTEGER,
                points INTEGER,
                goals_for INTEGER,
                goals_against INTEGER,
                goal_difference INTEGER,
                form TEXT,
                updated_date TEXT
            )
        ''')
        
        self.conn.commit()
        print("Database tables created successfully!")
    
    def get_competitions(self):
        """Get available competitions"""
        url = f"{self.base_url}/competitions"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            competitions = response.json()['competitions']
            
            print("Available competitions:")
            for comp in competitions[:10]:  # Show first 10
                print(f"- {comp['name']} ({comp['code']}) - ID: {comp['id']}")
            
            return competitions
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching competitions: {e}")
            return []
    
    def get_matches(self, competition_id, season=2024):
        """Get matches for a specific competition and season"""
        url = f"{self.base_url}/competitions/{competition_id}/matches"
        params = {"season": season}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            matches_data = response.json()
            matches = matches_data.get('matches', [])
            
            print(f"Found {len(matches)} matches for season {season}")
            
            # Store matches in database
            self.store_matches(matches, matches_data.get('competition', {}).get('name', 'Unknown'))
            
            return matches
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching matches: {e}")
            return []
    
    def store_matches(self, matches, competition_name):
        """Store matches in database"""
        cursor = self.conn.cursor()
        
        for match in matches:
            cursor.execute('''
                INSERT OR REPLACE INTO matches 
                (id, competition_name, season, matchday, home_team, away_team, 
                 home_score, away_score, match_date, status, winner)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match['id'],
                competition_name,
                match['season']['startDate'][:4],  # Extract year
                match.get('matchday'),
                match['homeTeam']['name'],
                match['awayTeam']['name'],
                match['score']['fullTime']['home'],
                match['score']['fullTime']['away'],
                match['utcDate'],
                match['status'],
                match.get('score', {}).get('winner')
            ))
        
        self.conn.commit()
        print(f"Stored {len(matches)} matches in database")
    
    def get_standings(self, competition_id, season=2024):
        """Get current standings for a competition"""
        url = f"{self.base_url}/competitions/{competition_id}/standings"
        params = {"season": season}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            standings_data = response.json()
            standings = standings_data.get('standings', [])
            
            if standings:
                table = standings[0].get('table', [])
                print(f"Found standings with {len(table)} teams")
                
                # Store standings
                self.store_standings(table, standings_data.get('competition', {}).get('name', 'Unknown'), season)
                
                return table
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching standings: {e}")
            return []
    
    def store_standings(self, standings, competition_name, season):
        """Store standings in database"""
        cursor = self.conn.cursor()
        current_date = datetime.now().isoformat()
        
        for team in standings:
            cursor.execute('''
                INSERT OR REPLACE INTO standings 
                (competition_name, season, team_name, position, played_games, 
                 won, draw, lost, points, goals_for, goals_against, 
                 goal_difference, form, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                competition_name,
                str(season),
                team['team']['name'],
                team['position'],
                team['playedGames'],
                team['won'],
                team['draw'],
                team['lost'],
                team['points'],
                team['goalsFor'],
                team['goalsAgainst'],
                team['goalDifference'],
                team.get('form', ''),
                current_date
            ))
        
        self.conn.commit()
        print(f"Stored standings for {len(standings)} teams")
    
    def show_recent_matches(self, limit=10):
        """Display recent matches from database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT home_team, away_team, home_score, away_score, match_date, competition_name
            FROM matches 
            WHERE status = 'FINISHED'
            ORDER BY match_date DESC 
            LIMIT ?
        ''', (limit,))
        
        matches = cursor.fetchall()
        
        print(f"\nRecent {limit} matches:")
        print("-" * 80)
        for match in matches:
            home, away, h_score, a_score, date, comp = match
            date_formatted = date[:10] if date else "Unknown"
            print(f"{date_formatted} | {home} {h_score}-{a_score} {away} ({comp})")
    
    def close(self):
        """Close database connection"""
        self.conn.close()

# Example usage
if __name__ == "__main__":
    # Replace 'YOUR_API_KEY' with your actual API key from football-data.org
    API_KEY = "751bc97db5fa4f4ba08955bdda5a07d0"
    
    # Initialize collector
    collector = FootballDataCollector(API_KEY)
    
    print("=== Football Data Collector Started ===\n")
    
    # Get available competitions
    competitions = collector.get_competitions()
    
    # Premier League ID is 2021
    premier_league_id = 2021
    
    print(f"\n=== Collecting Premier League Data ===")
    
    # Get matches for current season
    matches = collector.get_matches(premier_league_id, 2024)
    
    # Get current standings
    standings = collector.get_standings(premier_league_id, 2024)
    
    # Show some recent matches
    collector.show_recent_matches(10)
    
    # Close connection
    collector.close()
    
    print("\nData collection completed! Check 'football_data.db' file.")