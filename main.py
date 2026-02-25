# =====================================================
# 📦 IMPORTAÇÕES
# =====================================================

import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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
# 📁 Caminhos absolutos
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# =====================================================
# 🚀 Inicialização do App
# =====================================================

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

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
    """
    Gera o token de embed do Power BI SEM RLS.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/reports/{REPORT_ID}/GenerateToken"
    body = {"accessLevel": "view"}

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        print(f"ERRO POWER BI ({response.status_code}): {response.text}")
        raise HTTPException(status_code=500, detail="Erro ao gerar embed token")

    return response.json()

# =====================================================
# 👤 USUÁRIOS DEFINIDOS
# =====================================================

fake_users = {
    "rafael.rosa": {"password": "123", "role": "admin"},
    "bianca.coelho": {"password": "123", "role": "limitado"}
}
print("USUÁRIOS CARREGADOS:", fake_users)

# =====================================================
# 🔐 CONTROLE DE PERMISSÃO
# =====================================================

def check_permission(request: Request, pagina: str):
    role = request.cookies.get("role")
    
    if role == "admin":
        return True
    
    elif role == "limitado":
        paginas_permitidas = ["desempenho", "pdv", "clientes", "redes"]
        return pagina in paginas_permitidas
    
    return False

# =====================================================
# 🏠 LOGIN
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    username = username.strip().lower()
    password = password.strip()
    user = fake_users.get(username)
    if user and user["password"] == password:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="role", value=user["role"])
        response.set_cookie(key="username", value=username)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Usuário ou senha inválidos"})

# =====================================================
# 📊 DASHBOARD
# =====================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    role = request.cookies.get("role")
    if not role:
        return RedirectResponse(url="/")
    
    username = request.cookies.get("username")

    if role == "admin":
        allowed_pages = [
            {"name": "DESEMPENHO GERAL", "url": "/pagina/desempenho", "description": "Sell Out em tabelas e filtros.", "class": "pos-desempenho left", "icon": "desempenho.png"},
            {"name": "PDV ANÁLISE", "url": "/pagina/pdv", "description": "Visão de positivação detalhada.", "class": "pos-pdv left", "icon": "pdv.png"},
            {"name": "PERFIL CLIENTES", "url": "/pagina/clientes", "description": "O famoso P9. Frequência e compra.", "class": "pos-clientes left", "icon": "clientes.png"},
            {"name": "MATRIZ O.R.G", "url": "/pagina/matriz", "description": "Maturidade baseada em BCG.", "class": "pos-matriz left", "icon": "matriz.png"},
            {"name": "PROPAGANDISTAS", "url": "/pagina/propagandistas", "description": "Acompanhamento do time Out do Out.", "class": "pos-propaganda left", "icon": "propagandistas.png"},
            {"name": "MAPA ESTRATÉGICO", "url": "/pagina/mapa", "description": "Performance regional e cidades.", "class": "pos-mapa right", "icon": "mapa.png"},
            {"name": "REDES", "url": "/pagina/redes", "description": "Análise de grandes contas PET.", "class": "pos-redes right", "icon": "redes.png"},
            {"name": "RFV", "url": "/pagina/rfv", "description": "Recência, Frequência e Valor.", "class": "pos-rfv right", "icon": "rfv.png"},
            {"name": "CLIENTES FIDELIDADE", "url": "/pagina/fidelidade", "description": "Clientes estratégicos e engajados.", "class": "pos-fidelidade right", "icon": "fidelidade.png"},
            {"name": "BI TV", "url": "/pagina/bitv", "description": "Painéis de visualização em TV.", "class": "pos-bitv right", "icon": "bitv.png"},
        ]
    else:
        allowed_pages = [
            {"name": "DESEMPENHO GERAL", "url": "/pagina/desempenho", "description": "Sell Out em tabelas e filtros.", "class": "pos-desempenho left", "icon": "desempenho.png"},
            {"name": "PDV ANÁLISE", "url": "/pagina/pdv", "description": "Visão de positivação detalhada.", "class": "pos-pdv left", "icon": "pdv.png"},
            {"name": "REDES", "url": "/pagina/redes", "description": "Análise de grandes contas PET.", "class": "pos-redes right", "icon": "redes.png"},
        ]

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "role": role, "username": username, "allowed_pages": allowed_pages}
    )

# =====================================================
# 🔥 ENDPOINT EMBED POWER BI
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
# 📄 PÁGINAS DO PORTAL
# =====================================================

@app.get("/pagina/{pagina}", response_class=HTMLResponse)
async def pagina(request: Request, pagina: str):
    if not check_permission(request, pagina):
        return RedirectResponse(url="/dashboard")
    template_name = f"{pagina}.html"
    return templates.TemplateResponse(template_name, {"request": request})

# =====================================================
# 🚪 LOGOUT
# =====================================================

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("role")
    response.delete_cookie("username")
    return response