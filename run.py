import subprocess, sys
subprocess.call([sys.executable, "-m", "streamlit", "run", "app.py"] + sys.argv[1:])
