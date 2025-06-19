# Quick script to update prediction_models.py for new database
import re

with open('prediction_models.py', 'r') as file:
    content = file.read()

# Update database path
content = content.replace(
    "db_path: str = 'enhanced_football_data.db'",
    "db_path: str = 'comprehensive_football_data.db'"
)

# Update table name in query
content = content.replace('FROM enhanced_matches m', 'FROM comprehensive_matches m')
content = content.replace('m.competition,', 'm.league_name as competition,')

with open('prediction_models.py', 'w') as file:
    file.write(content)

print("✅ Updated prediction_models.py to use comprehensive database")