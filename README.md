# DataVista

DataVista is a production-minded AI business analytics platform built with FastAPI, Streamlit, SQLite, Pandas, Plotly, scikit-learn, Google Gemini, and ReportLab.

Users can upload private business datasets, clean and analyze them, explore interactive dashboards, train practical ML models, generate grounded AI insights, chat with their data, receive recommendations, and export professional PDF reports.

## Features

- Secure registration, login, logout, remember-me sessions, password hashing, protected routes, profile settings, and account deletion
- User-scoped dataset workspaces with CSV/Excel upload, duplicate upload prevention, rename, delete, re-analysis, cleaned downloads, and dataset history
- Automatic data cleaning with duplicate removal, missing-value handling, type inference, date standardization, outlier detection/removal, quality scoring, and recommendations
- Exploratory analytics for sales, customers, products, regions, time trends, distributions, and correlations
- Interactive dashboard with drill-down filters, KPI cards, trend charts, bar charts, scatter plots, treemaps, and heatmaps
- Machine learning for sales forecasting, churn modeling, and customer segmentation
- Gemini-powered business insights and dataset chat assistant with strict supplied-context guardrails
- Business Health Score and Data Quality Score with explanations
- Smart recommendations for promotions, discontinuation, regional attention, upsell, cross-sell, inventory, pricing, and customer actions
- Executive PDF Report Center with formatted KPIs, charts, readable recommendations, report history, download, and delete
- Notification Center, rotating file logging, security headers, upload validation, and cached dataframe reads
- Comprehensive pytest suite

## Architecture

```text
backend/
  app.py                 FastAPI app factory and middleware
  ai/                    Gemini client, insights, dataset chat
  analytics/             Cleaning, EDA, dashboard data, recommendations
  auth/                  Schemas, password/JWT security, repositories
  dashboard/             Workspace metrics and business health scoring
  database/              SQLite connection and schema initialization
  datasets/              Upload, storage, metadata, lifecycle services
  ml/                    Forecasting, churn, segmentation
  reports/               PDF generation and report repository
  routes/                API route modules
  utils/                 Logging, security headers, dataframe cache
frontend/
  app.py                 Streamlit entry point
  components/            Feature UI modules
  utils/api.py           Frontend API client
tests/                   Feature and endpoint tests
```

## Requirements

- Python 3.12 or 3.13
- pip
- Optional: Docker Desktop
- Optional for AI features: Google Gemini API key

Recommended VS Code extensions:

- Python
- Pylance
- Ruff
- Docker

## Installation

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` before production or portfolio demo use:

- Set `SECRET_KEY` to a long random value.
- Set `GEMINI_API_KEY` to enable AI Insights and AI Chat.
- Keep `GEMINI_MODEL=gemini-2.5-flash` unless you intentionally choose another supported Gemini model.

## Run

Backend:

```bash
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload
```

Frontend:

```bash
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

Open:

- Frontend: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Docker

```bash
docker compose up --build
```

Backend runs on port `8000`; frontend runs on port `8501`.

## Testing

```bash
.\.venv\Scripts\python.exe -m pytest
```

The suite covers authentication, dataset management, cleaning, analytics, interactive dashboards, ML, AI prompt modules, report generation, notifications, settings, security, logging, and performance cache behavior.

Release verification:

```bash
.\.venv\Scripts\python.exe -m compileall backend frontend tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
```

## Environment Variables

- `APP_NAME`: Application/API display name
- `ENVIRONMENT`: Runtime environment label
- `SECRET_KEY`: JWT signing secret
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Base session lifetime
- `DATABASE_URL`: SQLite URL, for example `sqlite:///./database/datavista.db`
- `UPLOAD_DIR`: Original uploaded dataset directory
- `CLEANED_DATA_DIR`: Cleaned CSV directory
- `LOG_DIR`: Rotating log directory
- `MAX_UPLOAD_MB`: Upload size limit
- `BACKEND_CORS_ORIGINS`: Comma-separated Streamlit origins
- `GEMINI_API_KEY`: Required for live Gemini requests
- `GEMINI_MODEL`: Gemini model name

## Dataset Guidance

DataVista works best with business CSV/XLSX files containing some of these columns:

- Date: `order_date`, `date`, `transaction_date`
- Revenue: `revenue`, `sales`, `amount`
- Profit: `profit`, `gross_profit`, `net_profit`
- Order: `order_id`, `invoice_id`
- Customer: `customer_id`, `customer_name`
- Product/category: `product`, `product_name`, `category`
- Geography: `region`, `state`, `country`
- ML churn: `churn`, `churned`, `is_churned` with binary values

Recommended public demo datasets:

- Superstore-style retail sales datasets
- Online retail transaction datasets
- Customer churn datasets with binary churn labels

Upload datasets through the Streamlit UI. No manual placement is required.

CSV uploads automatically try `utf-8`, `utf-8-sig`, `latin1`, and `cp1252` encodings before reporting a parsing failure. Duplicate files are blocked per user workspace.

## API Overview

Authentication:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `PATCH /auth/me`
- `PATCH /auth/password`
- `PATCH /auth/preferences`
- `DELETE /auth/me`

Datasets and analytics:

- `POST /datasets`
- `GET /datasets`
- `GET /datasets/{dataset_id}`
- `PATCH /datasets/{dataset_id}`
- `POST /datasets/{dataset_id}/reanalyze`
- `GET /datasets/{dataset_id}/analysis`
- `POST /datasets/{dataset_id}/analysis`
- `GET /datasets/{dataset_id}/dashboard-data`
- `POST /datasets/{dataset_id}/ml`
- `POST /datasets/{dataset_id}/insights`
- `POST /datasets/{dataset_id}/chat`
- `GET /datasets/{dataset_id}/recommendations`
- `GET /datasets/{dataset_id}/download-cleaned`
- `DELETE /datasets/{dataset_id}`

Reports and workspace:

- `GET /dashboard/summary`
- `GET /notifications`
- `GET /reports`
- `POST /reports`
- `GET /reports/{report_id}/download`
- `DELETE /reports/{report_id}`

## Reports

Generate PDF reports from the Report Center in the Streamlit app. Reports include dataset overview, KPIs, product/customer summaries, recommendations, forecasts when available, and optional AI insights.

## Troubleshooting

- `Gemini is not configured`: set `GEMINI_API_KEY` in `.env`.
- Upload rejected by content type: make sure the file extension and actual file type match.
- No churn model: include a binary churn column and enough numeric customer behavior fields.
- No forecast: include a date column and at least three dated revenue periods.
- Empty dashboard sections: the dataset may not contain the semantic columns required for that analysis.

## Future Improvements

- Async job queue for long-running reports and AI requests
- More granular report chart rendering
- OAuth/SAML enterprise authentication
- PostgreSQL deployment option
- Role-based access control for teams
