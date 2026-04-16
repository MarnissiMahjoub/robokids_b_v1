from flask import Flask, send_file, request
import os
from gpiozero import Robot, OutputDevice, DigitalInputDevice
import logging
import time

# --- CONFIGURATION LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

print("\n" + "=" * 50)
print("DEMARRAGE DU SERVICE ROBOKIDS")
print("=" * 50)

# --- INITIALISATION DU ROBOT ---
try:
    ena = OutputDevice(12)
    enb = OutputDevice(13)
    ena.on()
    enb.on()

    robot = Robot(left=(17, 18), right=(27, 22))
    robot.stop()
    print("[OK] Moteurs configurés (Pins: 17, 18, 27, 22 + EN: 12, 13)")
except Exception as e:
    robot = None
    print(f"[ERREUR MOTORS] : {e}")

# --- INITIALISATION DES CAPTEURS ---
try:
    sensors = {
        'left': {'trig': OutputDevice(10), 'echo': DigitalInputDevice(25)},
        'center': {'trig': OutputDevice(9), 'echo': DigitalInputDevice(8)},
        'right': {'trig': OutputDevice(11), 'echo': DigitalInputDevice(7)}
    }
    has_sensors = True
    print("[OK] Capteurs Ultrasons configurés (Trig: 10,9,11 | Echo: 25,8,7)")
except Exception as e:
    has_sensors = False
    print(f"[ERREUR SENSORS] : {e}")


def read_distance(sensor_key):
    """Lit la distance avec logs détaillés en cas d'échec."""
    if not has_sensors:
        return -1

    s = sensors[sensor_key]
    trig = s['trig']
    echo = s['echo']

    # Impulsion
    trig.on()
    time.sleep(0.00001)
    trig.off()

    t0 = time.time()
    t1 = time.time()
    timeout = t0 + 0.05

    # Attente signal HIGH
    while echo.value == 0:
        t0 = time.time()
        if t0 > timeout:
            print(f"  [!] TIMEOUT BAS : Capteur {sensor_key} ne répond pas.")
            return -1

    # Attente retour LOW
    timeout = t0 + 0.05
    while echo.value == 1:
        t1 = time.time()
        if t1 > timeout:
            print(f"  [!] TIMEOUT HAUT : Capteur {sensor_key} reste bloqué.")
            return -1

    return round((t1 - t0) * 17150, 1)


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
                fetch(url).then(() => document.getElementById('status').innerText = "CMD: " + cmd);
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
    if not has_sensors:
        return {"left": -1, "center": -1, "right": -1}

    dists = {
        "left": read_distance('left'),
        "center": read_distance('center'),
        "right": read_distance('right')
    }

    # LOG TERMINAL : Affiche les distances en boucle
    print(f"SENSORS >> L:{dists['left']} | C:{dists['center']} | R:{dists['right']}")

    return dists


@app.route('/<cmd>')
def control(cmd):
    if robot is None: return "Hardware Error", 500
    duration = request.args.get('duration', default=STEP_TIME, type=float)

    print(f"ACTION >> Commande: {cmd} | Durée: {duration}s")

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
        print("ACTION >> Robot STOP")

    return "OK", 200


@app.route('/logo')
def get_logo():
    path = "/home/mahjoub/Documents/local/robokids_b_v1/robokids.jpg"
    return send_file(path) if os.path.exists(path) else ("", 404)


if __name__ == '__main__':
    # Log de l'IP du serveur
    print("SERVEUR >> Lancé sur le port 5000")
    app.run(host='0.0.0.0', port=5000)
