# setup.py
from setuptools import setup, find_packages

setup(
    name="football-prediction-system",
    version="1.0.0",
    description="Enhanced Football Prediction System with Multiple Data Sources",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "requests>=2.28.0",
        "scikit-learn>=1.1.0",
        "xgboost>=1.6.0",
        "soccerdata>=1.3.0",
        "streamlit>=1.25.0",
        "plotly>=5.15.0",
        "beautifulsoup4>=4.11.0",
        "joblib>=1.1.0",
    ],
    python_requires=">=3.8",
)