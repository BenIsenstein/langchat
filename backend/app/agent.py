import os
from dotenv import load_dotenv
load_dotenv()

if "ANTHROPIC_API_KEY" not in os.environ:
    raise RuntimeError("ANTHROPIC_API_KEY must be set")

if "E2B_API_KEY" not in os.environ:
    raise RuntimeError("E2B_API_KEY must be set")

from langchain.agents import create_agent
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from e2b_code_interpreter import Sandbox

model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    # "claude-haiku-4-5-20251001", # haiku 4.5 is 1/3 the cost of sonnet 4.5
    # "claude-3-haiku-20240307", # cheapest active model
    timeout=10,
    max_tokens=1000
)

SYSTEM_PROMPT = """You are a highly competent personal assistant that uses reasoning and the available tools to assist the user.

You have access to one tool:

- code_sandbox: use this to execute code in an E2B code sandbox. As arguments, it accepts a string `code` containing the code to execute, and an optional string `lang` specifying the programming language (default is "python").

Answer the user's questions or service their requests to the best of your ability at all times.
If a user asks you to run some code, write and execute a script, compute a value, or an analogous request, use the code_sandbox skill."""

@tool
def code_sandbox(code: str, lang: str = "python") -> str:
    """Execute code in a sandboxed compute environment."""
    
    writer = get_stream_writer()
    sbx = Sandbox.create() # By default the sandbox is alive for 5 minutes
    execution = sbx.run_code(
        code,
        lang,
        on_error=lambda error: writer(error),
        on_stdout=lambda data: writer(data),
        on_stderr=lambda data: writer(data),
        on_result=lambda result: writer(result)
    )

    return execution.text

agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[code_sandbox],
    checkpointer=InMemorySaver()
)