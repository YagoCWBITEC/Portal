import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles  # <--- Importação garantida
from fastapi.templating import Jinja2Templates

# =====================================================
# 🔐 Carrega variáveis do .env
# =====================================================
load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GROUP_ID = os.getenv("GROUP_ID")
REPORT_ID = os.getenv("REPORT_ID")

AUTHORITY_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE = "https://analysis.windows.net/powerbi/api/.default"

# =====================================================
# 🚀 Inicialização do App
# =====================================================
app = FastAPI()

# 📁 Configuração de Arquivos Estáticos e Templates
# Isso garante que o FastAPI encontre o seu style.css dentro da pasta /static
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# =====================================================
# 🔑 Power BI - Token
# =====================================================

def get_access_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
    }
    response = requests.post(AUTHORITY_URL, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Erro ao gerar access token")
    return response.json().get("access_token")

def get_embed_token():
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/reports/{REPORT_ID}/GenerateToken"
    body = {"accessLevel": "view"}
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Erro ao gerar embed token")
    return response.json()

# =====================================================
# 👤 Usuários simulados
# =====================================================
fake_users = {
    "gerente": {"password": "123", "role": "gerente"},
    "analista": {"password": "123", "role": "analista"},
}

def check_permission(request: Request, allowed_roles: list):
    role = request.cookies.get("role")
    return role in allowed_roles

# =====================================================
# 🏠 Login
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    # Passamos o erro como None inicialmente
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = fake_users.get(username)

    if user and user["password"] == password:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="role", value=user["role"])
        return response

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Usuário ou senha inválidos"}
    )

# =====================================================
# 📊 Dashboard
# =====================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    role = request.cookies.get("role")
    if not role:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("dashboard.html", {"request": request, "role": role})

# =====================================================
# 🔥 Endpoint Embed Power BI
# =====================================================

@app.get("/get_embed_config/{pagina}")
def get_embed_config(pagina: str):
    embed_data = get_embed_token()
    PAGE_MAP = {
        "desempenho": "1e49e497e0d983a56770",
        "pdv": "feae6ae85cf7b9b152a5",
        "perfil": "af13722cc2b603b41004",
        "matriz": "a697ebff1f1010caa86e",
        "mapa": "ReportSectionf954b14703686e041069",
        "redes": "6f83fd3fc7da0346493e",
        "clientes": "58d19e2dc805cac78275",
        "bitv": "16d7a7e6f989c905e93e"
    }
    page_name = PAGE_MAP.get(pagina)
    if not page_name:
        return {"error": "Página não encontrada"}
    return {
        "embedToken": embed_data.get("token"),
        "embedUrl": f"https://app.powerbi.com/reportEmbed?reportId={REPORT_ID}&groupId={GROUP_ID}",
        "reportId": REPORT_ID,
        "pageName": page_name
    }

# =====================================================
# 📄 Páginas do Portal
# =====================================================

@app.get("/pagina/desempenho", response_class=HTMLResponse)
async def desempenho(request: Request):
    if not check_permission(request, ["gerente", "analista"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("desempenho.html", {"request": request})

@app.get("/pagina/pdv", response_class=HTMLResponse)
async def pdv(request: Request):
    if not check_permission(request, ["gerente", "analista"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("pdv.html", {"request": request})

@app.get("/pagina/perfil", response_class=HTMLResponse)
async def perfil(request: Request):
    if not check_permission(request, ["gerente"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("perfil.html", {"request": request})

@app.get("/pagina/matriz", response_class=HTMLResponse)
async def matriz(request: Request):
    if not check_permission(request, ["gerente"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("matriz.html", {"request": request})

@app.get("/pagina/mapa", response_class=HTMLResponse)
async def mapa(request: Request):
    if not check_permission(request, ["gerente", "analista"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("mapa.html", {"request": request})

@app.get("/pagina/redes", response_class=HTMLResponse)
async def redes(request: Request):
    if not check_permission(request, ["gerente"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("redes.html", {"request": request})

@app.get("/pagina/clientes", response_class=HTMLResponse)
async def clientes(request: Request):
    if not check_permission(request, ["gerente", "analista"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("clientes.html", {"request": request})

@app.get("/pagina/bitv", response_class=HTMLResponse)
async def bitv(request: Request):
    if not check_permission(request, ["gerente"]):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("bitv.html", {"request": request})

# =====================================================
# 🚪 Logout
# =====================================================

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("role")
    return response