import os
from dotenv import load_dotenv
load_dotenv()

if "ANTHROPIC_API_KEY" not in os.environ:
    raise RuntimeError("ANTHROPIC_API_KEY must be set")

if "E2B_API_KEY" not in os.environ:
    raise RuntimeError("E2B_API_KEY must be set")

from e2b_code_interpreter import Sandbox

code = "print('hello world!')"
sbx = Sandbox.create() # By default the sandbox is alive for 5 minutes
execution = sbx.run_code(
    code,
    "python",
    # on_error=lambda error: print(error),
    # on_stdout=lambda data: print(data),
    # on_stderr=lambda data: print(data),
    # on_result=lambda result: print(result),
)

for key in execution.__dict__.keys():
    print(f"{key}: {getattr(execution, key)}")
