import os
import subprocess

result = subprocess.run(
    ["grep", "-rn", "DynamicLighting", "/home/herbmatsui/narou", "--include=*.py"],
    capture_output=True,
    text=True
)
print(result.stdout[:2000])
print("---STDERR---")
print(result.stderr[:500])
