"""
Flask Web Application & API for Sales Forecasting System
Academic Project: Satyug Darshan Institute of Engineering & Technology (J.C. Bose UST YMCA)
Students: Sachin Kumar & Sagar Kumar | Guides: Ms. Shivani Bansal, Ms. Nikita Narang
"""

import os
import io
import json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import joblib
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS

from model_pipeline import (
    DATA_DIR, MODELS_DIR, CSV_PATH, METRICS_PATH, PRODUCTS_META_PATH,
    PRODUCTS_CATALOG, REGIONS, STORE_TYPES,
    build_features, train_and_evaluate_models
)

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Cached models and metadata
LOADED_MODELS = {}
CACHED_METRICS = None
CACHED_DATASET = None

def get_holiday_status(dt):
    month = dt.month
    day = dt.day
    if (month == 10 and day >= 20) or (month == 11 and day <= 15):
        return 1
    elif month == 11 and day >= 22:
        return 1
    elif month == 12 and day >= 18:
        return 1
    elif month == 1 and day <= 5:
        return 1
    return 0

def load_models_and_metadata():
    global LOADED_MODELS, CACHED_METRICS, CACHED_DATASET
    
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, "r") as f:
            CACHED_METRICS = json.load(f)
    else:
        CACHED_METRICS = train_and_evaluate_models()

    if os.path.exists(CSV_PATH):
        CACHED_DATASET = pd.read_csv(CSV_PATH)
        CACHED_DATASET["Date"] = pd.to_datetime(CACHED_DATASET["Date"])
    
    # Load model pipelines
    model_names = ["Linear Regression", "Decision Tree", "Random Forest", "Gradient Boosting"]
    for m in model_names:
        fpath = os.path.join(MODELS_DIR, f"{m.replace(' ', '_').lower()}_pipeline.joblib")
        if os.path.exists(fpath):
            try:
                LOADED_MODELS[m] = joblib.load(fpath)
            except Exception as e:
                print(f"Warning: could not load {m}: {e}")

load_models_and_metadata()

def get_product_by_name(product_name):
    global CACHED_DATASET
    if CACHED_DATASET is not None and not CACHED_DATASET.empty:
        match = CACHED_DATASET[CACHED_DATASET["Product_Name"].astype(str).str.lower() == str(product_name).lower()]
        if not match.empty:
            cat = str(match["Category"].iloc[0])
            price = float(match["Unit_Price"].iloc[0])
            cost = round(price * 0.65, 2)
            if "Cost_Amount" in match.columns and match["Quantity_Sold"].iloc[0] > 0:
                cost = round(float(match["Cost_Amount"].iloc[0] / match["Quantity_Sold"].iloc[0]), 2)
            return {"product_id": "PRD-CUSTOM", "name": product_name, "category": cat, "base_price": price, "cost_price": cost}

    for p in PRODUCTS_CATALOG:
        if p["name"].lower() == str(product_name).lower():
            return p
    return PRODUCTS_CATALOG[0]

def construct_feature_dataframe(records):
    """
    Constructs a DataFrame suitable for the trained ColumnTransformer pipeline.
    """
    rows = []
    for r in records:
        dt = pd.to_datetime(r["Date"])
        year = dt.year
        month = dt.month
        day = dt.day
        day_of_week = dt.weekday()
        is_weekend = 1 if day_of_week in [5, 6] else 0
        quarter = (month - 1) // 3 + 1
        holiday = get_holiday_status(dt) if "Holiday_Season" not in r else int(r["Holiday_Season"])

        month_sin = np.sin(2 * np.pi * month / 12.0)
        month_cos = np.cos(2 * np.pi * month / 12.0)
        dow_sin = np.sin(2 * np.pi * day_of_week / 7.0)
        dow_cos = np.cos(2 * np.pi * day_of_week / 7.0)

        rows.append({
            "Product_Name": r["Product_Name"],
            "Category": r["Category"],
            "Region": r["Region"],
            "Store_Type": r["Store_Type"],
            "Year": year,
            "Month": month,
            "Day": day,
            "DayOfWeek": day_of_week,
            "Quarter": quarter,
            "IsWeekend": is_weekend,
            "Month_Sin": month_sin,
            "Month_Cos": month_cos,
            "DOW_Sin": dow_sin,
            "DOW_Cos": dow_cos,
            "Unit_Price": float(r["Unit_Price"]),
            "Discount_Percent": float(r.get("Discount_Percent", 0.0)),
            "Promotion_Active": int(r.get("Promotion_Active", 0)),
            "Holiday_Season": holiday
        })
    return pd.DataFrame(rows)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/overview", methods=["GET"])
def api_overview():
    global CACHED_DATASET, CACHED_METRICS
    if CACHED_DATASET is None and os.path.exists(CSV_PATH):
        CACHED_DATASET = pd.read_csv(CSV_PATH)
        CACHED_DATASET["Date"] = pd.to_datetime(CACHED_DATASET["Date"])

    df = CACHED_DATASET
    summary = CACHED_METRICS.get("dataset_summary", {}) if CACHED_METRICS else {}
    
    # Calculate top products
    top_prods_df = df.groupby("Product_Name").agg(
        total_revenue=("Sales_Amount", "sum"),
        total_units=("Quantity_Sold", "sum"),
        avg_price=("Unit_Price", "mean"),
        category=("Category", "first")
    ).reset_index().sort_values(by="total_revenue", ascending=False).head(5)

    top_products = []
    for _, row in top_prods_df.iterrows():
        top_products.append({
            "name": row["Product_Name"],
            "category": row["category"],
            "revenue": round(float(row["total_revenue"]), 2),
            "units": int(row["total_units"]),
            "avg_price": round(float(row["avg_price"]), 2)
        })

    # Recent 30 days total
    latest_date = df["Date"].max()
    thirty_days_ago = latest_date - pd.Timedelta(days=30)
    recent_df = df[df["Date"] >= thirty_days_ago]
    recent_revenue = round(float(recent_df["Sales_Amount"].sum()), 2)
    recent_units = int(recent_df["Quantity_Sold"].sum())

    return jsonify({
        "status": "success",
        "summary": summary,
        "recent_30_days": {
            "revenue": recent_revenue,
            "units": recent_units
        },
        "top_products": top_products,
        "best_model": summary.get("best_model", "Gradient Boosting")
    })

@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    global CACHED_DATASET
    df = CACHED_DATASET.copy()

    # 1. Monthly Revenue & Quantity Time Series
    df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
    monthly = df.groupby("YearMonth").agg(
        revenue=("Sales_Amount", "sum"),
        units=("Quantity_Sold", "sum"),
        profit=("Gross_Profit", "sum")
    ).reset_index().sort_values("YearMonth")

    monthly_data = {
        "labels": monthly["YearMonth"].tolist(),
        "revenue": [round(float(v), 2) for v in monthly["revenue"]],
        "units": [int(v) for v in monthly["units"]],
        "profit": [round(float(v), 2) for v in monthly["profit"]]
    }

    # 2. Category Distribution
    cat_df = df.groupby("Category").agg(
        revenue=("Sales_Amount", "sum"),
        units=("Quantity_Sold", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    category_data = {
        "labels": cat_df["Category"].tolist(),
        "revenue": [round(float(v), 2) for v in cat_df["revenue"]],
        "units": [int(v) for v in cat_df["units"]]
    }

    # 3. Regional Sales Breakdown
    reg_df = df.groupby("Region").agg(
        revenue=("Sales_Amount", "sum"),
        units=("Quantity_Sold", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    region_data = {
        "labels": reg_df["Region"].tolist(),
        "revenue": [round(float(v), 2) for v in reg_df["revenue"]],
        "units": [int(v) for v in reg_df["units"]]
    }

    # 4. Store Type Breakdown
    store_df = df.groupby("Store_Type").agg(
        revenue=("Sales_Amount", "sum"),
        units=("Quantity_Sold", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    store_data = {
        "labels": store_df["Store_Type"].tolist(),
        "revenue": [round(float(v), 2) for v in store_df["revenue"]],
        "units": [int(v) for v in store_df["units"]]
    }

    # 5. Day of Week Pattern (0=Mon, 6=Sun)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_df = df.groupby("DayOfWeek").agg(
        avg_units=("Quantity_Sold", "mean"),
        total_revenue=("Sales_Amount", "sum")
    ).reset_index().sort_values("DayOfWeek")
    
    dow_data = {
        "labels": [day_names[int(i)] for i in dow_df["DayOfWeek"]],
        "avg_units": [round(float(v), 1) for v in dow_df["avg_units"]],
        "total_revenue": [round(float(v), 2) for v in dow_df["total_revenue"]]
    }

    # 6. Promotion Impact
    promo_df = df.groupby("Promotion_Active").agg(
        avg_units=("Quantity_Sold", "mean"),
        avg_revenue=("Sales_Amount", "mean")
    ).reset_index()

    promo_impact = {
        "non_promo": {
            "avg_units": round(float(promo_df[promo_df["Promotion_Active"] == 0]["avg_units"].values[0]), 1),
            "avg_revenue": round(float(promo_df[promo_df["Promotion_Active"] == 0]["avg_revenue"].values[0]), 2)
        },
        "promo": {
            "avg_units": round(float(promo_df[promo_df["Promotion_Active"] == 1]["avg_units"].values[0]), 1),
            "avg_revenue": round(float(promo_df[promo_df["Promotion_Active"] == 1]["avg_revenue"].values[0]), 2)
        }
    }

    return jsonify({
        "status": "success",
        "monthly": monthly_data,
        "category": category_data,
        "region": region_data,
        "store": store_data,
        "day_of_week": dow_data,
        "promo_impact": promo_impact
    })

@app.route("/api/actual_vs_predicted", methods=["GET"])
def api_actual_vs_predicted():
    """
    Returns the latest 45 daily observations aggregated across products
    with actual sales vs model predicted sales for visual validation.
    """
    global CACHED_DATASET, LOADED_MODELS, CACHED_METRICS
    df = CACHED_DATASET.copy()
    
    # Take the last 45 distinct dates
    unique_dates = df["Date"].drop_duplicates().sort_values(ascending=False).head(45).sort_values()
    subset = df[df["Date"].isin(unique_dates)].copy()

    best_model_name = CACHED_METRICS.get("dataset_summary", {}).get("best_model", "Gradient Boosting")
    model = LOADED_MODELS.get(best_model_name)

    feat_df = construct_feature_dataframe(subset.to_dict(orient="records"))
    preds_qty = model.predict(feat_df)
    preds_qty = np.maximum(preds_qty, 0)
    
    # Calculate predicted sales amount
    effective_prices = subset["Unit_Price"].values * (1.0 - subset["Discount_Percent"].values / 100.0)
    subset["Pred_Quantity"] = preds_qty
    subset["Pred_Revenue"] = preds_qty * effective_prices

    # Daily aggregation
    daily = subset.groupby(subset["Date"].dt.strftime("%Y-%m-%d")).agg(
        actual_revenue=("Sales_Amount", "sum"),
        pred_revenue=("Pred_Revenue", "sum"),
        actual_units=("Quantity_Sold", "sum"),
        pred_units=("Pred_Quantity", "sum")
    ).reset_index().sort_values("Date")

    return jsonify({
        "status": "success",
        "model_used": best_model_name,
        "dates": daily["Date"].tolist(),
        "actual_revenue": [round(float(v), 2) for v in daily["actual_revenue"]],
        "pred_revenue": [round(float(v), 2) for v in daily["pred_revenue"]],
        "actual_units": [int(round(v)) for v in daily["actual_units"]],
        "pred_units": [int(round(v)) for v in daily["pred_units"]]
    })

@app.route("/api/models", methods=["GET"])
def api_models():
    global CACHED_METRICS
    if CACHED_METRICS is None and os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, "r") as f:
            CACHED_METRICS = json.load(f)

    return jsonify({
        "status": "success",
        "models": CACHED_METRICS.get("models", {}),
        "feature_importances": CACHED_METRICS.get("feature_importances", []),
        "last_trained": CACHED_METRICS.get("last_trained", "")
    })

@app.route("/api/products", methods=["GET"])
def api_products():
    global CACHED_DATASET
    prods = []
    if CACHED_DATASET is not None and not CACHED_DATASET.empty:
        unique_prods = CACHED_DATASET.groupby("Product_Name").agg(
            category=("Category", "first"),
            base_price=("Unit_Price", "mean")
        ).reset_index()
        for idx, row in unique_prods.iterrows():
            p_price = round(float(row["base_price"]), 2)
            prods.append({
                "product_id": f"PRD-{idx+1:03d}",
                "name": str(row["Product_Name"]),
                "category": str(row["category"]),
                "base_price": p_price,
                "cost_price": round(p_price * 0.65, 2)
            })
    if not prods:
        prods = PRODUCTS_CATALOG

    regions = [str(r) for r in CACHED_DATASET["Region"].dropna().unique().tolist()] if (CACHED_DATASET is not None and "Region" in CACHED_DATASET.columns) else REGIONS
    store_types = [str(s) for s in CACHED_DATASET["Store_Type"].dropna().unique().tolist()] if (CACHED_DATASET is not None and "Store_Type" in CACHED_DATASET.columns) else STORE_TYPES

    return jsonify({
        "status": "success",
        "products": prods,
        "regions": regions,
        "store_types": store_types
    })

@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(force=True) or {}
    
    product_name = data.get("product_name", "Smartphone Pro Max")
    prod_meta = get_product_by_name(product_name)
    category = data.get("category", prod_meta["category"])
    
    date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    region = data.get("region", "North")
    store_type = data.get("store_type", "Online Flagship")
    unit_price = float(data.get("unit_price", prod_meta["base_price"]))
    discount_pct = float(data.get("discount_percent", 0.0))
    promo_active = int(data.get("promotion_active", 1 if discount_pct > 0 else 0))
    
    model_name = data.get("model_name")
    if not model_name or model_name not in LOADED_MODELS:
        model_name = CACHED_METRICS.get("dataset_summary", {}).get("best_model", "Gradient Boosting")

    pipeline = LOADED_MODELS.get(model_name)
    if pipeline is None:
        return jsonify({"status": "error", "message": f"Model {model_name} is not loaded."}), 400

    single_record = [{
        "Date": date_str,
        "Product_Name": product_name,
        "Category": category,
        "Region": region,
        "Store_Type": store_type,
        "Unit_Price": unit_price,
        "Discount_Percent": discount_pct,
        "Promotion_Active": promo_active
    }]

    input_df = construct_feature_dataframe(single_record)
    predicted_qty = float(pipeline.predict(input_df)[0])
    predicted_qty = max(0.0, predicted_qty)
    rounded_qty = max(1, int(round(predicted_qty)))

    effective_price = unit_price * (1.0 - discount_pct / 100.0)
    predicted_revenue = round(rounded_qty * effective_price, 2)
    estimated_cost = round(rounded_qty * prod_meta["cost_price"], 2)
    estimated_profit = round(predicted_revenue - estimated_cost, 2)
    margin_pct = round((estimated_profit / predicted_revenue * 100.0), 1) if predicted_revenue > 0 else 0.0

    # Uncertainty / Confidence Interval based on model RMSE
    model_rmse = CACHED_METRICS.get("models", {}).get(model_name, {}).get("rmse", 4.0)
    lower_qty = max(0, int(round(predicted_qty - 1.96 * model_rmse * 0.6)))
    upper_qty = int(round(predicted_qty + 1.96 * model_rmse * 0.6))
    lower_rev = round(lower_qty * effective_price, 2)
    upper_rev = round(upper_qty * effective_price, 2)

    # Inventory Recommendation
    # Safety stock = 1.65 * std_dev (lead time assumed 3 days)
    safety_stock = int(round(1.65 * model_rmse * np.sqrt(3)))
    reorder_point = int(round(rounded_qty * 3 + safety_stock))
    
    # Stockout risk evaluation
    if promo_active and discount_pct >= 20:
        stockout_risk = "High (Promo Spike)"
        inventory_action = f"High demand anticipated due to {discount_pct}% discount. Pre-allocate at least {reorder_point} units in regional fulfillment hubs."
    elif rounded_qty > 25:
        stockout_risk = "Moderate"
        inventory_action = f"Strong baseline volume expected. Maintain safety buffer of {safety_stock} units to prevent stockouts."
    else:
        stockout_risk = "Low (Stable)"
        inventory_action = f"Routine demand pattern. Standard replenishment order of {reorder_point} units is optimal."

    return jsonify({
        "status": "success",
        "inputs": {
            "date": date_str,
            "product_name": product_name,
            "category": category,
            "region": region,
            "store_type": store_type,
            "unit_price": unit_price,
            "discount_percent": discount_pct,
            "promotion_active": promo_active,
            "model_used": model_name
        },
        "forecast": {
            "predicted_quantity": rounded_qty,
            "raw_quantity": round(predicted_qty, 2),
            "predicted_revenue": predicted_revenue,
            "estimated_cost": estimated_cost,
            "estimated_profit": estimated_profit,
            "profit_margin_percent": margin_pct,
            "effective_price": round(effective_price, 2),
            "confidence_interval": {
                "lower_units": lower_qty,
                "upper_units": upper_qty,
                "lower_revenue": lower_rev,
                "upper_revenue": upper_rev
            },
            "inventory": {
                "recommended_safety_stock": safety_stock,
                "reorder_point": reorder_point,
                "stockout_risk": stockout_risk,
                "inventory_action": inventory_action
            }
        }
    })

@app.route("/api/forecast_horizon", methods=["POST"])
def api_forecast_horizon():
    data = request.get_json(force=True) or {}
    
    product_name = data.get("product_name", "Smartphone Pro Max")
    prod_meta = get_product_by_name(product_name)
    category = data.get("category", prod_meta["category"])
    region = data.get("region", "North")
    store_type = data.get("store_type", "Online Flagship")
    horizon_days = int(data.get("horizon_days", 30))
    start_date_str = data.get("start_date", datetime.now().strftime("%Y-%m-%d"))
    promo_scenario = data.get("promo_scenario", "promo_weekends") # 'none', 'promo_weekends', 'aggressive'
    unit_price = float(data.get("unit_price", prod_meta["base_price"]))

    model_name = data.get("model_name")
    if not model_name or model_name not in LOADED_MODELS:
        model_name = CACHED_METRICS.get("dataset_summary", {}).get("best_model", "Gradient Boosting")

    pipeline = LOADED_MODELS.get(model_name)
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")

    records = []
    for day_i in range(horizon_days):
        cur_dt = start_dt + timedelta(days=day_i)
        dow = cur_dt.weekday()
        is_weekend = dow in [5, 6]

        if promo_scenario == "promo_weekends":
            is_promo = 1 if is_weekend else 0
            discount = 15.0 if is_promo else 0.0
        elif promo_scenario == "aggressive":
            is_promo = 1
            discount = 25.0
        else: # none
            is_promo = 0
            discount = 0.0

        records.append({
            "Date": cur_dt.strftime("%Y-%m-%d"),
            "Product_Name": product_name,
            "Category": category,
            "Region": region,
            "Store_Type": store_type,
            "Unit_Price": unit_price,
            "Discount_Percent": discount,
            "Promotion_Active": is_promo
        })

    feat_df = construct_feature_dataframe(records)
    preds = pipeline.predict(feat_df)
    preds = np.maximum(preds, 0)

    model_rmse = CACHED_METRICS.get("models", {}).get(model_name, {}).get("rmse", 4.0)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    timeline = []
    total_qty = 0
    total_rev = 0.0
    peak_qty = 0
    peak_date = ""

    for idx, r in enumerate(records):
        q = max(1, int(round(preds[idx])))
        cur_dt = datetime.strptime(r["Date"], "%Y-%m-%d")
        eff_price = unit_price * (1.0 - r["Discount_Percent"] / 100.0)
        rev = round(q * eff_price, 2)
        low_q = max(0, int(round(q - 1.65 * model_rmse * 0.5)))
        high_q = int(round(q + 1.65 * model_rmse * 0.5))

        total_qty += q
        total_rev += rev

        if q > peak_qty:
            peak_qty = q
            peak_date = r["Date"]

        timeline.append({
            "date": r["Date"],
            "day_name": day_names[cur_dt.weekday()],
            "is_weekend": bool(cur_dt.weekday() in [5, 6]),
            "is_promo": bool(r["Promotion_Active"]),
            "discount_pct": r["Discount_Percent"],
            "predicted_quantity": q,
            "predicted_revenue": rev,
            "lower_quantity": low_q,
            "upper_quantity": high_q
        })

    avg_daily_qty = round(total_qty / horizon_days, 1)
    recommended_total_inventory = int(round(total_qty * 1.15)) # 15% safety stock buffer

    return jsonify({
        "status": "success",
        "meta": {
            "product_name": product_name,
            "horizon_days": horizon_days,
            "start_date": start_date_str,
            "promo_scenario": promo_scenario,
            "model_used": model_name
        },
        "aggregate": {
            "total_forecasted_units": total_qty,
            "total_forecasted_revenue": round(total_rev, 2),
            "average_daily_units": avg_daily_qty,
            "peak_demand_date": peak_date,
            "peak_demand_units": peak_qty,
            "recommended_total_inventory": recommended_total_inventory
        },
        "timeline": timeline
    })

@app.route("/api/upload_csv", methods=["POST"])
def api_upload_csv():
    """
    Allows user to upload a custom sales dataset, checks columns,
    and updates the dataset cache.
    """
    global CACHED_DATASET
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file part in request"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"}), 400

    try:
        df = pd.read_csv(file)
        # Check required columns
        required_cols = ["Date", "Product_Name", "Category", "Unit_Price", "Quantity_Sold", "Sales_Amount"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        
        if missing_cols:
            return jsonify({
                "status": "error",
                "message": f"Uploaded CSV missing required columns: {missing_cols}. Expected: {required_cols}"
            }), 400

        # Preprocess dates & fill defaults
        df["Date"] = pd.to_datetime(df["Date"])
        if "Region" not in df.columns:
            df["Region"] = "North"
        if "Store_Type" not in df.columns:
            df["Store_Type"] = "Online Flagship"
        if "Discount_Percent" not in df.columns:
            df["Discount_Percent"] = 0.0
        if "Promotion_Active" not in df.columns:
            df["Promotion_Active"] = 0
        if "Gross_Profit" not in df.columns:
            df["Gross_Profit"] = df["Sales_Amount"] * 0.35

        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month
        df["Day"] = df["Date"].dt.day
        df["DayOfWeek"] = df["Date"].dt.weekday
        df["Quarter"] = df["Date"].dt.quarter
        df["IsWeekend"] = df["DayOfWeek"].isin([5, 6]).astype(int)
        df["Holiday_Season"] = df["Date"].apply(get_holiday_status)

        # If uploaded dataset is small (< 100 records), merge into existing historical data
        # so models have sufficient volume for 80/20 train/test evaluation!
        if len(df) < 100 and CACHED_DATASET is not None and not CACHED_DATASET.empty:
            df = pd.concat([CACHED_DATASET, df], ignore_index=True)
            df = df.drop_duplicates(subset=["Date", "Product_Name", "Region", "Store_Type"], keep="last")

        # Save to data directory
        df.to_csv(CSV_PATH, index=False)
        CACHED_DATASET = df
        
        # Trigger retraining
        new_metrics = train_and_evaluate_models(df)
        load_models_and_metadata()

        preview_rows = df.head(8)[["Date", "Product_Name", "Category", "Unit_Price", "Quantity_Sold", "Sales_Amount"]].to_dict(orient="records")
        for r in preview_rows:
            r["Date"] = str(r["Date"])[:10]
            r["Unit_Price"] = round(float(r["Unit_Price"]), 2)
            r["Quantity_Sold"] = int(r["Quantity_Sold"])
            r["Sales_Amount"] = round(float(r["Sales_Amount"]), 2)

        return jsonify({
            "status": "success",
            "message": f"Successfully loaded dataset and retrained ML models on {len(df):,} records!",
            "records_count": len(df),
            "date_range": [str(df['Date'].min())[:10], str(df['Date'].max())[:10]],
            "preview": preview_rows
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to parse CSV: {str(e)}"}), 500

@app.route("/api/export_sample_csv", methods=["GET"])
def api_export_sample_csv():
    """
    Downloads a sample CSV template for users to view formatting.
    """
    sample_df = pd.DataFrame([
        {
            "Date": "2026-11-20",
            "Product_Name": "Smartphone Pro Max",
            "Category": "Electronics",
            "Region": "North",
            "Store_Type": "Online Flagship",
            "Unit_Price": 999.0,
            "Discount_Percent": 10.0,
            "Promotion_Active": 1,
            "Quantity_Sold": 14,
            "Sales_Amount": 12587.40,
            "Gross_Profit": 4400.0
        },
        {
            "Date": "2026-11-20",
            "Product_Name": "Running Cushion Pro Shoes",
            "Category": "Apparel & Footwear",
            "Region": "West",
            "Store_Type": "Retail Store",
            "Unit_Price": 119.0,
            "Discount_Percent": 0.0,
            "Promotion_Active": 0,
            "Quantity_Sold": 24,
            "Sales_Amount": 2856.0,
            "Gross_Profit": 1536.0
        }
    ])
    
    output = io.StringIO()
    sample_df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="sample_sales_data_template.csv"
    )

@app.route("/api/project_synopsis", methods=["GET"])
def api_project_synopsis():
    """
    Returns verified academic project synopsis details from the project document.
    """
    return jsonify({
        "status": "success",
        "project": {
            "title": "Sales Forecasting Using Machine Learning",
            "institution": "Satyug Darshan Institute of Engineering & Technology",
            "university": "J.C. Bose University of Science and Technology, YMCA (Formerly YMCA UST)",
            "department": "Department of Computer Science & Engineering",
            "students": [
                {
                    "name": "Sachin Kumar",
                    "enrolment_no": "24020004101",
                    "programme": "B.Tech (CSE), Section B2",
                    "email": "sachinkumar.cse24@satyug.edu.in",
                    "phone": "8506087601"
                },
                {
                    "name": "Sagar Kumar",
                    "enrolment_no": "24020004102",
                    "programme": "B.Tech (CSE), Section B2",
                    "email": "sagarkumar1.cse24@satyug.edu.in",
                    "phone": "7531099259"
                }
            ],
            "guides": [
                {"name": "Ms. Shivani Bansal", "designation": "Assistant Professor / Faculty Guide"},
                {"name": "Ms. Nikita Narang", "designation": "Assistant Professor / Faculty Guide"}
            ],
            "timeline": {
                "commencement": "08/09/2026",
                "completion": "30/11/2026"
            },
            "college_address": "Bhupani Vasudhara Road, Faridabad – 121001",
            "problem_statement": "Businesses often face difficulties in accurately predicting future sales due to changing customer preferences, seasonal demand, market conditions, and historical fluctuations. Incorrect sales estimates can result in overstocking, stock shortages, inefficient resource allocation, and financial losses. Therefore, there is a need for a reliable Sales Forecasting System that can analyze historical sales data and predict future sales.",
            "objectives": [
                "To analyze historical sales data.",
                "To identify sales trends and patterns.",
                "To preprocess and clean the dataset.",
                "To develop a machine learning model for sales prediction.",
                "To predict future sales based on historical information.",
                "To display the results through graphs and visualizations.",
                "To help businesses improve inventory and sales planning."
            ],
            "methodology_steps": [
                "1. Data Collection (Date, Product, Quantity, Price, Sales Amount)",
                "2. Data Preprocessing (Handling missing values, duplicate records, outliers)",
                "3. Exploratory Data Analysis (Monthly/yearly sales trends, seasonal patterns)",
                "4. Feature Engineering (Month, Year, Day, Day of Week, Cyclical Trigs, Holiday Flags)",
                "5. Model Building (Linear Regression, Decision Tree, Random Forest, Gradient Boosting)",
                "6. Prediction (Forecasting future sales quantity and revenue)",
                "7. Evaluation (RMSE, MAE, R² Score, MAPE)",
                "8. Visualization (Interactive executive charts, actual vs predicted, inventory gauges)"
            ],
            "technologies": [
                "Python 3.12+",
                "Flask RESTful Framework",
                "Scikit-learn (Ensemble & Regression)",
                "Pandas & NumPy (Data Processing)",
                "Chart.js & Tailwind CSS (Interactive Visualizations)"
            ]
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
