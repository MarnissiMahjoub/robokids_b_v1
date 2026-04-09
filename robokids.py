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
# Configuration : left=(IN1, IN2, ENA), right=(IN3, IN4, ENB)
# Pins BCM : IN1=17, IN2=18, ENA=12 | IN3=27, IN4=22, ENB=13
try:
    # Utilisation correcte de Robot(left=(pin1, pin2), right=(pin3, pin4))
    # ENA (gpio 12) et ENB (gpio 13) allumées pour autoriser les moteurs
    ena = OutputDevice(12)
    enb = OutputDevice(13)
    ena.on()
    enb.on()
    
    robot = Robot(left=(17, 18), right=(27, 22))
    robot.stop()
    print("=" * 40)
    print("SISTEME ROBOT : OPERATIONNEL")
    print("Mode : Step-by-Step (Sécurisé)")
    print("Vitesse : ENA/ENB activés (HIGH), PWM sur IN1/IN2")
    print("=" * 40)
except Exception as e:
    robot = None
    print(f"!!! ERREUR INITIALISATION : {e}")

# --- INITIALISATION DES CAPTEURS ULTRASONS ---
try:
    echo_pin = DigitalInputDevice(14)
    # Mappage par défaut (à inverser si besoin) : Gauche=26, Centre=19, Droite=21
    trig_pins = {
        'left': OutputDevice(26),
        'center': OutputDevice(19),
        'right': OutputDevice(21)
    }
    ultrasonic_lock = threading.Lock()
    has_sensors = True
    print("Capteurs Ultrasons : MULTIPLEXÉS (Echo=14)")
except Exception as e:
    has_sensors = False
    print(f"!!! ERREUR ULTRASONS : {e}")

def read_distance(trig):
    """Lis la distance via un trig spécifique en partageant l'echo."""
    if not has_sensors or echo_pin is None:
        return -1
    
    # On utilise un verrou pour interroger un seul capteur à la fois
    with ultrasonic_lock:
        trig.on()
        time.sleep(0.00001)
        trig.off()
        
        t0 = time.time()
        t1 = time.time()
        timeout = t0 + 0.05  # Timeout 50ms (~8 mètres max)
        
        # Attente du début de l'écho (HIGH)
        while echo_pin.value == 0:
            t0 = time.time()
            if t0 > timeout:
                return -1
                
        # Attente de la fin de l'écho (LOW)
        timeout = t0 + 0.05
        while echo_pin.value == 1:
            t1 = time.time()
            if t1 > timeout:
                return -1
                
        # Calcul de la distance en cm
        return (t1 - t0) * 17150

# --- REGLAGES ---
STEP_TIME = 0.1  # Temps d'activation en secondes (100ms)
SPEED = 0.8  # Vitesse (0.0 à 1.0). 0.8 est un bon compromis puissance/contrôle


@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Robokids Console</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        :root {
            --rk-yellow: #FFD700;
            --rk-dark: #121212;
            --rk-gray: #333333;
            --rk-white: #FFFFFF;
            --rk-red: #E63946;
        }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            text-align: center; 
            background: var(--rk-dark); 
            color: var(--rk-white); 
            margin: 0; 
            padding: 20px; 
            touch-action: manipulation;
        }
        
        .container {
            max-width: 450px;
            margin: 0 auto;
            background: #1e1e1e;
            padding: 25px;
            border-radius: 30px;
            border: 3px solid var(--rk-yellow);
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        }
        
        .logo-img {
            max-width: 120px;
            margin-bottom: 10px;
        }
        
        .logo-text {
            font-size: 32px;
            font-weight: 900;
            color: var(--rk-yellow);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 5px;
            text-shadow: 2px 2px 0px #000;
        }
        
        .subtitle {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        
        h2 { 
            font-size: 14px; 
            color: var(--rk-yellow); 
            margin-top: 10px; 
            margin-bottom: 10px;
            text-align: left;
            padding-left: 10px;
            border-left: 4px solid var(--rk-yellow);
            text-transform: uppercase;
        }
        
        .grid { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 15px; 
            margin-bottom: 20px;
        }
        
        button { 
            aspect-ratio: 1/1;
            font-size: 28px; 
            border: none; 
            border-radius: 20px; 
            background: var(--rk-gray); 
            color: var(--rk-white); 
            cursor: pointer; 
            user-select: none;
            transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 6px 0 #000;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        button:active { 
            transform: translateY(4px); 
            box-shadow: 0 2px 0 #000;
            background: var(--rk-yellow);
            color: var(--rk-dark);
        }
        
        .btn-f { grid-column: 2; }
        .btn-l { grid-column: 1; }
        .btn-s { 
            grid-column: 2; 
            background: var(--rk-red); 
            box-shadow: 0 6px 0 #800;
            font-weight: bold;
            font-size: 16px;
        }
        .btn-s:active { background: #ff4d5e; }
        .btn-r { grid-column: 3; }
        .btn-b { grid-column: 2; }
        
        /* Mode Continu */
        .mode-cont button { 
            border: 2px solid var(--rk-yellow);
            background: transparent;
        }
        
        .mode-cont button.active { 
            background: var(--rk-yellow); 
            color: var(--rk-dark);
            box-shadow: 0 2px 0 #b8860b; 
            transform: translateY(4px); 
        }
        
        .radio-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 10px;
            justify-content: center;
        }
        
        .radio-item {
            flex: 1 1 40%;
            min-width: 120px;
        }
        
        .radio-item input {
            position: absolute;
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .radio-item label {
            display: block;
            background: var(--rk-gray);
            color: var(--rk-white);
            padding: 12px 10px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 800;
            border: 2px solid transparent;
            transition: all 0.2s;
            position: relative;
            z-index: 5; /* Augmenté pour être au-dessus de tout */
        }
        
        .radio-item input:checked + label {
            border: 2px solid var(--rk-yellow) !important;
            color: var(--rk-yellow);
            background: rgba(255, 215, 0, 0.1);
        }
        
        /* Mode Switch Styling */
        .mode-switcher {
            display: flex;
            background: var(--rk-gray);
            border-radius: 15px;
            margin: 5px 0;
            padding: 5px;
            position: relative;
            border: 1px solid #444;
        }
        
        .mode-option {
            flex: 1;
            padding: 10px;
            cursor: pointer;
            z-index: 1;
            font-weight: 900;
            font-size: 14px;
            transition: color 0.3s;
            text-transform: uppercase;
        }
        
        .mode-option.active {
            color: var(--rk-dark);
        }
        
        .mode-slider {
            position: absolute;
            top: 5px;
            left: 5px;
            width: calc(50% - 5px);
            height: calc(100% - 100%); /* Hidden by default or handled by JS */
            height: 38px;
            background: var(--rk-yellow);
            border-radius: 10px;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .mode-slider.right {
            transform: translateX(100%);
        }

        #precision-settings {
            transition: opacity 0.3s, max-height 0.3s;
            overflow: hidden;
        }
        
        .hidden {
            opacity: 0;
            max-height: 0;
            margin: 0;
            padding: 0;
            pointer-events: none;
        }
        
        #sensors {
            margin: 15px 0;
            background: #111;
            padding: 12px;
            border-radius: 12px;
            display: flex;
            justify-content: space-around;
            border: 1px solid #333;
            font-size: 13px;
            font-weight: bold;
            color: var(--rk-yellow);
        }
        
        .sensor-val {
            color: var(--rk-white);
            font-family: monospace;
            font-size: 15px;
        }

        #status { 
            margin-top: 25px; 
            padding: 12px; 
            background: #000; 
            border-radius: 12px; 
            font-family: 'Courier New', Courier, monospace; 
            color: var(--rk-yellow); 
            font-size: 14px;
            border: 1px solid #333;
        }
        
        .indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: var(--rk-yellow);
            border-radius: 50%;
            margin-right: 8px;
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <img src="/logo" class="logo-img" alt="Robokids Logo">
        <div class="logo-text">ROBOKIDS</div>
        <div class="subtitle">Robot Control System v2.0</div>
        
        <div class="mode-switcher" onclick="toggleMainMode()">
            <div id="slider" class="mode-slider"></div>
            <div id="opt-step" class="mode-option active">Précision</div>
            <div id="opt-cont" class="mode-option">Continu</div>
        </div>

        <div id="sensors">
            <div>◀ L: <span id="dist-l" class="sensor-val">--</span>cm</div>
            <div>▲ C: <span id="dist-c" class="sensor-val">--</span>cm</div>
            <div>▶ R: <span id="dist-r" class="sensor-val">--</span>cm</div>
        </div>

        <div id="precision-settings">
            <h2>• Distance / Durée</h2>
            <div class="radio-group">
                <div class="radio-item">
                    <input type="radio" id="s1" name="step" value="0.05">
                    <label for="s1">TRÈS COURT (0.05s)</label>
                </div>
                <div class="radio-item">
                    <input type="radio" id="s2" name="step" value="0.1" checked>
                    <label for="s2">NORMAL (0.1s)</label>
                </div>
                <div class="radio-item">
                    <input type="radio" id="s3" name="step" value="0.2">
                    <label for="s3">LONG (0.2s)</label>
                </div>
                <div class="radio-item">
                    <input type="radio" id="s4" name="step" value="0.5">
                    <label for="s4">TRÈS LONG (0.5s)</label>
                </div>
            </div>
        </div>

        <h2>• Contrôles</h2>
        <div class="grid">
            <button class="btn-f" id="btn-F" onclick="handleMove('F')">▲</button>
            <button class="btn-l" id="btn-L" onclick="handleMove('L')">◀</button>
            <button class="btn-s" onclick="send('S')">STOP</button>
            <button class="btn-r" id="btn-R" onclick="handleMove('R')">▶</button>
            <button class="btn-b" id="btn-B" onclick="handleMove('B')">▼</button>
        </div>
        
        <div id="status"><span class="indicator"></span>SYSTEM READY</div>
    </div>

    <script>
        let isContinuousMode = false;
        let activeContinuousBtn = null;

        function toggleMainMode() {
            isContinuousMode = !isContinuousMode;
            
            // UI Update
            document.getElementById('slider').classList.toggle('right');
            document.getElementById('opt-step').classList.toggle('active');
            document.getElementById('opt-cont').classList.toggle('active');
            document.getElementById('precision-settings').classList.toggle('hidden');
            document.querySelector('.grid').classList.toggle('mode-cont');
            
            // Reset state
            send('S');
        }

        function handleMove(direction) {
            if (isContinuousMode) {
                const cmd = 'C' + direction;
                const btn = document.getElementById('btn-' + direction);
                
                if (activeContinuousBtn === btn) {
                    // Si on reclique sur le même bouton en mode continu, on l'arrête
                    send('S');
                } else {
                    // Sinon on lance le mouvement continu
                    stopVisualContinuous();
                    btn.classList.add('active');
                    activeContinuousBtn = btn;
                    send(cmd);
                }
            } else {
                // Mode Précision normal
                send(direction);
            }
        }

        function updateStatus(msg) {
            document.getElementById('status').innerHTML = '<span class="indicator"></span>' + msg.toUpperCase();
        }

        function send(cmd) {
            if (cmd === 'S') {
                stopVisualContinuous();
            }
            
            let url = '/' + cmd;
            if (!cmd.startsWith('C') && cmd !== 'S') {
                const step = document.querySelector('input[name="step"]:checked').value;
                url += '?duration=' + step;
            }

            fetch(url)
                .then(r => {
                    if(r.ok) updateStatus('CMD: ' + cmd);
                    else updateStatus('SERVER ERROR');
                })
                .catch(e => updateStatus('NETWORK ERROR'));
        }

        function stopVisualContinuous() {
            document.querySelectorAll('.grid button').forEach(b => b.classList.remove('active'));
            activeContinuousBtn = null;
        }

        // Boucle de mise à jour des ultrasons
        setInterval(() => {
            fetch('/sensors')
                .then(r => r.json())
                .then(data => {
                    const formatDist = val => val < 0 ? "ERR" : val.toFixed(1);
                    document.getElementById('dist-l').innerText = formatDist(data.left);
                    document.getElementById('dist-c').innerText = formatDist(data.center);
                    document.getElementById('dist-r').innerText = formatDist(data.right);
                    
                    // Alerte de proximité (visuel)
                    document.getElementById('dist-c').style.color = (data.center > 0 && data.center < 15) ? 'var(--rk-red)' : 'var(--rk-white)';
                })
                .catch(e => console.log("Sensors unreach"));
        }, 1000); // Mise à jour toutes les secondes pour éviter de surcharger le réseau
    </script>
</body>
</html>
"""

@app.route('/sensors')
def get_sensors():
    if not has_sensors:
        return {"left": -1, "center": -1, "right": -1}
    # On lit le capteur gauche, puis centre, puis droite (séquentiellement à cause du partage d'echo)
    return {
        "left": read_distance(trig_pins['left']),
        "center": read_distance(trig_pins['center']),
        "right": read_distance(trig_pins['right'])
    }

@app.route('/logo')
def get_logo():
    logo_path = "/home/mahjoub/Documents/local/robokids_b_v1/robokids.jpg"
    if os.path.exists(logo_path):
        return send_file(logo_path, mimetype='image/jpeg')
    return "", 404


@app.route('/<cmd>')
def control(cmd):
    if robot is None:
        return "Erreur Matérielle", 500

    duration = request.args.get('duration', default=STEP_TIME, type=float)

    print(f"Commande reçue : {cmd} (durée: {duration})")

    if cmd == 'F':
        robot.forward(speed=SPEED)
        time.sleep(duration)
        robot.stop()

    elif cmd == 'CF':
        robot.forward(speed=SPEED)

    elif cmd == 'B':
        robot.backward(speed=SPEED)
        time.sleep(duration)
        robot.stop()

    elif cmd == 'CB':
        robot.backward(speed=SPEED)

    elif cmd == 'L':
        # FORCER la rotation sur soi-même à gauche (gauche recule, droite avance)
        robot.left_motor.backward(speed=SPEED)
        robot.right_motor.forward(speed=SPEED)
        time.sleep(duration)
        robot.stop()

    elif cmd == 'CL':
        robot.left_motor.backward(speed=SPEED)
        robot.right_motor.forward(speed=SPEED)

    elif cmd == 'R':
        # FORCER la rotation sur soi-même à droite (gauche avance, droite recule)
        robot.left_motor.forward(speed=SPEED)
        robot.right_motor.backward(speed=SPEED)
        time.sleep(duration)
        robot.stop()

    elif cmd == 'CR':
        robot.left_motor.forward(speed=SPEED)
        robot.right_motor.backward(speed=SPEED)

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
