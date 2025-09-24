from dataclasses import dataclass

from asyncio import Future
from textual.message import Message

from toad.answer import Answer
from toad.acp import protocol


class AgentMessage(Message):
    pass


@dataclass
class Thinking(AgentMessage):
    type: str
    text: str


@dataclass
class Update(AgentMessage):
    type: str
    text: str


@dataclass
class RequestPermission(AgentMessage):
    options: list[protocol.PermissionOption]
    tool_call: protocol.ToolCallUpdate
    result_future: Future[Answer]


@dataclass
class ToolCallUpdate(AgentMessage):
    status: str | None
    content: list[protocol.ToolCallContent]
