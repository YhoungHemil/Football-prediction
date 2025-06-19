# Update streamlit dashboard to use cleaned data
with open('streamlit_frontend.py', 'r') as file:
    content = file.read()

# Update database path in dashboard
content = content.replace(
    "db_path='enhanced_football_data.db'",
    "db_path='comprehensive_football_data.db'"
)

# Also update any direct database connections
content = content.replace(
    "sqlite3.connect('enhanced_football_data.db')",
    "sqlite3.connect('comprehensive_football_data.db')"
)

with open('streamlit_frontend.py', 'w') as file:
    file.write(content)

print("✅ Updated dashboard to use comprehensive database")