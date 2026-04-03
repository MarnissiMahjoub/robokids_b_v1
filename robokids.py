from flask import Flask
from gpiozero import Robot
import logging
import time

# --- CONFIGURATION LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# --- INITIALISATION DU ROBOT ---
# Configuration : left=(IN1, IN2, ENA), right=(IN3, IN4, ENB)
# Pins BCM : IN1=17, IN2=18, ENA=12 | IN3=27, IN4=22, ENB=13
try:
    robot = Robot(left=(17, 18, 12), right=(27, 22, 13))
    robot.stop()
    print("=" * 40)
    print("SISTEME ROBOT : OPERATIONNEL")
    print("Mode : Step-by-Step (Sécurisé)")
    print("Vitesse : PWM sur GPIO 12 & 13")
    print("=" * 40)
except Exception as e:
    robot = None
    print(f"!!! ERREUR INITIALISATION : {e}")

# --- REGLAGES ---
STEP_TIME = 0.1  # Temps d'activation en secondes (100ms)
SPEED = 0.8  # Vitesse (0.0 à 1.0). 0.8 est un bon compromis puissance/contrôle


@app.route('/')
def index():
    return "<h1>Robot Robokids Ready!</h1><p>Utilisez /F, /B, /L, /R ou /S</p>"


@app.route('/<cmd>')
def control(cmd):
    if robot is None:
        return "Erreur Matérielle", 500

    print(f"Commande reçue : {cmd}")

    if cmd == 'F':
        robot.forward(speed=SPEED)
        time.sleep(STEP_TIME)
        robot.stop()

    elif cmd == 'B':
        robot.backward(speed=SPEED)
        time.sleep(STEP_TIME)
        robot.stop()

    elif cmd == 'L':
        # Rotation plus courte pour plus de précision dans les virages
        robot.left(speed=SPEED)
        time.sleep(0.05)
        robot.stop()

    elif cmd == 'R':
        robot.right(speed=SPEED)
        time.sleep(0.05)
        robot.stop()

    elif cmd == 'S':
        robot.stop()

    else:
        return "Commande inconnue", 400

    return f"Action {cmd} effectuee", 200


# Pour éviter l'erreur favicon dans le terminal
@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == '__main__':
    # Rappel : host 0.0.0.0 pour être visible par l'app mobile
    app.run(host='0.0.0.0', port=5000, debug=False)
