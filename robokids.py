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

# --- INITIALISATION DU ROBOT ---
try:
    ena = OutputDevice(12)
    enb = OutputDevice(13)
    ena.on()
    enb.on()

    robot = Robot(left=(17, 18), right=(27, 22))
    robot.stop()
    print("=" * 40)
    print("SYSTEME ROBOT : OPERATIONNEL")
    print("=" * 40)
except Exception as e:
    robot = None
    print(f"!!! ERREUR INITIALISATION : {e}")

# --- INITIALISATION DES CAPTEURS ULTRASONS (3 ECHO SÉPARÉS) ---
try:
    # Mappage : Gauche (26/14), Centre (19/15), Droite (21/18)
    sensors = {
        'left': {'trig': OutputDevice(26), 'echo': DigitalInputDevice(14)},
        'center': {'trig': OutputDevice(19), 'echo': DigitalInputDevice(15)},
        'right': {'trig': OutputDevice(21), 'echo': DigitalInputDevice(18)}
    }
    has_sensors = True
    print("Capteurs Ultrasons : 3 CANAUX INDÉPENDANTS")
except Exception as e:
    has_sensors = False
    print(f"!!! ERREUR ULTRASONS : {e}")


def read_distance(sensor_name):
    """Lit la distance pour un capteur spécifique sans interférer avec les autres."""
    if not has_sensors:
        return -1

    s = sensors[sensor_name]
    trig = s['trig']
    echo = s['echo']

    # Impulsion de déclenchement
    trig.on()
    time.sleep(0.00001)
    trig.off()

    t0 = time.time()
    t1 = time.time()
    timeout = t0 + 0.05

    # Attente du début de l'écho
    while echo.value == 0:
        t0 = time.time()
        if t0 > timeout: return -1

    # Attente de la fin de l'écho
    timeout = t0 + 0.05
    while echo.value == 1:
        t1 = time.time()
        if t1 > timeout: return -1

    return (t1 - t0) * 17150


# --- REGLAGES ---
STEP_TIME = 0.1
SPEED = 0.8


@app.route('/')
def index():
    # Ton HTML reste exactement le même que celui que tu m'as envoyé
    return """... (Insère ici ton bloc HTML complet) ..."""


@app.route('/sensors')
def get_sensors():
    if not has_sensors:
        return {"left": -1, "center": -1, "right": -1}

    # On lit les distances une par une pour éviter les rebonds sonores
    d_left = read_distance('left')
    time.sleep(0.02)
    d_center = read_distance('center')
    time.sleep(0.02)
    d_right = read_distance('right')

    return {
        "left": round(d_left, 1),
        "center": round(d_center, 1),
        "right": round(d_right, 1)
    }


@app.route('/<cmd>')
def control(cmd):
    if robot is None: return "Erreur Matérielle", 500
    duration = request.args.get('duration', default=STEP_TIME, type=float)

    if cmd == 'F':
        robot.forward(speed=SPEED)
        time.sleep(duration)
        robot.stop()
    elif cmd == 'CF':
        robot.forward(speed=SPEED)
    elif cmd == 'FL':
        robot.value = (SPEED * 0.3, SPEED)
        time.sleep(duration)
        robot.stop()
    elif cmd == 'CFL':
        robot.value = (SPEED * 0.3, SPEED)
    elif cmd == 'FR':
        robot.value = (SPEED, SPEED * 0.3)
        time.sleep(duration)
        robot.stop()
    elif cmd == 'CFR':
        robot.value = (SPEED, SPEED * 0.3)
    elif cmd == 'B':
        robot.backward(speed=SPEED)
        time.sleep(duration)
        robot.stop()
    elif cmd == 'CB':
        robot.backward(speed=SPEED)
    elif cmd == 'L':
        robot.left(speed=SPEED)
        time.sleep(duration)
        robot.stop()
    elif cmd == 'CL':
        robot.left(speed=SPEED)
    elif cmd == 'R':
        robot.right(speed=SPEED)
        time.sleep(duration)
        robot.stop()
    elif cmd == 'CR':
        robot.right(speed=SPEED)
    elif cmd == 'S':
        robot.stop()
    else:
        return "Commande inconnue", 400

    return f"Action {cmd} effectuee", 200


@app.route('/logo')
def get_logo():
    logo_path = "/home/mahjoub/Documents/local/robokids_b_v1/robokids.jpg"
    if os.path.exists(logo_path):
        return send_file(logo_path, mimetype='image/jpeg')
    return "", 404


@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
