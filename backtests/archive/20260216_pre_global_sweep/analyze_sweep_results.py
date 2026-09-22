import os
import json
import pandas as pd

def analyze_sweep_results(sweep_dir):
    results = []
    
    print(f"🔍 Analyzing sweep directory: {sweep_dir}")
    
    for root, dirs, files in os.walk(sweep_dir):
        if "summary.json" in files:
            try:
                path = os.path.join(root, "summary.json")
                with open(path, "r") as f:
                    data = json.load(f)
                
                # Extract info from folder structure if not in json or to verify
                # Expected structure: .../Strength_XX/TF_Xm/bt_SYMBOL_...
                parts = root.split(os.sep)
                
                # Attempt to extract strength and TF from path if needed, 
                # but data['metrics'] usually has what we need, except maybe strength explicitly if not logged
                # The trade list has strength, but let's rely on path for "Configuration"
                
                strength_str = next((p for p in parts if "Strength_" in p), "Unknown")
                tf_str = next((p for p in parts if "TF_" in p), "Unknown")
                
                symbol = os.path.basename(root).split('_')[1] # e.g. bt_CADJPY_1m... -> CADJPY
                
                metrics = data.get("metrics", {})
                
                results.append({
                    "Asset": symbol,
                    "Timeframe": tf_str.replace("TF_", ""),
                    "Strength": strength_str.replace("Strength_", "") + "%",
                    "Trades": metrics.get("total_trades", 0),
                    "Win Rate": f"{metrics.get('win_rate', 0)}%",
                    "Profit Factor": metrics.get("profit_factor", 0),
                    "Avg RR": metrics.get("avg_rr", 0),
                    "Return": f"{metrics.get('total_return_pct', 0)}%"
                })
            except Exception as e:
                print(f"❌ Error reading {path}: {e}")

    if not results:
        print("No results found.")
        return

    df = pd.DataFrame(results)
    
    # Sort by Profit Factor descending
    # Sort by Profit Factor descending
    df_sorted = df.sort_values(by="Profit Factor", ascending=False)
    
    output_path = os.path.join(sweep_dir, "analysis_report.md")
    with open(output_path, "w") as f:
        f.write("# Forex Crosses Sweep Analysis (Sorted by Profit Factor)\n\n")
        f.write("```\n")
        f.write(df_sorted.to_string(index=False)) 
        f.write("\n```\n")
        
        f.write("\n\n# Potential Sweet Spots (PF > 1.5, Trades > 5)\n\n")
        f.write("```\n")
        sweet_spots = df[(df["Profit Factor"] >= 1.5) & (df["Trades"] >= 5)].sort_values(by="Profit Factor", ascending=False)
        f.write(sweet_spots.to_string(index=False))
        f.write("\n```\n")

    print(f"✅ Analysis saved to: {output_path}")

if __name__ == "__main__":
    # Target the specific timestamp directory 
    target_dir = os.path.join("backtests", "fx_crosses_sweep_20260216_153738")
    analyze_sweep_results(target_dir)
