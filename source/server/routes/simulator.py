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

# Profile pages routes - MF Hub (using original HTML from Resors_Comtech)
@router.get("/cc3", response_class=HTMLResponse)
async def profile_cc3():
    """Main Profiles page - redirects to MF Hub selection"""
    return FileResponse(str(iframe_dir / "profiles" / "mf_hub_select.html"))

@router.get("/profiles/mf_hub", response_class=HTMLResponse)
async def profile_mf_hub():
    """MF Hub profile selection page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_select.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub Profile Selection</h1>")

@router.get("/profiles/mf_hub/basic", response_class=HTMLResponse)
async def profile_mf_hub_basic():
    """MF Hub Basic profile settings page - using original HTML content"""
    template_path = iframe_dir / "profiles" / "mf_hub_basic.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub Basic Settings</h1>")

@router.get("/profiles/mf_hub/tdm_rx", response_class=HTMLResponse)
async def profile_mf_hub_tdm_rx():
    """MF Hub TDM/SCPC RX profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tdm_rx.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TDM RX Settings</h1>")

@router.get("/profiles/mf_hub/tdm_tx", response_class=HTMLResponse)
async def profile_mf_hub_tdm_tx():
    """MF Hub TDM/SCPC TX profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tdm_tx.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TDM TX Settings</h1>")

@router.get("/profiles/mf_hub/modulator", response_class=HTMLResponse)
async def profile_mf_hub_modulator():
    """MF Hub Modulator profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_modulator.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub Modulator Settings</h1>")

@router.get("/profiles/mf_hub/timing", response_class=HTMLResponse)
async def profile_mf_hub_timing():
    """MF Hub Timing profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_timing.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub Timing Settings</h1>")

@router.get("/profiles/mf_hub/tlc", response_class=HTMLResponse)
async def profile_mf_hub_tlc():
    """MF Hub TLC profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tlc.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TLC Settings</h1>")

@router.get("/profiles/mf_hub/tdm_acm", response_class=HTMLResponse)
async def profile_mf_hub_tdm_acm():
    """MF Hub TDM ACM profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tdm_acm.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TDM ACM Settings</h1>")

@router.get("/profiles/mf_hub/tdma_rf", response_class=HTMLResponse)
async def profile_mf_hub_tdma_rf():
    """MF Hub TDMA RF profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tdma_rf.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TDMA RF Settings</h1>")

@router.get("/profiles/mf_hub/tdma_prot", response_class=HTMLResponse)
async def profile_mf_hub_tdma_prot():
    """MF Hub TDMA Protocol profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tdma_prot.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TDMA Protocol Settings</h1>")

@router.get("/profiles/mf_hub/tdma_bw", response_class=HTMLResponse)
async def profile_mf_hub_tdma_bw():
    """MF Hub TDMA Bandwidth profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tdma_bw.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TDMA BW Settings</h1>")

@router.get("/profiles/mf_hub/tdma_acm", response_class=HTMLResponse)
async def profile_mf_hub_tdma_acm():
    """MF Hub TDMA ACM profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_tdma_acm.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub TDMA ACM Settings</h1>")

@router.get("/profiles/mf_hub/roaming", response_class=HTMLResponse)
async def profile_mf_hub_roaming():
    """MF Hub Roaming profile settings page - using original HTML"""
    template_path = iframe_dir / "profiles" / "mf_hub_roaming.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>MF Hub Roaming Settings</h1>")

# API endpoints for profile settings
@router.post("/api/profiles/basic")
async def api_profile_basic(request: Request):
    """API endpoint to save basic profile settings"""
    data = await request.json()
    logger.info(f"Basic profile settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tdm_rx")
async def api_profile_tdm_rx(request: Request):
    """API endpoint to save TDM RX settings"""
    data = await request.json()
    logger.info(f"TDM RX settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tdm_tx")
async def api_profile_tdm_tx(request: Request):
    """API endpoint to save TDM TX settings"""
    data = await request.json()
    logger.info(f"TDM TX settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/timing")
async def api_profile_timing(request: Request):
    """API endpoint to save timing settings"""
    data = await request.json()
    logger.info(f"Timing settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tlc")
async def api_profile_tlc(request: Request):
    """API endpoint to save TLC settings"""
    data = await request.json()
    logger.info(f"TLC settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tdm_acm")
async def api_profile_tdm_acm(request: Request):
    """API endpoint to save TDM ACM settings"""
    data = await request.json()
    logger.info(f"TDM ACM settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tdma_rf")
async def api_profile_tdma_rf(request: Request):
    """API endpoint to save TDMA RF settings"""
    data = await request.json()
    logger.info(f"TDMA RF settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tdma_prot")
async def api_profile_tdma_prot(request: Request):
    """API endpoint to save TDMA protocol settings"""
    data = await request.json()
    logger.info(f"TDMA Protocol settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tdma_bw")
async def api_profile_tdma_bw(request: Request):
    """API endpoint to save TDMA bandwidth settings"""
    data = await request.json()
    logger.info(f"TDMA BW settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/tdma_acm")
async def api_profile_tdma_acm(request: Request):
    """API endpoint to save TDMA ACM settings"""
    data = await request.json()
    logger.info(f"TDMA ACM settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/roaming")
async def api_profile_roaming(request: Request):
    """API endpoint to save roaming settings"""
    data = await request.json()
    logger.info(f"Roaming settings: {data}")
    return {"status": "ok", "saved": data}

@router.post("/api/profiles/copy")
async def api_profile_copy(request: Request):
    """API endpoint to copy profile settings"""
    data = await request.json()
    logger.info(f"Copy profile from {data.get('from')} to {data.get('to')}")
    return {"status": "ok", "copied": data}

# Site Setup pages routes (using original HTML from Resors_Comtech)
@router.get("/site_setup", response_class=HTMLResponse)
async def site_setup_main():
    """Main Site Setup page - using original HTML"""
    template_path = iframe_dir / "site_setup" / "main.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Site Setup</h1>")

@router.get("/site_setup/setup_via_script", response_class=HTMLResponse)
async def site_setup_via_script():
    """Site Setup via script page - using original HTML"""
    template_path = iframe_dir / "site_setup" / "setup_via_script.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Setup via Script</h1>")

# API endpoints for Site Setup
@router.post("/api/site_setup")
async def api_site_setup(request: Request):
    """API endpoint to save site setup settings"""
    data = await request.json()
    logger.info(f"Site setup settings: {data}")
    return {"status": "ok", "saved": data}

# System pages routes (using original HTML from Resors_Comtech)
@router.get("/system/general", response_class=HTMLResponse)
async def system_general():
    """System General page - using original HTML"""
    template_path = iframe_dir / "system" / "general.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System General</h1>")

@router.get("/system/ethernet", response_class=HTMLResponse)
async def system_ethernet():
    """System Ethernet page - using original HTML"""
    template_path = iframe_dir / "system" / "ethernet.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System Ethernet</h1>")

@router.get("/system/demodulator", response_class=HTMLResponse)
async def system_demodulator():
    """System Demodulator page - using original HTML"""
    template_path = iframe_dir / "system" / "demodulator.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System Demodulator</h1>")

@router.get("/system/modulator", response_class=HTMLResponse)
async def system_modulator():
    """System Modulator page - using original HTML"""
    template_path = iframe_dir / "system" / "modulator.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System Modulator</h1>")

@router.get("/system/interfaces", response_class=HTMLResponse)
async def system_interfaces():
    """System Interfaces page - using original HTML"""
    template_path = iframe_dir / "system" / "interfaces.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System Interfaces</h1>")

@router.get("/system/time_related", response_class=HTMLResponse)
async def system_time_related():
    """System Time-related page - using original HTML"""
    template_path = iframe_dir / "system" / "time_related.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System Time-related</h1>")

@router.get("/system/user_access", response_class=HTMLResponse)
async def system_user_access():
    """System User Access page - using original HTML"""
    template_path = iframe_dir / "system" / "user_access.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System User Access</h1>")

@router.get("/system/save_load", response_class=HTMLResponse)
async def system_save_load():
    """System Save/Load page - using original HTML"""
    template_path = iframe_dir / "system" / "save_load.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System Save/Load</h1>")

@router.get("/system/flash_boot", response_class=HTMLResponse)
async def system_flash_boot():
    """System Flash/Boot page - using original HTML"""
    template_path = iframe_dir / "system" / "flash_boot.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>System Flash/Boot</h1>")

# Maintenance pages routes (using original HTML from Resors_Comtech)
@router.get("/maintenance/log", response_class=HTMLResponse)
async def maintenance_log():
    """Maintenance Log page - using original HTML"""
    template_path = iframe_dir / "maintenance" / "log.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Maintenance Log</h1>")

@router.get("/maintenance/pointing", response_class=HTMLResponse)
async def maintenance_pointing():
    """Maintenance Pointing page - using original HTML"""
    template_path = iframe_dir / "maintenance" / "pointing.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Maintenance Pointing</h1>")

@router.get("/maintenance/reboot", response_class=HTMLResponse)
async def maintenance_reboot():
    """Maintenance Reboot page - using original HTML"""
    template_path = iframe_dir / "maintenance" / "reboot.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Maintenance Reboot</h1>")

@router.get("/maintenance/run_script", response_class=HTMLResponse)
async def maintenance_run_script():
    """Maintenance Run Script page - using original HTML"""
    template_path = iframe_dir / "maintenance" / "run_script.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Maintenance Run Script</h1>")

@router.get("/maintenance/support_info", response_class=HTMLResponse)
async def maintenance_support_info():
    """Maintenance Support Info page - using original HTML"""
    template_path = iframe_dir / "maintenance" / "support_info.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Maintenance Support Info</h1>")

@router.get("/maintenance/traffic_gen", response_class=HTMLResponse)
async def maintenance_traffic_gen():
    """Maintenance Traffic Generator page - using original HTML"""
    template_path = iframe_dir / "maintenance" / "traffic_gen.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Maintenance Traffic Gen</h1>")

@router.get("/maintenance/tuning", response_class=HTMLResponse)
async def maintenance_tuning():
    """Maintenance Tuning page - using original HTML"""
    template_path = iframe_dir / "maintenance" / "tuning.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Maintenance Tuning</h1>")

# Network pages routes (using original HTML from Resors_Comtech)
@router.get("/network/acm", response_class=HTMLResponse)
async def network_acm():
    """Network ACM page - using original HTML"""
    template_path = iframe_dir / "network" / "acm.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Network ACM</h1>")

@router.get("/network/beam_switching", response_class=HTMLResponse)
async def network_beam_switching():
    """Network Beam Switching page - using original HTML"""
    template_path = iframe_dir / "network" / "beam_switching.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Network Beam Switching</h1>")

@router.get("/network/cotm_amip", response_class=HTMLResponse)
async def network_cotm_amip():
    """Network COTM/AMIP page - using original HTML"""
    template_path = iframe_dir / "network" / "cotm_amip.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Network COTM/AMIP</h1>")

@router.get("/network/mf_tdma", response_class=HTMLResponse)
async def network_mf_tdma():
    """Network MF TDMA page - using original HTML"""
    template_path = iframe_dir / "network" / "mf_tdma.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Network MF TDMA</h1>")

@router.get("/network/stlc_nms_red", response_class=HTMLResponse)
async def network_stlc_nms_red():
    """Network STLC/NMS/Redundancy page - using original HTML"""
    template_path = iframe_dir / "network" / "stlc_nms_red.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Network STLC/NMS/Red</h1>")

@router.get("/network/security", response_class=HTMLResponse)
async def network_security():
    """Network Security page - using original HTML"""
    template_path = iframe_dir / "network" / "security.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Network Security</h1>")

@router.get("/network/stations", response_class=HTMLResponse)
async def network_stations():
    """Network Stations page - using original HTML"""
    template_path = iframe_dir / "network" / "stations.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>Network Stations</h1>")

# IP Routing pages routes (using original HTML from Resors_Comtech)
@router.get("/ip_routing/static", response_class=HTMLResponse)
async def ip_routing_static():
    """IP Routing Static page - using original HTML"""
    template_path = iframe_dir / "ip_routing" / "static.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Routing Static</h1>")

@router.get("/ip_routing/dynamic", response_class=HTMLResponse)
async def ip_routing_dynamic():
    """IP Routing Dynamic page - using original HTML"""
    template_path = iframe_dir / "ip_routing" / "dynamic.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Routing Dynamic</h1>")

# QoS pages routes (using original HTML from Resors_Comtech)
@router.get("/qos/policies", response_class=HTMLResponse)
async def qos_policies():
    """QoS Policies page - using original HTML"""
    template_path = iframe_dir / "qos" / "policies.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>QoS Policies</h1>")

@router.get("/qos/real_time", response_class=HTMLResponse)
async def qos_real_time():
    """QoS Real-time page - using original HTML"""
    template_path = iframe_dir / "qos" / "real_time.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>QoS Real-time</h1>")

@router.get("/qos/service_monitoring", response_class=HTMLResponse)
async def qos_service_monitoring():
    """QoS Service Monitoring page - using original HTML"""
    template_path = iframe_dir / "qos" / "service_monitoring.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>QoS Service Monitoring</h1>")

@router.get("/qos/shapers", response_class=HTMLResponse)
async def qos_shapers():
    """QoS Shapers page - using original HTML"""
    template_path = iframe_dir / "qos" / "shapers.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>QoS Shapers</h1>")

# IP Protocols pages routes (using original HTML from Resors_Comtech)
@router.get("/ip_protocols/arp", response_class=HTMLResponse)
async def ip_protocols_arp():
    """IP Protocols ARP page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "arp.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols ARP</h1>")

@router.get("/ip_protocols/acceleration", response_class=HTMLResponse)
async def ip_protocols_acceleration():
    """IP Protocols Acceleration page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "acceleration.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols Acceleration</h1>")

@router.get("/ip_protocols/dhcp", response_class=HTMLResponse)
async def ip_protocols_dhcp():
    """IP Protocols DHCP page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "dhcp.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols DHCP</h1>")

@router.get("/ip_protocols/dns", response_class=HTMLResponse)
async def ip_protocols_dns():
    """IP Protocols DNS page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "dns.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols DNS</h1>")

@router.get("/ip_protocols/gtp", response_class=HTMLResponse)
async def ip_protocols_gtp():
    """IP Protocols GTP page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "gtp.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols GTP</h1>")

@router.get("/ip_protocols/multicast", response_class=HTMLResponse)
async def ip_protocols_multicast():
    """IP Protocols Multicast page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "multicast.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols Multicast</h1>")

@router.get("/ip_protocols/nat", response_class=HTMLResponse)
async def ip_protocols_nat():
    """IP Protocols NAT page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "nat.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols NAT</h1>")

@router.get("/ip_protocols/other_settings", response_class=HTMLResponse)
async def ip_protocols_other_settings():
    """IP Protocols Other Settings page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "other_settings.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols Other Settings</h1>")

@router.get("/ip_protocols/ripv2", response_class=HTMLResponse)
async def ip_protocols_ripv2():
    """IP Protocols RIPv2 page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "ripv2.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols RIPv2</h1>")

@router.get("/ip_protocols/rtp", response_class=HTMLResponse)
async def ip_protocols_rtp():
    """IP Protocols RTP page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "rtp.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols RTP</h1>")

@router.get("/ip_protocols/snmp", response_class=HTMLResponse)
async def ip_protocols_snmp():
    """IP Protocols SNMP page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "snmp.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols SNMP</h1>")

@router.get("/ip_protocols/sntp", response_class=HTMLResponse)
async def ip_protocols_sntp():
    """IP Protocols SNTP page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "sntp.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols SNTP</h1>")

@router.get("/ip_protocols/tftp", response_class=HTMLResponse)
async def ip_protocols_tftp():
    """IP Protocols TFTP page - using original HTML"""
    template_path = iframe_dir / "ip_protocols" / "tftp.html"
    if template_path.exists():
        return FileResponse(str(template_path))
    return HTMLResponse("<h1>IP Protocols TFTP</h1>")
