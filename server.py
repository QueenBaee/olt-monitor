import os
import asyncio
import telnetlib3
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, template_folder="templates", static_folder="static")

OLT_USER = os.getenv("OLT_USER")
OLT_PASS = os.getenv("OLT_PASS")

async def fetch_rx_data(olt_host, port, threshold=-22):
    print(f"[INFO] Connecting to OLT {olt_host} ...")
    reader, writer = await telnetlib3.open_connection(
        olt_host, 23, shell=None, connect_minwait=0.1, connect_maxwait=1, encoding="utf8"
    )

    def safe_write(cmd):
        if not cmd.endswith("\n"):
            cmd += "\n"
        writer.write(cmd)

    # Login sequence
    banner = ""
    for _ in range(20):
        chunk = await reader.read(300)
        banner += chunk
        if "Username:" in banner or "Login:" in banner:
            break
        await asyncio.sleep(0.2)

    if "Username:" in banner or "Login:" in banner:
        print("[INFO] Sending username...")
        safe_write(OLT_USER)
    else:
        print("[ERROR] Username/Login prompt not found.")
        writer.close()
        return []

    data = await reader.read(300)
    while "Password:" not in data:
        more = await reader.read(300)
        if not more:
            break
        data += more
    print("[INFO] Sending password...")
    safe_write(OLT_PASS)

    # Tunggu prompt #
    buffer = ""
    for _ in range(20):
        part = await reader.read(300)
        buffer += part
        if "#" in buffer:
            break
        await asyncio.sleep(0.2)

    # === SET COMMAND SESUAI OLT ===
    if olt_host == "10.246.2.218":
        rx_cmd = f"sho pon pow onu-rx gpon_olt-{port}"  # port = '1/2/1'
        int_cmd_func = lambda onu: f"sho running-config-interface {onu.replace('gpon-olt_', 'gpon_onu-')}"
    else:
        rx_cmd = f"sho pon pow onu-rx gpon-olt_{port}"  # port = '1/2/1'
        int_cmd_func = lambda onu: f"sho run int {onu}"

    print(f"[INFO] Sending command: {rx_cmd}")
    safe_write(rx_cmd)

    output = ""
    while True:
        try:
            chunk = await asyncio.wait_for(reader.read(500), timeout=2)
            if not chunk:
                break
            output += chunk
            if "--More--" in chunk:
                safe_write(" ")
                await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            break

    # === PARSE RESULT ===
    result = []

    onus = []
    for line in output.splitlines():
        if "gpon-onu" in line or "gpon_onu" in line:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    rx_val = float(parts[1].replace("(dbm)", "").replace("(", "").replace(")", ""))
                    if rx_val >= (threshold - 0.05):
                        onus.append((parts[0], rx_val))
                except ValueError:
                    continue

    async def get_detail(onu_tuple):
        onu, rx_val = onu_tuple
        cmd = int_cmd_func(onu)
        safe_write(cmd)
        detail = ""
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(500), timeout=1)
                if not chunk:
                    break
                detail += chunk
                if "--More--" in chunk:
                    safe_write(" ")
                    await asyncio.sleep(0.1)
            except asyncio.TimeoutError:
                break
        name = description = ""
        for dline in detail.splitlines():
            if dline.strip().startswith("name "):
                name = dline.strip().replace("name ", "")
            if dline.strip().startswith("description "):
                description = dline.strip().replace("description ", "")
        return {
            "onu": onu,
            "rx_power": round(rx_val, 3),
            "name": name,
            "description": description
        }

    # Ambil detail semua ONUs secara async
    if onus:
        result = []
        for onu in onus:
            detail = await get_detail(onu)
            result.append(detail)
    else:
        print(f"[INFO] Found 0 ONUs above or equal to {threshold} dBm.")
    safe_write("exit")
    writer.close()
    return result

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/low-rx")
def api_low_rx():
    olt_host = request.args.get("olt")
    port = request.args.get("port")
    threshold = float(request.args.get("threshold", -22))
    if not olt_host or not port:
        return jsonify({"error": "Missing olt or port parameter"}), 400
    data = asyncio.run(fetch_rx_data(olt_host, port, threshold))
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
