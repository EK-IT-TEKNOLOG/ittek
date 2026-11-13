# Small program to display the MicroPython verison
import sys
res = sys.implementation
print("Installed package")
print("-----------------")
print(f"Name    : {res[0]}")
major, minor, patch, dummy = res[1]
print(f"Version : {major}.{minor}.{patch}")
print(f"Platform: {res[2]}")