from flask import Flask, request, redirect
import os
import yt_dlp

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def download():
    # pega o URL do formulário ou da query-string
    url = request.form.get("url") or request.args.get("url")
    if not url:
        return "Falta o parâmetro url", 400

    # lê login/senha das variáveis de ambiente que você vai criar no Render
    username = os.getenv("IG_USER")
    password = os.getenv("IG_PASS")
    if not username or not password:
        return "Configure as variáveis IG_USER e IG_PASS no painel do Render", 500

    opts = {
        "username": username,
        "password": password,
        "format":   "best[ext=mp4]",
        "quiet":    True,
        "no_warnings": True
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)   # só pega o link direto
            video_url = info["url"]                        # URL do MP4
            return redirect(video_url)                     # baixo direto no navegador
    except Exception as e:
        return str(e), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
