"""Fail-closed Robinhood research boundary. No verified live tool bindings yet.

Names below are INTERNAL capabilities, not claims about Robinhood's tool names.
Server descriptions/readOnlyHint annotations cannot grant permission.
"""
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Callable, Protocol

from .routing import ProviderUnavailable

ENDPOINT = 'https://agent.robinhood.com/mcp/trading'


class ResearchOperation(str, Enum):
    HISTORICAL_EQUITY_PRICES = 'historical_equity_prices'
    TECHNICAL_INDICATORS = 'technical_indicators'
    LEVEL_II = 'level_ii'
    EARNINGS = 'earnings'
    SEC_FILINGS = 'sec_filings'
    POLITICIAN_DISCLOSURES = 'politician_disclosures'
    MARKET_SCANS = 'market_scans'
    LEGEND_CHARTS = 'legend_charts'


@dataclass(frozen=True)
class ReviewedReadBinding:
    tool_name: str
    # A validator must enforce the reviewed argument schema, including rejecting
    # unknown fields and any action discriminator not proven to be data-only.
    validate_arguments: Callable[[dict], None]
    official_evidence_url: str
    schema_sha256: str


# Deliberately empty: official documentation and schemas are currently inaccessible.
# Only reviewed source changes may add exact tool names. Never populate this from
# server discovery, local user input, prefix matching, or readOnlyHint alone.
READ_ONLY_BINDINGS = MappingProxyType({})


class AuthorizedResearchTransport(Protocol):
    """Future app-owned auth/transport boundary, independent of Codex connectors.

    An implementation requires verified official auth documentation and a grant
    constrained to research-data access. No production implementation exists yet.
    """
    def invoke_reviewed_tool(self, tool_name: str, arguments: dict) -> dict: ...


class ReadOnlyResearchGateway:
    def __init__(self, transport: AuthorizedResearchTransport):
        self._transport = transport

    def read(self, operation: ResearchOperation, arguments: dict):
        if not isinstance(operation, ResearchOperation):
            raise PermissionError('Only enumerated research-data operations are permitted')
        binding = READ_ONLY_BINDINGS.get(operation)
        if binding is None:
            raise ProviderUnavailable('Robinhood operation is not officially verified and allowlisted')
        # Validate before any transport/authentication/network activity.
        binding.validate_arguments(arguments)
        return self._transport.invoke_reviewed_tool(binding.tool_name, arguments)


class RobinhoodDaily:
    """Provider-neutral placeholder; cannot access a brokerage or emit prices."""
    def fetch(self, symbol, start, end):
        raise ProviderUnavailable(
            'Robinhood MCP is a disabled research candidate: official operations, '
            'app authorization and historical adjustment semantics must be verified first'
        )
