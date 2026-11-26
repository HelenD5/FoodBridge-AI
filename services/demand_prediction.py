
import os
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from services.database import fetch_all


MODEL_PATH = "models/ngo_demand_model.pkl"

CATEGORIES = ["Rice", "Vegetables", "Fruits", "Bread", "Meals", "Other"]

FEATURES = [
    "people_served",
    "previous_demand",
    "current_stock",
    "donations_received",
    "day_of_week",
    "food_category"
]


def generate_training_data(rows=3000):

    np.random.seed(42)

    people = np.random.randint(30, 501, rows)

    previous_demand = people * np.random.uniform(
        0.7, 1.5, rows
    )

    current_stock = np.random.randint(0, 201, rows)

    donations = np.random.randint(0, 101, rows)

    day = np.random.randint(0, 7, rows)

    category = np.random.choice(
        CATEGORIES,
        rows
    )

    category_factor = {
        "Rice": 1.0,
        "Vegetables": 0.8,
        "Fruits": 0.6,
        "Bread": 0.7,
        "Meals": 1.2,
        "Other": 0.75
    }

    factor = np.array([
        category_factor[c] for c in category
    ])

    # Simulated demand patterns
    demand = (
        people * factor
        + previous_demand * 0.25
        - current_stock * 0.15
        - donations * 0.20
        + day * 2
        + np.random.normal(0, 15, rows)
    )

    demand = np.maximum(demand, 1)

    return pd.DataFrame({
        "people_served": people,
        "previous_demand": previous_demand,
        "current_stock": current_stock,
        "donations_received": donations,
        "day_of_week": day,
        "food_category": category,
        "required_quantity": demand
    })


def prepare_features(data):

    X = data[FEATURES].copy()

    X["food_category"] = pd.Categorical(
        X["food_category"],
        categories=CATEGORIES
    )

    X = pd.get_dummies(
        X,
        columns=["food_category"],
        dtype=int
    )

    return X


def train_demand_model():

    os.makedirs("models", exist_ok=True)

    data = generate_training_data()

    X = prepare_features(data)
    y = data["required_quantity"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )

    models = {
        "Random Forest": RandomForestRegressor(
            n_estimators=150,
            max_depth=10,
            random_state=42
        ),

        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        )
    }

    results = []
    best_model = None
    best_mae = float("inf")
    best_name = None

    for name, model in models.items():

        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        mae = mean_absolute_error(
            y_test, predictions
        )

        rmse = np.sqrt(
            mean_squared_error(y_test, predictions)
        )

        r2 = r2_score(
            y_test, predictions
        )

        results.append({
            "Model": name,
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "R2 Score": round(r2, 3)
        })

        if mae < best_mae:

            best_mae = mae
            best_model = model
            best_name = name

    bundle = {
        "model": best_model,
        "model_name": best_name,
        "columns": list(X.columns),
        "metrics": results
    }

    joblib.dump(bundle, MODEL_PATH)

    return pd.DataFrame(results), best_name


def load_demand_model():

    if not os.path.exists(MODEL_PATH):

        train_demand_model()

    return joblib.load(MODEL_PATH)


def predict_ngo_demand():

    bundle = load_demand_model()

    # Get latest demand record for every NGO and category
    records = fetch_all("""
        SELECT
            n.ngo_id,
            n.ngo_name,
            n.people_served,
            nd.food_category,
            nd.required_quantity,
            nd.current_stock,
            nd.donations_received,
            nd.demand_date
        FROM ngo_demand nd
        JOIN ngos n ON nd.ngo_id = n.ngo_id
        JOIN (
            SELECT ngo_id, food_category,
                   MAX(demand_date) AS latest_date
            FROM ngo_demand
            GROUP BY ngo_id, food_category
        ) latest
        ON nd.ngo_id = latest.ngo_id
        AND nd.food_category = latest.food_category
        AND nd.demand_date = latest.latest_date
    """)

    if not records:

        return pd.DataFrame()

    data = pd.DataFrame(records)

    data["previous_demand"] = data["required_quantity"]

    # Predict for tomorrow
    tomorrow = pd.Timestamp.today() + pd.Timedelta(days=1)

    data["day_of_week"] = tomorrow.dayofweek

    X = data[FEATURES].copy()

    X = prepare_features(X)

    # Match training columns exactly
    X = X.reindex(
        columns=bundle["columns"],
        fill_value=0
    )

    predictions = bundle["model"].predict(X)

    data["predicted_demand"] = np.maximum(
        1, np.round(predictions)
    ).astype(int)

    data["predicted_shortage"] = np.maximum(
        0,
        data["predicted_demand"]
        - data["current_stock"]
        - data["donations_received"]
    )

    return data

def get_shortage_status(prediction_df):

    if prediction_df.empty:
        return prediction_df

    def classify_shortage(shortage):

        if shortage >= 50:
            return "Critical"

        elif shortage > 0:
            return "Needs Food"

        else:
            return "Sufficient"

    prediction_df["Status"] = prediction_df["predicted_shortage"].apply(
        classify_shortage
    )

    return prediction_df