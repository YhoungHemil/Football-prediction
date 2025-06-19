from weighted_feature_system import AdvancedFootballFeatures
from prediction_models import FootballPredictionModels
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

def train_enhanced_models_optimized():
    print("🚀 TRAINING MODELS WITH OPTIMIZED WEIGHTED FEATURES")
    print("=" * 60)
    
    # Initialize systems
    feature_engine = AdvancedFootballFeatures()
    predictor = FootballPredictionModels(db_path='comprehensive_football_data.db')
    
    # Load base data
    df = predictor.load_data()
    print(f"📊 Loaded {len(df)} matches")
    
    # Calculate ELO ratings ONCE for all teams
    print("🎯 Calculating ELO ratings for all teams (one time only)...")
    elo_ratings = feature_engine.calculate_elo_ratings()
    print(f"✅ ELO ratings calculated for {len(elo_ratings)} teams")
    
    # Add basic weighted features without expensive calculations
    print("🔧 Adding optimized features...")
    enhanced_features = []
    
    for idx, match in df.iterrows():
        if idx % 1000 == 0:
            print(f"  Processing match {idx:,}/{len(df):,}...")
        
        try:
            home_team = match['home_team']
            away_team = match['away_team']
            
            # Get ELO ratings (already calculated)
            home_elo = elo_ratings.get(home_team, 1500)
            away_elo = elo_ratings.get(away_team, 1500)
            
            # Calculate basic weighted features
            weighted_features = {
                'home_advantage_weighted': 0.55 * 3.5,  # Base home advantage * weight
                'team_strength_gap_weighted': ((home_elo - away_elo) / 400) * 3.2,  # ELO diff * weight
                'recent_form_weighted': 0.0,  # Simplified for speed
                'h2h_record_weighted': 0.0,   # Simplified for speed
                'league_position_weighted': 0.0,  # Simplified for speed
                'rest_days_weighted': 0.0,    # Simplified for speed
                'motivation_weighted': 0.0,   # Simplified for speed
                'home_goals_for_avg': 1.0,
                'away_goals_for_avg': 1.0,
                'h2h_avg_goals': 2.5,
                'home_elo': home_elo,
                'away_elo': away_elo,
                'elo_difference': home_elo - away_elo
            }
            
            # Composite score
            weighted_features['composite_home_advantage'] = (
                weighted_features['home_advantage_weighted'] +
                weighted_features['team_strength_gap_weighted']
            )
            
            enhanced_features.append(weighted_features)
            
        except Exception as e:
            # Default features if calculation fails
            default_features = {
                'home_advantage_weighted': 1.925,
                'team_strength_gap_weighted': 0.0,
                'recent_form_weighted': 0.0,
                'h2h_record_weighted': 0.0,
                'league_position_weighted': 0.0,
                'rest_days_weighted': 0.0,
                'motivation_weighted': 0.0,
                'composite_home_advantage': 1.925,
                'home_goals_for_avg': 1.0,
                'away_goals_for_avg': 1.0,
                'h2h_avg_goals': 2.5,
                'home_elo': 1500,
                'away_elo': 1500,
                'elo_difference': 0
            }
            enhanced_features.append(default_features)
    
    # Convert to DataFrame
    features_df = pd.DataFrame(enhanced_features)
    
    # Combine with original data
    enhanced_df = pd.concat([df.reset_index(drop=True), features_df], axis=1)
    
    print(f"✅ Added {len(features_df.columns)} optimized features")
    print(f"📊 Enhanced dataset shape: {enhanced_df.shape}")
    
    # Create prediction targets
    enhanced_df['total_goals'] = enhanced_df['home_score'] + enhanced_df['away_score']
    enhanced_df['result'] = enhanced_df.apply(lambda x: 'H' if x['home_score'] > x['away_score'] 
                                            else ('A' if x['home_score'] < x['away_score'] else 'D'), axis=1)
    enhanced_df['over_2_5'] = (enhanced_df['total_goals'] > 2.5).astype(int)
    enhanced_df['btts'] = ((enhanced_df['home_score'] > 0) & (enhanced_df['away_score'] > 0)).astype(int)
    
    # Train models with enhanced features
    results = {}
    
    for pred_type in ['match_outcome', 'over_under_2_5', 'btts']:
        print(f"\n🎯 Training enhanced {pred_type} model...")
        
        # Enhanced feature set
        feature_columns = [
            'composite_home_advantage',
            'team_strength_gap_weighted',
            'home_elo',
            'away_elo',
            'elo_difference',
            'home_goals_for_avg',
            'away_goals_for_avg'
        ]
        
        X = enhanced_df[feature_columns].fillna(0)
        
        # Set target
        if pred_type == 'match_outcome':
            y = enhanced_df['result']
        elif pred_type == 'over_under_2_5':
            y = enhanced_df['over_2_5']
        else:  # btts
            y = enhanced_df['btts']
        
        # Remove missing targets
        mask = ~y.isna()
        X = X[mask]
        y = y[mask]
        
        if len(X) < 100:
            print(f"⚠️ Insufficient data for {pred_type}")
            continue
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Train models
        models = {
            'logistic': LogisticRegression(random_state=42, max_iter=1000),
            'forest': RandomForestClassifier(n_estimators=150, random_state=42, max_depth=12)
        }
        
        best_accuracy = 0
        best_model = None
        best_model_name = ""
        
        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            print(f"  {name}: {accuracy:.1%} accuracy")
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_model = model
                best_model_name = name
        
        # Save model
        joblib.dump({
            'model': best_model,
            'feature_columns': feature_columns,
            'accuracy': best_accuracy
        }, f'{pred_type}_elo_enhanced_model.pkl')
        
        results[pred_type] = {
            'accuracy': best_accuracy,
            'model': best_model_name,
            'samples': len(X)
        }
    
    # Results comparison
    print(f"\n🎉 ELO-ENHANCED MODEL RESULTS:")
    print("=" * 40)
    
    old_results = {'match_outcome': 0.479, 'over_under_2_5': 0.598, 'btts': 0.561}
    
    for pred_type, result in results.items():
        old_acc = old_results.get(pred_type, 0)
        new_acc = result['accuracy']
        improvement = new_acc - old_acc
        
        print(f"{pred_type}: {old_acc:.1%} → {new_acc:.1%} ({improvement:+.1%} improvement)")
    
    feature_engine.close()
    return results

if __name__ == "__main__":
    results = train_enhanced_models_optimized()