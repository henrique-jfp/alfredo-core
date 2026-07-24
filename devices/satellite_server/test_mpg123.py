"""Test if mpg123 is found by shutil and can play a test tone."""
import shutil
import os

print("shutil.which('mpg123'):", shutil.which("mpg123"))
print("PATH:", os.environ.get("PATH", ""))

if shutil.which("mpg123"):
    print("mpg123 FOUND!")
else:
    print("mpg123 NOT FOUND by shutil!")
    # Check if the file exists
    for p in os.environ.get("PATH", "").split(":"):
        test = os.path.join(p, "mpg123")
        if os.path.exists(test):
            print(f"  Found at {test} but shutil.which failed!")
