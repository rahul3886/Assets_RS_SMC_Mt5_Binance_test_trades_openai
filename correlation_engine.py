import pandas as pd
import numpy as np

class CorrelationEngine:
    """
    Upgrade 7: Cross-Asset Correlation Module.
    Manages market-wide exposure by clustering correlated assets and 
    filtering redundant signals.
    """
    def __init__(self):
        # Known Institutional Clusters
        self.clusters = {
            "USD_NEXUS": ["EURUSD", "GBPUSD", "XAUUSD", "XAGUSD", "BTC/USDT"], # DXY Influence
            "YEN_CARRY": ["GBPJPY", "CADJPY", "USDJPY"], # Risk Sentiment
            "METAL_SYNC": ["XAUUSD", "XAGUSD"], # Commodity Link
            "CRYPTO_BETA": ["BTC/USDT", "ETH/USDT", "SOL/USDT"] # Market Beta
        }
        
    def tag_signals(self, signals):
        """
        Upgrade 7 (Hybrid): Tags signals with their macro cluster and 
        identifies the 'Leader' without blocking others.
        """
        if not signals:
            return []
            
        cluster_leaders = {} # Cluster Name -> Symbol
        cluster_max_strength = {} # Cluster Name -> Max Strength
        
        # 1. Find Winners (Leaders) for each cluster
        for sig in signals:
            symbol = sig.get('symbol')
            strength = sig.get('strength', 0)
            assigned_clusters = [name for name, assets in self.clusters.items() if symbol in assets]
            
            for cluster in assigned_clusters:
                if strength > cluster_max_strength.get(cluster, -1):
                    cluster_max_strength[cluster] = strength
                    cluster_leaders[cluster] = symbol
        
        # 2. Tag all signals
        for sig in signals:
            symbol = sig.get('symbol')
            strength = sig.get('strength', 0)
            assigned_clusters = [name for name, assets in self.clusters.items() if symbol in assets]
            
            sig['clusters'] = assigned_clusters
            sig['is_leader'] = False
            sig['warning'] = None
            
            if assigned_clusters:
                is_leader = any(cluster_leaders.get(c) == symbol for c in assigned_clusters)
                sig['is_leader'] = is_leader
                
                if not is_leader:
                    # Logic: Only warn if the leader is significantly stronger
                    leader_strength = max([cluster_max_strength.get(c, 0) for c in assigned_clusters])
                    if leader_strength - strength > 10:
                        sig['warning'] = "CORRELATION_OVERLAP"
        
        return signals

    def get_cluster_exposure(self, active_trades):
        """Calculates current portfolio exposure per institutional cluster."""
        exposure = {cluster: 0 for cluster in self.clusters}
        for trade in active_trades:
            symbol = trade.get('symbol')
            for cluster, assets in self.clusters.items():
                if symbol in assets:
                    exposure[cluster] += 1
        return exposure
