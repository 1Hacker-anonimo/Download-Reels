from flask import Flask, request, Response, redirect, stream_with_context
import os, requests, logging
from requests.exceptions import RequestException

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

INDEX_PAGE = '''
<!DOCTYPE html>
<html lang="pt-BR" id="html">
<head>
    <meta charset="UTF-8">
    <title>GLADIADOR – Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --bg: #0a0a0a;
            --card-bg: #111;
            --text: #e0e0e0;
            --accent: #ff0044;
            --accent-hover: #e6003d;
            --border: #222;
            --sub: #aaa;
        }
        [data-theme="light"] {
            --bg: #f5f5f5;
            --card-bg: #ffffff;
            --text: #222222;
            --accent: #ff0044;
            --accent-hover: #cc0037;
            --border: #dddddd;
            --sub: #666666;
        }
        *{margin:0;padding:0;box-sizing:border-box;font-family:Segoe UI,Roboto,Arial,sans-serif}
        body{background:var(--bg);color:var(--text);min-height:100vh;padding:20px;display:flex;align-items:center;justify-content:center}
        .card{background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:40px 30px;max-width:420px;width:100%;text-align:center;box-shadow:0 0 25px rgba(255,0,68,0.2)}
        h1{color:var(--accent);font-size:2.4rem;margin-bottom:12px;letter-spacing:1px;text-transform:uppercase}
        .sub{color:var(--sub);font-size:1rem;margin-bottom:25px}
        form{display:flex;flex-direction:column;gap:15px}
        input[type=url]{background:#1a1a1a;border:1px solid #333;border-radius:6px;color:#fff;padding:14px 16px;font-size:1rem;transition:border .2s}
        input[type=url]:focus{border-color:var(--accent);outline:none}
        .btn{background:var(--accent);color:#fff;border:none;border-radius:6px;padding:14px;font-size:1.05rem;font-weight:bold;cursor:pointer;transition:background .2s;margin-top:10px}
        .btn:hover{background:var(--accent-hover)}
        .foot{margin-top:30px;font-size:.75rem;color:var(--sub)}
        .overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);display:none;flex-direction:column;align-items:center;justify-content:center;z-index:999}
        .overlay.show{display:flex}
        .spinner{width:50px;height:50px;border:5px solid #222;border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}
        .overlay p{margin-top:15px;color:var(--accent);font-weight:bold}
        .options{margin-top:30px;display:flex;flex-direction:column;gap:10px}
        .theme-btn, .app-btn{background:#333;color:#fff;border:none;border-radius:6px;padding:12px;cursor:pointer;font-size:1rem}
        .theme-btn:hover, .app-btn:hover{background:#444}
        [data-theme="light"] .theme-btn, [data-theme="light"] .app-btn{background:#ddd;color:#222}
        [data-theme="light"] .theme-btn:hover, [data-theme="light"] .app-btn:hover{background:#ccc}
    </style>
</head>
<body>

    <div class="card">
        <h1>GLADIADOR</h1>
        <p class="sub">Cole o link do Reel e baixa automaticamente em HD</p>

        <form id="form" action="/dl" method="get">
            <input name="url" type="url" placeholder="https://www.instagram.com/reel/..." required>
            <button class="btn" type="submit">Baixar Reel</button>
        </form>

        <div class="options">
            <button class="theme-btn" onclick="toggleTheme()">Mudar Tema (Escuro/Claro)</button>
            <a href="#" class="app-btn" onclick="alert('Em breve: app para Android! Por enquanto use o site no navegador.'); return false;">Baixar o App</a>
        </div>

        <div class="foot">Feito por <strong>GLADIADOR</strong> – 2026</div>
    </div>

    <div id="loader" class="overlay">
        <div class="spinner"></div>
        <p>baixando...</p>
    </div>

    <script>
        function showLoader(){
            const l = document.getElementById('loader');
            l.classList.add('show');
            setTimeout(() => l.classList.remove('show'), 1000);
        }

        document.getElementById('form').addEventListener('submit', showLoader);

        // Tema escuro/claro
        function toggleTheme() {
            const html = document.getElementById('html');
            const current = html.getAttribute('data-theme') || 'dark';
            const newTheme = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }

        // Carregar tema salvo
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.getElementById('html').setAttribute('data-theme', savedTheme);
    </script>
</body>
</html>
'''

@app.route("/")
def home():
    return INDEX_PAGE

@app.route("/dl")  # Instagram Reels
def download():
    url = request.args.get("url")
    if not url:
        return redirect("/")

    username = os.getenv("IG_USER")
    password = os.getenv("IG_PASS")
    if not username or not password:
        return "Configure IG_USER e IG_PASS nas variáveis de ambiente do Render", 500

    import yt_dlp
    ydl_opts = {
        "username": username,
        "password": password,
        "format": "best[ext=mp4]",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info["url"]
            filename = f"{info['id']}.mp4"
    except Exception as e:
        logging.exception("Erro Instagram")
        return f"Erro ao obter vídeo do Instagram: {str(e)}<br><br>Verifique se o link é válido, público e se as credenciais estão corretas.", 400

    def generate():
        try:
            with requests.get(video_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=16*1024):
                    if chunk:
                        yield chunk
        except RequestException:
            logging.exception("Stream Instagram")
            return

    return Response(
        stream_with_context(generate()),
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "video/mp4",
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
