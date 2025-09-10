"""
ACP remote API
"""

from toad import jsonrpc
from toad.acp import protocol

API = jsonrpc.API()


@API.method()
def initialize(
    protocolVersion: int, clientCapabilities: protocol.ClientCapabilities
) -> protocol.InitializeResponse:
    """https://agentclientprotocol.com/protocol/initialization"""
    ...


@API.method(name="new", prefix="session/")
def session_new(
    cwd: str, mcpServers: list[protocol.McpServer]
) -> protocol.NewSessionResponse:
    """https://agentclientprotocol.com/protocol/session-setup#session-id"""
    ...


@API.method(name="prompt", prefix="session/")
def session_prompt(
    prompt: list[protocol.ContentBlock], sessionId: str
) -> protocol.SessionPromptResponse:
    """https://agentclientprotocol.com/protocol/prompt-turn#1-user-message"""
    ...
