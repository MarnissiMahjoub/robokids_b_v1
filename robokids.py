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
    # Utilisation correcte de Robot(left=(pin1, pin2), right=(pin3, pin4))
    # ENA et ENB ne sont pas des arguments directs de Robot, mais souvent gérés par PWM si on utilise Motor
    robot = Robot(left=(17, 18), right=(27, 22))
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
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Robokids Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body { font-family: sans-serif; text-align: center; background: #222; color: white; margin: 0; padding: 20px; touch-action: manipulation; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-width: 300px; margin: 50px auto; }
        button { 
            padding: 20px; font-size: 24px; border: none; border-radius: 10px; 
            background: #444; color: white; cursor: pointer; user-select: none;
            transition: background 0.1s;
        }
        button:active { background: #007bff; }
        .btn-f { grid-column: 2; }
        .btn-l { grid-column: 1; }
        .btn-s { grid-column: 2; background: #dc3545; }
        .btn-r { grid-column: 3; }
        .btn-b { grid-column: 2; }
        #status { margin-top: 20px; color: #888; }
    </style>
</head>
<body>
    <h1>Robokids Console</h1>
    <div class="grid">
        <button class="btn-f" onclick="send('F')">⬆️</button>
        <button class="btn-l" onclick="send('L')">⬅️</button>
        <button class="btn-s" onclick="send('S')">⏹️</button>
        <button class="btn-r" onclick="send('R')">➡️</button>
        <button class="btn-b" onclick="send('B')">⬇️</button>
    </div>
    <div id="status">Prêt</div>

    <script>
        function send(cmd) {
            const status = document.getElementById('status');
            status.innerText = 'Commande : ' + cmd;
            fetch('/' + cmd)
                .then(r => {
                    if(!r.ok) status.innerText = 'Erreur';
                })
                .catch(e => status.innerText = 'Erreur réseau');
        }
    </script>
</body>
</html>
"""


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
