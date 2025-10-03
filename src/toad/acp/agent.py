import asyncio
import json
import os
from pathlib import Path
from typing import cast

import rich.repr

from textual.content import Content
from textual.message_pump import MessagePump
from textual import log

from toad import jsonrpc
from toad.agent import AgentBase
from toad.acp import protocol
from toad.acp import api
from toad.acp.api import API
from toad.acp import messages
from toad.acp.prompt import build as build_prompt
from toad import constants
from toad.answer import Answer

PROTOCOL_VERSION = 1


@rich.repr.auto
class Agent(AgentBase):
    """An agent that speaks the APC (https://agentclientprotocol.com/overview/introduction) protocol."""

    def __init__(self, project_root: Path, command: str) -> None:
        """

        Args:
            project_root: Project root path.
            command: Command to launch agent.
        """
        super().__init__(project_root)

        self.command = command

        self.server = jsonrpc.Server()
        self.server.expose_instance(self)

        self._agent_task: asyncio.Task | None = None
        self._task: asyncio.Task | None = None
        self._process: asyncio.subprocess.Process | None = None
        self.done_event = asyncio.Event()

        self.agent_capabilities: protocol.AgentCapabilities = {
            "loadSession": False,
            "promptCapabilities": {
                "audio": False,
                "embeddedContent": False,
                "image": False,
            },
        }
        self.auth_methods: list[protocol.AuthMethod] = []
        self.session_id: str = ""

        self.tool_calls: dict[str, protocol.ToolCall] = {}

        self._message_target: MessagePump | None = None

    def __rich_repr__(self) -> rich.repr.Result:
        yield self.project_root_path
        yield self.command

    def get_info(self) -> Content:
        return Content(self.command)

    def start(self, message_target: MessagePump | None = None) -> None:
        """Start the agent."""
        self._message_target = message_target
        self._agent_task = asyncio.create_task(self._run_agent())

    def send(self, request: jsonrpc.Request) -> None:
        """Send a request to the agent.

        This is called automatically, if you go through `self.request`.

        Args:
            request: JSONRPC request object.

        """
        assert self._process is not None, "Process should be present here"
        print("SEND", request.body)
        if (stdin := self._process.stdin) is not None:
            stdin.write(b"%s\n" % request.body_json)

    def request(self) -> jsonrpc.Request:
        """Create a request object."""
        return API.request(self.send)

    @jsonrpc.expose("session/update")
    def rpc_session_update(self, sessionId: str, update: protocol.SessionUpdate):
        """Agent requests an update.

        https://agentclientprotocol.com/protocol/schema
        """

        if (message_target := self._message_target) is None:
            return

        match update:
            case {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": type, "text": text},
            }:
                message_target.post_message(messages.Update(type, text))

            case {
                "sessionUpdate": "agent_thought_chunk",
                "content": {"type": type, "text": text},
            }:
                message_target.post_message(messages.Thinking(type, text))

            case {
                "sessionUpdate": "tool_call",
                "toolCallId": tool_call_id,
            }:
                self.tool_calls[tool_call_id] = update
                message_target.post_message(messages.ToolCall(update))

            case {
                "sessionUpdate": "tool_call_update",
                "toolCallId": tool_call_id,
            }:
                if tool_call_id in self.tool_calls:
                    current_tool_call = self.tool_calls[tool_call_id]
                    for key, value in update.items():
                        if value is not None:
                            current_tool_call[key] = value

                    message_target.post_message(
                        messages.ToolCallUpdate(current_tool_call, update)
                    )
                else:
                    log.warning(f"Unknown tool call id in update; {update}")

    '''
    {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'session/request_permission',
        'params': {
            'sessionId': '6506cc77-3c25-4b39-8a01-0aea0045d046',
            'options': [
                {'optionId': 'proceed_always', 'name': 'Allow All Edits', 'kind': 'allow_always'},
                {'optionId': 'proceed_once', 'name': 'Allow', 'kind': 'allow_once'},
                {'optionId': 'cancel', 'name': 'Reject', 'kind': 'reject_once'}
            ],
            'toolCall': {
                'toolCallId': 'write_file-1759479269516',
                'status': 'pending',
                'title': 'Writing to mandelbrot.py',
                'content': [
                    {
                        'type': 'diff',
                        'path': 'mandelbrot.py',
                        'oldText': '',
                        'newText': 'import os\n\n\ndef get_terminal_size():\n    """Get the size of the terminal."""\n    try:\n
    return os.get_terminal_size()\n    except OSError:\n        return 80, 24\n\n\ndef mandelbrot(c, max_iter):\n
    """Determine if a point is in the Mandelbrot set."""\n    z = 0\n    n = 0\n    while abs(z) <= 2 and n < max_iter:\n
    z = z * z + c\n        n += 1\n    return n\n\n\ndef draw_mandelbrot():\n    """Draw the Mandelbrot set in the
    terminal."""\n    width, height = get_terminal_size()\n    x_min, x_max = -2.0, 1.0\n    y_min, y_max = -1.0, 1.0\n
    max_iter = 256\n\n    chars = " .,-%*#@ "\n\n    for py in range(height):\n        line = ""\n        for px in
    range(width):\n            x = x_min + (x_max - x_min) * px / width\n            y = y_min + (y_max - y_min) * py / height\n
    c = complex(x, y)\n            m = mandelbrot(c, max_iter)\n            char_index = (m * (len(chars) - 1)) // max_iter\n
    line += chars[char_index]\n        print(line)\n\n\nif __name__ == "__main__":\n    draw_mandelbrot()\n'
                    }
                ],
                'locations': [{'path': '/Users/willmcgugan/sandbox/mandelbrot.py'}],
                'kind': 'edit'
            }
        }
    }
    '''

    @jsonrpc.expose("session/request_permission")
    async def rpc_request_permission(
        self,
        sessionId: str,
        options: list[protocol.PermissionOption],
        toolCall: protocol.ToolCallUpdatePermissionRequest,
        _meta: dict | None = None,
    ) -> protocol.RequestPermissionResponse:
        """_summary_

        Args:
            sessionId: The session ID.
            options: A list of permission options (potential replies).
            toolCall: The tool or tools the agent is requesting permission to call.
            _meta: Optional meta information.

        Returns:
            The response to the permission request.
        """
        print("REQUEST PERMISSION")
        assert self._message_target is not None
        result_future: asyncio.Future[Answer] = asyncio.Future()
        kind = toolCall.get("kind", None)
        tool_call_id = toolCall.get("toolCallId", None)
        print(f"{kind=} {tool_call_id=}")

        if tool_call_id not in self.tool_calls:
            permission_tool_call = toolCall
            permission_tool_call.pop("sessionUpdate", None)
            tool_call = cast(protocol.ToolCall, permission_tool_call)
            self.tool_calls[tool_call_id] = tool_call

        log(self.tool_calls)

        # if kind is None and tool_call_id in self.tool_calls:
        #     permission_tool_call = self.tool_calls[tool_call_id]
        #     self.tool_calls[tool_call_id] = permission_tool_call

        #     permission_tool_call.pop("sessionUpdate")
        #     toolCall = cast(
        #         protocol.ToolCallUpdatePermissionRequest,
        #         permission_tool_call,
        #     )

        print("Post RequestPermission")
        self._message_target.post_message(
            messages.RequestPermission(options, toolCall, result_future)
        )
        await result_future
        ask_result = result_future.result()

        request_permission_outcome: protocol.OutcomeSelected = {
            "optionId": ask_result.id,
            "outcome": "selected",
        }
        result: protocol.RequestPermissionResponse = {
            "outcome": request_permission_outcome
        }
        return result

    @jsonrpc.expose("fs/read_text_file")
    def rpc_read_text_file(
        self,
        sessionId: str,
        path: str,
        line: int | None = None,
        limit: int | None = None,
    ) -> dict[str, str]:
        """Read a file in the project."""
        # TODO: what if the read is outside of the project path?
        # https://agentclientprotocol.com/protocol/file-system#reading-files
        read_path = self.project_root_path / path
        try:
            text = read_path.read_text(encoding="utf-8", errors="ignore")
        except IOError:
            text = ""
        if line is not None:
            line = max(0, line - 1)
            if limit is None:
                text = "\n".join(text.splitlines()[line:])
            else:
                text = "\n".join(text.splitlines()[line : line + limit])
        return {"content": text}

    @jsonrpc.expose("fs/write_text_file")
    def rpc_write_text_file(self, sessionId: str, path: str, content: str) -> None:
        # TODO: What if the agent wants to write outside of the project path?
        # https://agentclientprotocol.com/protocol/file-system#writing-files
        print("WRITE TEXT FILE", path)
        write_path = self.project_root_path / path
        write_path.write_text(content, encoding="utf-8", errors="ignore")

    async def _run_agent(self) -> None:
        """Task to communicate with the agent subprocess."""

        agent_output = open("agent.jsonl", "wb")

        PIPE = asyncio.subprocess.PIPE
        print("COMMAND", repr(self.command))
        env = os.environ.copy()
        env["TOAD_CWD"] = str(Path("./").absolute())
        process = self._process = await asyncio.create_subprocess_shell(
            self.command,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            env=env,
            cwd=str(self.project_root_path),
        )
        print(process)
        print(process.stdout)

        self._task = asyncio.create_task(self.run())

        assert process.stdout is not None
        assert process.stdin is not None

        tasks: set[asyncio.Task] = set()

        async def call_jsonrpc(request: jsonrpc.JSONObject | jsonrpc.JSONList) -> None:
            try:
                result = await self.server.call(request)
                result_json = json.dumps(result).encode("utf-8")
                if process.stdin is not None:
                    process.stdin.write(b"%s\n" % result_json)
            finally:
                if (task := asyncio.current_task()) is not None:
                    tasks.discard(task)

        while line := await process.stdout.readline():
            # This line should contain JSON, which may be:
            #   A) a JSONRPC request
            #   B) a JSONRPC response to a previous request
            print("LINE", line)
            if not line.strip():
                continue

            agent_output.write(line)
            agent_output.flush()

            try:
                agent_data: jsonrpc.JSONType = json.loads(line.decode("utf-8"))
                log(agent_data)
            except Exception:
                # TODO: handle this
                raise

            if isinstance(agent_data, dict):
                if "result" in agent_data or "error" in agent_data:
                    API.process_response(agent_data)
                    continue

            elif isinstance(agent_data, list):
                if not all(isinstance(datum, dict) for datum in agent_data):
                    log.warning(f"Agent sent invalid data: {agent_data!r}")
                    continue
                if all(
                    isinstance(datum, dict) and ("result" in datum or "error" in datum)
                    for datum in agent_data
                ):
                    API.process_response(agent_data)
                    continue

            # By this point we know it is a JSON RPC call
            print("JSONRPC CALL")
            assert isinstance(agent_data, dict)
            log(agent_data)
            tasks.add(asyncio.create_task(call_jsonrpc(agent_data)))

        print("AGENT RETURN", process.returncode)

        agent_output.close()
        print("exit")

    async def run(self) -> None:
        """The main logic of the Agent."""
        if constants.ACP_INITIALIZE:
            # Boilerplate to initialize comms
            await self.acp_initialize()
            # Create a new session
            await self.acp_new_session()

    async def send_prompt(self, prompt: str) -> str | None:
        """Send a prompt to the agent.

        !!! note
            This method blocks as it may defer to a thread to read resources.

        Args:
            prompt: Prompt text.
        """
        prompt_content_blocks = await asyncio.to_thread(
            build_prompt, self.project_root_path, prompt
        )
        return await self.acp_session_prompt(prompt_content_blocks)

    async def acp_initialize(self):
        """Initialize agent."""
        with self.request():
            initialize_response = api.initialize(
                PROTOCOL_VERSION,
                {
                    "fs": {
                        "readTextFile": True,
                        "writeTextFile": True,
                    },
                    "terminal": True,
                },
            )

        response = await initialize_response.wait()
        # Store agents capabilities
        if agent_capabilities := response.get("agentCapabilities"):
            self.agent_capabilities = agent_capabilities
        if auth_methods := response.get("authMethods"):
            self.auth_methods = auth_methods

    async def acp_new_session(self) -> None:
        """Create a new session."""
        with self.request():
            session_new_response = api.session_new(
                str(self.project_root_path),
                [],
            )
        response = await session_new_response.wait()
        self.session_id = response["sessionId"]

    async def acp_session_prompt(
        self, prompt: list[protocol.ContentBlock]
    ) -> str | None:
        """Send the prompt to the agent.

        Returns:
            The stop reason.

        """
        with self.request():
            session_prompt = api.session_prompt(prompt, self.session_id)
        result = await session_prompt.wait()
        return result.get("stopReason")


if __name__ == "__main__":
    from rich import print

    async def run_agent():
        agent = Agent(Path("./"), "gemini --experimental-acp")
        print(agent)
        agent.start()
        await agent.done_event.wait()

    asyncio.run(run_agent())
