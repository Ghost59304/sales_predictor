"""
Sales Forecasting Machine Learning Pipeline
Academic Project: Satyug Darshan Institute of Engineering & Technology (J.C. Bose UST YMCA)
Students: Sachin Kumar & Sagar Kumar | Guides: Ms. Shivani Bansal, Ms. Nikita Narang
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

CSV_PATH = os.path.join(DATA_DIR, "historical_sales_data.csv")
METRICS_PATH = os.path.join(MODELS_DIR, "model_metrics.json")
PRODUCTS_META_PATH = os.path.join(MODELS_DIR, "products_metadata.json")

PRODUCTS_CATALOG = [
    {"product_id": "PRD-101", "name": "Smartphone Pro Max", "category": "Electronics", "base_price": 999.0, "cost_price": 650.0},
    {"product_id": "PRD-102", "name": "Ultra Slim Laptop 15\"", "category": "Electronics", "base_price": 1299.0, "cost_price": 880.0},
    {"product_id": "PRD-103", "name": "Wireless Noise-Cancelling ANC Headphones", "category": "Audio & Accessories", "base_price": 249.0, "cost_price": 140.0},
    {"product_id": "PRD-104", "name": "4K Ultra HD Smart LED TV 55\"", "category": "Electronics", "base_price": 649.0, "cost_price": 420.0},
    {"product_id": "PRD-105", "name": "Smart Fitness Tracker Watch", "category": "Audio & Accessories", "base_price": 179.0, "cost_price": 95.0},
    {"product_id": "PRD-106", "name": "Running Cushion Pro Shoes", "category": "Apparel & Footwear", "base_price": 119.0, "cost_price": 55.0},
    {"product_id": "PRD-107", "name": "Premium Cotton Oxford Casual Shirt", "category": "Apparel & Footwear", "base_price": 49.0, "cost_price": 20.0},
    {"product_id": "PRD-108", "name": "Classic Stretch Denim Jeans", "category": "Apparel & Footwear", "base_price": 69.0, "cost_price": 32.0},
    {"product_id": "PRD-109", "name": "Digital Air Fryer Deluxe 5.5L", "category": "Home & Kitchen", "base_price": 129.0, "cost_price": 70.0},
    {"product_id": "PRD-110", "name": "Barista Espresso & Cappuccino Machine", "category": "Home & Kitchen", "base_price": 299.0, "cost_price": 175.0},
    {"product_id": "PRD-111", "name": "Ergonomic Lumbar High-Back Office Chair", "category": "Home & Kitchen", "base_price": 219.0, "cost_price": 120.0},
    {"product_id": "PRD-112", "name": "Organic Herbal Green Tea 100pk", "category": "Groceries & FMCG", "base_price": 24.0, "cost_price": 9.0},
    {"product_id": "PRD-113", "name": "Cold-Pressed Extra Virgin Olive Oil 1L", "category": "Groceries & FMCG", "base_price": 29.0, "cost_price": 14.0},
    {"product_id": "PRD-114", "name": "Hydrating Hyaluronic Facial Serum 50ml", "category": "Health & Beauty", "base_price": 39.0, "cost_price": 12.0},
    {"product_id": "PRD-115", "name": "Cordless Handheld Vacuum Cleaner", "category": "Home & Kitchen", "base_price": 159.0, "cost_price": 85.0}
]

REGIONS = ["North", "South", "East", "West", "Central"]
STORE_TYPES = ["Online Flagship", "Retail Store", "Direct-to-Consumer", "Superstore Partner"]

def generate_synthetic_historical_data(start_date="2023-01-01", end_date="2026-11-15", seed=42):
    """
    Generates realistic historical sales data with seasonal, weekly,
    promotional, and price-elasticity dynamics.
    """
    np.random.seed(seed)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1

    records = []
    
    # Yearly growth rate ~ 10%
    for day_idx in range(total_days):
        current_date = start_dt + timedelta(days=day_idx)
        year = current_date.year
        month = current_date.month
        day = current_date.day
        day_of_week = current_date.weekday() # 0 = Monday, 6 = Sunday
        is_weekend = 1 if day_of_week in [5, 6] else 0
        quarter = (month - 1) // 3 + 1

        # Holiday flags (Diwali in Oct/Nov, Black Friday in late Nov, Christmas in Dec, New Year in Jan)
        is_holiday = 0
        if (month == 10 and day >= 20) or (month == 11 and day <= 15):
            is_holiday = 1 # Festive/Diwali season
        elif month == 11 and day >= 22:
            is_holiday = 1 # Black Friday / Cyber Week
        elif month == 12 and day >= 18:
            is_holiday = 1 # Christmas & Year-End shopping
        elif month == 1 and day <= 5:
            is_holiday = 1 # New Year sales

        # Sample 8 to 12 products per day across different regions to produce a rich dataset
        num_sales_events = np.random.randint(8, 14)
        selected_prods = np.random.choice(PRODUCTS_CATALOG, size=num_sales_events, replace=True)

        for prod in selected_prods:
            region = np.random.choice(REGIONS)
            store_type = np.random.choice(STORE_TYPES)
            
            # Promotion probability is higher on weekends or holidays
            promo_prob = 0.45 if (is_weekend or is_holiday) else 0.18
            is_promo = 1 if (np.random.rand() < promo_prob) else 0

            # Discount
            if is_promo:
                discount_pct = float(np.random.choice([10.0, 15.0, 20.0, 25.0, 30.0]))
            else:
                discount_pct = 0.0

            unit_price = prod["base_price"]

            # Base daily demand depends on product category & price tier
            if prod["category"] == "Groceries & FMCG":
                base_qty = 35.0
            elif prod["category"] == "Apparel & Footwear":
                base_qty = 22.0
            elif prod["category"] == "Health & Beauty":
                base_qty = 18.0
            elif prod["category"] == "Audio & Accessories":
                base_qty = 14.0
            elif prod["category"] == "Home & Kitchen":
                base_qty = 10.0
            else: # Electronics
                base_qty = 7.0

            # Multipliers
            # 1. Year trend (+9% per year from 2023)
            trend_mult = 1.0 + (year - 2023) * 0.09
            
            # 2. Day of week (Weekend boost +35% to +50%)
            dow_mult = 1.42 if is_weekend else 1.0
            if day_of_week == 4: # Friday evening bump
                dow_mult = 1.18

            # 3. Monthly / Seasonal factor
            # Q4 (Oct, Nov, Dec) is peak retail; Jan-Feb slightly slower
            month_mult_map = {
                1: 0.88, 2: 0.90, 3: 0.98, 4: 1.02, 5: 1.05, 6: 1.08,
                7: 1.12, 8: 1.15, 9: 1.18, 10: 1.35, 11: 1.55, 12: 1.65
            }
            season_mult = month_mult_map.get(month, 1.0)
            
            # 4. Holiday boost
            holiday_mult = 1.40 if is_holiday else 1.0

            # 5. Promotional elasticity (+4% demand per 5% discount)
            promo_mult = 1.0 + (discount_pct / 100.0) * 1.5 if is_promo else 1.0

            # 6. Store type boost
            store_mult = 1.25 if store_type == "Online Flagship" else 1.0

            # Expected quantity
            expected_qty = (base_qty * trend_mult * dow_mult * season_mult * holiday_mult * promo_mult * store_mult)
            
            # Add Gaussian noise
            noise = np.random.normal(0, max(1.2, expected_qty * 0.10))
            quantity_sold = int(max(1, round(expected_qty + noise)))

            # Actual revenue
            effective_price = unit_price * (1.0 - discount_pct / 100.0)
            revenue = round(quantity_sold * effective_price, 2)
            cost_amount = round(quantity_sold * prod["cost_price"], 2)
            gross_profit = round(revenue - cost_amount, 2)

            records.append({
                "Date": current_date.strftime("%Y-%m-%d"),
                "Year": year,
                "Month": month,
                "Day": day,
                "DayOfWeek": day_of_week,
                "Quarter": quarter,
                "IsWeekend": is_weekend,
                "Product_ID": prod["product_id"],
                "Product_Name": prod["name"],
                "Category": prod["category"],
                "Region": region,
                "Store_Type": store_type,
                "Unit_Price": unit_price,
                "Discount_Percent": discount_pct,
                "Promotion_Active": is_promo,
                "Holiday_Season": is_holiday,
                "Quantity_Sold": quantity_sold,
                "Sales_Amount": revenue,
                "Cost_Amount": cost_amount,
                "Gross_Profit": gross_profit
            })

    df = pd.DataFrame(records)
    df.to_csv(CSV_PATH, index=False)
    print(f"Generated synthetic historical dataset with {len(df)} records saved to {CSV_PATH}")
    return df

def build_features(df):
    """
    Enriches dataset with cyclical calendar features, lag/moving average indicators.
    """
    df = df.copy()
    # Ensure Date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"])

    # Cyclical representations of month and day of week
    df["Month_Sin"] = np.sin(2 * np.pi * df["Month"] / 12.0)
    df["Month_Cos"] = np.cos(2 * np.pi * df["Month"] / 12.0)
    df["DOW_Sin"] = np.sin(2 * np.pi * df["DayOfWeek"] / 7.0)
    df["DOW_Cos"] = np.cos(2 * np.pi * df["DayOfWeek"] / 7.0)
    return df

def train_and_evaluate_models(df=None):
    """
    Prepares data, trains 4 ML models, evaluates performance metrics,
    and serializes models and metrics for dashboard consumption.
    """
    if df is None:
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
        else:
            df = generate_synthetic_historical_data()

    df = build_features(df)

    # Feature definitions
    categorical_features = ["Product_Name", "Category", "Region", "Store_Type"]
    numerical_features = [
        "Year", "Month", "Day", "DayOfWeek", "Quarter", "IsWeekend",
        "Month_Sin", "Month_Cos", "DOW_Sin", "DOW_Cos",
        "Unit_Price", "Discount_Percent", "Promotion_Active", "Holiday_Season"
    ]

    X = df[categorical_features + numerical_features]
    y_qty = df["Quantity_Sold"]
    y_rev = df["Sales_Amount"]

    # Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )

    # Train / Test split
    X_train, X_test, y_train, y_test, y_rev_train, y_rev_test = train_test_split(
        X, y_qty, y_rev, test_size=0.20, random_state=42
    )

    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=12, min_samples_split=10, random_state=42),
        "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=14, min_samples_split=6, n_jobs=-1, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=120, max_depth=5, learning_rate=0.1, random_state=42)
    }

    metrics_results = {}
    fitted_pipelines = {}

    for model_name, model in models.items():
        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", model)
        ])
        
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        
        # Clip negative predictions to zero
        y_pred = np.maximum(y_pred, 0)

        # Performance evaluation
        mse = mean_squared_error(y_test, y_pred)
        rmse = float(np.sqrt(mse))
        mae = float(mean_absolute_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))
        
        # MAPE: Mean Absolute Percentage Error (avoid division by 0)
        non_zero_mask = y_test > 0
        mape = float(np.mean(np.abs((y_test[non_zero_mask] - y_pred[non_zero_mask]) / y_test[non_zero_mask])) * 100)

        # Calculate revenue accuracy
        unit_prices_test = X_test["Unit_Price"].values
        discounts_test = X_test["Discount_Percent"].values
        pred_rev = y_pred * unit_prices_test * (1.0 - discounts_test / 100.0)
        rev_rmse = float(np.sqrt(mean_squared_error(y_rev_test, pred_rev)))
        rev_r2 = float(r2_score(y_rev_test, pred_rev))

        metrics_results[model_name] = {
            "r2_score": round(r2, 4),
            "rmse": round(rmse, 3),
            "mae": round(mae, 3),
            "mape": round(mape, 2),
            "rev_rmse": round(rev_rmse, 2),
            "rev_r2": round(rev_r2, 4),
            "is_best": False
        }

        # Save model pipeline
        model_filename = os.path.join(MODELS_DIR, f"{model_name.replace(' ', '_').lower()}_pipeline.joblib")
        joblib.dump(pipeline, model_filename)
        fitted_pipelines[model_name] = pipeline
        print(f"Model [{model_name}] -> R2: {r2:.4f}, RMSE: {rmse:.3f}, MAE: {mae:.3f}, MAPE: {mape:.2f}%")

    # Determine best model based on R2 score
    best_model_name = max(metrics_results, key=lambda k: metrics_results[k]["r2_score"])
    metrics_results[best_model_name]["is_best"] = True

    # Feature Importance extraction (from Random Forest or Gradient Boosting)
    rf_pipeline = fitted_pipelines["Random Forest"]
    rf_regressor = rf_pipeline.named_steps["regressor"]
    onehot_encoder = rf_pipeline.named_steps["preprocessor"].named_transformers_["cat"]
    cat_feature_names = list(onehot_encoder.get_feature_names_out(categorical_features))
    all_feature_names = numerical_features + cat_feature_names
    importances = rf_regressor.feature_importances_

    # Top 12 most important features
    top_indices = np.argsort(importances)[::-1][:12]
    top_features = [{"feature": all_feature_names[i], "importance": round(float(importances[i]), 4)} for i in top_indices]

    # Overall dataset statistics
    dataset_summary = {
        "total_records": len(df),
        "date_start": str(df["Date"].min())[:10],
        "date_end": str(df["Date"].max())[:10],
        "total_revenue": round(float(df["Sales_Amount"].sum()), 2),
        "total_units_sold": int(df["Quantity_Sold"].sum()),
        "average_order_value": round(float(df["Sales_Amount"].mean()), 2),
        "total_gross_profit": round(float(df["Gross_Profit"].sum()), 2),
        "best_model": best_model_name
    }

    full_metrics = {
        "models": metrics_results,
        "feature_importances": top_features,
        "dataset_summary": dataset_summary,
        "last_trained": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(full_metrics, f, indent=2)

    with open(PRODUCTS_META_PATH, "w") as f:
        json.dump(PRODUCTS_CATALOG, f, indent=2)

    print(f"Model training complete. Best model: {best_model_name}. Metadata saved.")
    return full_metrics

if __name__ == "__main__":
    print("Starting Sales Forecasting Model Training Pipeline...")
    generate_synthetic_historical_data()
    train_and_evaluate_models()
