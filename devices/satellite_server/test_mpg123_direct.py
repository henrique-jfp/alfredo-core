"""Test mpg123 directly - generate an MP3 and play via mpg123."""
import subprocess
import sys

# First, let's download a small test MP3 or generate a WAV and convert
# Actually, let's just test mpg123 with a pipe
print("Testing mpg123 with stdin pipe...")

# Generate a minimal test: pipe 'mpg123 --stdout -q -' to see if it reads from stdin
proc = subprocess.Popen(
    ["mpg123", "-q", "--stdout", "-"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Send a valid MP3 file (we'll use one from a known source)
# For now just close stdin and see what happens
proc.stdin.close()
stdout, stderr = proc.communicate(timeout=5)
print(f"Return code: {proc.returncode}")
print(f"Stdout: {len(stdout)} bytes")
print(f"Stderr: {stderr[:200] if stderr else '(empty)'}")
print("Done")
