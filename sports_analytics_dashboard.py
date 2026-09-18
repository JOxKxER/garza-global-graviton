"""Local informational sports analytics dashboard."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from sports_analytics_engine import (
    SQLiteStore,
    analyze_odds,
    american_to_probability,
    cashout_ev,
    compare_strategies,
    calculate_bears_titans_parlay,
)
from sports_modeling import (
    build_baselines,
    generate_predictions,
    normalize_injuries,
    normalize_historical_games,
    normalize_sentiment,
    aggregate_player_statistics,
    aggregate_coach_statistics,
    calculate_parlay_probability,
    estimate_event,
    score_public_headlines,
)

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "sports_analytics.example.json"
DB_PATH = ROOT / "sports_analytics.db"
MODELING_DATA_PATH = ROOT / "sports_modeling_data.json"
SOURCE_REGISTRY_PATH = ROOT / "sports_information_sources.json"
app = FastAPI(title="Graviton Sports Analytics", version="1.0.0")


class CashoutRequest(BaseModel):
    win_probability: float
    potential_payout: float
    cashout_offer: float


class StrategyRequest(BaseModel):
    model_probability: float
    prices: list[int]
    strategy: str = "straight"


class EventModelRequest(BaseModel):
    home_team: str
    away_team: str
    event_date: str
    home_stats: dict[str, float] = {}
    away_stats: dict[str, float] = {}
    injuries: dict[str, float] = {}
    headlines: list[dict[str, object]] = []
    player_statistics: list[dict[str, object]] = []
    coach_statistics: list[dict[str, object]] = []
    simulations: int = 10000


class ParlayRequest(BaseModel):
    legs: list[dict[str, object]]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "informational-only"}


@app.get("/api/odds")
def odds() -> dict[str, object]:
    frame = SQLiteStore(DB_PATH).records(limit=10000)
    if not frame.empty:
        frame = frame.sort_values(
            ["observed_at", "price_american"], ascending=[False, True]
        )
    return {"records": frame.to_dict(orient="records")}


@app.get("/api/current-odds")
def current_odds() -> dict[str, object]:
    """Return the freshest normalized observations for the dashboard."""
    frame = SQLiteStore(DB_PATH).records(limit=10000)
    if frame.empty:
        return {"records": []}
    frame = frame.sort_values("observed_at", ascending=False)
    return {"records": frame.head(100).to_dict(orient="records")}


@app.get("/api/analysis")
def analysis() -> dict[str, object]:
    return analyze_odds(SQLiteStore(DB_PATH).records())


@app.get("/api/categories")
def categories() -> dict[str, object]:
    """Return record counts by informational source category."""
    frame = SQLiteStore(DB_PATH).records()
    if frame.empty:
        return {"categories": {}}
    counts = frame["category"].value_counts().to_dict()
    return {
        "categories": {str(key): int(value) for key, value in counts.items()}
    }


@app.get("/api/predictions")
def predictions() -> dict[str, object]:
    """Return transparent model predictions from configured public data."""
    if not MODELING_DATA_PATH.exists():
        return {
            "predictions": [],
            "status": "modeling data not configured",
            "informational_only": True,
        }
    try:
        payload = json.loads(MODELING_DATA_PATH.read_text(encoding="utf-8"))
        games = normalize_historical_games(payload.get("games", []))
        injuries = normalize_injuries(payload.get("injuries", []))
        sentiment = normalize_sentiment(payload.get("sentiment", []))
        player_statistics = aggregate_player_statistics(
            payload.get("player_statistics", [])
        )
        coach_statistics = aggregate_coach_statistics(
            payload.get("coach_statistics", [])
        )
        odds_frame = SQLiteStore(DB_PATH).records()
        if not odds_frame.empty:
            odds_frame["implied_probability"] = odds_frame["price_american"].map(
                american_to_probability
            )
        return {
            "predictions": generate_predictions(
                games,
                injuries,
                sentiment,
                odds_frame,
                player_statistics,
                coach_statistics,
            ),
            "baselines": {
                team: baseline.__dict__
                for team, baseline in build_baselines(
                    games, injuries, sentiment
                ).items()
            },
            "player_statistics": player_statistics,
            "coach_statistics": coach_statistics,
            "informational_only": True,
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {
            "predictions": [],
            "status": f"modeling data error: {error}",
            "informational_only": True,
        }


@app.get("/api/information-sources")
def information_sources() -> dict[str, object]:
    """Describe public data structures and validation stages used by the app."""
    try:
        registry = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
        return registry
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Source registry unavailable: {error}",
        ) from error


@app.post("/api/event-model")
def event_model(request: EventModelRequest) -> dict[str, object]:
    """Model a selected event from user-supplied/publicly sourced inputs."""
    try:
        sentiment = score_public_headlines(request.headlines)
        player_data = aggregate_player_statistics(request.player_statistics)
        coach_data = aggregate_coach_statistics(request.coach_statistics)
        return estimate_event(
            request.home_team,
            request.away_team,
            request.event_date,
            request.home_stats,
            request.away_stats,
            request.injuries,
            sentiment,
            player_data,
            coach_data,
            simulations=request.simulations,
        )
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/parlay-probability")
def parlay_probability(request: ParlayRequest) -> dict[str, object]:
    """Calculate a non-transactional probability estimate for entered legs."""
    try:
        return calculate_parlay_probability(request.legs)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
@app.get("/api/bears-titans-parlay")
def bears_titans_parlay() -> dict[str, object]:
    """Calculate the latest matching Bears/Titans informational setup."""
    return calculate_bears_titans_parlay(SQLiteStore(DB_PATH).records())


@app.post("/api/strategy")
def strategy(request: StrategyRequest) -> dict[str, object]:
    try:
        return compare_strategies(
            request.model_probability, request.prices, request.strategy
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/cashout-ev")
def cashout(request: CashoutRequest) -> dict[str, object]:
    try:
        return cashout_ev(
            request.win_probability,
            request.potential_payout,
            request.cashout_offer,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Graviton Sports Analytics</title><style>
:root{font-family:Georgia,serif;font-weight:600;color:#15211f;background:#e9eee8}body{margin:0;font-size:18px}.wrap{max-width:1100px;margin:auto;padding:28px}header{display:flex;justify-content:space-between;align-items:end;border-bottom:3px solid #15211f;padding-bottom:18px}h1{font-size:clamp(2.4rem,5vw,4.4rem);font-weight:900;margin:0;letter-spacing:0}.stamp{font:700 14px monospace;text-transform:uppercase}.toolbar{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:20px 0}.toolbar button{border:1px solid #15211f;background:#15211f;color:#f9fbf6;padding:12px 16px;cursor:pointer;font:700 14px monospace;text-transform:uppercase}.toolbar button:hover{background:#a03c25}.toolbar button:disabled{opacity:.55;cursor:wait}.badge{display:inline-flex;align-items:center;gap:6px;border:2px solid #aab6aa;padding:10px 12px;font:700 13px monospace;text-transform:uppercase}.badge::before{content:"";width:9px;height:9px;border-radius:50%;background:#a03c25}.badge.ready::before{background:#287d58}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:22px}.panel{background:#f9fbf6;border:1px solid #aab6aa;padding:18px;min-height:170px}.panel h2{margin-top:0;font-size:1.3rem;font-weight:900}.wide{grid-column:span 2}.metric{font-size:2.6rem;font-weight:900;color:#a03c25}.muted{color:#46544d;font-weight:600;line-height:1.5}.marker-list{display:grid;gap:8px}.marker{border-left:5px solid #287d58;background:#e1f0e5;padding:11px 13px;font:700 14px monospace}.marker small{display:block;color:#46544d;margin-top:4px;font-weight:600}.odds-table{width:100%;border-collapse:collapse;font:700 14px monospace;background:#fff}.odds-table th,.odds-table td{border-bottom:1px solid #cbd5cc;padding:10px 8px;text-align:left}.odds-table th{background:#15211f;color:#f9fbf6}.odds-table tr.priority{background:#e1f0e5}.odds-table .probability{color:#287d58;font-weight:900}.event-time{display:block;color:#58645d;font-size:12px;margin-top:3px;font-weight:600}pre{white-space:pre-wrap;font:600 14px monospace;background:#15211f;color:#e9eee8;padding:12px;min-height:100px}@media(max-width:760px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}header{display:block}.stamp{display:block;margin-top:10px}.toolbar button{flex:1 1 130px}.odds-table{font-size:12px}.odds-table th,.odds-table td{padding:8px 5px}}
</style></head><body><main class="wrap"><header><h1>Graviton Sports Analytics</h1><span class="stamp">Local / informational only</span></header>
<p class="muted">Odds comparison, statistical signals, and live-state modeling. No wagering, transactions, or bet placement.</p>
<nav class="toolbar" aria-label="Dashboard controls"><button id="refresh" type="button">Refresh data</button><button id="analysis" type="button">Refresh signals</button><span class="badge" id="status">Connecting</span><span class="badge" id="updated">No update</span><span class="badge" id="local-clock">Local time</span></nav><article class="panel" id="model-panel"><h2>Quantitative model</h2><p class="muted">Public historical baselines, injury context, sentiment, and market context. Informational model output only.</p><pre id="predictions">Loading model output...</pre></article><article class="panel" id="source-panel"><h2>Public data structure</h2><p class="muted">Source fields, provenance, validation, and processing stages used by this dashboard.</p><pre id="source-registry">Loading source registry...</pre></article>
<section class="grid"><article class="panel wide"><h2>Most Current Odds</h2><p class="muted">Freshest permitted observations appear first. These are informational market signals, not safe or guaranteed outcomes.</p><div id="category-counts" class="marker-list">Loading categories...</div><div id="odds">Loading current odds...</div></article><article class="panel"><h2>Signal monitor</h2><div class="metric" id="count">--</div><p class="muted">stored odds observations</p><pre id="signals">Loading analysis...</pre></article><article class="panel"><h2>Bears / Titans setup</h2><p class="muted">Latest available lines for Bears +2, Titans -2.5, Over 37.5, and Chicago Bears moneyline. Missing live lines remain unfilled.</p><div id="parlay">Loading parlay data...</div></article><article class="panel"><h2>Threshold signals</h2><p class="muted">Informational markers for categories at or above the 60% implied-probability threshold. This is not a safe-bet claim or wagering advice.</p><div class="marker-list" id="markers">Loading markers...</div></article><article class="panel"><h2>Model notes</h2><p class="muted">Sportsbook odds and prediction-market data are shown in separate categories. Event times are localized to your browser timezone.</p><p class="muted">Data freshness and model error can materially affect results.</p></article></section></main><script>
const refreshButton=document.getElementById('refresh'),analysisButton=document.getElementById('analysis'),statusBadge=document.getElementById('status'),updatedBadge=document.getElementById('updated');
function localTime(value){if(!value)return 'Time unavailable';const parsed=new Date(value);return Number.isNaN(parsed.getTime())?'Time unavailable':parsed.toLocaleString([], {dateStyle:'medium',timeStyle:'short'})}
function renderCategories(records){const counts={};records.forEach(record=>{counts[record.category||'uncategorized']=(counts[record.category||'uncategorized']||0)+1});document.getElementById('category-counts').innerHTML=Object.entries(counts).map(([category,count])=>`<div class="marker">${category.toUpperCase()}<small>${count} records in this category</small></div>`).join('')||'<div class="marker">No categories yet.</div>'}
function spreadText(record){if(record.market!=='spreads'||record.point===null||record.point===undefined)return '';const team=record.outcome;return record.point>0?`${team} can lose by no more than ${record.point} points`:`${team} must win by ${Math.ceil(Math.abs(record.point))} or more points`}
function renderOdds(records){const sorted=[...records].map(record=>{const probability=record.price_american<0?Math.abs(record.price_american)/(Math.abs(record.price_american)+100):100/(record.price_american+100);return {...record,probability}}).sort((a,b)=>b.probability-a.probability).slice(0,30);const rows=sorted.map(record=>`<tr class="${record.probability>=.60?'priority':''}"><td>${record.outcome}<span class="event-time">${record.home_team} vs ${record.away_team}<br>${localTime(record.commence_time)}</span></td><td>${record.category||'uncategorized'} / ${record.market}</td><td>${record.bookmaker}</td><td class="probability">${(record.probability*100).toFixed(1)}%</td><td>${record.price_american>0?'+':''}${record.price_american}${record.point===null||record.point===undefined?'':`<span class="event-time">${record.point>0?'+':''}${record.point} · ${spreadText(record)}</span>`}</td></tr>`).join('');document.getElementById('odds').innerHTML=`<table class="odds-table"><thead><tr><th>Outcome / event</th><th>Category / market</th><th>Reference</th><th>Implied probability</th><th>Price / spread meaning</th></tr></thead><tbody>${rows||'<tr><td colspan="5">No odds snapshots available.</td></tr>'}</tbody></table>`}
function renderMarkers(records){const threshold=.60;const groups={};records.forEach(record=>{const probability=record.price_american<0?Math.abs(record.price_american)/(Math.abs(record.price_american)+100):100/(record.price_american+100);if(probability>=threshold){const key=(record.category||'uncategorized')+' / '+record.market;groups[key]??=[];groups[key].push({record,probability})}});const html=Object.entries(groups).map(([market,items])=>{const best=items.sort((a,b)=>b.probability-a.probability)[0];return `<div class="marker">${market.toUpperCase()} · ${best.record.outcome}<small>${(best.probability*100).toFixed(1)}% implied · ${best.record.bookmaker}</small></div>`}).join('');document.getElementById('markers').innerHTML=html||'<div class="marker">No threshold signals yet.<small>Waiting for current odds snapshots.</small></div>'}
function updateClock(){document.getElementById('local-clock').textContent='Local '+new Date().toLocaleTimeString()}
async function loadPredictions(){try{const response=await fetch('/api/predictions');const data=await response.json();document.getElementById('predictions').textContent=JSON.stringify({predictions:data.predictions,baselines:data.baselines,status:data.status,informational_only:data.informational_only},null,2)}catch(error){document.getElementById('predictions').textContent=error.message}}
async function loadSources(){try{const response=await fetch('/api/information-sources');const data=await response.json();document.getElementById('source-registry').textContent=JSON.stringify({source_types:data.source_types,processing_stages:data.processing_stages},null,2)}catch(error){document.getElementById('source-registry').textContent=error.message}}
function renderParlay(data){const target=document.getElementById('parlay');if(!data.available){target.innerHTML='<p class="muted">'+(data.message||'Current lines unavailable.')+'</p>';return}const legRows=Object.entries(data.legs).map(([name,leg])=>`<div class="marker">${name.replaceAll('_',' ').toUpperCase()} · ${(leg.implied_probability*100).toFixed(2)}%<small>${leg.price_american>0?'+':''}${leg.price_american} · ${leg.bookmaker} · observed ${localTime(leg.observed_at)}</small></div>`).join('');target.innerHTML=legRows+`<div class="metric">${(data.combined_implied_percent).toFixed(4)}%</div><p class="muted">Combined product estimate, assuming independent legs. Informational only.</p>`}
async function load(){refreshButton.disabled=true;analysisButton.disabled=true;statusBadge.textContent='Refreshing';statusBadge.className='badge';try{const [o,a,p]=await Promise.all([fetch('/api/current-odds').then(r=>r.json()),fetch('/api/analysis').then(r=>r.json()),fetch('/api/bears-titans-parlay').then(r=>r.json())]);document.getElementById('count').textContent=a.records??0;const records=o.records||[];renderCategories(records);renderOdds(records);renderMarkers(records);renderParlay(p);document.getElementById('signals').textContent=JSON.stringify({movements:a.line_movements,anomalies:a.anomalies},null,2);statusBadge.textContent='Live';statusBadge.className='badge ready';updatedBadge.textContent='Updated '+new Date().toLocaleTimeString();updateClock()}catch(error){statusBadge.textContent='Offline';statusBadge.className='badge';document.getElementById('signals').textContent=error.message}finally{refreshButton.disabled=false;analysisButton.disabled=false}}
refreshButton.addEventListener('click',load);analysisButton.addEventListener('click',load);load();loadPredictions();loadSources();updateClock();setInterval(load,30000);setInterval(loadPredictions,30000);setInterval(loadSources,30000);setInterval(updateClock,1000);
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sports_analytics_dashboard:app", host="127.0.0.1", port=8090)
