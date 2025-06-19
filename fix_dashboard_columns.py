# Fix column name issues in dashboard
with open('streamlit_frontend.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Fix specific column references
column_fixes = [
    # Competition column references
    ("SELECT COUNT(DISTINCT competition)", "SELECT COUNT(DISTINCT league_name)"),
    ("GROUP BY competition", "GROUP BY league_name"),
    ("ORDER BY competition", "ORDER BY league_name"),
    
    # In dataframe displays
    ("'competition']", "'league_name']"),
    ("\"competition\"]", "\"league_name\"]"),
    
    # In SQL SELECT statements  
    ("m.competition,", "m.league_name,"),
    ("competition TEXT", "league_name TEXT"),
    
    # Any remaining competition references in queries
    ("WHERE competition", "WHERE league_name"),
    ("competition =", "league_name ="),
]

# Apply all fixes
for old, new in column_fixes:
    content = content.replace(old, new)

# Write back fixed content
with open('streamlit_frontend.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("✅ Fixed all column name references in dashboard")
print("📊 'competition' → 'league_name'")
print("🚀 Restart dashboard now")