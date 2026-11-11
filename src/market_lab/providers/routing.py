from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from ..data import PriceProvider, Provenance


class ProviderUnavailable(RuntimeError):
    """Missing authorization or unverified provider capability, not corrupt data."""


@dataclass(frozen=True)
class Retrieval:
    bars: pd.DataFrame
    provenance: Provenance
    requested_provider: str
    selected_provider: str
    used_fallback: bool


class ResearchDataService:
    def __init__(self, providers: Mapping[str, PriceProvider]):
        self._providers = dict(providers)

    def fetch(self, provider, symbol, start, end, *, fallback=None):
        """Fallback is opt-in and only for ProviderUnavailable, never validation errors."""
        if provider not in self._providers or (fallback is not None and fallback not in self._providers):
            raise ValueError('Unknown research provider')
        if fallback == provider:
            raise ValueError('Fallback must be a different provider')
        selected = provider
        try:
            bars, meta = self._providers[selected].fetch(symbol, start, end)
        except ProviderUnavailable:
            if fallback is None:
                raise
            selected = fallback
            bars, meta = self._providers[selected].fetch(symbol, start, end)
        return Retrieval(bars, meta, provider, selected, selected != provider)
