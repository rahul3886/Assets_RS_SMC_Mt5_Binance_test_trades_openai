import pandas as pd
import io

def analyze_logs():
    with open('docs/live_demo_trades.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Extract the table rows
    table_lines = [line for line in lines if '|' in line and '---' not in line and '#' not in line]
    
    data = []
    for line in table_lines[1:]: # Skip header
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if len(cols) < 10: continue
        
        asset = cols[1]
        tf = cols[2]
        status = cols[8]
        
        if "ENTERED" in status: continue
        
        try:
            pnl_str = cols[9].replace('$', '').replace('+', '').replace(',', '')
            pnl = float(pnl_str)
            data.append({'asset': asset, 'tf': tf, 'pnl': pnl})
        except:
            continue

    df = pd.DataFrame(data)
    if df.empty:
        print("No valid trades found.")
        return

    output = []
    output.append("="*60)
    output.append("ASSET PROFITABILITY DEEP-DIVE (MTF)")
    output.append("="*60)

    for tf in ['1m', '5m']:
        tf_df = df[df['tf'] == tf]
        if tf_df.empty: continue
        
        output.append(f"\nTIMEFRAME: {tf}")
        # Group by asset
        asset_stats = tf_df.groupby('asset')['pnl'].sum().sort_values(ascending=False)
        
        output.append("   [+] PROFIT LEADERS:")
        leaders = asset_stats[asset_stats > 0]
        for asset, val in leaders.items():
            output.append(f"      - {asset:10}: ${val:,.2f}")
            
        output.append("   [-] LOSS MAKERS (To be removed):")
        losers = asset_stats[asset_stats <= 0]
        for asset, val in losers.items():
            output.append(f"      - {asset:10}: ${val:,.2f}")

    # FINAL FILTERED ANALYSIS
    output.append("\n" + "="*60)
    output.append("REFINED PORTFOLIO: ONLY PROFITABLE ASSETS RETAINED")
    output.append("="*60)
    
    filtered_data = []
    for tf in ['1m', '5m']:
        tf_df = df[df['tf'] == tf]
        if tf_df.empty: continue
        
        asset_pnl = tf_df.groupby('asset')['pnl'].sum()
        profitable_assets = asset_pnl[asset_pnl > 0].index.tolist()
        
        final_tf_df = tf_df[tf_df['asset'].isin(profitable_assets)]
        
        if not final_tf_df.empty:
            net = final_tf_df['pnl'].sum()
            wr = (final_tf_df['pnl'] > 0).mean() * 100
            output.append(f"RESULTS for {tf}: ${net:,.2f} | WR {wr:.1f}% | Assets: {len(profitable_assets)}")
            filtered_data.append(final_tf_df)

    if filtered_data:
        grand_df = pd.concat(filtered_data)
        output.append("\n" + "="*60)
        output.append(f"GRAND TOTAL (Optimized): +${grand_df['pnl'].sum():,.2f}")
        output.append(f"Optimized Win Rate: {(grand_df['pnl'] > 0).mean() * 100:.1f}%")
        output.append("="*60)
    
    print("\n".join(output))

if __name__ == "__main__":
    analyze_logs()
