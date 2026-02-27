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
# 🔐 CONFIGURAÇÕES E VARIÁVEIS DE AMBIENTE
# =====================================================
load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GROUP_ID = os.getenv("GROUP_ID")
REPORT_ID = os.getenv("REPORT_ID")
DATASET_ID = os.getenv("DATASET_ID")

AUTHORITY_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE = "https://analysis.windows.net/powerbi/api/.default"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# =====================================================
# 🔑 FUNÇÕES POWER BI
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

def get_last_refresh_date():
    try:
        access_token = get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{GROUP_ID}/datasets/{DATASET_ID}/refreshes?$top=1"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            refreshes = response.json().get("value", [])
            if refreshes and refreshes[0].get("status") == "Completed":
                return refreshes[0].get("endTime")
        return None
    except Exception as e:
        print(f"ERRO AO BUSCAR REFRESH: {e}")
        return None

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
# 👤 USUÁRIOS E PERMISSÕES
# =====================================================

fake_users = {
    "rafael.rosa": {
        "password": "123",
        "role": "admin",
        "email": "rafael.rosa@organnact.com"
    },
    "conrado.b": {
        "password": "123",
        "role": "limitado",
        "email": "CONRADO B COMERCIAL" # Valor exato para o filtro no Power BI
    }
}

def check_permission(request: Request, pagina: str):
    role = request.cookies.get("role")
    if role == "admin": 
        return True
    if role == "limitado":
        # Conrado só pode acessar a página de desempenho
        return pagina in ["desempenho"]
    return False

# =====================================================
# 🏠 ROTAS DE NAVEGAÇÃO
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    username = username.strip().lower()
    user = fake_users.get(username)
    if user and user["password"] == password:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="role", value=user["role"])
        response.set_cookie(key="username", value=username)
        response.set_cookie(key="email", value=user["email"])
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Usuário ou senha inválidos"})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    role = request.cookies.get("role")
    if not role: 
        return RedirectResponse(url="/")
    
    last_refresh = get_last_refresh_date()
    username = request.cookies.get("username")

    # Mapeamento dinâmico dos botões do Dashboard
    if role == "admin":
        allowed_pages = [
            {"name": "DESEMPENHO GERAL", "url": "/pagina/desempenho"},
            {"name": "PDV ANÁLISE", "url": "/pagina/pdv"},
            {"name": "PERFIL CLIENTES", "url": "/pagina/clientes"},
            {"name": "REDES", "url": "/pagina/redes"},
            {"name": "MATRIZ O.R.G", "url": "/pagina/matriz"},
            {"name": "MAPA ESTRATÉGICO", "url": "/pagina/mapa"}
        ]
    elif role == "limitado":
        # REGRAS PARA O CONRADO: Vê apenas Desempenho
        allowed_pages = [
            {"name": "DESEMPENHO GERAL", "url": "/pagina/desempenho"}
        ]
    else:
        allowed_pages = []
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "role": role, 
        "username": username,
        "last_refresh": last_refresh,
        "allowed_pages": allowed_pages
    })

# =====================================================
# 🔥 ENDPOINT CONFIGURAÇÃO EMBED (USADO PELO JS)
# =====================================================

@app.get("/get_embed_config/{pagina}")
def get_embed_config(pagina: str, request: Request):
    embed_data = get_embed_token()
    
    PAGE_MAP = {
        "desempenho": "1e49e497e0d983a56770",
        "pdv": "feae6ae85cf7b9b152a5",
        "clientes": "58d19e2dc805cac78275",
        "redes": "6f83fd3fc7da0346493e",
        "perfil": "af13722cc2b603b41004",
        "matriz": "a697ebff1f1010caa86e",
        "mapa": "ReportSectionf954b14703686e041069"
    }

    page_name = PAGE_MAP.get(pagina)
    if not page_name:
        return {"error": "Página não mapeada"}

    return {
        "embedToken": embed_data.get("token"),
        "embedUrl": f"https://app.powerbi.com/reportEmbed?reportId={REPORT_ID}&groupId={GROUP_ID}",
        "reportId": REPORT_ID,
        "pageName": page_name,
        "role": request.cookies.get("role"),
        "email": request.cookies.get("email"), # Retorna "CONRADO B COMERCIAL"
        "username": request.cookies.get("username")
    }

@app.get("/pagina/{pagina}", response_class=HTMLResponse)
async def pagina(request: Request, pagina: str):
    if not check_permission(request, pagina):
        # Se tentar acessar o que não deve, volta pro Dashboard
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse(f"{pagina}.html", {"request": request})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("role")
    response.delete_cookie("username")
    response.delete_cookie("email")
    return response