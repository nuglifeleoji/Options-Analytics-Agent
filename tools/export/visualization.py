"""
Visualization Tool
Author: Leo Ji

Create charts and visualizations for options data.
"""

import json
from datetime import datetime
from langchain_core.tools import tool
from config.settings import PATHS, VIZ_CONFIG
import matplotlib
matplotlib.use(VIZ_CONFIG.MATPLOTLIB_BACKEND)
import matplotlib.pyplot as plt


@tool
def plot_options_chain(data: str, ticker: str) -> str:
    """Create a butterfly chart (symmetric horizontal bar chart) showing options distribution.
    
    Args:
        data: JSON string containing options data from search_options tool
        ticker: Stock ticker symbol (e.g., 'AAPL') for chart title
    
    Returns:
        Success message with the chart filename (PNG image)
    """
    try:
        # Parse the JSON data
        options_data = json.loads(data)
        
        # Check if we have results
        if "results" not in options_data or not options_data["results"]:
            return "No options data found to plot."
        
        contracts = options_data["results"]
        
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
            return "No valid options data to plot (missing strike prices or contract types)."
        
        # Get all unique strike prices and sort them
        all_strikes = sorted(set(list(calls_dict.keys()) + list(puts_dict.keys())))
        
        # Prepare data for butterfly chart
        call_counts = [calls_dict.get(strike, 0) for strike in all_strikes]
        put_counts = [puts_dict.get(strike, 0) for strike in all_strikes]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, max(8, len(all_strikes) * 0.3)))
        
        # Create horizontal bar chart (butterfly style)
        y_pos = range(len(all_strikes))
        
        # Plot calls on the right (positive)
        ax.barh(y_pos, call_counts, height=0.7, 
               color='#2ecc71', edgecolor='#27ae60', linewidth=1.5,
               label=f'Call Options', alpha=0.8)
        
        # Plot puts on the left (negative)
        ax.barh(y_pos, [-count for count in put_counts], height=0.7,
               color='#e74c3c', edgecolor='#c0392b', linewidth=1.5,
               label=f'Put Options', alpha=0.8)
        
        # Customize y-axis (strike prices)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f'${s:.2f}' for s in all_strikes], fontsize=9)
        ax.set_ylabel('Strike Price', fontsize=12, fontweight='bold')
        
        # Customize x-axis
        max_count = max(max(call_counts) if call_counts else 0, 
                       max(put_counts) if put_counts else 0)
        ax.set_xlim(-max_count * 1.2, max_count * 1.2)
        
        # Set x-axis labels (show absolute values)
        x_ticks = ax.get_xticks()
        ax.set_xticklabels([f'{abs(int(x))}' for x in x_ticks])
        ax.set_xlabel('Number of Contracts', fontsize=12, fontweight='bold')
        
        # Add center line
        ax.axvline(x=0, color='black', linewidth=2, linestyle='-', alpha=0.3)
        
        # Title
        ax.set_title(f'{ticker} Options Chain - Butterfly Chart', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='--', axis='x')
        
        # Legend
        ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
        
        # Add statistics
        total_calls = sum(call_counts)
        total_puts = sum(put_counts)
        
        stats_text = f'Calls: {total_calls} contracts | Puts: {total_puts} contracts'
        if total_puts > 0:
            stats_text += f' | Call/Put Ratio: {total_calls/total_puts:.2f}'
        else:
            stats_text += ' | No Puts'
            
        ax.text(0.5, -0.08, stats_text, 
               ha='center', va='top', transform=ax.transAxes,
               fontsize=10, style='italic', color='#555',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                        edgecolor='gray', alpha=0.8))
        
        plt.tight_layout()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        first_exp_date = contracts[0].get('expiration_date', '') if contracts else ''
        
        if first_exp_date:
            exp_month = first_exp_date[:7]
            png_filename = f"{PATHS.CHARTS_DIR}/{ticker}_butterfly_{exp_month}_{timestamp}.png"
        else:
            png_filename = f"{PATHS.CHARTS_DIR}/{ticker}_butterfly_{timestamp}.png"
        
        # Save as PNG
        plt.savefig(png_filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        result = f"""✅ Successfully created butterfly chart: {png_filename}
📊 Contract Summary:
  • Total Contracts: {total_calls + total_puts}
  • Call Contracts: {total_calls} (right side, green)
  • Put Contracts: {total_puts} (left side, red)
  • Strike Prices: {len(all_strikes)}"""
        
        if total_puts > 0:
            result += f"\n  • Call/Put Ratio: {total_calls/total_puts:.2f}"
        else:
            result += "\n  • ⚠️ Warning: No Put options found in this dataset"
        
        result += "\n\n💡 Butterfly chart shows symmetric distribution: Calls on right, Puts on left."
        
        return result
        
    except json.JSONDecodeError:
        return "❌ Error: Invalid JSON data provided"
    except Exception as e:
        return f"❌ Error creating chart: {str(e)}"


__all__ = ['plot_options_chain']

