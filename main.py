import subprocess  
print(subprocess.run(["playwright", "--version"], capture_output=True, text=True).stdout or "Playwright not installed.")
