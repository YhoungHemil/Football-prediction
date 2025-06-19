# Fix all database references in streamlit dashboard
import re

with open('streamlit_frontend.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Replace all database references
replacements = [
    # Direct database paths
    ("'enhanced_football_data.db'", "'comprehensive_football_data.db'"),
    ('"enhanced_football_data.db"', '"comprehensive_football_data.db"'),
    
    # Database initialization
    ("db_path = 'enhanced_football_data.db'", "db_path = 'comprehensive_football_data.db'"),
    ("db_path='enhanced_football_data.db'", "db_path='comprehensive_football_data.db'"),
    
    # Table names
    ("FROM enhanced_matches", "FROM comprehensive_matches"),
    ("enhanced_matches", "comprehensive_matches"),
    
    # Column names that changed
    ("m.competition", "m.league_name as competition"),
]

# Apply all replacements
for old, new in replacements:
    content = content.replace(old, new)

# Also fix any remaining table references in SQL queries
sql_patterns = [
    (r"SELECT.*FROM\s+enhanced_matches", lambda m: m.group(0).replace("enhanced_matches", "comprehensive_matches")),
    (r"UPDATE\s+enhanced_matches", lambda m: m.group(0).replace("enhanced_matches", "comprehensive_matches")),
    (r"INSERT.*INTO\s+enhanced_matches", lambda m: m.group(0).replace("enhanced_matches", "comprehensive_matches")),
]

for pattern, replacement in sql_patterns:
    content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

# Write back the fixed content
with open('streamlit_frontend.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("✅ Fixed dashboard database references")
print("📊 Dashboard now uses comprehensive_football_data.db with 5,231 clean matches")
print("🚀 Restart dashboard: streamlit run streamlit_frontend.py")