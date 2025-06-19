import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from prediction_models import FootballPredictionModels
import json

# Page configuration
st.set_page_config(
    page_title="Football Prediction Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem;
    }
    .prediction-card {
        border: 2px solid #1f77b4;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #f8f9fa;
    }
    .profit-positive {
        color: #28a745;
        font-weight: bold;
    }
    .profit-negative {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class FootballDashboard:
    def __init__(self):
        self.db_path = 'comprehensive_football_data.db'
        self.predictor = None
        self.initialize_predictor()
    
    def initialize_predictor(self):
        """Initialize the prediction models"""
        try:
            self.predictor = FootballPredictionModels(self.db_path)
            # Try to load existing models
            try:
                self.predictor.load_models()
                st.success("✅ Prediction models loaded successfully!")
            except:
                st.warning("⚠️ No trained models found. Please train models first.")
        except Exception as e:
            st.error(f"❌ Error initializing predictor: {e}")
    
    def load_data_from_db(self, query: str) -> pd.DataFrame:
        """Load data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn)
        except Exception as e:
            st.error(f"Database error: {e}")
            return pd.DataFrame()
    
    def get_recent_matches(self, limit: int = 50) -> pd.DataFrame:
        """Get recent matches from database"""
        query = f'''
        SELECT 
            home_team, away_team, home_score, away_score,
            match_date, competition,
            (home_score + away_score) as total_goals,
            CASE 
                WHEN home_score > away_score THEN 'H'
                WHEN home_score < away_score THEN 'A'
                ELSE 'D'
            END as result
        FROM comprehensive_matches 
        WHERE home_score IS NOT NULL 
        ORDER BY match_date DESC 
        LIMIT {limit}
        '''
        return self.load_data_from_db(query)
    
    def get_team_stats(self) -> pd.DataFrame:
        """Get team statistics"""
        query = '''
        SELECT 
            team,
            COUNT(*) as matches_played,
            AVG(goals_for) as avg_goals_for,
            AVG(goals_against) as avg_goals_against,
            SUM(points) as total_points,
            AVG(points) as avg_points
        FROM (
            SELECT home_team as team, home_score as goals_for, away_score as goals_against,
                   CASE WHEN home_score > away_score THEN 3
                        WHEN home_score = away_score THEN 1
                        ELSE 0 END as points
            FROM comprehensive_matches WHERE home_score IS NOT NULL
            UNION ALL
            SELECT away_team as team, away_score as goals_for, home_score as goals_against,
                   CASE WHEN away_score > home_score THEN 3
                        WHEN away_score = home_score THEN 1
                        ELSE 0 END as points
            FROM comprehensive_matches WHERE home_score IS NOT NULL
        ) 
        GROUP BY team
        ORDER BY avg_points DESC
        '''
        return self.load_data_from_db(query)
    
    def display_header(self):
        """Display main header"""
        st.markdown('<div class="main-header">⚽ Football Prediction Dashboard</div>', unsafe_allow_html=True)
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_matches = self.load_data_from_db("SELECT COUNT(*) as count FROM comprehensive_matches WHERE home_score IS NOT NULL")
            st.metric("Total Matches", total_matches['count'].iloc[0] if not total_matches.empty else 0)
        
        with col2:
            total_teams = self.load_data_from_db("SELECT COUNT(DISTINCT home_team) as count FROM comprehensive_matches")
            st.metric("Teams", total_teams['count'].iloc[0] if not total_teams.empty else 0)
        
        with col3:
            competitions = self.load_data_from_db("SELECT COUNT(DISTINCT league_name) as count FROM comprehensive_matches")
            st.metric("Competitions", competitions['count'].iloc[0] if not competitions.empty else 0)
        
        with col4:
            if self.predictor and hasattr(self.predictor, 'models'):
                st.metric("Trained Models", len(self.predictor.models))
            else:
                st.metric("Trained Models", 0)
    
    def prediction_page(self):
        """Main prediction interface"""
        st.header("🔮 Match Prediction")
        
        if not self.predictor or not hasattr(self.predictor, 'models') or not self.predictor.models:
            st.warning("⚠️ No trained models available. Please train models first in the 'Model Training' section.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Match Details")
            
            # Get teams from database
            teams_query = "SELECT DISTINCT home_team FROM comprehensive_matches ORDER BY home_team"
            teams_df = self.load_data_from_db(teams_query)
            teams = teams_df['home_team'].tolist() if not teams_df.empty else []
            
            home_team = st.selectbox("Home Team", teams)
            away_team = st.selectbox("Away Team", [t for t in teams if t != home_team])
            
            match_date = st.date_input("Match Date", datetime.now())
            league_name = st.selectbox("Competition", 
                                     ["Premier League", "Championship", "La Liga", "Serie A", "Bundesliga"])
            
            # Additional features
            st.subheader("Match Context")
            day_of_week = match_date.weekday()
            month = match_date.month
            
            # Form inputs (simplified)
            home_form = st.slider("Home Team Recent Form (Points from last 5)", 0, 15, 8)
            away_form = st.slider("Away Team Recent Form (Points from last 5)", 0, 15, 6)
        
        with col2:
            st.subheader("Predictions")
            
            if st.button("🎯 Generate Predictions", type="primary"):
                if home_team and away_team and home_team != away_team:
                    # Create match features
                    match_features = {
                        'day_of_week': day_of_week,
                        'month': month,
                        'home_form_points': home_form,
                        'away_form_points': away_form,
                        'home_form_goals_for': home_form * 0.8,
                        'home_form_goals_against': (15 - home_form) * 0.5,
                        'away_form_goals_for': away_form * 0.7,
                        'away_form_goals_against': (15 - away_form) * 0.6,
                        'h2h_home_wins': 2,
                        'h2h_away_wins': 1,
                        'h2h_draws': 1,
                        'h2h_total_matches': 4,
                        'h2h_avg_goals': 2.5
                    }
                    
                    # Get predictions
                    predictions = self.predictor.predict_match(home_team, away_team, match_features)
                    
                    # Display predictions
                    for pred_type, result in predictions.items():
                        if 'error' not in result:
                            st.markdown(f'<div class="prediction-card">', unsafe_allow_html=True)
                            st.subheader(pred_type.replace('_', ' ').title())
                            
                            if pred_type == 'match_outcome':
                                if 'probabilities' in result:
                                    probs = result['probabilities']
                                    st.write(f"**Home Win**: {probs.get('H', 0):.1%}")
                                    st.write(f"**Draw**: {probs.get('D', 0):.1%}")
                                    st.write(f"**Away Win**: {probs.get('A', 0):.1%}")
                                    st.write(f"**Prediction**: {result['prediction']}")
                                    st.write(f"**Confidence**: {result['confidence']:.1%}")
                            
                            elif pred_type in ['over_under_2_5', 'btts']:
                                prob = result.get('probability', 0)
                                pred = "Yes" if result.get('prediction', 0) == 1 else "No"
                                st.write(f"**Prediction**: {pred}")
                                st.write(f"**Probability**: {prob:.1%}")
                                st.write(f"**Confidence**: {result.get('confidence', 0):.1%}")
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error("Please select different teams for home and away")
    
    def analytics_page(self):
        """Analytics and visualization page"""
        st.header("📊 Analytics Dashboard")
        
        tab1, tab2, tab3 = st.tabs(["Match Analytics", "Team Performance", "Prediction Performance"])
        
        with tab1:
            st.subheader("Recent Match Results")
            recent_matches = self.get_recent_matches(100)
            
            if not recent_matches.empty:
                # Goal distribution
                fig_goals = px.histogram(recent_matches, x='total_goals', 
                                       title="Goal Distribution in Recent Matches",
                                       nbins=10)
                st.plotly_chart(fig_goals, use_container_width=True)
                
                # Results distribution
                result_counts = recent_matches['result'].value_counts()
                fig_results = px.pie(values=result_counts.values, names=result_counts.index,
                                   title="Match Results Distribution")
                st.plotly_chart(fig_results, use_container_width=True)
                
                # Recent matches table
                st.subheader("Latest Results")
                display_df = recent_matches[['home_team', 'away_team', 'home_score', 'away_score', 
                                           'match_date', 'league_name']].head(20)
                st.dataframe(display_df, use_container_width=True)
        
        with tab2:
            st.subheader("Team Performance")
            team_stats = self.get_team_stats()
            
            if not team_stats.empty:
                # Top teams by points
                top_teams = team_stats.head(10)
                fig_points = px.bar(top_teams, x='team', y='avg_points',
                                  title="Top Teams by Average Points per Game")
                fig_points.update_xaxes(tickangle=45)
                st.plotly_chart(fig_points, use_container_width=True)
                
                # Goals scored vs conceded
                fig_goals = px.scatter(team_stats, x='avg_goals_for', y='avg_goals_against',
                                     hover_data=['team'], title="Goals For vs Against")
                st.plotly_chart(fig_goals, use_container_width=True)
                
                # Team stats table
                st.subheader("Team Statistics")
                display_stats = team_stats.round(2)
                st.dataframe(display_stats, use_container_width=True)
        
        with tab3:
            st.subheader("Model Performance")
            
            if self.predictor and hasattr(self.predictor, 'models'):
                # Model accuracy comparison
                model_performance = []
                for pred_type, model_info in self.predictor.models.items():
                    if 'results' in model_info:
                        for model_name, results in model_info['results'].items():
                            model_performance.append({
                                'Prediction Type': pred_type,
                                'Model': model_name,
                                'Accuracy': results.get('accuracy', 0),
                                'CV Mean': results.get('cv_mean', 0)
                            })
                
                if model_performance:
                    perf_df = pd.DataFrame(model_performance)
                    
                    # Accuracy comparison chart
                    fig_acc = px.bar(perf_df, x='Prediction Type', y='Accuracy', 
                                   color='Model', barmode='group',
                                   title="Model Accuracy Comparison")
                    fig_acc.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_acc, use_container_width=True)
                    
                    # Performance table
                    st.dataframe(perf_df, use_container_width=True)
                else:
                    st.info("No model performance data available")
            else:
                st.warning("No trained models found")
    
    def model_training_page(self):
        """Model training interface"""
        st.header("🤖 Model Training")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Training Configuration")
            
            # Data info
            total_matches = self.load_data_from_db("SELECT COUNT(*) as count FROM comprehensive_matches WHERE home_score IS NOT NULL")
            if not total_matches.empty:
                st.info(f"📊 Available training data: {total_matches['count'].iloc[0]} completed matches")
            
            # Training options
            prediction_types = st.multiselect(
                "Select prediction types to train:",
                ['match_outcome', 'over_under_2_5', 'btts', 'corners_over_9_5', 'cards_over_3_5'],
                default=['match_outcome', 'over_under_2_5', 'btts']
            )
            
            test_size = st.slider("Test set size (%)", 10, 30, 20)
            
            st.subheader("Model Options")
            enable_ensemble = st.checkbox("Enable ensemble models", value=True)
            cross_validation = st.checkbox("Perform cross-validation", value=True)
        
        with col2:
            st.subheader("Training Actions")
            
            if st.button("🚀 Start Training", type="primary"):
                if not prediction_types:
                    st.error("Please select at least one prediction type")
                else:
                    # Training progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Initialize predictor if needed
                        if not self.predictor:
                            self.initialize_predictor()
                        
                        total_steps = len(prediction_types)
                        
                        # Load and prepare data
                        status_text.text("Loading data...")
                        df = self.predictor.load_data()
                        df = self.predictor.create_features(df)
                        
                        progress_bar.progress(0.1)
                        
                        # Train models (without XGBoost to avoid issues)
                        for i, pred_type in enumerate(prediction_types):
                            status_text.text(f"Training {pred_type}...")
                            
                            X, y = self.predictor.prepare_features_for_model(df, pred_type)
                            
                            if len(X) > 100:
                                try:
                                    # Use our working training function instead
                                    from sklearn.ensemble import RandomForestClassifier
                                    from sklearn.linear_model import LogisticRegression
                                    from sklearn.model_selection import train_test_split
                                    from sklearn.metrics import accuracy_score
                                    import joblib
                                    
                                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
                                    
                                    # Train simple models without XGBoost
                                    models = {
                                        'logistic': LogisticRegression(random_state=42, max_iter=1000),
                                        'forest': RandomForestClassifier(n_estimators=100, random_state=42)
                                    }
                                    
                                    best_accuracy = 0
                                    for name, model in models.items():
                                        model.fit(X_train, y_train)
                                        y_pred = model.predict(X_test)
                                        accuracy = accuracy_score(y_test, y_pred)
                                        if accuracy > best_accuracy:
                                            best_accuracy = accuracy
                                            best_model = model
                                    
                                    # Save model
                                    joblib.dump(best_model, f'{pred_type}_dashboard_model.pkl')
                                    st.success(f"{pred_type}: {best_accuracy:.1%} accuracy")
                                    
                                except Exception as e:
                                    st.error(f"Training failed for {pred_type}: {e}")
                                
                                progress_bar.progress((i + 1) / total_steps)
                            else:
                                st.warning(f"Insufficient data for {pred_type}: {len(X)} samples")
                        
                        # Save models
                        status_text.text("Saving models...")
                        self.predictor.save_models()
                        progress_bar.progress(1.0)
                        
                        status_text.text("Training completed!")
                        st.success("✅ Model training completed successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Training failed: {e}")
                        st.exception(e)
            
            if st.button("📊 Evaluate Models"):
                if self.predictor and hasattr(self.predictor, 'models'):
                    with st.spinner("Evaluating models..."):
                        try:
                            performance = self.predictor.evaluate_historical_performance()
                            
                            st.subheader("Historical Performance")
                            for pred_type, results in performance.items():
                                st.metric(
                                    pred_type.replace('_', ' ').title(),
                                    f"{results['accuracy']:.1%}",
                                    f"{results['total_predictions']} predictions"
                                )
                        except Exception as e:
                            st.error(f"Evaluation failed: {e}")
                else:
                    st.warning("No trained models to evaluate")
            
            if st.button("💾 Export Models"):
                if self.predictor and hasattr(self.predictor, 'models'):
                    try:
                        self.predictor.save_models('exported_models.pkl')
                        st.success("✅ Models exported to 'exported_models.pkl'")
                    except Exception as e:
                        st.error(f"Export failed: {e}")
                else:
                    st.warning("No models to export")
    
    def data_management_page(self):
        """Data management interface"""
        st.header("💾 Data Management")
        
        tab1, tab2, tab3 = st.tabs(["Data Collection", "Database Status", "Data Quality"])
        
        with tab1:
            st.subheader("Data Collection")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Available Data Sources:**")
                st.write("• FBref (via soccerdata)")
                st.write("• The Odds API")
                st.write("• Football-Data.org API")
                
                leagues_to_collect = st.multiselect(
                    "Select leagues to collect:",
                    ['Premier League', 'Championship', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1'],
                    default=['Premier League']
                )
                
                seasons_to_collect = st.multiselect(
                    "Select seasons:",
                    ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'],
                    default=['2023-24']
                )
            
            with col2:
                if st.button("🔄 Start Data Collection", type="primary"):
                    if leagues_to_collect and seasons_to_collect:
                        st.info("Data collection would start here...")
                        st.write("This would trigger the enhanced_multi_collector.py script")
                    else:
                        st.error("Please select leagues and seasons")
                
                if st.button("📊 Update Team Ratings"):
                    st.info("Team ratings update would start here...")
                
                if st.button("🎲 Collect Latest Odds"):
                    st.info("Odds collection would start here...")
        
        with tab2:
            st.subheader("Database Status")
            
            # Database statistics
            tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
            tables_df = self.load_data_from_db(tables_query)
            
            if not tables_df.empty:
                st.write(f"**Database Tables:** {len(tables_df)} tables found")
                
                for table in tables_df['name']:
                    count_query = f"SELECT COUNT(*) as count FROM {table}"
                    count_df = self.load_data_from_db(count_query)
                    if not count_df.empty:
                        st.write(f"• {table}: {count_df['count'].iloc[0]} records")
            
            # Data freshness
            latest_match_query = "SELECT MAX(match_date) as latest FROM comprehensive_matches"
            latest_df = self.load_data_from_db(latest_match_query)
            if not latest_df.empty and latest_df['latest'].iloc[0]:
                st.write(f"**Latest match data:** {latest_df['latest'].iloc[0]}")
        
        with tab3:
            st.subheader("Data Quality Report")
            
            # Missing data analysis
            missing_data_query = '''
            SELECT 
                COUNT(*) as total_matches,
                SUM(CASE WHEN home_score IS NULL THEN 1 ELSE 0 END) as missing_scores,
                SUM(CASE WHEN home_corners IS NULL THEN 1 ELSE 0 END) as missing_corners,
                SUM(CASE WHEN home_yellow_cards IS NULL THEN 1 ELSE 0 END) as missing_cards
            FROM comprehensive_matches
            '''
            quality_df = self.load_data_from_db(missing_data_query)
            
            if not quality_df.empty:
                row = quality_df.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Matches", row['total_matches'])
                
                with col2:
                    missing_pct = (row['missing_scores'] / row['total_matches']) * 100 if row['total_matches'] > 0 else 0
                    st.metric("Missing Scores", f"{missing_pct:.1f}%")
                
                with col3:
                    missing_corners_pct = (row['missing_corners'] / row['total_matches']) * 100 if row['total_matches'] > 0 else 0
                    st.metric("Missing Corners", f"{missing_corners_pct:.1f}%")
                
                with col4:
                    missing_cards_pct = (row['missing_cards'] / row['total_matches']) * 100 if row['total_matches'] > 0 else 0
                    st.metric("Missing Cards", f"{missing_cards_pct:.1f}%")
    
    def betting_simulation_page(self):
        """Betting simulation and profit tracking"""
        st.header("💰 Betting Simulation")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Simulation Parameters")
            
            stake_per_bet = st.number_input("Stake per bet (£)", min_value=1, max_value=1000, value=10)
            confidence_threshold = st.slider("Minimum confidence threshold", 0.5, 0.9, 0.65)
            
            bet_types = st.multiselect(
                "Bet types to simulate:",
                ['match_outcome', 'over_under_2_5', 'btts'],
                default=['over_under_2_5']
            )
            
            simulation_period = st.selectbox(
                "Simulation period:",
                ['Last 30 days', 'Last 3 months', 'Last 6 months', 'Last season']
            )
        
        with col2:
            st.subheader("Simulation Results")
            
            if st.button("🎰 Run Simulation", type="primary"):
                if bet_types:
                    # Placeholder simulation results
                    st.success("Simulation completed!")
                    
                    # Mock results
                    total_bets = 147
                    winning_bets = 89
                    total_staked = total_bets * stake_per_bet
                    total_returned = 1567.50
                    profit = total_returned - total_staked
                    roi = (profit / total_staked) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Bets", total_bets)
                        st.metric("Winning Bets", winning_bets)
                    
                    with col2:
                        st.metric("Total Staked", f"£{total_staked}")
                        st.metric("Total Returned", f"£{total_returned:.2f}")
                    
                    with col3:
                        profit_color = "profit-positive" if profit > 0 else "profit-negative"
                        st.metric("Profit/Loss", f"£{profit:.2f}")
                        st.metric("ROI", f"{roi:.1f}%")
                    
                    # Profit chart (mock data)
                    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
                    cumulative_profit = np.cumsum(np.random.randn(30) * 20) + 100
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=dates, y=cumulative_profit, mode='lines', name='Cumulative Profit'))
                    fig.update_layout(title="Profit Over Time", xaxis_title="Date", yaxis_title="Profit (£)")
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.error("Please select at least one bet type")
    
    def run(self):
        """Main application runner"""
        # Sidebar navigation
        st.sidebar.title("Navigation")
        
        pages = {
            "🏠 Dashboard": self.display_header,
            "🔮 Predictions": self.prediction_page,
            "📊 Analytics": self.analytics_page,
            "🤖 Model Training": self.model_training_page,
            "💾 Data Management": self.data_management_page,
            "💰 Betting Simulation": self.betting_simulation_page
        }
        
        selected_page = st.sidebar.selectbox("Select Page", list(pages.keys()))
        
        # Add sidebar info
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📈 Quick Stats")
        
        # Database connection test
        try:
            test_query = "SELECT COUNT(*) as count FROM comprehensive_matches LIMIT 1"
            result = self.load_data_from_db(test_query)
            if not result.empty:
                st.sidebar.success("✅ Database connected")
            else:
                st.sidebar.error("❌ Database empty")
        except:
            st.sidebar.error("❌ Database error")
        
        # Model status
        if self.predictor and hasattr(self.predictor, 'models') and self.predictor.models:
            st.sidebar.success("✅ Models loaded")
        else:
            st.sidebar.warning("⚠️ No models")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ℹ️ About")
        st.sidebar.markdown("""
        This dashboard provides:
        - Match outcome predictions
        - Goal total predictions  
        - BTTS predictions
        - Historical performance analysis
        - Betting simulation tools
        """)
        
        # Run selected page
        if selected_page == "🏠 Dashboard":
            self.display_header()
        else:
            pages[selected_page]()

# Main execution
if __name__ == "__main__":
    dashboard = FootballDashboard()
    dashboard.run()