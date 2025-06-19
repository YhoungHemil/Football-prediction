import sqlite3
import pandas as pd
import re
from typing import List, Set

class FootballDataCleaner:
    """Clean football database to keep only club matches"""
    
    def __init__(self, db_path: str = 'comprehensive_football_data.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        
        # Define patterns for international teams vs clubs
        self.international_teams = {
            # European national teams
            'germany', 'spain', 'france', 'italy', 'england', 'portugal', 'netherlands', 
            'belgium', 'croatia', 'poland', 'ukraine', 'austria', 'czech republic',
            'denmark', 'sweden', 'norway', 'finland', 'switzerland', 'hungary',
            'slovakia', 'slovenia', 'scotland', 'wales', 'ireland', 'northern ireland',
            'serbia', 'bosnia and herzegovina', 'montenegro', 'albania', 'north macedonia',
            'greece', 'turkey', 'romania', 'bulgaria', 'moldova', 'georgia',
            
            # South American national teams
            'brazil', 'argentina', 'uruguay', 'colombia', 'chile', 'peru', 'ecuador',
            'paraguay', 'bolivia', 'venezuela',
            
            # Other national teams
            'united states', 'usa', 'mexico', 'canada', 'japan', 'south korea',
            'australia', 'new zealand', 'saudi arabia', 'iran', 'morocco',
            'egypt', 'nigeria', 'ghana', 'cameroon', 'senegal', 'algeria',
            'tunisia', 'south africa', 'ivory coast',
            
            # Common international team patterns
            'fc', 'ac', 'real', 'atletico', 'bayern', 'borussia', 'juventus',
            'inter', 'milan', 'barcelona', 'manchester', 'arsenal', 'chelsea',
            'liverpool', 'tottenham', 'ajax', 'psv', 'feyenoord'
        }
        
        # Known club prefixes/suffixes that indicate club teams
        self.club_indicators = {
            'fc', 'ac', 'sc', 'cf', 'cd', 'cp', 'ca', 'rc', 'real', 'atletico',
            'athletic', 'sporting', 'club', 'united', 'city', 'town', 'county',
            'rovers', 'wanderers', 'albion', 'villa', 'palace', 'crystal',
            'queens park', 'brighton', 'hove', 'west ham', 'tottenham',
            'manchester', 'liverpool', 'arsenal', 'chelsea', 'everton',
            'leicester', 'wolverhampton', 'southampton', 'burnley', 'watford',
            'norwich', 'aston', 'newcastle', 'sheffield', 'leeds', 'birmingham',
            'bolton', 'blackburn', 'preston', 'derby', 'nottingham', 'forest',
            'stoke', 'swansea', 'cardiff', 'hull', 'sunderland', 'middlesbrough',
            'bayern', 'borussia', 'werder', 'hamburg', 'stuttgart', 'hoffenheim',
            'mainz', 'augsburg', 'freiburg', 'union', 'hertha', 'cologne',
            'juventus', 'inter', 'milan', 'napoli', 'roma', 'lazio', 'fiorentina',
            'atalanta', 'torino', 'genoa', 'sampdoria', 'bologna', 'parma',
            'barcelona', 'madrid', 'valencia', 'sevilla', 'bilbao', 'betis',
            'villarreal', 'celta', 'espanyol', 'getafe', 'leganes', 'girona',
            'ajax', 'psv', 'feyenoord', 'az', 'vitesse', 'groningen',
            'psg', 'paris', 'marseille', 'lyon', 'lille', 'nice', 'monaco',
            'rennes', 'strasbourg', 'montpellier', 'nantes', 'bordeaux'
        }
    
    def is_national_team_match(self, home_team: str, away_team: str) -> bool:
        """Determine if this is a national team match"""
        home_clean = home_team.lower().strip()
        away_clean = away_team.lower().strip()
        
        # Check if both teams are single-word country names (common pattern)
        home_words = home_clean.split()
        away_words = away_clean.split()
        
        # Single word country names (Germany, Spain, etc.)
        if (len(home_words) == 1 and len(away_words) == 1 and
            home_clean in self.international_teams and away_clean in self.international_teams):
            return True
        
        # Two-word country names (United States, South Korea, etc.)
        home_full = ' '.join(home_words)
        away_full = ' '.join(away_words)
        
        if (home_full in self.international_teams and away_full in self.international_teams):
            return True
        
        # Check for obvious national team patterns
        national_patterns = [
            r'\b(under|u)\s*\d+\b',  # Under-21, U21, etc.
            r'\b(women|ladies)\b',    # Women's national teams
            r'\b(youth|junior)\b'     # Youth teams
        ]
        
        for pattern in national_patterns:
            if (re.search(pattern, home_clean, re.IGNORECASE) or 
                re.search(pattern, away_clean, re.IGNORECASE)):
                return True
        
        return False
    
    def is_club_team(self, team_name: str) -> bool:
        """Determine if this is a club team"""
        team_clean = team_name.lower().strip()
        words = team_clean.split()
        
        # Check for club indicators
        for word in words:
            if word in self.club_indicators:
                return True
        
        # Check for common club patterns
        club_patterns = [
            r'\bfc\b', r'\bac\b', r'\bsc\b', r'\bcf\b',  # Football Club variations
            r'\bunited\b', r'\bcity\b', r'\btowns?\b',   # Common club names
            r'\brovers?\b', r'\bwanderers?\b',           # English club types
            r'\balbion\b', r'\bvilla\b', r'\bpalace\b',  # More English clubs
            r'\dfc\b', r'\d{4}\b'                        # Numbers (founding years)
        ]
        
        for pattern in club_patterns:
            if re.search(pattern, team_clean, re.IGNORECASE):
                return True
        
        return False
    
    def analyze_current_data(self):
        """Analyze current data to understand what we have"""
        print("🔍 ANALYZING CURRENT DATA")
        print("=" * 50)
        
        # Get basic statistics
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM comprehensive_matches")
        total_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM comprehensive_matches WHERE home_score IS NOT NULL")
        completed_matches = cursor.fetchone()[0]
        
        print(f"📊 Total matches: {total_matches:,}")
        print(f"📊 Completed matches: {completed_matches:,}")
        
        # Sample matches to check patterns
        cursor.execute("""
            SELECT home_team, away_team, league_name, country
            FROM comprehensive_matches 
            WHERE home_score IS NOT NULL 
            LIMIT 20
        """)
        
        samples = cursor.fetchall()
        
        print(f"\n📝 SAMPLE MATCHES:")
        national_team_count = 0
        club_count = 0
        
        for home, away, league, country in samples:
            is_national = self.is_national_team_match(home, away)
            match_type = "🌍 NATIONAL" if is_national else "🏛️ CLUB"
            
            if is_national:
                national_team_count += 1
            else:
                club_count += 1
            
            print(f"  {match_type}: {home} vs {away} ({league})")
        
        print(f"\n📈 SAMPLE BREAKDOWN:")
        print(f"  • National team matches: {national_team_count}")
        print(f"  • Club matches: {club_count}")
        
        return total_matches, completed_matches
    
    def identify_non_club_matches(self) -> List[str]:
        """Identify all non-club matches for removal"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, home_team, away_team, league_name
            FROM comprehensive_matches
            WHERE home_score IS NOT NULL
        """)
        
        all_matches = cursor.fetchall()
        
        non_club_matches = []
        club_matches = []
        
        print(f"\n🔍 ANALYZING {len(all_matches):,} MATCHES...")
        
        for match_id, home, away, league in all_matches:
            if self.is_national_team_match(home, away):
                non_club_matches.append(match_id)
            else:
                club_matches.append(match_id)
        
        print(f"📊 ANALYSIS RESULTS:")
        print(f"  • National team matches: {len(non_club_matches):,}")
        print(f"  • Club matches: {len(club_matches):,}")
        print(f"  • Club percentage: {(len(club_matches)/len(all_matches))*100:.1f}%")
        
        return non_club_matches
    
    def create_clean_database(self):
        """Create a clean database with only club matches"""
        print(f"\n🧹 STARTING DATA CLEANUP")
        print("=" * 50)
        
        # Identify matches to remove
        non_club_match_ids = self.identify_non_club_matches()
        
        if not non_club_match_ids:
            print("✅ No national team matches found - data already clean!")
            return
        
        print(f"\n🗑️ REMOVING {len(non_club_match_ids):,} NATIONAL TEAM MATCHES...")
        
        # Create backup first
        cursor = self.conn.cursor()
        
        # Create backup table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comprehensive_matches_backup AS 
            SELECT * FROM comprehensive_matches
        """)
        
        print("💾 Created backup table: comprehensive_matches_backup")
        
        # Remove national team matches
        placeholders = ','.join(['?' for _ in non_club_match_ids])
        cursor.execute(f"""
            DELETE FROM comprehensive_matches 
            WHERE id IN ({placeholders})
        """, non_club_match_ids)
        
        self.conn.commit()
        
        # Check results
        cursor.execute("SELECT COUNT(*) FROM comprehensive_matches WHERE home_score IS NOT NULL")
        remaining_matches = cursor.fetchone()[0]
        
        print(f"✅ CLEANUP COMPLETED!")
        print(f"  • Removed: {len(non_club_match_ids):,} national team matches")
        print(f"  • Remaining: {remaining_matches:,} club matches")
        print(f"  • Improvement: {(len(non_club_match_ids)/5279)*100:.1f}% data cleaned")
    
    def verify_cleanup(self):
        """Verify the cleanup was successful"""
        print(f"\n✅ VERIFYING CLEANUP")
        print("=" * 30)
        
        cursor = self.conn.cursor()
        
        # Get sample of remaining matches
        cursor.execute("""
            SELECT home_team, away_team, league_name
            FROM comprehensive_matches 
            WHERE home_score IS NOT NULL 
            ORDER BY RANDOM()
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        
        print("📝 SAMPLE REMAINING MATCHES:")
        all_clubs = True
        
        for home, away, league in samples:
            is_national = self.is_national_team_match(home, away)
            match_type = "🌍 NATIONAL" if is_national else "🏛️ CLUB"
            
            if is_national:
                all_clubs = False
            
            print(f"  {match_type}: {home} vs {away} ({league})")
        
        if all_clubs:
            print("✅ SUCCESS: All remaining matches appear to be club matches!")
        else:
            print("⚠️ WARNING: Some national team matches may still remain")
        
        # Final statistics
        cursor.execute("SELECT COUNT(*) FROM comprehensive_matches WHERE home_score IS NOT NULL")
        final_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT league_name) FROM comprehensive_matches")
        leagues_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT league_name, COUNT(*) FROM comprehensive_matches GROUP BY league_name ORDER BY COUNT(*) DESC LIMIT 5")
        top_leagues = cursor.fetchall()
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"  • Total club matches: {final_count:,}")
        print(f"  • Leagues represented: {leagues_count}")
        print(f"  • Top leagues:")
        
        for league, count in top_leagues:
            print(f"    - {league}: {count:,} matches")
    
    def close(self):
        """Close database connection"""
        self.conn.close()
    
    def run_full_cleanup(self):
        """Run the complete cleanup process"""
        print("🧹 FOOTBALL DATA CLEANUP - CLUB MATCHES ONLY")
        print("=" * 60)
        
        try:
            # Step 1: Analyze current data
            self.analyze_current_data()
            
            # Step 2: Clean the data
            self.create_clean_database()
            
            # Step 3: Verify cleanup
            self.verify_cleanup()
            
            print(f"\n🎉 CLEANUP COMPLETED SUCCESSFULLY!")
            print(f"💾 Database: {self.db_path}")
            print(f"💾 Backup: comprehensive_matches_backup table")
            print(f"\n🚀 READY FOR IMPROVED MODEL TRAINING!")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()

if __name__ == "__main__":
    cleaner = FootballDataCleaner()
    cleaner.run_full_cleanup()