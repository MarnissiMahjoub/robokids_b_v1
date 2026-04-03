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
            margin-bottom: 25px;
            text-transform: uppercase;
        }
        
        h2 { 
            font-size: 14px; 
            color: var(--rk-yellow); 
            margin-top: 30px; 
            margin-bottom: 15px;
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
        <div class="logo-text">ROBOKIDS</div>
        <div class="subtitle">Robot Control System v2.0</div>
        
        <h2>• Mode Précision</h2>
        <div class="grid">
            <button class="btn-f" onclick="send('F')">▲</button>
            <button class="btn-l" onclick="send('L')">◀</button>
            <button class="btn-s" onclick="send('S')">STOP</button>
            <button class="btn-r" onclick="send('R')">▶</button>
            <button class="btn-b" onclick="send('B')">▼</button>
        </div>

        <h2>• Mode Continu</h2>
        <div class="grid mode-cont">
            <button class="btn-f" id="btn-CF" onclick="toggle('CF')">▲</button>
            <button class="btn-l" id="btn-CL" onclick="toggle('CL')">◀</button>
            <button class="btn-s" onclick="send('S')">STOP</button>
            <button class="btn-r" id="btn-CR" onclick="toggle('CR')">▶</button>
            <button class="btn-b" id="btn-CB" onclick="toggle('CB')">▼</button>
        </div>
        
        <div id="status"><span class="indicator"></span>SYSTEM READY</div>
    </div>

    <script>
        function updateStatus(msg) {
            document.getElementById('status').innerHTML = '<span class="indicator"></span>' + msg.toUpperCase();
        }

        function send(cmd) {
            if (cmd === 'S' || !cmd.startsWith('C')) {
                stopAllContinuous();
            }
            
            fetch('/' + cmd)
                .then(r => {
                    if(r.ok) updateStatus('CMD: ' + cmd);
                    else updateStatus('SERVER ERROR');
                })
                .catch(e => updateStatus('NETWORK ERROR'));
        }

        function toggle(cmd) {
            const btn = document.getElementById('btn-' + cmd);
            const isActive = btn.classList.contains('active');
            
            stopAllContinuous();

            if (!isActive) {
                btn.classList.add('active');
                send(cmd);
            } else {
                send('S');
            }
        }

        function stopAllContinuous() {
            document.querySelectorAll('.mode-cont button').forEach(b => b.classList.remove('active'));
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

    elif cmd == 'CF':
        robot.forward(speed=SPEED)

    elif cmd == 'B':
        robot.backward(speed=SPEED)
        time.sleep(STEP_TIME)
        robot.stop()

    elif cmd == 'CB':
        robot.backward(speed=SPEED)

    elif cmd == 'L':
        robot.left(speed=SPEED)
        time.sleep(0.05)
        robot.stop()

    elif cmd == 'CL':
        robot.left(speed=SPEED)

    elif cmd == 'R':
        robot.right(speed=SPEED)
        time.sleep(0.05)
        robot.stop()

    elif cmd == 'CR':
        robot.right(speed=SPEED)

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
