from prediction_models import FootballPredictionModels
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score
import joblib

def train_simple_models():
    print("🤖 Training models without XGBoost...")
    
    # Load data
    predictor = FootballPredictionModels(db_path='comprehensive_football_data.db')
    df = predictor.load_data()
    df = predictor.create_features(df)
    
    print(f"✅ Loaded {len(df)} matches with features")
    
    # Train for each prediction type
    results = {}
    
    for pred_type in ['match_outcome', 'over_under_2_5', 'btts']:
        print(f"\n🎯 Training {pred_type}...")
        
        try:
            X, y = predictor.prepare_features_for_model(df, pred_type)
            
            if len(X) < 100:
                print(f"⚠️ Insufficient data for {pred_type}")
                continue
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
            
            # Scale for Logistic Regression
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train models (NO XGBoost)
            models = {
                'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
                'random_forest': RandomForestClassifier(n_estimators=100, random_state=42)
            }
            
            model_results = {}
            trained_models = {}
            
            for name, model in models.items():
                if name == 'logistic_regression':
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                else:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                
                accuracy = accuracy_score(y_test, y_pred)
                model_results[name] = accuracy
                trained_models[name] = model
                
                print(f"  {name}: {accuracy:.1%} accuracy")
            
            # Simple ensemble (Logistic + Random Forest)
            if pred_type == 'match_outcome':
                # Hard voting for multiclass
                ensemble = VotingClassifier([
                    ('lr', models['logistic_regression']),
                    ('rf', models['random_forest'])
                ], voting='hard')
            else:
                # Soft voting for binary
                ensemble = VotingClassifier([
                    ('lr', models['logistic_regression']),
                    ('rf', models['random_forest'])
                ], voting='soft')
            
            # Train ensemble
            ensemble.fit(X_train_scaled, y_train)
            ensemble_pred = ensemble.predict(X_test_scaled)
            ensemble_accuracy = accuracy_score(y_test, ensemble_pred)
            
            print(f"  ensemble: {ensemble_accuracy:.1%} accuracy")
            
            # Save best model
            best_accuracy = max(model_results.values())
            best_model_name = max(model_results.keys(), key=lambda x: model_results[x])
            
            if ensemble_accuracy > best_accuracy:
                best_model = ensemble
                best_model_name = 'ensemble'
                best_accuracy = ensemble_accuracy
            else:
                best_model = trained_models[best_model_name]
            
            # Save model and scaler
            model_data = {
                'model': best_model,
                'scaler': scaler,
                'model_name': best_model_name,
                'accuracy': best_accuracy,
                'prediction_type': pred_type
            }
            
            joblib.dump(model_data, f'{pred_type}_model.pkl')
            
            results[pred_type] = {
                'best_model': best_model_name,
                'accuracy': best_accuracy,
                'total_samples': len(X)
            }
            
        except Exception as e:
            print(f"❌ Error training {pred_type}: {e}")
            continue
    
    # Final summary
    print(f"\n🎉 TRAINING COMPLETED!")
    print("=" * 40)
    for pred_type, result in results.items():
        print(f"{pred_type}: {result['accuracy']:.1%} accuracy ({result['total_samples']} samples)")
        print(f"  Best model: {result['best_model']}")
    
    return results

if __name__ == "__main__":
    results = train_simple_models()