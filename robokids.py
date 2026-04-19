from flask import Flask, send_file, request, jsonify
import os
from gpiozero import Robot, OutputDevice, DigitalInputDevice
import logging
import time
import threading

# --- CONFIGURATION LOGS ---
# On remet le log en INFO pour voir les requêtes HTTP (les "OK")
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)

app = Flask(__name__)

# Variable pour activer/désactiver la sécurité
security_enabled = True

print("\n" + "=" * 50)
print("DEMARRAGE DU SERVICE ROBOKIDS - MODE DEBUG TOTAL")
print("=" * 50, flush=True)

# --- INITIALISATION DU ROBOT ---
try:
    print("[INIT] Configuration des moteurs...", end=" ", flush=True)
    ena = OutputDevice(12)
    enb = OutputDevice(13)
    ena.on()
    enb.on()
    robot = Robot(left=(17, 18), right=(27, 22))
    robot.stop()
    print("OK", flush=True)
except Exception as e:
    robot = None
    print(f"\n[ERREUR MOTORS] : {e}", flush=True)

# --- INITIALISATION DES CAPTEURS ---
try:
    print("[INIT] Configuration des capteurs...", end=" ", flush=True)
    sensors = {
        'left': {'trig': OutputDevice(11), 'echo': DigitalInputDevice(7)},
        'center': {'trig': OutputDevice(9), 'echo': DigitalInputDevice(8)},
        'right': {'trig': OutputDevice(10), 'echo': DigitalInputDevice(25)}
    }
    has_sensors = True
    print("OK", flush=True)
except Exception as e:
    has_sensors = False
    print(f"\n[ERREUR SENSORS] : {e}", flush=True)


# --- FONCTION DE LECTURE ---
def read_distance(sensor_key):
    if not has_sensors:
        return -1

    s = sensors[sensor_key]
    trig, echo = s['trig'], s['echo']

    trig.on()
    time.sleep(0.00001)
    trig.off()

    t0 = t1 = time.time()
    timeout = t0 + 0.04

    while echo.value == 0:
        t0 = time.time()
        if t0 > timeout: return -1

    timeout = t0 + 0.04
    while echo.value == 1:
        t1 = time.time()
        if t1 > timeout: return -1

    dist = round((t1 - t0) * 17150, 1)

    # LOG DE LECTURE (très utile pour voir si un capteur est mort)
    # print(f"[CAPTEUR] {sensor_key.upper()}: {dist} cm", flush=True)

    return dist


# --- SURVEILLANCE ANTI-COLLISION ---
def security_thread():
    global security_enabled
    print("[THREAD] Surveillance anti-collision ACTIVÉE", flush=True)
    while True:
        if has_sensors and robot and security_enabled:
            d_c = read_distance('center')
            d_l = read_distance('left')
            d_r = read_distance('right')

            # Log discret pour vérifier que le thread tourne
            # print(f"Distances: L={d_l} C={d_c} R={d_r}", flush=True)

            if (0 < d_l < 20) or (0 < d_c < 20) or (0 < d_r < 20):
                if robot.value != (0, 0):
                    robot.stop()
                    print(f"!!! SÉCURITÉ !!! Obstacle détecté (L:{d_l}, C:{d_c}, R:{d_r}) - ARRET", flush=True)
        time.sleep(0.1)


# --- REGLAGES ---
STEP_TIME = 0.1
SPEED = 0.8


@app.route('/')
def index():
    print("[HTTP] Accès à la page d'accueil", flush=True)
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Robokids Console</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            :root { --rk-yellow: #FFD700; --rk-dark: #121212; --rk-gray: #333333; --rk-white: #FFFFFF; --rk-red: #E63946; --rk-green: #2ecc71; }
            body { font-family: sans-serif; text-align: center; background: var(--rk-dark); color: var(--rk-white); padding: 15px; }
            .container { max-width: 450px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 30px; border: 3px solid var(--rk-yellow); }
            .ui-row { background: #222; padding: 10px; border-radius: 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
            .switch { position: relative; display: inline-block; width: 44px; height: 22px; }
            .switch input { opacity: 0; width: 0; height: 0; }
            .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #555; transition: .4s; border-radius: 22px; }
            .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
            input:checked + .slider { background-color: var(--rk-green); }
            input:checked + .slider:before { transform: translateX(22px); }
            .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 15px; }
            button { aspect-ratio: 1/1; font-size: 24px; border-radius: 15px; background: var(--rk-gray); color: white; border: none; box-shadow: 0 4px 0 #000; }
            button:active { background: var(--rk-yellow); color: black; transform: translateY(2px); box-shadow: 0 2px 0 #000; }
            #sensors { margin: 10px 0; background: #111; padding: 10px; border-radius: 10px; display: flex; justify-content: space-around; color: var(--rk-yellow); font-size: 13px;}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="font-size: 28px; font-weight: 900; color: var(--rk-yellow); margin-bottom:10px;">ROBOKIDS</div>
            <div class="ui-row">
                <span>SÉCURITÉ ULTRASON</span>
                <label class="switch">
                    <input type="checkbox" id="sec-toggle" checked onchange="toggleSec()">
                    <span class="slider"></span>
                </label>
            </div>
            <div id="sensors">
                <div>L: <span id="dist-l">--</span>cm</div>
                <div>C: <span id="dist-c">--</span>cm</div>
                <div>R: <span id="dist-r">--</span>cm</div>
            </div>
            <div class="grid">
                <button onclick="send('FL')">↖</button><button onclick="send('F')">▲</button><button onclick="send('FR')">↗</button>
                <button onclick="send('L')">◀</button><button style="background:var(--rk-red)" onclick="send('S')">STP</button><button onclick="send('R')">▶</button>
                <button onclick="send('BL')">↙</button><button onclick="send('B')">▼</button><button onclick="send('BR')">↘</button>
            </div>
        </div>
        <script>
            function toggleSec() {
                let status = document.getElementById('sec-toggle').checked ? 'on' : 'off';
                fetch('/toggle_security?status=' + status);
            }
            function send(cmd) { fetch('/' + cmd); }
            setInterval(() => {
                fetch('/sensors').then(r => r.json()).then(data => {
                    document.getElementById('dist-l').innerText = data.left;
                    document.getElementById('dist-c').innerText = data.center;
                    document.getElementById('dist-r').innerText = data.right;
                });
            }, 800);
        </script>
    </body>
    </html>
    """


@app.route('/toggle_security')
def toggle_security():
    global security_enabled
    status = request.args.get('status')
    security_enabled = (status == 'on')
    print(f"[ACTION] Sécurité changée via UI : {security_enabled}", flush=True)
    return "OK"


@app.route('/sensors')
def get_sensors():
    # On ne logue pas ici pour éviter de polluer le terminal toutes les 800ms
    return jsonify({"left": read_distance('left'), "center": read_distance('center'), "right": read_distance('right')})


@app.route('/<cmd>')
def control(cmd):
    if robot is None:
        print("[ERREUR] Commande reçue mais robot non initialisé", flush=True)
        return "Error", 500

    print(f"[MOTEUR] Commande reçue : {cmd}", flush=True)

    if security_enabled and cmd in ['F', 'FL', 'FR']:
        dist_c = read_distance('center')
        if 0 < dist_c < 20:
            print(f"[BLOQUÉ] Marche avant refusée : Obstacle à {dist_c}cm", flush=True)
            return "Obstacle", 403

    if cmd == 'F':
        robot.forward(speed=SPEED)
    elif cmd == 'B':
        robot.backward(speed=SPEED)
    elif cmd == 'L':
        robot.left(speed=SPEED)
    elif cmd == 'R':
        robot.right(speed=SPEED)
    elif cmd == 'FL':
        robot.value = (0.3, 1)
    elif cmd == 'FR':
        robot.value = (1, 0.3)
    elif cmd == 'BL':
        robot.value = (-0.3, -1)
    elif cmd == 'BR':
        robot.value = (-1, -0.3)
    elif cmd == 'S':
        robot.stop()
        print("[MOTEUR] Stop manuel", flush=True)

    if cmd in ['F', 'B', 'L', 'R', 'FL', 'FR', 'BL', 'BR']:
        time.sleep(STEP_TIME)
        robot.stop()

    return "OK"


if __name__ == '__main__':
    if has_sensors:
        print("[SYSTEME] Démarrage du thread de sécurité...", flush=True)
        t = threading.Thread(target=security_thread, daemon=True)
        t.start()

    print(f"[SYSTEME] Lancement de Flask sur le port 5000...", flush=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
