# FoodBridge AI — Rapid MVP

AI-powered NGO meal-demand prediction and surplus food allocation prototype.

## Run locally
1. Install Python 3.10+.
2. Open this folder in VS Code / terminal.
3. Create a virtual environment:
   - Windows: `python -m venv .venv`
   - Activate: `.venv\\Scripts\\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Launch: `streamlit run app.py`

The app creates a synthetic dataset, trains Linear Regression, Decision Tree, Random Forest, and Gradient Boosting models, compares MAE/RMSE/R², saves the best pipeline, and opens the dashboard.

**Dataset disclaimer:** the data is synthetic and created for demonstration. Predictions are not validated against real NGO operational data.
