VSAT Satellite Terminal Simulator — Quick Start
================================================

OPTION 1: Run EXE (no Python needed)
-------------------------------------
1. Open the "exe" folder
2. Double-click VSAT_Simulator.exe
3. The server will start and open a browser
4. Share the URL shown in console with students

OPTION 2: Run from Python source (fallback)
--------------------------------------------
1. Install Python 3.10+ from https://www.python.org/downloads/
2. Open the "source" folder
3. Double-click START_SERVER.bat
   (it will install dependencies automatically)
4. Or manually:
   pip install -r requirements.txt
   python run.py

CONFIGURATION
-------------
Edit config.json (in root or in source/) to change:
  - Port (default: 8080)
  - Admin password (default: "admin")
  - Simulation settings

NETWORK SETUP (two computers)
------------------------------
- SERVER: Run the exe or script. Note the IP shown in console.
- CLIENT: Open browser and go to http://<SERVER_IP>:8080
- If client can't connect, check Windows Firewall:
  Allow port 8080 (or disable firewall temporarily)

TROUBLESHOOTING
---------------
- Check logs/vsat_server.log for detailed error information
- If EXE fails, try source/ fallback
- Ensure port 8080 is not used by another application
- On Windows Firewall: allow python.exe or VSAT_Simulator.exe
