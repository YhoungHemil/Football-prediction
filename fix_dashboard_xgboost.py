# Remove XGBoost from dashboard training to avoid label encoding issues

with open('streamlit_frontend.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Find and replace the training section in model_training_page
old_training = '''                        # Train models
                        for i, pred_type in enumerate(prediction_types):
                            status_text.text(f"Training {pred_type}...")
                            
                            X, y = self.predictor.prepare_features_for_model(df, pred_type)
                            
                            if len(X) > 100:
                                self.predictor.train_models(pred_type, X, y)
                                progress_bar.progress((i + 1) / total_steps)
                            else:
                                st.warning(f"Insufficient data for {pred_type}: {len(X)} samples")'''

new_training = '''                        # Train models (without XGBoost to avoid issues)
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
                                st.warning(f"Insufficient data for {pred_type}: {len(X)} samples")'''

content = content.replace(old_training, new_training)

with open('streamlit_frontend.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("✅ Fixed dashboard training - removed XGBoost")
print("🎯 Dashboard now uses Logistic Regression + Random Forest only")
print("🚀 Restart dashboard and try training again")