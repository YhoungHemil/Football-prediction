from prediction_models import FootballPredictionModels

# Force the correct database path
predictor = FootballPredictionModels(db_path='comprehensive_football_data.db')

print("🤖 Starting model training with comprehensive database...")

try:
    # Test database connection first
    df = predictor.load_data()
    print(f"✅ Successfully loaded {len(df)} matches from comprehensive database")
    
    if len(df) > 100:
        # Run training
        predictor.run_full_training()
        print("✅ Training completed successfully!")
        
        # Quick evaluation
        performance = predictor.evaluate_historical_performance(test_period_months=3)
        print("\n📊 Model Performance:")
        for pred_type, results in performance.items():
            if 'accuracy' in results:
                print(f"  {pred_type}: {results['accuracy']:.1%} accuracy")
    else:
        print(f"❌ Insufficient data: only {len(df)} matches")
        
except Exception as e:
    print(f"❌ Training failed: {e}")
    import traceback
    traceback.print_exc()