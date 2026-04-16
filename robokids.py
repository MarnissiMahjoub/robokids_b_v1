from flask import Flask, send_file, request
import os
from gpiozero import Robot, OutputDevice, DigitalInputDevice
import logging
import time
import threading

# --- CONFIGURATION LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

print("\n" + "=" * 50)
print("DEMARRAGE DU SERVICE ROBOKIDS - SECURITÉ 20CM")
print("=" * 50)

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

# --- INITIALISATION DES CAPTEURS (L et R INVERSÉS ICI) ---
try:
    sensors = {
        # Inversion demandée : Right devient Left et inversement
        'left': {'trig': OutputDevice(11), 'echo': DigitalInputDevice(7)},
        'center': {'trig': OutputDevice(9), 'echo': DigitalInputDevice(8)},
        'right': {'trig': OutputDevice(10), 'echo': DigitalInputDevice(25)}
    }
    has_sensors = True
    print("[OK] Capteurs configurés et L/R inversés")
except Exception as e:
    has_sensors = False
    print(f"[ERREUR SENSORS] : {e}")


def read_distance(sensor_key):
    """Lecture brute d'un capteur."""
    if not has_sensors:
        return -1

    s = sensors[sensor_key]
    trig = s['trig']
    echo = s['echo']

    trig.on()
    time.sleep(0.00001)
    trig.off()

    t0 = time.time()
    t1 = time.time()
    timeout = t0 + 0.04  # Timeout court pour la réactivité

    while echo.value == 0:
        t0 = time.time()
        if t0 > timeout: return -1

    timeout = t0 + 0.04
    while echo.value == 1:
        t1 = time.time()
        if t1 > timeout: return -1

    return round((t1 - t0) * 17150, 1)


# --- BOUCLE DE SURVEILLANCE ANTI-COLLISION ---
def security_thread():
    """Vérifie les obstacles en arrière-plan sans attendre l'interface web."""
    while True:
        if has_sensors and robot:
            d_l = read_distance('left')
            d_c = read_distance('center')
            d_r = read_distance('right')

            # Affichage des logs en continu dans le terminal
            print(f"DISTANCES >> L:{d_l} | C:{d_c} | R:{d_r}", flush=True)

            # Si un obstacle est détecté à moins de 20cm (et distance valide > 0)
            if (0 < d_l < 20) or (0 < d_c < 20) or (0 < d_r < 20):
                # Si le robot n'est pas déjà arrêté
                if robot.value != (0, 0):
                    robot.stop()
                    print("!!! ALERTE 20CM : ARRET AUTOMATIQUE !!!", flush=True)

        time.sleep(0.1)  # Fréquence de 10Hz (très réactif)


# Lancement du thread de sécurité
if has_sensors:
    monitor = threading.Thread(target=security_thread, daemon=True)
    monitor.start()

# --- REGLAGES ---
STEP_TIME = 0.1
SPEED = 0.8


@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Robokids Console</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            :root { --rk-yellow: #FFD700; --rk-dark: #121212; --rk-gray: #333333; --rk-white: #FFFFFF; --rk-red: #E63946; }
            body { font-family: sans-serif; text-align: center; background: var(--rk-dark); color: var(--rk-white); padding: 20px; }
            .container { max-width: 450px; margin: 0 auto; background: #1e1e1e; padding: 25px; border-radius: 30px; border: 3px solid var(--rk-yellow); }
            .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }
            button { aspect-ratio: 1/1; font-size: 28px; border-radius: 20px; background: var(--rk-gray); color: white; border: none; box-shadow: 0 6px 0 #000; }
            button:active, button.active { background: var(--rk-yellow); color: black; transform: translateY(4px); box-shadow: 0 2px 0 #000; }
            #sensors { margin: 15px 0; background: #111; padding: 12px; border-radius: 12px; display: flex; justify-content: space-around; color: var(--rk-yellow); }
            .mode-switcher { background: var(--rk-gray); border-radius: 15px; padding: 10px; margin: 10px 0; cursor: pointer; font-weight: bold; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <div style="font-size: 32px; font-weight: 900; color: var(--rk-yellow);">ROBOKIDS</div>
            <div class="mode-switcher" onclick="toggleMainMode()" id="mode-label">MODE: PRECISION</div>
            <div id="sensors">
                <div>L: <span id="dist-l">--</span>cm</div>
                <div>C: <span id="dist-c">--</span>cm</div>
                <div>R: <span id="dist-r">--</span>cm</div>
            </div>
            <div id="precision-settings">
                <input type="radio" id="s1" name="step" value="0.05"> 0.05s
                <input type="radio" id="s2" name="step" value="0.1" checked> 0.1s
                <input type="radio" id="s3" name="step" value="0.2"> 0.2s
            </div>
            <div class="grid">
                <button onclick="handleMove('FL')">↖</button>
                <button onclick="handleMove('F')">▲</button>
                <button onclick="handleMove('FR')">↗</button>
                <button onclick="handleMove('L')">◀</button>
                <button style="background:var(--rk-red)" onclick="send('S')">STOP</button>
                <button onclick="handleMove('R')">▶</button>
                <button></button>
                <button onclick="handleMove('B')">▼</button>
                <button></button>
            </div>
            <div id="status">READY</div>
        </div>
        <script>
            let isContinuousMode = false;
            function toggleMainMode() {
                isContinuousMode = !isContinuousMode;
                document.getElementById('mode-label').innerText = isContinuousMode ? "MODE: CONTINU" : "MODE: PRECISION";
                document.getElementById('precision-settings').classList.toggle('hidden');
                send('S');
            }
            function handleMove(dir) {
                if (isContinuousMode) { send('C' + dir); }
                else { send(dir); }
            }
            function send(cmd) {
                let url = '/' + cmd;
                if (!cmd.startsWith('C') && cmd !== 'S') {
                    const step = document.querySelector('input[name="step"]:checked').value;
                    url += '?duration=' + step;
                }
                fetch(url);
            }
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


@app.route('/sensors')
def get_sensors():
    # Cette route sert maintenant surtout à l'affichage web
    return {
        "left": read_distance('left'),
        "center": read_distance('center'),
        "right": read_distance('right')
    }


@app.route('/<cmd>')
def control(cmd):
    if robot is None: return "Hardware Error", 500
    duration = request.args.get('duration', default=STEP_TIME, type=float)

    # Sécurité supplémentaire : si on demande d'avancer mais qu'il y a un obstacle
    if cmd in ['F', 'CF', 'FL', 'FR', 'CFL', 'CFR']:
        if 0 < read_distance('center') < 20:
            print("COMMANDE REFUSÉE : OBSTACLE TROP PROCHE")
            return "Obstacle", 403

    if cmd == 'F':
        robot.forward(speed=SPEED);
        time.sleep(duration);
        robot.stop()
    elif cmd == 'CF':
        robot.forward(speed=SPEED)
    elif cmd == 'FL':
        robot.value = (SPEED * 0.3, SPEED);
        time.sleep(duration);
        robot.stop()
    elif cmd == 'CFL':
        robot.value = (SPEED * 0.3, SPEED)
    elif cmd == 'FR':
        robot.value = (SPEED, SPEED * 0.3);
        time.sleep(duration);
        robot.stop()
    elif cmd == 'CFR':
        robot.value = (SPEED, SPEED * 0.3)
    elif cmd == 'B':
        robot.backward(speed=SPEED);
        time.sleep(duration);
        robot.stop()
    elif cmd == 'CB':
        robot.backward(speed=SPEED)
    elif cmd == 'L':
        robot.left(speed=SPEED);
        time.sleep(duration);
        robot.stop()
    elif cmd == 'CL':
        robot.left(speed=SPEED)
    elif cmd == 'R':
        robot.right(speed=SPEED);
        time.sleep(duration);
        robot.stop()
    elif cmd == 'CR':
        robot.right(speed=SPEED)
    elif cmd == 'S':
        robot.stop()

    return "OK", 200


@app.route('/logo')
def get_logo():
    path = "/home/mahjoub/Documents/local/robokids_b_v1/robokids.jpg"
    return send_file(path) if os.path.exists(path) else ("", 404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
