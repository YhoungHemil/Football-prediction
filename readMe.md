# README.md

# ⚽ Enhanced Football Prediction System

A comprehensive football prediction system with multiple data sources, advanced machine learning models, and a user-friendly dashboard.

## Features

- **Multi-source data collection**: FBref, The Odds API, Football-Data.org
- **Advanced ML models**: Logistic Regression, Random Forest, XGBoost, Ensemble methods
- **Comprehensive predictions**: Match outcomes, goal totals, BTTS, corners, cards
- **Interactive dashboard**: Streamlit-based web interface
- **Betting simulation**: Profit tracking and ROI analysis
- **Multiple leagues**: Top 5 European leagues + lower divisions

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <your-repo>
cd football-prediction-system

# Install requirements
pip install -r requirements.txt

# Or install as package
pip install -e .
```

### 2. Configuration

1. Get API key from [The Odds API](https://the-odds-api.com/) (free tier: 500 requests/month)
2. Update `config.py` with your API keys:

```python
# In config.py
odds_api_key: str = "your_odds_api_key_here"
```

### 3. Usage

```bash
# Run data collection
python run_system.py collect

# Train models
python run_system.py train

# Start dashboard
python run_system.py dashboard

# Run full pipeline
python run_system.py all
```

## Project Structure

```
football-prediction-system/
├── enhanced_multi_collector.py    # Multi-source data collector
├── prediction_models.py           # ML models framework
├── streamlit_frontend.py          # Dashboard interface
├── config.py                     # Configuration management
├── run_system.py                 # Main runner script
├── requirements.txt              # Dependencies
├── README.md                     # Documentation
├── enhanced_football_data.db     # SQLite database
└── logs/
    ├── multi_collector.log       # Collection logs
    ├── system.log               # System logs
    └── football_collector.log   # Legacy logs
```

## Data Sources

### Primary Sources
- **FBref** (via soccerdata): Match results, team stats, player data
- **The Odds API**: Betting odds for all major markets
- **Football-Data.org**: Backup match data

### Supported Leagues
- **England**: Premier League, Championship, League One, League Two
- **Spain**: La Liga, Segunda División  
- **Germany**: Bundesliga, 2. Bundesliga
- **Italy**: Serie A, Serie B
- **France**: Ligue 1, Ligue 2
- **European**: Champions League, Europa League, Conference League

## Machine Learning Models

### Model Types
1. **Logistic Regression**: Fast, interpretable baseline
2. **Random Forest**: Robust ensemble method
3. **XGBoost**: Gradient boosting for complex patterns
4. **Voting Ensemble**: Combines multiple models

### Prediction Types
- **Match Outcome**: Home/Draw/Away (55-65% accuracy)
- **Over/Under 2.5**: Goal totals (60-70% accuracy)
- **BTTS**: Both teams to score (65-75% accuracy)
- **Corners Over 9.5**: Corner totals (55-65% accuracy)
- **Cards Over 3.5**: Card totals (50-60% accuracy)

## Features

### Data Collection
- **Multi-source scraping** with fallback mechanisms
- **Rate limiting** and error handling
- **User agent rotation** for reliable access
- **Data quality validation**

### Machine Learning
- **Feature engineering**: Team form, H2H records, strength ratings
- **Cross-validation** for model selection
- **Ensemble methods** for improved accuracy
- **Historical backtesting**

### Dashboard
- **Real-time predictions** for upcoming matches
- **Performance analytics** and visualizations
- **Betting simulation** with profit tracking
- **Model training interface**
- **Data management tools**

## API Configuration

### The Odds API Setup
1. Register at [the-odds-api.com](https://the-odds-api.com/)
2. Get free API key (500 requests/month)
3. Add to `config.py`:

```python
odds_api_key: str = "your_key_here"
```

### Supported Markets
- Match Result (1X2)
- Over/Under Goals (0.5, 1.5, 2.5, 3.5)
- Both Teams to Score
- First Half Markets
- Asian Handicaps

## Database Schema

### Core Tables
- **enhanced_matches**: Match results with advanced statistics
- **player_stats**: Individual player performance data
- **team_form_enhanced**: Team form tracking with advanced metrics
- **match_odds**: Betting odds from multiple bookmakers
- **predictions**: Model predictions with confidence scores

### Advanced Features
- **Expected Goals (xG)** integration
- **Tactical data** (possession, shots, passes)
- **Form indicators** (last 5, last 10 matches)
- **Head-to-head records**

## Usage Examples

### Collect Data for Specific Leagues
```python
from enhanced_multi_collector import MultiSourceFootballCollector

config = {
    'odds_api_key': 'your_key',
    'request_delay': 3
}

collector = MultiSourceFootballCollector(config)
collector.collect_league_data({
    'name': 'ENG-Premier League',
    'seasons': ['2023-24'],
    'odds_sport_key': 'soccer_epl'
})
```

### Train Custom Models
```python
from prediction_models import FootballPredictionModels

predictor = FootballPredictionModels()
predictor.run_full_training()

# Evaluate performance
performance = predictor.evaluate_historical_performance()
```

### Make Predictions
```python
# Predict single match
predictions = predictor.predict_match(
    home_team="Arsenal",
    away_team="Manchester United", 
    match_features={
        'home_form_points': 12,
        'away_form_points': 8
    }
)

print(predictions['match_outcome'])
# Output: {'prediction': 'H', 'probabilities': {'H': 0.65, 'D': 0.20, 'A': 0.15}}
```

## Performance Metrics

### Expected Accuracy (Based on Research)
- **Match Outcomes**: 55-65% (varies by league)
- **Goal Markets**: 60-70% (most predictable)
- **BTTS**: 65-75% (high confidence predictions)
- **In-game Events**: 50-65% (corners, cards)

### Profitability Targets
- **High Odds (3.0+)**: 40-50% accuracy = profitable
- **Medium Odds (1.6-2.4)**: 65-70% accuracy needed
- **Low Odds (1.2-1.6)**: 75%+ accuracy required

## Advanced Features

### Playing Style Detection
Automatically detects team tactics:
- **Counter-attacking**: Low possession + high conversion
- **Possession-based**: High pass accuracy + territory control  
- **Wing-heavy**: High crosses + corner frequency
- **Defensive**: Low goals conceded + high blocks

### Betting Simulation
- **Historical backtesting** on 5 seasons of data
- **Profit tracking** with detailed ROI analysis
- **Risk management** with confidence thresholds
- **Multiple betting strategies**

### Data Quality Management
- **Missing data handling** with multiple fallbacks
- **Data validation** across sources
- **Quality scoring** for prediction confidence
- **Automated data refresh** scheduling

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check if database exists
   ls -la enhanced_football_data.db
   
   # Run data collection first
   python run_system.py collect
   ```

2. **API Rate Limit Exceeded**
   ```python
   # Increase delays in config.py
   request_delay: int = 6  # Increase from 3 to 6 seconds
   ```

3. **Missing Dependencies**
   ```bash
   # Install specific packages
   pip install soccerdata
   pip install xgboost
   ```

4. **Model Training Fails**
   ```bash
   # Check data availability
   python -c "from prediction_models import FootballPredictionModels; p=FootballPredictionModels(); print(len(p.load_data()))"
   ```

### Debug Mode
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python run_system.py collect
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## Roadmap

### Phase 1 (Month 1) ✅
- Multi-source data collection
- Basic ML models (Logistic, RF, XGBoost)
- Streamlit dashboard
- Top 5 European leagues

### Phase 2 (Month 2)
- Player-level predictions
- Advanced ensemble methods
- Real-time odds integration
- Lower division leagues

### Phase 3 (Month 3)
- Neural networks for complex patterns
- Live betting features
- Mobile-responsive interface
- Automated trading simulation

### Future Enhancements
- Real-time match tracking
- Social betting features
- Advanced visualization
- Mobile app development

## License

MIT License - see LICENSE file for details

## Support

- **Documentation**: Check this README and code comments
- **Issues**: Create GitHub issue with details
- **Email**: contact@yourproject.com

## Disclaimer

This system is for educational and research purposes. Always gamble responsibly and within your means. Past performance does not guarantee future results.

---

## Quick Commands Reference

```bash
# Data Collection
python run_system.py collect

# Model Training  
python run_system.py train

# Start Dashboard
streamlit run streamlit_frontend.py

# Full Pipeline
python run_system.py all

# Debug Mode
LOG_LEVEL=DEBUG python run_system.py collect

# Export Models
python -c "from prediction_models import FootballPredictionModels; p=FootballPredictionModels(); p.load_models(); p.save_models('backup.pkl')"
```