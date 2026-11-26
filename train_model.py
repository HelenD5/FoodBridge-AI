import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

SEED = 42
DATA_DIR = "data"
MODEL_DIR = "models"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

def create_dataset(n=2500, seed=SEED):
    rng = np.random.default_rng(seed)
    ngo_types = ["Children's Home", "Elder Care", "Community Kitchen", "Shelter"]
    food_categories = ["Rice/Meals", "Bread", "Vegetables", "Mixed"]
    ngo_ids = [f"NGO_{i:02d}" for i in range(1, 16)]
    people = rng.integers(40, 500, n)
    ngo_type = rng.choice(ngo_types, n)
    food = rng.choice(food_categories, n)
    weekday = rng.integers(0, 7, n)
    weekend = (weekday >= 5).astype(int)
    holiday = rng.binomial(1, 0.08, n)
    previous_day = np.maximum(10, people * rng.uniform(.50, .95, n) + rng.normal(0, 25, n))
    previous_week = np.maximum(10, people * rng.uniform(.55, .92, n) + rng.normal(0, 22, n))
    stock = rng.integers(0, 120, n)
    donations = rng.integers(0, 180, n)
    type_factor = np.select(
        [ngo_type == "Children's Home", ngo_type == "Elder Care",
         ngo_type == "Community Kitchen", ngo_type == "Shelter"],
        [0.82, 0.70, 1.00, 0.88], default=0.85
    )
    food_factor = np.select(
        [food == "Rice/Meals", food == "Bread", food == "Vegetables", food == "Mixed"],
        [1.00, .55, .65, .90], default=1.0
    )
    demand = people * type_factor * food_factor
    demand += previous_day * .12 + previous_week * .08
    demand += weekend * 12 + holiday * 20
    demand -= stock * .40 + donations * .28
    demand += rng.normal(0, 28, n)
    demand = np.clip(demand, 10, people * 1.25)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    df = pd.DataFrame({
        "date": rng.choice(dates.astype(str), n),
        "ngo_id": rng.choice(ngo_ids, n),
        "ngo_type": ngo_type,
        "people_served": people,
        "weekday": weekday,
        "is_weekend": weekend,
        "is_holiday": holiday,
        "food_category": food,
        "previous_day_demand": previous_day.round(1),
        "previous_week_demand": previous_week.round(1),
        "available_stock": stock,
        "donations_received": donations,
        "required_meals": demand.round().astype(int)
    })
    return df

FEATURES = [
    "ngo_type", "people_served", "weekday", "is_weekend", "is_holiday",
    "food_category", "previous_day_demand", "previous_week_demand",
    "available_stock", "donations_received"
]
TARGET = "required_meals"

def train():
    csv_path = os.path.join(DATA_DIR, "foodbridge_dataset.csv")
    df = create_dataset()
    df.to_csv(csv_path, index=False)
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED
    )
    categorical = ["ngo_type", "food_category"]
    numeric = [c for c in FEATURES if c not in categorical]
    preprocessor = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", "passthrough", numeric)
    ])
    candidates = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=8, random_state=SEED),
        "Random Forest": RandomForestRegressor(n_estimators=150, max_depth=12, random_state=SEED, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=120, max_depth=2, random_state=SEED)
    }
    results = []
    trained = {}
    for name, estimator in candidates.items():
        pipe = Pipeline([("prep", preprocessor), ("model", estimator)])
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        metrics = {
            "Model": name,
            "MAE": float(mean_absolute_error(y_test, preds)),
            "RMSE": rmse,
            "R2": float(r2_score(y_test, preds))
        }
        results.append(metrics)
        trained[name] = pipe
    metrics_df = pd.DataFrame(results).sort_values("MAE")
    best_name = metrics_df.iloc[0]["Model"]
    joblib.dump(trained[best_name], os.path.join(MODEL_DIR, "best_model.joblib"))
    joblib.dump(FEATURES, os.path.join(MODEL_DIR, "features.joblib"))
    metrics_df.to_csv(os.path.join(MODEL_DIR, "model_metrics.csv"), index=False)
    print("Dataset saved:", csv_path)
    print(metrics_df.to_string(index=False))
    print("Best model:", best_name)
    return metrics_df, best_name

if __name__ == "__main__":
    train()
