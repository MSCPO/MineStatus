from flask import Flask, jsonify, request
from mcstatus import JavaServer 
 
def fetch_server_info(ip):
    try:
        server = JavaServer.lookup(ip)  
        status = server.status()  
        return {
            "online": True,
            "player": {
                "online": status.players.online,
                "max": status.players.max
            },
            "delay": status.latency,
            "icon": status.icon,
            "motd": {
                "plain": status.motd.to_plain(),
                "html": status.motd.to_html(),
                "minecraft": status.motd.to_minecraft(),
                "ansi": status.motd.to_ansi()
            }
        }
    except Exception as e:
        return {"error": str(e), "online": False}

app = Flask(__name__)

@app.route("/")
def ReturnData():
    ip = request.args.get('ip') 
    server_status = fetch_server_info(ip)
    if "error" in server_status:
        return jsonify({"error": server_status["error"], "online": False}), 500
    else:
        return jsonify(server_status)

if __name__ == "__main__":
    app.run(debug=True) 