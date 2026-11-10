import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict
from .backtest import metrics

def record(directory, version, provenance, strategy, costs, result):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    payload = {"created_at":datetime.now(timezone.utc).isoformat(), "dataset_version":version, "provenance":asdict(provenance), "strategy":asdict(strategy), "costs":asdict(costs), "initial_cash":result.initial, "period":[str(result.equity.index[0]),str(result.equity.index[-1])], "metrics":metrics(result), "evaluation":"exploratory in-sample; NOT holdout-validated", "seed":None, "engine_version":"0.1.0"}
    text = json.dumps(payload, indent=2, allow_nan=False)
    identifier = hashlib.sha256(text.encode()).hexdigest()[:20]
    (path/f"{identifier}.json").write_text(text)
    result.equity.to_csv(path/f"{identifier}-equity.csv")
    result.journal.to_csv(path/f"{identifier}-trades.csv", index=False)
    return identifier
