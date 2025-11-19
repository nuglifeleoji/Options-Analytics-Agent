"""
FastAPI Microservice for Options Tools
Provides HTTP API endpoints for options data search, CSV export, and charting
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
import json
import csv
import os
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Options Tools API",
    description="Microservice for stock options data retrieval and analysis",
    version="1.0.0"
)

# Get API key from environment
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
if not POLYGON_API_KEY:
    raise RuntimeError("POLYGON_API_KEY not found in environment variables. Please set it in .env file.")


# ========== Request Models ==========

class SearchOptionsRequest(BaseModel):
    ticker: str
    date: str  # YYYY-MM or YYYY-MM-DD
    limit: int = 100

class MakeCSVRequest(BaseModel):
    data: dict
    ticker: str

class PlotChartRequest(BaseModel):
    data: dict
    ticker: str


# ========== Response Models ==========

class OptionsDataResponse(BaseModel):
    results: list
    count: int
    total_available: int
    message: str

class CSVResponse(BaseModel):
    status: str
    filename: str
    rows: int

class ChartResponse(BaseModel):
    status: str
    filename: str
    total_calls: int
    total_puts: int


# ========== Health Check ==========

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Options Tools Microservice",
        "status": "running",
        "endpoints": {
            "search_options": "/api/search_options",
            "make_csv": "/api/make_csv",
            "plot_chart": "/api/plot_chart"
        }
    }


# ========== Tool Endpoints ==========

@app.post("/api/search_options", response_model=OptionsDataResponse)
async def search_options(request: SearchOptionsRequest):
    """
    Search for options contracts
    
    Args:
        ticker: Stock symbol (e.g., 'AAPL')
        date: Expiration date (YYYY-MM-DD) or month (YYYY-MM)
        limit: Maximum number of contracts to return (default: 100, max: 1000)
    
    Returns:
        Options data with contract details
    """
    try:
        ticker = request.ticker.upper()
        date = request.date
        limit = min(max(request.limit, 1), 1000)
        
        # Call Polygon API
        url = "https://api.polygon.io/v3/reference/options/contracts"
        params = {
            "underlying_ticker": ticker,
            "limit": 1000,
            "apiKey": POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, 
                              detail=f"Polygon API error: {response.status_code}")
        
        data = response.json()
        all_contracts = data.get('results', [])
        
        # Filter by date
        if len(date) == 7:  # Month format
            filtered = [c for c in all_contracts if c.get('expiration_date', '').startswith(date)]
        else:  # Specific date
            filtered = [c for c in all_contracts if c.get('expiration_date') == date]
        
        # Limit results
        limited_results = filtered[:limit] if len(filtered) > limit else filtered
        
        return OptionsDataResponse(
            results=limited_results,
            count=len(limited_results),
            total_available=len(filtered),
            message=f"Showing {len(limited_results)} of {len(filtered)} contracts"
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/make_csv", response_model=CSVResponse)
async def make_csv(request: MakeCSVRequest):
    """
    Export options data to CSV file
    
    Args:
        data: Options data dict with 'results' array
        ticker: Stock ticker for filename
    
    Returns:
        CSV file creation status and filename
    """
    try:
        contracts = request.data.get('results', [])
        
        if not contracts:
            raise HTTPException(status_code=400, detail="No contracts data provided")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        first_exp_date = contracts[0].get('expiration_date', '') if contracts else ''
        
        if first_exp_date:
            exp_month = first_exp_date[:7]
            csv_filename = f"{request.ticker}_options_{exp_month}_{timestamp}.csv"
        else:
            csv_filename = f"{request.ticker}_options_{timestamp}.csv"
        
        # Write CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ticker', 'contract_type', 'strike_price', 'expiration_date', 
                         'exercise_style', 'shares_per_contract']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for contract in contracts:
                writer.writerow({
                    'ticker': contract.get('ticker', ''),
                    'contract_type': contract.get('contract_type', '').upper(),
                    'strike_price': contract.get('strike_price', 0),
                    'expiration_date': contract.get('expiration_date', ''),
                    'exercise_style': contract.get('exercise_style', ''),
                    'shares_per_contract': contract.get('shares_per_contract', 100)
                })
        
        return CSVResponse(
            status="success",
            filename=csv_filename,
            rows=len(contracts)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV creation failed: {str(e)}")


@app.post("/api/plot_chart", response_model=ChartResponse)
async def plot_chart(request: PlotChartRequest):
    """
    Create butterfly chart visualization
    
    Args:
        data: Options data dict with 'results' array
        ticker: Stock ticker for chart title
    
    Returns:
        Chart creation status and filename
    """
    try:
        contracts = request.data.get('results', [])
        
        if not contracts:
            raise HTTPException(status_code=400, detail="No contracts data provided")
        
        # Count contracts by strike price and type
        calls_dict = {}
        puts_dict = {}
        
        for contract in contracts:
            strike = contract.get('strike_price')
            contract_type = contract.get('contract_type', '').lower()
            
            if strike and contract_type:
                if contract_type == 'call':
                    calls_dict[strike] = calls_dict.get(strike, 0) + 1
                elif contract_type == 'put':
                    puts_dict[strike] = puts_dict.get(strike, 0) + 1
        
        if not calls_dict and not puts_dict:
            raise HTTPException(status_code=400, detail="No valid strike price data")
        
        # Prepare data
        all_strikes = sorted(set(list(calls_dict.keys()) + list(puts_dict.keys())))
        call_counts = [calls_dict.get(strike, 0) for strike in all_strikes]
        put_counts = [puts_dict.get(strike, 0) for strike in all_strikes]
        
        # Create butterfly chart
        fig, ax = plt.subplots(figsize=(12, max(8, len(all_strikes) * 0.3)))
        y_pos = range(len(all_strikes))
        
        ax.barh(y_pos, call_counts, height=0.7, 
               color='#2ecc71', edgecolor='#27ae60', linewidth=1.5,
               label='Call Options', alpha=0.8)
        
        ax.barh(y_pos, [-count for count in put_counts], height=0.7,
               color='#e74c3c', edgecolor='#c0392b', linewidth=1.5,
               label='Put Options', alpha=0.8)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f'${s:.2f}' for s in all_strikes], fontsize=9)
        ax.set_ylabel('Strike Price', fontsize=12, fontweight='bold')
        
        max_count = max(max(call_counts) if call_counts else 0, 
                       max(put_counts) if put_counts else 0)
        ax.set_xlim(-max_count * 1.2, max_count * 1.2)
        
        x_ticks = ax.get_xticks()
        ax.set_xticklabels([f'{abs(int(x))}' for x in x_ticks])
        ax.set_xlabel('Number of Contracts', fontsize=12, fontweight='bold')
        
        ax.axvline(x=0, color='black', linewidth=2, linestyle='-', alpha=0.3)
        ax.set_title(f'{request.ticker} Options Chain - Butterfly Chart', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--', axis='x')
        ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
        
        plt.tight_layout()
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        first_exp_date = contracts[0].get('expiration_date', '') if contracts else ''
        
        if first_exp_date:
            exp_month = first_exp_date[:7]
            png_filename = f"{request.ticker}_butterfly_{exp_month}_{timestamp}.png"
        else:
            png_filename = f"{request.ticker}_butterfly_{timestamp}.png"
        
        plt.savefig(png_filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        return ChartResponse(
            status="success",
            filename=png_filename,
            total_calls=sum(call_counts),
            total_puts=sum(put_counts)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart creation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

