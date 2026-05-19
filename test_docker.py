from src.core.sandbox import SandboxManager

print("Initializing Sandbox Manager...")
sandbox = SandboxManager()

print("\nRunning a safe test script...")
# This asks Docker to run a simple math problem
safe_result = sandbox.run_code("print('Hello from the isolated Sandbox! 5 + 5 =', 5+5)")
print(f"Status: {safe_result['status']}")
print(f"Output: {safe_result.get('output', '').strip()}")

print("\nRunning a failing test script...")
# This forces an error to see if we capture the traceback
fail_result = sandbox.run_code("x = 1 / 0")
print(f"Status: {fail_result['status']}")
print(f"Error Caught:\n{fail_result.get('error', '').strip()}")
