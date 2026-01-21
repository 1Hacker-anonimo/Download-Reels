
import os, re, json, requests, tempfile, mimetypes
from flask import Flask, request, Response, render_template_string, redirect, abort
import yt_dlp

app = Flask(__name__)
sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Accept-Language": "pt-BR,pt=0.9",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
})

# ---------- FUNÇÕES AUXILIARES ----------
def username_from_url(url: str) -> str:
    m = re.search(r"instagram\.com/([^/?]+)", url)
    return m.group(1) if m else url.strip("/@ ")

# ---------- DOWNLOAD REELS ----------
def ig_reels_data(url):
    """Devolve dict com url, thumbnail, title ou None se falhar."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "best[height<=720]",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "url":      info["url"],
                "thumb":    info["thumbnail"],
                "title":    info.get("title", "Reels"),
                "duration": info.get("duration_string", ""),
            }
    except Exception:
        return None

# ---------- DOWNLOAD YOUTUBE ----------
def youtube_data(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "best[ext=mp4][height<=720]/best[height<=720]",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "url":      info["url"],
                "thumb":    info["thumbnail"],
                "title":    info.get("title", "Vídeo"),
                "duration": info.get("duration_string", ""),
}
    except Exception:
        return None

# ---------- DOWNLOAD STORIES ----------
def ig_public_stories(username: str):
    try:
        r = sess.get(f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}")
        if r.status_code == 404: return {"error": "Perfil não existe"}
        if r.status_code == 401: return {"error": "login_required – troque de IP ou cookie"}
        data = r.json()
        user = data["data"]["user"]
        if user["is_private"]: return {"error": "Perfil privado – impossível baixar stories"}
        user_id = user["id"]
        r = sess.get(
            f"https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}",
            headers={"X-IG-App-ID": "936619743392459"}
        )
        if r.status_code != 200 or not r.json().get("reels"): return []
        reel = r.json()["reels"][user_id]
        items = []
        for m in reel.get("items", []):
            media_id = m["id"]
            is_video = m["media_type"] == 2
            if is_video:
                url = m["video_versions"][0]["url"]
                thumb = m.get("image_versions2",  {}).get("candidates", [{}])[0].get("url", "")
            else:
                url = m["image_versions2"]["candidates"][0]["url"]
                thumb = url
            items.append({"id": media_id, "url": url, "is_video": is_video, "thumbnail": thumb})
        return items
    except Exception as e:
        return {"error": str(e)}

# ---------- ROTAS ----------
@app.route("/")
def index():
    return render_template_string(HTML_BASE, stories=None, reels=None, youtube=None)

@app.route("/reels")
def reels_dl():
    url = request.args.get("url")
    if not url: return redirect("/")
    data = ig_reels_data(url)
    if not data: return "URL inválida ou privada", 400
    return render_template_string(HTML_BASE, reels=data)

@app.route("/youtube")
def youtube_dl():
    url = request.args.get("url")
    if not url: return redirect("/")
    data = youtube_data(url)
    if not data: return "URL inválida ou indisponível", 400
    return render_template_string(HTML_BASE, youtube=data)

@app.route("/story")
def story_list():
    url_or_user = request.args.get("url") or ""
    if not url_or_user: return redirect("/")
    username = username_from_url(url_or_user)
    stories = ig_public_stories(username)
    if isinstance(stories, dict) and stories.get("error"):
        return stories["error"], 400
    return render_template_string(HTML_BASE, stories=stories, username=username)

# ---------- HTML ÚNICO ----------
HTML_BASE = """<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <title>Universal Downloader – Reels / YouTube / Stories</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body{background:#111;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
    .logo{font-size:1.8rem;font-weight:700;background:linear-gradient(45deg,#833ab4,#fd1d1d,#fcb045);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
    .card-img-top{height:220px;object-fit:cover;}
    .btn-download{background:#fd1d1d;border:none;color:#fff}
    .btn-download:hover{background:#e14a4a}
  </style>
</head>
<body>
<nav class="navbar navbar-dark bg-dark border-bottom">
  <div class="container">
    <span class="logo">Universal Downloader</span>
  </div>
</nav>
<div class="container py-4">
  <div class="text-center mb-5">
    <h1 class="fw-bold">Reels, YouTube ou Stories</h1>
    <p class="lead">Cole o link abaixo e escolha o tipo de download.</p>
  </div>

  <!-- FORMULÁRIO GENÉRICO -->
  <form class="row g-2 justify-content-center" id="frm" onsubmit="return false;">
    <div class="col-12 col-md-6">
      <input type="text" class="form-control form-control-lg" id="url" name="url"
             placeholder="https://www.instagram.com/reel/... ou https://youtu.be/..." required>
    </div>
    <div class="col-auto">
      <button class="btn btn-download btn-lg px-4" onclick="go()">Download</button>
    </div>
  </form>

  <!-- RESULTADOS -->
  {% if reels %}
  <hr>
  <h4>Instagram Reel</h4>
  <div class="card mb-4" style="max-width:540px;margin:auto">
    <img src="{{ reels.thumb }}" class="card-img-top">
    <div class="card-body text-center">
      <h5 class="card-title">{{ reels.title }}</h5>
      <p class="text-muted">{{ reels.duration }}</p>
      <a href="{{ reels.url }}" class="btn btn-download" download>Baixar Reel</a>
    </div>
  </div>
  {% endif %}

  {% if youtube %}
  <hr>
  <h4>YouTube</h4>
  <div class="card mb-4" style="max-width:540px;margin:auto">
    <img src="{{ youtube.thumb }}" class="card-img-top">
    <div class="card-body text-center">
      <h5 class="card-title">{{ youtube.title }}</h5>
      <p class="text-muted">{{ youtube.duration }}</p>
      <a href="{{ youtube.url }}" class="btn btn-download" download>Baixar Vídeo</a>
    </div>
  </div>
  {% endif %}

  {% if stories %}
  <hr>
  <h4>Stories de <span class="text-primary">@{{ username }}</span></h4>
  <div class="row g-3">
  {% for s in stories %}
    <div class="col-6 col-md-4 col-lg-3">
      <div class="card h-100">
        <img src="{{ s.thumbnail }}" class="card-img-top">
        <div class="card-body d-flex flex-column">
          <span class="badge bg-secondary mb-2">{{ "Vídeo" if s.is_video else "Foto" }}</span>
          <a href="{{ s.url }}" class="btn btn-download mt-auto" download>Baixar</a>
        </div>
      </div>
    </div>
  {% endfor %}
  </div>
  {% endif %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
  function go(){
    const u = document.getElementById("url").value.trim();
    if(!u)return;
    if(/instagram\.com\/reel\//.test(u)) location.href="/reels?url="+encodeURIComponent(u);
    else if(/instagram\.com\/stories\//|@/.test(u)) location.href="/story?url="+encodeURIComponent(u);
    else if(/youtube\.com|youtu\.be/.test(u)) location.href="/youtube?url="+encodeURIComponent(u);
    else alert("Link não reconhecido.");
  }
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

