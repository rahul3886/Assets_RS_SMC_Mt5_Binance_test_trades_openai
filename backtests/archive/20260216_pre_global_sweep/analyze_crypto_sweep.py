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
                
                parts = root.split(os.sep)
                strength_str = next((p for p in parts if "Strength_" in p), "Unknown")
                tf_str = next((p for p in parts if "TF_" in p), "Unknown")
                
                symbol = os.path.basename(root).split('_')[1] # e.g. bt_DOGE_... -> DOGE
                # Handle DOGE/USDT case where folder might be bt_DOGEUSDT_... or bt_DOGE_... depending on replacement
                # The script replaced '/' with '' so bt_DOGEUSDT_...
                
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
    df_sorted = df.sort_values(by="Profit Factor", ascending=False)
    
    output_path = os.path.join(sweep_dir, "analysis_report.md")
    # Enforce UTF-8 encoding to avoid charmap errors with emojis
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Crypto Speculative Sweep Analysis (Sorted by Profit Factor)\n\n")
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
    # We need to find the latest crypto_spec_sweep folder
    base_dir = "backtests"
    # Filter for directories that start with crypto_spec_sweep (not just contain it)
    sweeps = [d for d in os.listdir(base_dir) 
              if d.startswith("crypto_spec_sweep") and os.path.isdir(os.path.join(base_dir, d))]
    
    if sweeps:
        latest = sorted(sweeps)[-1]
        target_dir = os.path.join(base_dir, latest)
        analyze_sweep_results(target_dir)
    else:
        print("❌ No crypto sweep directories found.")
