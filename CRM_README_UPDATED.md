# CARPLUS AUTOSALE CRM
## Guía de Instalación para Hostinger

### Requisitos
- Python 3.9+
- Node.js 18+
- MongoDB 4.4+
- Servidor con soporte para Python (VPS o Cloud Hosting)

---

## ⚠️ IMPORTANTE: Configuración de URLs

### REACT_APP_BACKEND_URL
Esta es la variable MÁS IMPORTANTE. Debe apuntar a tu servidor backend en producción.

**En el archivo `frontend/.env` o al compilar:**
```
REACT_APP_BACKEND_URL=https://tu-dominio.com
```

Por ejemplo, si tu dominio es `carplus.hostinger.com`:
```
REACT_APP_BACKEND_URL=https://carplus.hostinger.com
```

Sin esta configuración correcta:
- ❌ El formulario de Pre-Qualify NO funcionará
- ❌ Los formularios públicos NO funcionarán
- ❌ El login NO funcionará

---

## Estructura del Proyecto

```
CRM/
├── backend/              # API FastAPI (Python)
│   ├── server.py         # Servidor principal
│   ├── requirements.txt  # Dependencias Python
│   ├── .env.example      # Variables de entorno (copiar a .env)
│   └── uploads/          # Carpeta para documentos subidos
├── frontend/             # Código fuente React
│   ├── src/
│   ├── public/
│   └── package.json
└── frontend_build/       # Build de producción (listo para servir)
    └── static/
```

---

## Instalación Paso a Paso

### Paso 1: MongoDB

**Opción A - MongoDB Atlas (Recomendado para Hostinger)**
1. Crear cuenta gratuita en https://www.mongodb.com/atlas
2. Crear un cluster gratuito (M0)
3. Crear un usuario de base de datos
4. Obtener la URL de conexión (se ve así):
   ```
   mongodb+srv://usuario:contraseña@cluster.xxxxx.mongodb.net/carplus_db
   ```
5. Agregar tu IP de Hostinger a la lista de IPs permitidas

**Opción B - MongoDB Local (Solo para VPS)**
```bash
# Ubuntu/Debian
sudo apt install mongodb
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

### Paso 2: Backend (API)

```bash
# Navegar a la carpeta del backend
cd CRM/backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
```

**Editar el archivo `.env` con tus credenciales:**
```bash
# MongoDB (usar tu URL de Atlas o localhost)
MONGO_URL="mongodb+srv://usuario:contraseña@cluster.xxxxx.mongodb.net"
DB_NAME="carplus_db"

# Permitir CORS desde tu dominio
CORS_ORIGINS="*"

# Twilio SMS (opcional - para enviar SMS)
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# SMTP Email (para notificaciones)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password
SMTP_FROM_NAME=CARPLUS CRM

# URL del Frontend (para enlaces en emails)
FRONTEND_URL=https://tu-dominio.com
```

**Iniciar el servidor:**
```bash
# Desarrollo
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Producción (con Gunicorn)
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
```

### Paso 3: Frontend

**Opción A - Usar Build Precompilado (Más Fácil)**

⚠️ **NOTA:** El build precompilado tiene la URL de desarrollo. DEBES recompilar.

**Opción B - Compilar (Recomendado)**

```bash
cd CRM/frontend

# Crear archivo .env
echo "REACT_APP_BACKEND_URL=https://tu-dominio.com" > .env

# Instalar dependencias
yarn install
# o: npm install

# Compilar
yarn build
# o: npm run build
```

La carpeta `build/` contendrá los archivos para subir a tu hosting.

---

## Configuración en Hostinger VPS

### 1. Instalar dependencias del sistema

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nodejs npm nginx
npm install -g yarn
```

### 2. Configurar Nginx

Crear archivo `/etc/nginx/sites-available/carplus`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    # Frontend (archivos estáticos)
    location / {
        root /var/www/carplus/frontend/build;
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Para subida de archivos grandes
        client_max_body_size 50M;
    }

    # Uploads (documentos)
    location /uploads {
        alias /var/www/carplus/backend/uploads;
    }
}
```

Activar el sitio:
```bash
sudo ln -s /etc/nginx/sites-available/carplus /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Mantener Backend Activo con Supervisor

Instalar supervisor:
```bash
sudo apt install supervisor
```

Crear archivo `/etc/supervisor/conf.d/carplus.conf`:
```ini
[program:carplus-api]
command=/var/www/carplus/backend/venv/bin/gunicorn server:app -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8001
directory=/var/www/carplus/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/carplus/error.log
stdout_logfile=/var/log/carplus/access.log
environment=PATH="/var/www/carplus/backend/venv/bin"
```

Crear carpeta de logs e iniciar:
```bash
sudo mkdir -p /var/log/carplus
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start carplus-api
```

### 4. SSL con Let's Encrypt (HTTPS)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

---

## Credenciales por Defecto

**Admin:**
- Usuario: `xadmin`
- Contraseña: `Cali2020`

**Vendedor de prueba:**
- Email: `vendedor1@test.com`
- Contraseña: `Test1234`

⚠️ **IMPORTANTE**: Cambia estas credenciales después de la instalación.

---

## Formulario de Pre-Qualify (Público)

Para integrar el formulario de pre-calificación en tu sitio web:

**URL del formulario:**
```
https://tu-dominio.com/public/prequalify
```

**Endpoint API (si usas tu propio formulario):**
```
POST https://tu-dominio.com/api/prequalify/submit
Content-Type: application/json

{
  "email": "cliente@email.com",
  "firstName": "Nombre",
  "lastName": "Apellido",
  "phone": "1234567890",
  ...
}
```

Cuando se recibe una solicitud, TODOS los administradores recibirán un email de notificación con los datos completos.

---

## Solución de Problemas

### El frontend no conecta con el backend
1. Verificar que `REACT_APP_BACKEND_URL` apunta a tu dominio
2. Verificar que Nginx está corriendo: `sudo systemctl status nginx`
3. Verificar que el backend está corriendo: `sudo supervisorctl status`

### Error de MongoDB
1. Verificar la URL de conexión en `.env`
2. Si usas Atlas, verificar que la IP de tu servidor está en la whitelist

### Los emails no se envían
1. Si usas Gmail, crear una "App Password" en: https://myaccount.google.com/apppasswords
2. Verificar las credenciales SMTP en `.env`

### Ver logs
```bash
# Backend
tail -f /var/log/carplus/error.log

# Nginx
tail -f /var/log/nginx/error.log
```

---

## Endpoints API Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/register` | Registro |
| GET | `/api/clients` | Lista de clientes |
| POST | `/api/clients` | Crear cliente |
| GET | `/api/user-records` | Records de clientes |
| POST | `/api/prequalify/submit` | Formulario pre-qualify (público) |
| GET | `/api/prequalify/submissions` | Lista pre-qualify (admin) |
| GET | `/api/appointments` | Lista de citas |
| POST | `/api/send-sms` | Enviar SMS |

---

## Resumen de Archivos a Modificar

1. **`backend/.env`** - Credenciales de MongoDB, SMTP, Twilio
2. **`frontend/.env`** - URL del backend (`REACT_APP_BACKEND_URL`)

---

Desarrollado para CARPLUS AUTOSALE - Friendly Brokerage
