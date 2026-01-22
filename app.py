from flask import Flask, request, Response, redirect, stream_with_context, jsonify
import os, requests, logging
from requests.exceptions import RequestException

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

INDEX_PAGE = '''
<!DOCTYPE html>
<html lang="pt-BR" id="html" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GLADIADOR – Downloader</title>
    <style>
        :root {
            --bg: #0a0a0a;
            --card-bg: #111111;
            --text: #e0e0e0;
            --accent: #ff0044;
            --accent-hover: #e6003d;
            --border: #222222;
            --input-bg: #1a1a1a;
            --sub: #888888;
        }
        [data-theme="light"] {
            --bg: #f8f8f8;
            --card-bg: #ffffff;
            --text: #222222;
            --accent: #ff0044;
            --accent-hover: #cc0037;
            --border: #dddddd;
            --input-bg: #f0f0f0;
            --sub: #666666;
        }
        * { margin:0; padding:0; box-sizing:border-box; font-family:Segoe UI,Roboto,Arial,sans-serif; }
        body { background:var(--bg); color:var(--text); min-height:100vh; padding:20px; display:flex; flex-direction:column; align-items:center; }
        .menu-icon { position:fixed; top:20px; left:20px; z-index:1001; cursor:pointer; }
        .menu-icon span { display:block; width:30px; height:4px; background:var(--accent); margin:6px 0; transition:0.3s; border-radius:2px; }
        .side-panel { position:fixed; top:0; left:-50%; width:50%; height:100%; background:var(--card-bg); border-right:1px solid var(--border); padding:80px 20px 20px; transition:left 0.4s ease; z-index:1000; color:var(--text); overflow-y:auto; }
        .side-panel.show { left:0; }
        .close-btn { position:absolute; top:20px; right:20px; font-size:2.5rem; cursor:pointer; color:var(--accent); }
        .menu-item { margin:20px 0; font-size:1.2rem; cursor:pointer; padding:15px; border-radius:8px; transition:0.3s; background:rgba(255,0,68,0.1); }
        .menu-item:hover { background:rgba(255,0,68,0.3); }
        .container { max-width:480px; width:100%; text-align:center; margin-top:80px; }
        h1 { color:var(--accent); font-size:3rem; margin-bottom:20px; text-shadow:0 0 15px rgba(255,0,68,0.6); }
        .input-group { background:var(--input-bg); border:2px solid var(--border); border-radius:16px; padding:8px; margin-bottom:20px; box-shadow:0 5px 20px rgba(0,0,0,0.5); }
        input[type=url] { background:transparent; border:none; color:var(--text); font-size:1.1rem; width:100%; padding:15px; outline:none; }
        input[type=url]::placeholder { color:var(--sub); }
        .btn { background:var(--accent); color:white; border:none; border-radius:12px; padding:18px; font-size:1.4rem; font-weight:bold; cursor:pointer; transition:all 0.3s; width:100%; box-shadow:0 8px 20px rgba(255,0,68,0.5); }
        .btn:hover { background:var(--accent-hover); transform:translateY(-3px); box-shadow:0 12px 30px rgba(255,0,68,0.7); }
        #loader { display:none; margin:40px auto; border:8px solid #333; border-top:8px solid var(--accent); border-radius:50%; width:70px; height:70px; animation:spin 1s linear infinite; }
        @keyframes spin { 0% { transform:rotate(0deg); } 100% { transform:rotate(360deg); } }
        #previewContainer { margin-top:30px; width:100%; border-radius:16px; overflow:hidden; box-shadow:0 10px 40px rgba(0,0,0,0.7); display:none; background:#000; }
        video { width:100%; height:auto; display:block; }
        .download-btn { margin-top:20px; background:#00cc00; color:white; border:none; border-radius:12px; padding:20px; font-size:1.5rem; font-weight:bold; cursor:pointer; width:100%; transition:all 0.3s; box-shadow:0 8px 20px rgba(0,204,0,0.5); }
        .download-btn:hover { background:#00b300; transform:translateY(-3px); }
        .foot { margin-top:50px; font-size:0.9rem; color:var(--sub); text-align:center; }
    </style>
</head>
<body>

    <div class="menu-icon" onclick="toggleMenu()">
        <span></span><span></span><span></span>
    </div>

    <div id="sidePanel" class="side-panel">
        <div class="close-btn" onclick="toggleMenu()">×</div>
        <div class="menu-item" onclick="toggleTheme()">Mudar Tema (Escuro / Claro)</div>
        <div class="menu-item" onclick="alert('Em breve: app para Android/iOS! Por enquanto use o site no navegador.');">Baixar o App</div>
    </div>

    <div class="container">
        <h1>GLADIADOR</h1>
        <div class="input-group">
            <input id="reelUrl" type="url" placeholder="Cole o link do Reel aqui..." autocomplete="off">
        </div>
        <button class="btn" onclick="baixarReel()">BAIXAR</button>

        <div id="loader"></div>

        <div id="previewContainer">
            <video id="previewVideo" controls autoplay muted></video>
            <button class="download-btn" id="downloadBtn" onclick="downloadVideo()">Baixar Vídeo</button>
        </div>

        <div class="foot">Feito por <strong>GLADIADOR</strong> – 2026</div>
    </div>

    <script>
        const html = document.getElementById('html');
        const savedTheme = localStorage.getItem('theme') || 'dark';
        html.setAttribute('data-theme', savedTheme);

        function toggleTheme() {
            const current = html.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }

        function toggleMenu() {
            document.getElementById('sidePanel').classList.toggle('show');
        }

        let currentVideoUrl = '';

        async function baixarReel() {
            const url = document.getElementById('reelUrl').value.trim();
            if (!url) return alert('Cole um link válido do Instagram Reel!');

            document.getElementById('loader').style.display = 'block';
            document.getElementById('previewContainer').style.display = 'none';

            try {
                const res = await fetch(`/dl?url=${encodeURIComponent(url)}`);
                const data = await res.json();

                if (!data.success) throw new Error(data.error || 'Erro desconhecido');

                currentVideoUrl = data.video_url;

                const video = document.getElementById('previewVideo');
                video.src = currentVideoUrl;
                document.getElementById('previewContainer').style.display = 'block';
                document.getElementById('downloadBtn').style.display = 'block';

            } catch (err) {
                alert('Erro: ' + err.message + '\\n\\nTente outro Reel ou verifique login/credenciais.');
            } finally {
                document.getElementById('loader').style.display = 'none';
            }
        }

        function downloadVideo() {
            if (!currentVideoUrl) return;
            const a = document.createElement('a');
            a.href = currentVideoUrl;
            a.download = 'reel_gladiador.mp4';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    </script>
</body>
</html>
'''

@app.route("/")
def home():
    return INDEX_PAGE

@app.route("/dl")
def download():
    url = request.args.get("url")
    if not url:
        return jsonify({"success": False, "error": "URL vazia"}), 400

    username = os.getenv("IG_USER")
    password = os.getenv("IG_PASS")
    if not username or not password:
        return jsonify({"success": False, "error": "Credenciais não configuradas"}), 500

    try:
        import yt_dlp
        ydl_opts = {
            "username": username,
            "password": password,
            "format": "best[ext=mp4]",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info["url"]

        return jsonify({"success": True, "video_url": video_url})

    except Exception as e:
        logging.exception("Erro Reel")
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
