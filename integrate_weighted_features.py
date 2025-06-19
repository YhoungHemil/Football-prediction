from weighted_feature_system import AdvancedFootballFeatures
from prediction_models import FootballPredictionModels
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

def train_enhanced_models():
    print("🚀 TRAINING MODELS WITH WEIGHTED FEATURES")
    print("=" * 50)
    
    # Initialize systems
    feature_engine = AdvancedFootballFeatures()
    predictor = FootballPredictionModels(db_path='comprehensive_football_data.db')
    
    # Load base data
    df = predictor.load_data()
    print(f"📊 Loaded {len(df)} matches")
    
    # Add weighted features to each match
    print("🔧 Adding weighted features to matches...")
    enhanced_features = []
    
    for idx, match in df.iterrows():
        if idx % 500 == 0:
            print(f"  Processing match {idx}/{len(df)}...")
        
        try:
            weighted_features = feature_engine.create_weighted_features(
                home_team=match['home_team'],
                away_team=match['away_team'],
                match_date=match['match_date'],
                league=match['competition'],
                season=match['season']
            )
            enhanced_features.append(weighted_features)
            
        except Exception as e:
            # If feature calculation fails, use defaults
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
                'h2h_avg_goals': 2.5
            }
            enhanced_features.append(default_features)
    
    # Convert to DataFrame
    features_df = pd.DataFrame(enhanced_features)
    
    # Combine with original data
    enhanced_df = pd.concat([df.reset_index(drop=True), features_df], axis=1)
    
    print(f"✅ Added {len(features_df.columns)} weighted features")
    print(f"📊 Enhanced dataset shape: {enhanced_df.shape}")
    
    # Create enhanced prediction targets
    enhanced_df['total_goals'] = enhanced_df['home_score'] + enhanced_df['away_score']
    enhanced_df['result'] = enhanced_df.apply(lambda x: 'H' if x['home_score'] > x['away_score'] 
                                            else ('A' if x['home_score'] < x['away_score'] else 'D'), axis=1)
    enhanced_df['over_2_5'] = (enhanced_df['total_goals'] > 2.5).astype(int)
    enhanced_df['btts'] = ((enhanced_df['home_score'] > 0) & (enhanced_df['away_score'] > 0)).astype(int)
    
    # Train enhanced models
    results = {}
    
    for pred_type in ['match_outcome', 'over_under_2_5', 'btts']:
        print(f"\n🎯 Training enhanced {pred_type} model...")
        
        # Select features for this prediction type
        feature_columns = [
            'composite_home_advantage',
            'team_strength_gap_weighted', 
            'recent_form_weighted',
            'h2h_record_weighted',
            'league_position_weighted',
            'motivation_weighted',
            'home_goals_for_avg',
            'away_goals_for_avg',
            'h2h_avg_goals'
        ]
        
        X = enhanced_df[feature_columns].fillna(0)
        
        # Set target variable
        if pred_type == 'match_outcome':
            y = enhanced_df['result']
        elif pred_type == 'over_under_2_5':
            y = enhanced_df['over_2_5']
        else:  # btts
            y = enhanced_df['btts']
        
        # Remove rows with missing targets
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
            'forest': RandomForestClassifier(n_estimators=150, random_state=42, max_depth=10)
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
        
        # Save enhanced model
        model_data = {
            'model': best_model,
            'feature_columns': feature_columns,
            'model_name': best_model_name,
            'accuracy': best_accuracy,
            'prediction_type': pred_type
        }
        
        joblib.dump(model_data, f'{pred_type}_enhanced_model.pkl')
        
        results[pred_type] = {
            'accuracy': best_accuracy,
            'model': best_model_name,
            'samples': len(X)
        }
    
    # Final comparison
    print(f"\n🎉 ENHANCED MODEL RESULTS:")
    print("=" * 40)
    print("Prediction Type    | Old Acc | New Acc | Improvement")
    print("-" * 50)
    
    old_results = {
        'match_outcome': 0.479,
        'over_under_2_5': 0.598,
        'btts': 0.561
    }
    
    for pred_type, result in results.items():
        old_acc = old_results.get(pred_type, 0)
        new_acc = result['accuracy']
        improvement = new_acc - old_acc
        
        print(f"{pred_type:15} | {old_acc:.1%}   | {new_acc:.1%}   | {improvement:+.1%}")
    
    feature_engine.close()
    return results

if __name__ == "__main__":
    results = train_enhanced_models()