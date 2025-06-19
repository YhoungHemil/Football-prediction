# run_system.py
"""Main runner script for the football prediction system"""

import argparse
import logging
from config import config
from enhanced_multi_collector import MultiSourceFootballCollector
from prediction_models import FootballPredictionModels

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('system.log'),
            logging.StreamHandler()
        ]
    )

def collect_data():
    """Run data collection"""
    print("🔄 Starting data collection...")
    
    collector_config = {
        'football_data_api_key': config.api.football_data_api_key,
        'odds_api_key': config.api.odds_api_key,
        'request_delay': config.api.request_delay,
        'retry_delay': config.api.retry_delay,
        'max_retries': config.api.max_retries
    }
    
    collector = MultiSourceFootballCollector(collector_config)
    
    try:
        collector.run_full_collection()
        print("✅ Data collection completed!")
    except Exception as e:
        print(f"❌ Data collection failed: {e}")
    finally:
        collector.close()

def train_models():
    """Run model training"""
    print("🤖 Starting model training...")
    
    predictor = FootballPredictionModels(config.database.db_path)
    
    try:
        predictor.run_full_training()
        print("✅ Model training completed!")
        
        # Evaluate performance
        performance = predictor.evaluate_historical_performance()
        print("\n📊 Model Performance:")
        for pred_type, results in performance.items():
            print(f"  {pred_type}: {results['accuracy']:.1%} accuracy")
            
    except Exception as e:
        print(f"❌ Model training failed: {e}")

def run_dashboard():
    """Run Streamlit dashboard"""
    print("🌐 Starting dashboard...")
    import subprocess
    import sys
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_frontend.py"])
    except Exception as e:
        print(f"❌ Dashboard failed to start: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Football Prediction System")
    parser.add_argument('command', choices=['collect', 'train', 'dashboard', 'all'],
                       help='Command to run')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.command == 'collect':
        collect_data()
    elif args.command == 'train':
        train_models()
    elif args.command == 'dashboard':
        run_dashboard()
    elif args.command == 'all':
        print("🚀 Running full pipeline...")
        collect_data()
        train_models()
        run_dashboard()

if __name__ == "__main__":
    main()
