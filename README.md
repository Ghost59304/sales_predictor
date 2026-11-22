# Sales Forecasting System Using Machine Learning
**A Data-Driven Predictive Analytics & Inventory Demand Planning Dashboard**

> **Academic Project Synopsis Reference**  
> **Institution:** Satyug Darshan Institute of Engineering & Technology, Faridabad – 121001  
> **Affiliation:** J.C. Bose University of Science and Technology, YMCA (Formerly YMCA UST)  
> **Department:** Department of Computer Science & Engineering  
> **Students:** Sachin Kumar (24020004101), Sagar Kumar (24020004102) — B.Tech (CSE), Section B2  
> **Faculty Guides:** Ms. Shivani Bansal, Ms. Nikita Narang  
> **Project Duration:** 08/09/2026 – 30/11/2026  

---

## 1. Problem Statement & Motivation
Businesses frequently encounter challenges when estimating future customer demand due to shifting market dynamics, seasonal holiday spikes, regional variances, and pricing elasticities. Faulty estimates lead directly to **overstocking, costly stock shortages, inefficient capital allocation, and supply chain disruptions**.

This project provides an end-to-end, deployable **Sales Forecasting System** that analyzes multi-year historical sales records and employs state-of-the-art machine learning regression algorithms to forecast future sales quantities, revenues, and inventory reorder points with high precision.

---

## 2. Core Features & Capabilities

### 📊 Executive Analytics & Visualizations
- **Historical Sales Trajectory:** Monthly revenue, units sold, and gross profit trends spanning multiple years with seasonal Q4 lifts.
- **Ground Truth vs. ML Model Predictions:** Real-time visual comparison showing how closely the trained models track historical sales observations.
- **Multi-Dimensional Breakdowns:** Category share doughnut chart, regional performance bar charts, and day-of-week seasonality curves.
- **Top Revenue Drivers:** Automated ranking of top-performing products by total revenue and unit transactions.

### 🔮 Interactive Single Forecast Calculator
- **Dynamic Inputs:** Select any future date, product, geographic zone (North, South, East, West, Central), and sales channel (Online Flagship, Retail Store, DTC, Superstore Partner).
- **Price Elasticity & Promotions:** Test custom base unit prices and promotional discounts (0% to 40% off) with live elasticity simulation.
- **Instant ML Inference:** Generates predicted units, expected revenue, estimated profit, and profit margins.
- **Inventory & Supply Chain Guidance:** Automatic calculation of recommended safety buffer stock, reorder point (ROP), and stockout risk assessment.

### 📈 Multi-Day Horizon Demand Planner (7 to 90 Days)
- **Scenario Simulation:** Choose between Standard Baseline, Weekend Flash Sales, or Aggressive Campaigns.
- **Confidence Bands:** 90% and 95% confidence intervals (shaded upper/lower bounds) reflecting model standard error.
- **Timeline Export:** Download full day-by-day projected demand schedules as CSV or JSON.

### 🧠 Model Comparison & Explainability Matrix
- Rigorous comparative evaluation of **4 regression architectures**:
  1. **Linear Regression** (Baseline)
  2. **Decision Tree Regressor**
  3. **Random Forest Regressor** (Ensemble Bagging)
  4. **Gradient Boosting Regressor** (Ensemble Boosting - Best Performer: **96.7% R²**)
- Metrics computed: **R² Score**, **RMSE**, **MAE**, **MAPE (%)**, and **Revenue R²**.
- **Feature Importance:** Ranks top predictive factors (e.g., `Unit_Price`, `Holiday_Season`, `Category`, `Discount_Percent`, `DayOfWeek`).

### 📂 Custom Dataset Upload & Retraining
- Drag-and-drop CSV upload for custom enterprise or store datasets.
- Schema verification and automatic on-the-fly model retraining.
- Downloadable sample CSV template (`sample_sales_data_template.csv`).

### 🎓 Academic Synopsis Portal
- Complete interactive academic documentation tab with student details, faculty guide credentials, problem statement, objectives, and methodology flowcharts.

---

## 3. Machine Learning Benchmark Results

| Model Architecture | Status | R² Score (Units) | RMSE (Units) | MAE (Units) | MAPE (%) | Revenue R² |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gradient Boosting** | **★ Best** | **96.70%** | **3.997** | **2.571** | **9.10%** | **97.07%** |
| **Random Forest** | Strong | 95.64% | 4.595 | 2.875 | 10.10% | 96.25% |
| **Decision Tree** | Good | 93.04% | 5.805 | 3.440 | 11.61% | 94.75% |
| **Linear Regression** | Baseline | 86.36% | 8.128 | 5.352 | 24.05% | 55.84% |

---

## 4. Technology Stack
- **Backend & API:** Python 3.12+, Flask 3.1+, Flask-CORS, Gunicorn
- **Data & ML:** Scikit-learn 1.6+, Pandas 2.2+, NumPy 2.0+, Joblib
- **Frontend UI:** HTML5, Tailwind CSS (Dark/Light mode support), Chart.js 4.4+, FontAwesome 6
- **Deployment:** Docker, Docker Compose, Gunicorn WSGI, Procfile (Heroku / Render / Railway)

---

## 5. Quickstart & Local Execution

### Prerequisites
- Python 3.10+ (Recommended: Python 3.12)
- pip

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: (Optional) Re-run Data Generation & Training
```bash
python model_pipeline.py
```

### Step 3: Launch Web Application
- **On Windows:** Double-click `run.bat` or run:
  ```powershell
  python app.py
  ```
- **On Linux/macOS:**
  ```bash
  chmod +x run.sh && ./run.sh
  ```
Open your browser and navigate to: **[http://localhost:5000](http://localhost:5000)**

---

## 6. Docker Container Deployment

To run in an isolated Docker container:

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Or build manually
docker build -t sales-forecasting .
docker run -p 5000:5000 sales-forecasting
```

Access at `http://localhost:5000`.

---

## 7. Cloud Deployment (Render / Heroku / Railway)

The repository includes a ready-to-use `Procfile` and `wsgi.py`.

### Deploying to Render:
1. Push code to GitHub.
2. Log into [Render](https://render.com) and create a **New Web Service**.
3. Select your repository.
4. Set:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python model_pipeline.py`
   - **Start Command:** `gunicorn wsgi:app`
5. Click **Deploy Web Service**.

---

## 8. REST API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web application dashboard UI |
| `GET` | `/api/overview` | Overall sales statistics, top products, and best model name |
| `GET` | `/api/analytics` | Monthly trends, category distribution, regional demand, and day-of-week patterns |
| `GET` | `/api/actual_vs_predicted` | 45-day comparison of actual historical sales vs. ML predictions |
| `GET` | `/api/models` | Performance metrics across all 4 ML models and feature importances |
| `GET` | `/api/products` | Catalog of products with base prices, categories, and cost prices |
| `POST` | `/api/predict` | Real-time single scenario sales and inventory forecast |
| `POST` | `/api/forecast_horizon` | Multi-day forward demand projection (7, 14, 30, 60, 90 days) |
| `POST` | `/api/upload_csv` | Upload custom sales dataset and automatically trigger pipeline retraining |
| `GET` | `/api/export_sample_csv` | Download sample CSV template |
| `GET` | `/api/project_synopsis` | Academic project details conforming to college submission |
