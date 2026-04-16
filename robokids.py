from flask import Flask, send_file, request, jsonify
import os
from gpiozero import Robot, OutputDevice, DigitalInputDevice
import logging
import time
import threading

# --- CONFIGURATION LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Variable globale pour activer/désactiver la sécurité par ultrason
security_enabled = True

print("\n" + "=" * 50)
print("SYSTEME ROBOKIDS : MODE SÉCURITÉ & AUTO-WIFI")
print("=" * 50)


# --- FONCTION CONNEXION WIFI AUTOMATIQUE ---
def connect_to_wifi(ssid, password):
    print(f"[WIFI] Tentative de connexion à : {ssid}...", flush=True)
    # nmcli tente la connexion. On met ça dans un thread pour ne pas bloquer le démarrage du robot.
    status = os.system(f'sudo nmcli dev wifi connect "{ssid}" password "{password}"')
    if status == 0:
        print(f"[WIFI] Connecté avec succès à {ssid}", flush=True)
    else:
        print(f"[WIFI] Réseau {ssid} non trouvé ou erreur de mot de passe.", flush=True)


# --- INITIALISATION DU ROBOT ---
try:
    ena = OutputDevice(12)
    enb = OutputDevice(13)
    ena.on()
    enb.on()
    robot = Robot(left=(17, 18), right=(27, 22))
    robot.stop()
    print("[OK] Moteurs configurés")
except Exception as e:
    robot = None
    print(f"[ERREUR MOTORS] : {e}")

# --- INITIALISATION DES CAPTEURS (L/R INVERSÉS) ---
try:
    sensors = {
        'left': {'trig': OutputDevice(11), 'echo': DigitalInputDevice(7)},
        'center': {'trig': OutputDevice(9), 'echo': DigitalInputDevice(8)},
        'right': {'trig': OutputDevice(10), 'echo': DigitalInputDevice(25)}
    }
    has_sensors = True
    print("[OK] Capteurs configurés (Inversion L/R appliquée)")
except Exception as e:
    has_sensors = False
    print(f"[ERREUR SENSORS] : {e}")


def read_distance(sensor_key):
    if not has_sensors: return -1
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
    return round((t1 - t0) * 17150, 1)


# --- BOUCLE DE SURVEILLANCE SÉCURITÉ ---
def security_thread():
    global security_enabled
    while True:
        if has_sensors and robot and security_enabled:
            d_l = read_distance('left')
            d_c = read_distance('center')
            d_r = read_distance('right')

            # Si un obstacle est < 20cm sur n'importe quel capteur
            if (0 < d_l < 20) or (0 < d_c < 20) or (0 < d_r < 20):
                if robot.value != (0, 0):  # Si le robot est en mouvement
                    robot.stop()
                    print(f"!!! STOP SÉCURITÉ (L:{d_l} C:{d_c} R:{d_r}) !!!", flush=True)
        time.sleep(0.1)


# --- ROUTES FLASK ---
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Robokids Console</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            :root { --rk-yellow: #FFD700; --rk-dark: #121212; --rk-gray: #333333; --rk-white: #FFFFFF; --rk-red: #E63946; --rk-green: #2ecc71; }
            body { font-family: sans-serif; text-align: center; background: var(--rk-dark); color: var(--rk-white); padding: 15px; margin:0; }
            .container { max-width: 400px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 30px; border: 3px solid var(--rk-yellow); }

            /* Toggle Switch */
            .ui-row { background: #222; padding: 15px; border-radius: 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
            .switch { position: relative; display: inline-block; width: 50px; height: 26px; }
            .switch input { opacity: 0; width: 0; height: 0; }
            .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #555; transition: .4s; border-radius: 34px; }
            .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; }
            input:checked + .slider { background-color: var(--rk-green); }
            input:checked + .slider:before { transform: translateX(24px); }

            #sensors { margin-bottom: 15px; background: #111; padding: 12px; border-radius: 12px; display: flex; justify-content: space-around; color: var(--rk-yellow); font-size: 14px; }
            .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
            button { aspect-ratio: 1/1; font-size: 24px; border-radius: 18px; background: var(--rk-gray); color: white; border: none; box-shadow: 0 5px 0 #000; }
            button:active { transform: translateY(3px); box-shadow: 0 2px 0 #000; background: var(--rk-yellow); color: black; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color:var(--rk-yellow); margin:0 0 15px 0;">ROBOKIDS</h1>

            <div class="ui-row">
                <span>SÉCURITÉ ULTRASON</span>
                <label class="switch">
                    <input type="checkbox" id="sec-toggle" checked onchange="updateSecurity()">
                    <span class="slider"></span>
                </label>
            </div>

            <div id="sensors">
                <div>L: <span id="dist-l">--</span></div>
                <div>C: <span id="dist-c">--</span></div>
                <div>R: <span id="dist-r">--</span></div>
            </div>

            <div class="grid">
                <button onclick="move('FL')">↖</button><button onclick="move('F')">▲</button><button onclick="move('FR')">↗</button>
                <button onclick="move('L')">◀</button><button style="background:var(--rk-red)" onclick="move('S')">■</button><button onclick="move('R')">▶</button>
                <button onclick="move('BL')">↙</button><button onclick="move('B')">▼</button><button onclick="move('BR')">↘</button>
            </div>
        </div>

        <script>
            function updateSecurity() {
                let status = document.getElementById('sec-toggle').checked ? 'on' : 'off';
                fetch('/toggle_security?status=' + status);
            }
            function move(cmd) { fetch('/' + cmd); }
            setInterval(() => {
                fetch('/sensors').then(r => r.json()).then(data => {
                    document.getElementById('dist-l').innerText = data.left + "cm";
                    document.getElementById('dist-c').innerText = data.center + "cm";
                    document.getElementById('dist-r').innerText = data.right + "cm";
                });
            }, 800);
        </script>
    </body>
    </html>
    """


@app.route('/toggle_security')
def toggle_security():
    global security_enabled
    security_enabled = (request.args.get('status') == 'on')
    print(f"SECURITÉ : {'ACTIVÉE' if security_enabled else 'DÉSACTIVÉE'}", flush=True)
    return "OK"


@app.route('/sensors')
def get_sensors():
    return jsonify({"left": read_distance('left'), "center": read_distance('center'), "right": read_distance('right')})


@app.route('/<cmd>')
def control(cmd):
    if not robot: return "Error", 500

    # Si sécurité ON et commande vers l'avant, on check le capteur central
    if security_enabled and cmd in ['F', 'FL', 'FR']:
        if 0 < read_distance('center') < 20:
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

    # Arrêt automatique après 0.1s pour les petits mouvements
    if cmd in ['F', 'B', 'L', 'R', 'FL', 'FR', 'BL', 'BR']:
        time.sleep(0.1)
        robot.stop()

    return "OK"


if __name__ == '__main__':
    # 1. Connexion Wi-Fi (Pense à changer le mot de passe ici)
    threading.Thread(target=connect_to_wifi, args=("mahjoub", "12345678"), daemon=True).start()

    # 2. Thread de sécurité
    if has_sensors:
        threading.Thread(target=security_thread, daemon=True).start()

    app.run(host='0.0.0.0', port=5000)
