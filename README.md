# Crypto Market Agent

**Live:** [crypto-market-agent.vercel.app](https://crypto-market-agent.vercel.app/)

An alternative investment analytics platform for cryptocurrency market data. Explore historical rankings by market cap, run AI-powered queries, and analyze sector dynamics through interactive dashboards.

## Features

- **Quarterly Snapshots** — Top N coins by market cap across quarters (2020+)
- **AI Chat Agent** — Conversational interface powered by GPT-4o with tool-calling for natural language crypto queries
- **Correlation Matrix** — Price correlation heatmaps across assets
- **Risk Metrics** — Sharpe ratio, Sortino ratio, max drawdown, VaR (95%/99%)
- **Sector Rotation** — Aggregated performance by sector (Layer 1, DeFi, Meme, AI, RWA, etc.)
- **CSV Export** — Download filtered datasets for further analysis

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.10, FastAPI, OpenAI GPT-4o, Pandas, NumPy |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Data | CoinGecko Pro API, Joblib caching |
| Deployment | Railway (backend), Vercel (frontend) |

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [CoinGecko Pro API key](https://www.coingecko.com/en/api)
- [OpenAI API key](https://platform.openai.com/)

### Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
COINGECKO_API_KEY=your-key
ALLOWED_ORIGINS=http://localhost:5173   # comma-separated origins for CORS
BASE_URL=http://localhost:8000          # used for CSV download links
```

### Backend

```bash
python -m venv priceandmc
source priceandmc/bin/activate
pip install -r requirements.txt
uvicorn src.api.server:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Vite proxies `/api` requests to the backend.

### CLI Agent

```bash
python -m src.main
```

Interactive REPL — type crypto questions, `reset` to clear history, `quit` to exit.

## Project Structure

```
src/
  main.py              # CLI entry point
  api/server.py        # FastAPI REST API
  agent/agent.py       # AI agent with tool-calling loop
  agent/tools.py       # Tools exposed to GPT-4o
  data/coingecko_client.py  # CoinGecko API client with caching
  data/analytics.py    # Correlation, risk metrics, sector analysis
  data/date_utils.py   # Quarter boundary utilities
frontend/
  src/pages/           # Dashboard, Explorer, Correlation, Risk, Sectors
  src/components/      # Charts, tables, filters, AI chat widget
  src/api/             # API client
database/              # Joblib-cached snapshots
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/top-coins` | Top N coins at quarter boundaries (filterable) |
| `GET /api/top-coins/export` | CSV download |
| `GET /api/coin/{id}` | Single coin snapshot at a date |
| `GET /api/coin/{id}/history` | Time-series data (quarterly/monthly/yearly) |
| `GET /api/analytics/correlation` | Price correlation matrix |
| `GET /api/analytics/risk-metrics` | Sharpe, Sortino, drawdown, VaR |
| `GET /api/analytics/sectors` | Sector performance aggregation |
| `GET /api/quarters` | Available quarter dates |
| `GET /api/sectors` | Token categories |
| `POST /api/chat` | AI agent conversation |

## Deployment

**Backend** deploys on Railway via Nixpacks (see `Procfile` and `railway.json`).

**Frontend** deploys on Vercel (see `frontend/vercel.json`). Set `VITE_API_URL` to your backend URL in Vercel environment settings.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

MIT
