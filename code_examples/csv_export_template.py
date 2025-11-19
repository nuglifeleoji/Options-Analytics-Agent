"""
CSV Export Template for Options Data
=====================================

This is a code template that the agent can use to dynamically generate
custom CSV export functions based on user requirements.

The agent can modify this template to:
- Change column selection
- Apply custom filtering
- Add calculated fields
- Change formatting
- Sort data differently
"""

import csv
import json
from datetime import datetime

# Example options data structure
example_data = """
{
    "results": [
        {
            "ticker": "O:AAPL251107C00250000",
            "contract_type": "call",
            "strike_price": 250.0,
            "expiration_date": "2025-11-07",
            "shares_per_contract": 100,
            "primary_exchange": "BATS",
            "exercise_style": "american",
            "underlying_ticker": "AAPL"
        },
        {
            "ticker": "O:AAPL251107P00250000",
            "contract_type": "put",
            "strike_price": 250.0,
            "expiration_date": "2025-11-07",
            "shares_per_contract": 100,
            "primary_exchange": "BATS",
            "exercise_style": "american",
            "underlying_ticker": "AAPL"
        }
    ],
    "count": 2
}
"""

def generate_options_csv(data_json: str, ticker: str, **kwargs):
    """
    Generate a CSV file from options data
    
    Parameters you can customize:
    - columns: list of column names to include
    - filter_type: 'call', 'put', or 'both'
    - min_strike: minimum strike price
    - max_strike: maximum strike price
    - sort_by: column to sort by
    """
    # Parse JSON data
    data = json.loads(data_json)
    contracts = data.get("results", [])
    
    if not contracts:
        print("No data to export")
        return None
    
    # Get customization options
    filter_type = kwargs.get('filter_type', 'both')  # 'call', 'put', or 'both'
    min_strike = kwargs.get('min_strike', 0)
    max_strike = kwargs.get('max_strike', float('inf'))
    sort_by = kwargs.get('sort_by', 'strike_price')
    
    # Filter contracts
    filtered_contracts = []
    for contract in contracts:
        # Filter by type
        if filter_type != 'both':
            if contract.get('contract_type', '').lower() != filter_type.lower():
                continue
        
        # Filter by strike price
        strike = contract.get('strike_price', 0)
        if strike < min_strike or strike > max_strike:
            continue
        
        filtered_contracts.append(contract)
    
    # Sort contracts
    filtered_contracts.sort(key=lambda x: x.get(sort_by, 0))
    
    # Define columns (customize as needed)
    columns = kwargs.get('columns', [
        "Ticker Symbol",
        "Contract Type",
        "Strike Price",
        "Expiration Date",
        "Shares per Contract"
    ])
    
    # Map API fields to display names
    field_mapping = {
        "Ticker Symbol": "ticker",
        "Contract Type": "contract_type",
        "Strike Price": "strike_price",
        "Expiration Date": "expiration_date",
        "Shares per Contract": "shares_per_contract",
        "Primary Exchange": "primary_exchange",
        "Exercise Style": "exercise_style",
        "Underlying Ticker": "underlying_ticker"
    }
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ticker}_options_{filter_type}_{timestamp}.csv"
    
    # Write CSV
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for contract in filtered_contracts:
            row = {}
            for col in columns:
                api_field = field_mapping.get(col, col.lower().replace(' ', '_'))
                value = contract.get(api_field, 'N/A')
                
                # Format specific fields
                if col == "Contract Type" and value != 'N/A':
                    value = value.upper()
                elif col == "Strike Price" and value != 'N/A':
                    value = f"${value:.2f}"
                
                row[col] = value
            
            writer.writerow(row)
    
    print(f"✅ Exported {len(filtered_contracts)} contracts to {filename}")
    return filename


# ==================== Usage Examples ====================

# Example 1: Basic export (all data)
# generate_options_csv(example_data, "AAPL")

# Example 2: Only call options
# generate_options_csv(example_data, "AAPL", filter_type='call')

# Example 3: Filter by strike price range
# generate_options_csv(example_data, "AAPL", min_strike=240, max_strike=260)

# Example 4: Custom columns
# generate_options_csv(example_data, "AAPL", 
#                     columns=["Strike Price", "Contract Type", "Expiration Date"])

# Example 5: Combination
# generate_options_csv(example_data, "AAPL",
#                     filter_type='put',
#                     min_strike=245,
#                     max_strike=255,
#                     columns=["Strike Price", "Expiration Date"])


# ==================== Advanced Example ====================

def generate_summary_csv(data_json: str, ticker: str):
    """
    Generate a summary CSV grouped by strike price
    """
    data = json.loads(data_json)
    contracts = data.get("results", [])
    
    # Group by strike price
    strike_summary = {}
    for contract in contracts:
        strike = contract.get('strike_price', 0)
        contract_type = contract.get('contract_type', '').lower()
        
        if strike not in strike_summary:
            strike_summary[strike] = {'calls': 0, 'puts': 0, 'expiration': set()}
        
        if contract_type == 'call':
            strike_summary[strike]['calls'] += 1
        elif contract_type == 'put':
            strike_summary[strike]['puts'] += 1
        
        strike_summary[strike]['expiration'].add(contract.get('expiration_date', 'N/A'))
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ticker}_summary_{timestamp}.csv"
    
    # Write summary CSV
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Strike Price', 'Call Options', 'Put Options', 'Total', 'Call/Put Ratio', 'Expirations'])
        
        for strike in sorted(strike_summary.keys()):
            summary = strike_summary[strike]
            calls = summary['calls']
            puts = summary['puts']
            total = calls + puts
            ratio = f"{calls/puts:.2f}" if puts > 0 else "N/A"
            expirations = len(summary['expiration'])
            
            writer.writerow([f"${strike:.2f}", calls, puts, total, ratio, expirations])
    
    print(f"✅ Exported summary to {filename}")
    return filename


# ==================== Agent Instructions ====================
"""
Dear Agent,

When a user asks for a custom CSV export, you can:

1. Read this template file
2. Modify the code based on user requirements:
   - Change the columns list
   - Adjust the filtering logic
   - Add custom calculations
   - Change formatting rules
3. Use code_execution_tool to run the modified code

Example user requests and how to handle them:

User: "I only want call options with strike price between 240-260"
→ Use: generate_options_csv(data, "AAPL", filter_type='call', min_strike=240, max_strike=260)

User: "Give me a summary grouped by strike price"
→ Use: generate_summary_csv(data, "AAPL")

User: "I want a CSV with only strike price and expiration date"
→ Modify columns parameter: columns=["Strike Price", "Expiration Date"]

User: "Show me the most expensive options first"
→ Add sorting: sort contracts by strike_price in descending order

Be creative and adapt the code to user needs!
"""

