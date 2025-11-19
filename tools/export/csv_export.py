"""
CSV Export Tool
Author: Leo Ji

Export options data to CSV format.
"""

import json
import csv
from datetime import datetime
from langchain_core.tools import tool
from config.settings import PATHS


@tool
def make_option_table(data: str, ticker: str) -> str:
    """Convert options data to a CSV file and save it.
    
    Args:
        data: JSON string containing options data from search_options tool
        ticker: Stock ticker symbol (e.g., 'AAPL') for naming the file
    
    Returns:
        Success message with the CSV filename
    """
    try:
        # Parse the JSON data
        options_data = json.loads(data)
        
        # Check if we have results
        if "results" not in options_data or not options_data["results"]:
            return "No options data found to export."
        
        contracts = options_data["results"]
        
        # Try to extract expiration date from first contract for better filename
        first_exp_date = contracts[0].get('expiration_date', '') if contracts else ''
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create descriptive filename based on expiration dates
        if first_exp_date:
            # Extract year-month from first contract
            exp_month = first_exp_date[:7]  # YYYY-MM
            filename = f"{PATHS.CSV_DIR}/{ticker}_options_{exp_month}_{timestamp}.csv"
        else:
            filename = f"{PATHS.CSV_DIR}/{ticker}_options_{timestamp}.csv"
        
        # Define CSV columns with better formatting
        fieldnames = [
            "Ticker Symbol",
            "Contract Type",
            "Strike Price",
            "Expiration Date",
            "Shares per Contract",
            "Primary Exchange",
            "Exercise Style",
            "Underlying Ticker"
        ]
        
        # Write to CSV file
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for contract in contracts:
                # Format contract type
                contract_type = contract.get("contract_type", "N/A")
                if contract_type != "N/A":
                    contract_type = contract_type.upper()  # CALL or PUT
                
                row = {
                    "Ticker Symbol": contract.get("ticker", "N/A"),
                    "Contract Type": contract_type,
                    "Strike Price": f"${contract.get('strike_price', 'N/A')}" if contract.get('strike_price') else "N/A",
                    "Expiration Date": contract.get("expiration_date", "N/A"),
                    "Shares per Contract": contract.get("shares_per_contract", "N/A"),
                    "Primary Exchange": contract.get("primary_exchange", "N/A"),
                    "Exercise Style": contract.get("exercise_style", "N/A"),
                    "Underlying Ticker": contract.get("underlying_ticker", ticker.upper())
                }
                writer.writerow(row)
        
        return f"✅ Successfully saved {len(contracts)} options contracts to CSV file: {filename}"
        
    except json.JSONDecodeError:
        return "❌ Error: Invalid JSON data provided"
    except Exception as e:
        return f"❌ Error creating CSV file: {str(e)}"


__all__ = ['make_option_table']

