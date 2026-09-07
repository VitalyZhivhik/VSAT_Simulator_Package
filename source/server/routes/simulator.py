"""Simulator routes for Comtech CEL-AC interface"""
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path

logger = logging.getLogger("vsat")
router = APIRouter(prefix="/sim", tags=["simulator"])

# Paths
templates_dir = Path(__file__).parent.parent / "static" / "templates" / "comtech"
iframe_dir = templates_dir / "iframe_content"

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def simulator_main():
    """Main simulator page with Comtech interface"""
    main_html = templates_dir / "main.html"
    if main_html.exists():
        return FileResponse(str(main_html))
    return HTMLResponse("<h1>Simulator interface not found</h1>", status_code=404)

@router.get("/ss{page_id}", response_class=HTMLResponse)
async def simulator_status_page(page_id: str):
    """Status pages (ssXX) - iframe content"""
    # Map page IDs to template files
    page_map = {
        "40": "ss40.html",  # Overview
        "35": "ss35.html",  # System General
        "34": "ss34.html",  # Ethernet
        "33": "ss33.html",  # Demodulator
        "32": "ss32.html",  # Modulator
        "27": "ss27.html",  # Demodulator 2
        "37": "ss37.html",  # Network Overview
        "15": "ss15.html",  # Service Monitoring
        "30": "ss30.html",  # Support Info
        "52": "ss52.html",  # Log
        "54": "ss54.html",  # Pointing
        "44": "ss44.html",  # Tuning
        "38": "ss38.html",  # RTP
        "62": "ss62.html",  # GTP
        "4": "ss4.html",    # Static Routing
        "64": "ss64.html",  # Dynamic Routing
        "9": "ss9.html",    # SNMP
        "8": "ss8.html",    # DHCP
        "59": "ss59.html",  # DNS
        "23": "ss23.html",  # ARP
        "7": "ss7.html",    # NAT
        "10": "ss10.html",  # RIPv2
        "39": "ss39.html",  # Multicast
        "12": "ss12.html",  # Acceleration
        "5": "ss5.html",    # QoS Policies
        "6": "ss6.html",    # QoS Shapers
        "24": "ss24.html",  # Stations
        "31": "ss31.html",  # MF TDMA
        "28": "ss28.html",  # ACM
        "14": "ss14.html",  # STLC/NMS/Red
        "17": "ss17.html",  # COTM/AMIP
        "58": "ss58.html",  # Security
    }
    
    template_name = page_map.get(page_id, f"ss{page_id}.html")
    template_path = iframe_dir / template_name
    
    if template_path.exists():
        return FileResponse(str(template_path))
    
    # Default status page template
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" type="text/css" href="/static/css/ls.css">
        <title>Status Page {page_id}</title>
    </head>
    <body>
        <center>
            <h2>Status Page {page_id}</h2>
            <p>Content coming soon...</p>
            <p><a href="/sim/ss40">Back to Overview</a></p>
        </center>
    </body>
    </html>
    """)

@router.get("/cc{page_id}", response_class=HTMLResponse)
async def simulator_config_page(page_id: str):
    """Configuration pages (ccXX) - iframe content"""
    # Similar mapping for config pages
    template_path = iframe_dir / f"cc{page_id}.html"
    
    if template_path.exists():
        return FileResponse(str(template_path))
    
    # Default config page template
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" type="text/css" href="/static/css/ls.css">
        <title>Config Page {page_id}</title>
    </head>
    <body>
        <center>
            <h2>Configuration Page {page_id}</h2>
            <p>Content coming soon...</p>
            <p><a href="/sim/ss40">Back to Overview</a></p>
        </center>
    </body>
    </html>
    """)

@router.get("/cm{page_id}", response_class=HTMLResponse)
async def simulator_mod_config_page(page_id: str):
    """Modulator config pages (cmXX)"""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" type="text/css" href="/static/css/ls.css">
        <title>Modulator Config {page_id}</title>
    </head>
    <body>
        <center>
            <h2>Modulator Configuration {page_id}</h2>
            <p>Content coming soon...</p>
        </center>
    </body>
    </html>
    """)

@router.get("/JS0")
async def get_simulator_status():
    """Get current simulator status (called by JavaScript for auto-refresh)"""
    # This returns the status data structure expected by the frontend
    return {
        "Name": "AC Sim",
        "Profile": "1-Star station (           )",
        "ProfileNum": "1",
        "State": "No RX",
        "StateColor": "#fe5e37",
        "StateWeight": "600",
        "StateLock": "hidden",
        "Lan1": "cg",
        "Lan2": "cw",
        "Dem1": "cr",
        "Dem2": "cwd",
        "Mod": "cr",
        "Net": "cw",
        "Cfg": "saveconf_active",
        "Flt": "clearfaults",
        "SysLed": "cg",
        "Sys": "cg",
        "Mon": "cw"
    }

@router.get("/api/overview_data")
async def get_overview_data():
    """Get detailed overview data for iframe refresh"""
    return {
        "cpu_load": 22,
        "buffers": 2,
        "temp": 60,
        "eth_state": "Up",
        "eth_link": "Eth1:100/FD Eth2:No link",
        "eth_tx": 896,
        "eth_rx": 1040,
        "dem1_state": "Down",
        "dem1_lvl": "- 64.6 dBm",
        "dem2_state": "Disabled",
        "dem2_lvl": "- 8.0 dBm",
        "mod_state": "Down",
        "mod_lvl": "- 5.0 dBm/TLC"
    }

@router.get("/z")
async def save_config():
    """Save configuration command"""
    logger.info("Configuration save requested")
    return {"status": "ok"}

@router.get("/hz")
async def clear_faults():
    """Clear faults command"""
    logger.info("Clear faults requested")
    return {"status": "ok"}

@router.get("/hy")
async def profile_status():
    """Profile status refresh"""
    logger.info("Profile status refresh requested")
    return {"status": "ok"}
