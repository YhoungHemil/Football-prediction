import pandas as pd
import numpy as np
import sqlite3
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import xgboost as xgb
from typing import Dict, List, Tuple, Any
import joblib
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class FootballPredictionModels:
    """Comprehensive football prediction models"""
    
    def __init__(self, db_path: str = 'comprehensive_football_data.db'):
        self.db_path = db_path
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.feature_importance = {}
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Model configurations
        self.model_configs = {
            'match_outcome': {
                'target': 'result',
                'type': 'multiclass',
                'classes': ['H', 'D', 'A']  # Home, Draw, Away
            },
            'over_under_2_5': {
                'target': 'over_2_5',
                'type': 'binary',
                'classes': [0, 1]  # Under, Over
            },
            'btts': {
                'target': 'btts',
                'type': 'binary',
                'classes': [0, 1]  # No, Yes
            },
            'corners_over_9_5': {
                'target': 'corners_over_9_5',
                'type': 'binary',
                'classes': [0, 1]
            },
            'cards_over_3_5': {
                'target': 'cards_over_3_5',
                'type': 'binary',
                'classes': [0, 1]
            }
        }
    
    def load_data(self) -> pd.DataFrame:
        """Load and prepare data from database"""
        query = '''
        SELECT 
            m.id,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score,
            m.match_date,
            m.league_name as competition,
            m.season,
            m.home_corners,
            m.away_corners,
            m.home_yellow_cards,
            m.away_yellow_cards,
            m.home_possession,
            m.away_possession,
            m.home_shots_total,
            m.away_shots_total
        FROM comprehensive_matches m
        WHERE m.home_score IS NOT NULL 
        AND m.away_score IS NOT NULL
        ORDER BY m.match_date
        '''
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        self.logger.info(f"Loaded {len(df)} matches from database")
        return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive features for prediction"""
        # Basic match features
        df['total_goals'] = df['home_score'] + df['away_score']
        df['goal_difference'] = df['home_score'] - df['away_score']
        df['total_corners'] = df['home_corners'].fillna(0) + df['away_corners'].fillna(0)
        df['total_cards'] = df['home_yellow_cards'].fillna(0) + df['away_yellow_cards'].fillna(0)
        
        # Target variables
        df['result'] = df.apply(lambda x: 'H' if x['home_score'] > x['away_score'] 
                               else ('A' if x['home_score'] < x['away_score'] else 'D'), axis=1)
        df['over_2_5'] = (df['total_goals'] > 2.5).astype(int)
        df['btts'] = ((df['home_score'] > 0) & (df['away_score'] > 0)).astype(int)
        df['corners_over_9_5'] = (df['total_corners'] > 9.5).astype(int)
        df['cards_over_3_5'] = (df['total_cards'] > 3.5).astype(int)
        
        # Convert date
        df['match_date'] = pd.to_datetime(df['match_date'])
        df['day_of_week'] = df['match_date'].dt.dayofweek
        df['month'] = df['match_date'].dt.month
        
        # Get team form (last 5 matches)
        df = self.add_team_form_features(df)
        
        # Add head-to-head features
        df = self.add_h2h_features(df)
        
        # Add strength ratings
        df = self.add_team_strength_features(df)
        
        return df
    
    def add_team_form_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add team form features (last 5 matches)"""
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # Initialize form columns
        form_cols = ['home_form_points', 'away_form_points', 'home_form_goals_for', 
                    'home_form_goals_against', 'away_form_goals_for', 'away_form_goals_against']
        for col in form_cols:
            df[col] = 0.0
        
        # Calculate form for each team
        teams = pd.concat([df['home_team'], df['away_team']]).unique()
        
        for team in teams:
            team_matches = df[(df['home_team'] == team) | (df['away_team'] == team)].copy()
            
            for idx, match in team_matches.iterrows():
                # Get last 5 matches before this one
                prev_matches = team_matches[team_matches['match_date'] < match['match_date']].tail(5)
                
                if len(prev_matches) > 0:
                    # Calculate form metrics
                    points = 0
                    goals_for = 0
                    goals_against = 0
                    
                    for _, prev_match in prev_matches.iterrows():
                        if prev_match['home_team'] == team:
                            goals_for += prev_match['home_score']
                            goals_against += prev_match['away_score']
                            if prev_match['home_score'] > prev_match['away_score']:
                                points += 3
                            elif prev_match['home_score'] == prev_match['away_score']:
                                points += 1
                        else:
                            goals_for += prev_match['away_score']
                            goals_against += prev_match['home_score']
                            if prev_match['away_score'] > prev_match['home_score']:
                                points += 3
                            elif prev_match['away_score'] == prev_match['home_score']:
                                points += 1
                    
                    # Update dataframe
                    if match['home_team'] == team:
                        df.loc[idx, 'home_form_points'] = points
                        df.loc[idx, 'home_form_goals_for'] = goals_for
                        df.loc[idx, 'home_form_goals_against'] = goals_against
                    else:
                        df.loc[idx, 'away_form_points'] = points
                        df.loc[idx, 'away_form_goals_for'] = goals_for
                        df.loc[idx, 'away_form_goals_against'] = goals_against
        
        return df
    
    def add_h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add head-to-head features"""
        df['h2h_home_wins'] = 0
        df['h2h_away_wins'] = 0
        df['h2h_draws'] = 0
        df['h2h_total_matches'] = 0
        df['h2h_avg_goals'] = 0.0
        
        for idx, match in df.iterrows():
            home_team = match['home_team']
            away_team = match['away_team']
            current_date = match['match_date']
            
            # Get historical matches between these teams
            h2h_matches = df[
                ((df['home_team'] == home_team) & (df['away_team'] == away_team) |
                 (df['home_team'] == away_team) & (df['away_team'] == home_team)) &
                (df['match_date'] < current_date)
            ]
            
            if len(h2h_matches) > 0:
                home_wins = 0
                away_wins = 0
                draws = 0
                total_goals = 0
                
                for _, h2h_match in h2h_matches.iterrows():
                    total_goals += h2h_match['total_goals']
                    
                    # From home team perspective
                    if h2h_match['home_team'] == home_team:
                        if h2h_match['home_score'] > h2h_match['away_score']:
                            home_wins += 1
                        elif h2h_match['home_score'] < h2h_match['away_score']:
                            away_wins += 1
                        else:
                            draws += 1
                    else:  # away team in h2h was home team in current match
                        if h2h_match['away_score'] > h2h_match['home_score']:
                            home_wins += 1
                        elif h2h_match['away_score'] < h2h_match['home_score']:
                            away_wins += 1
                        else:
                            draws += 1
                
                df.loc[idx, 'h2h_home_wins'] = home_wins
                df.loc[idx, 'h2h_away_wins'] = away_wins
                df.loc[idx, 'h2h_draws'] = draws
                df.loc[idx, 'h2h_total_matches'] = len(h2h_matches)
                df.loc[idx, 'h2h_avg_goals'] = total_goals / len(h2h_matches)
        
        return df
    
    def add_team_strength_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add team strength features based on recent performance"""
        # Calculate rolling averages for team strength
        df['home_avg_goals_scored'] = 0.0
        df['home_avg_goals_conceded'] = 0.0
        df['away_avg_goals_scored'] = 0.0
        df['away_avg_goals_conceded'] = 0.0
        
        teams = pd.concat([df['home_team'], df['away_team']]).unique()
        
        for team in teams:
            team_home_matches = df[df['home_team'] == team].sort_values('match_date')
            team_away_matches = df[df['away_team'] == team].sort_values('match_date')
            
            # Home strength
            for idx, match in team_home_matches.iterrows():
                prev_home = team_home_matches[team_home_matches['match_date'] < match['match_date']].tail(10)
                if len(prev_home) > 0:
                    df.loc[idx, 'home_avg_goals_scored'] = prev_home['home_score'].mean()
                    df.loc[idx, 'home_avg_goals_conceded'] = prev_home['away_score'].mean()
            
            # Away strength
            for idx, match in team_away_matches.iterrows():
                prev_away = team_away_matches[team_away_matches['match_date'] < match['match_date']].tail(10)
                if len(prev_away) > 0:
                    df.loc[idx, 'away_avg_goals_scored'] = prev_away['away_score'].mean()
                    df.loc[idx, 'away_avg_goals_conceded'] = prev_away['home_score'].mean()
        
        return df
    
    def prepare_features_for_model(self, df: pd.DataFrame, prediction_type: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and target for specific prediction type"""
        # Feature columns
        feature_cols = [
            'day_of_week', 'month',
            'home_form_points', 'away_form_points',
            'home_form_goals_for', 'home_form_goals_against',
            'away_form_goals_for', 'away_form_goals_against',
            'h2h_home_wins', 'h2h_away_wins', 'h2h_draws', 'h2h_total_matches', 'h2h_avg_goals',
            'home_avg_goals_scored', 'home_avg_goals_conceded',
            'away_avg_goals_scored', 'away_avg_goals_conceded'
        ]
        
        # Add team encoding
        if 'home_team_encoded' not in df.columns:
            le_home = LabelEncoder()
            le_away = LabelEncoder()
            df['home_team_encoded'] = le_home.fit_transform(df['home_team'])
            df['away_team_encoded'] = le_away.fit_transform(df['away_team'])
            
            # Store encoders for later use
            self.encoders[f'{prediction_type}_home'] = le_home
            self.encoders[f'{prediction_type}_away'] = le_away
        
        feature_cols.extend(['home_team_encoded', 'away_team_encoded'])
        
        # Competition encoding
        if 'competition' in df.columns:
            le_comp = LabelEncoder()
            df['competition_encoded'] = le_comp.fit_transform(df['competition'])
            feature_cols.append('competition_encoded')
            self.encoders[f'{prediction_type}_comp'] = le_comp
        
        # Prepare features and target
        X = df[feature_cols].fillna(0)
        y = df[self.model_configs[prediction_type]['target']]
        
        # Remove rows with missing targets
        mask = ~y.isna()
        X = X[mask]
        y = y[mask]
        
        return X.values, y.values
    
    def train_models(self, prediction_type: str, X: np.ndarray, y: np.ndarray):
        """Train multiple models for a prediction type"""
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.scalers[prediction_type] = scaler
        
        # Initialize models
        models = {}
        
        if self.model_configs[prediction_type]['type'] == 'binary':
            models = {
                'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
                'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
                'xgboost': xgb.XGBClassifier(random_state=42, eval_metric='logloss')
            }
        else:  # multiclass
            models = {
                'logistic_regression': LogisticRegression(random_state=42, max_iter=1000, multi_class='ovr'),
                'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
                'xgboost': xgb.XGBClassifier(random_state=42, eval_metric='mlogloss', use_label_encoder=False)
            }
        
        results = {}
        trained_models = {}
        
        # Encode labels for XGBoost
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y_train_encoded = le.fit_transform(y_train)
        y_test_encoded = le.transform(y_test)
        
        for name, model in models.items():
            # Train model
            if name == 'logistic_regression':
                model.fit(X_train_scaled, y_train)
                y_pred = model.predict(X_test_scaled)
            elif name == 'xgboost':
                model.fit(X_train, y_train_encoded)
                y_pred_encoded = model.predict(X_test)
                y_pred = le.inverse_transform(y_pred_encoded)
            else:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
            
            # Evaluate
            accuracy = accuracy_score(y_test, y_pred)
            
            # Cross-validation
            if name == 'logistic_regression':
                cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            else:
                cv_scores = cross_val_score(model, X_train, y_train, cv=5)
            
            results[name] = {
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
            
            trained_models[name] = model
            
            self.logger.info(f"{name}: Accuracy={accuracy:.3f}, CV={cv_scores.mean():.3f}(±{cv_scores.std():.3f})")
        
        # Create ensemble model
        if self.model_configs[prediction_type]['type'] == 'binary':
            ensemble = VotingClassifier([
                ('lr', models['logistic_regression']),
                ('rf', models['random_forest']),
                ('xgb', models['xgboost'])
            ], voting='soft')
        else:
            ensemble = VotingClassifier([
                ('lr', models['logistic_regression']),
                ('rf', models['random_forest']),
                ('xgb', models['xgboost'])
            ], voting='hard')
        
        # Train ensemble with appropriate data
        ensemble.fit(X_train_scaled, y_train)
        ensemble_pred = ensemble.predict(X_test_scaled)
        ensemble_accuracy = accuracy_score(y_test, ensemble_pred)
        
        results['ensemble'] = {'accuracy': ensemble_accuracy}
        trained_models['ensemble'] = ensemble
        
        self.logger.info(f"Ensemble accuracy: {ensemble_accuracy:.3f}")
        
        # Store best models
        best_model_name = max(results.keys(), key=lambda x: results[x]['accuracy'])
        self.models[prediction_type] = {
            'all_models': trained_models,
            'best_model': trained_models[best_model_name],
            'best_model_name': best_model_name,
            'results': results
        }
        
        # Feature importance for tree-based models
        if hasattr(trained_models['random_forest'], 'feature_importances_'):
            self.feature_importance[prediction_type] = trained_models['random_forest'].feature_importances_
    
    def predict_match(self, home_team: str, away_team: str, match_features: Dict) -> Dict:
        """Predict outcomes for a single match"""
        predictions = {}
        
        # Create feature vector
        feature_vector = self.create_match_feature_vector(home_team, away_team, match_features)
        
        for prediction_type, model_info in self.models.items():
            try:
                # Scale features if needed
                if prediction_type in self.scalers:
                    feature_vector_scaled = self.scalers[prediction_type].transform([feature_vector])
                else:
                    feature_vector_scaled = [feature_vector]
                
                # Get prediction
                model = model_info['best_model']
                
                if hasattr(model, 'predict_proba'):
                    probabilities = model.predict_proba(feature_vector_scaled)[0]
                    prediction = model.predict(feature_vector_scaled)[0]
                    
                    if self.model_configs[prediction_type]['type'] == 'binary':
                        predictions[prediction_type] = {
                            'prediction': int(prediction),
                            'probability': float(probabilities[1]),
                            'confidence': float(max(probabilities))
                        }
                    else:  # multiclass
                        class_names = self.model_configs[prediction_type]['classes']
                        predictions[prediction_type] = {
                            'prediction': class_names[prediction] if isinstance(prediction, (int, np.integer)) else prediction,
                            'probabilities': {class_names[i]: float(prob) for i, prob in enumerate(probabilities)},
                            'confidence': float(max(probabilities))
                        }
                else:
                    prediction = model.predict(feature_vector_scaled)[0]
                    predictions[prediction_type] = {
                        'prediction': prediction,
                        'confidence': 0.5  # Default confidence for models without probability
                    }
                    
            except Exception as e:
                self.logger.error(f"Prediction failed for {prediction_type}: {e}")
                predictions[prediction_type] = {'error': str(e)}
        
        return predictions
    
    def create_match_feature_vector(self, home_team: str, away_team: str, match_features: Dict) -> List:
        """Create feature vector for a match"""
        # This is a simplified version - in practice, you'd need to calculate
        # current team form, h2h stats, etc. from the database
        
        feature_vector = [
            match_features.get('day_of_week', 5),  # Default Saturday
            match_features.get('month', 3),  # Default March
            match_features.get('home_form_points', 8),  # Default form
            match_features.get('away_form_points', 6),
            match_features.get('home_form_goals_for', 7),
            match_features.get('home_form_goals_against', 4),
            match_features.get('away_form_goals_for', 5),
            match_features.get('away_form_goals_against', 6),
            match_features.get('h2h_home_wins', 2),
            match_features.get('h2h_away_wins', 1),
            match_features.get('h2h_draws', 1),
            match_features.get('h2h_total_matches', 4),
            match_features.get('h2h_avg_goals', 2.5),
            match_features.get('home_avg_goals_scored', 1.8),
            match_features.get('home_avg_goals_conceded', 1.2),
            match_features.get('away_avg_goals_scored', 1.4),
            match_features.get('away_avg_goals_conceded', 1.6),
            0,  # home_team_encoded (would need to encode)
            0,  # away_team_encoded
            0   # competition_encoded
        ]
        
        return feature_vector
    
    def save_models(self, filepath: str = 'football_models.pkl'):
        """Save trained models"""
        model_data = {
            'models': self.models,
            'scalers': self.scalers,
            'encoders': self.encoders,
            'feature_importance': self.feature_importance,
            'model_configs': self.model_configs
        }
        joblib.dump(model_data, filepath)
        self.logger.info(f"Models saved to {filepath}")
    
    def load_models(self, filepath: str = 'football_models.pkl'):
        """Load trained models"""
        model_data = joblib.load(filepath)
        self.models = model_data['models']
        self.scalers = model_data['scalers']
        self.encoders = model_data['encoders']
        self.feature_importance = model_data['feature_importance']
        self.model_configs = model_data['model_configs']
        self.logger.info(f"Models loaded from {filepath}")
    
    def evaluate_historical_performance(self, test_period_months: int = 6):
        """Evaluate model performance on historical data"""
        self.logger.info("Evaluating historical performance...")
        
        # Load data
        df = self.load_data()
        df = self.create_features(df)
        
        # Define test period
        latest_date = pd.to_datetime(df['match_date']).max()
        test_start_date = latest_date - timedelta(days=test_period_months * 30)
        
        test_data = df[pd.to_datetime(df['match_date']) >= test_start_date]
        train_data = df[pd.to_datetime(df['match_date']) < test_start_date]
        
        self.logger.info(f"Training on {len(train_data)} matches, testing on {len(test_data)} matches")
        
        results = {}
        
        for prediction_type in self.model_configs.keys():
            self.logger.info(f"Evaluating {prediction_type}")
            
            # Prepare training data
            X_train, y_train = self.prepare_features_for_model(train_data, prediction_type)
            X_test, y_test = self.prepare_features_for_model(test_data, prediction_type)
            
            if len(X_train) > 0 and len(X_test) > 0:
                # Train models
                self.train_models(prediction_type, X_train, y_train)
                
                # Test on historical data
                model = self.models[prediction_type]['best_model']
                
                if prediction_type in self.scalers:
                    X_test_scaled = self.scalers[prediction_type].transform(X_test)
                    y_pred = model.predict(X_test_scaled)
                else:
                    y_pred = model.predict(X_test)
                
                accuracy = accuracy_score(y_test, y_pred)
                results[prediction_type] = {
                    'accuracy': accuracy,
                    'total_predictions': len(y_test),
                    'model_name': self.models[prediction_type]['best_model_name']
                }
                
                self.logger.info(f"{prediction_type}: {accuracy:.3f} accuracy on {len(y_test)} predictions")
        
        return results
    
    def run_full_training(self):
        """Run complete model training pipeline"""
        self.logger.info("Starting full model training pipeline...")
        
        # Load and prepare data
        df = self.load_data()
        df = self.create_features(df)
        
        # Train models for each prediction type
        for prediction_type in self.model_configs.keys():
            self.logger.info(f"Training models for {prediction_type}")
            
            X, y = self.prepare_features_for_model(df, prediction_type)
            
            if len(X) > 100:  # Minimum data requirement
                self.train_models(prediction_type, X, y)
            else:
                self.logger.warning(f"Insufficient data for {prediction_type}: {len(X)} samples")
        
        # Save models
        self.save_models()
        
        self.logger.info("Model training completed!")

# Example usage
if __name__ == "__main__":
    # Initialize predictor
    predictor = FootballPredictionModels()
    
    # Run full training
    predictor.run_full_training()
    
    # Evaluate performance
    performance = predictor.evaluate_historical_performance()
    
    print("\n🎯 HISTORICAL PERFORMANCE RESULTS:")
    print("=" * 50)
    for pred_type, results in performance.items():
        print(f"{pred_type}: {results['accuracy']:.1%} accuracy on {results['total_predictions']} predictions")
    
    # Example prediction
    match_features = {
        'day_of_week': 5,  # Saturday
        'month': 3,        # March
        'home_form_points': 10,
        'away_form_points': 7
    }
    
    predictions = predictor.predict_match("Arsenal", "Manchester United", match_features)
    
    print("\n🔮 EXAMPLE PREDICTION:")
    print("=" * 30)
    for pred_type, result in predictions.items():
        if 'error' not in result:
            print(f"{pred_type}: {result}")