from flask import Flask, jsonify
import re
import telnetlib

app = Flask(__name__)

OLT_HOST = "10.246.0.242"
OLT_USER = "root"
OLT_PASS = "root"

THRESHOLD = -22  # tampilkan yang >= -22 dBm


@app.route("/get_rx")
def get_rx():
    try:
        print("[INFO] Connecting to OLT", OLT_HOST, "...")
        tn = telnetlib.Telnet(OLT_HOST)
        tn.read_until(b"Login: ")
        tn.write(OLT_USER.encode('ascii') + b"\n")

        tn.read_until(b"Password: ")
        tn.write(OLT_PASS.encode('ascii') + b"\n")

        command = "sho pon pow onu-rx gpon-olt_1/2/1"
        print("[INFO] Sending command:", command)
        tn.write(command.encode('ascii') + b"\n")
        tn.write(b"exit\n")

        output = tn.read_all().decode('utf-8', errors='ignore')
        pattern = r"(gpon-onu_\S+)\s+(-?\d+\.\d+)"
        results = re.findall(pattern, output)

        # ambil data yang >= -22 dBm (dibulatkan 2 angka)
        filtered = []
        for onu, rx in results:
            rx_val = round(float(rx), 2)
            if rx_val >= THRESHOLD:
                filtered.append({"onu": onu, "rx_power": rx_val})

        return jsonify(filtered)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
