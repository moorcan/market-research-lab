import hashlib
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict
from . import __version__
from .backtest import metrics, ADJUSTED_EXPLORATORY
from .data import require_adjusted_provenance
from .serialization import dumps

def record(directory, version, provenance, strategy, costs, result):
    require_adjusted_provenance(provenance)
    if result.simulation_mode != ADJUSTED_EXPLORATORY:
        raise ValueError("Unsupported simulation mode")
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    payload = {"simulation_mode":result.simulation_mode, "executable_price_simulation":False, "created_at":datetime.now(timezone.utc).isoformat(), "dataset_version":version, "provenance":asdict(provenance), "strategy":asdict(strategy), "costs":asdict(costs), "initial_cash":result.initial, "period":[str(result.equity.index[0]),str(result.equity.index[-1])], "metrics":metrics(result), "evaluation":"exploratory in-sample; NOT holdout-validated", "seed":None, "engine_version":__version__}
    text = dumps(payload, indent=2)
    identifier = hashlib.sha256(text.encode()).hexdigest()[:20]
    (path/f"{identifier}.json").write_text(text)
    result.equity.to_csv(path/f"{identifier}-equity.csv")
    result.journal.to_csv(path/f"{identifier}-trades.csv", index=False)
    return identifier
