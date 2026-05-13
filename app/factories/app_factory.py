from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# Inicializar extensiones
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_name='default'):
    """
    Fábrica de aplicaciones Flask
    
    Args:
        config_name (str): Nombre de la configuración ('development', 'testing', 'production')
    
    Returns:
        Flask: Aplicación Flask configurada
    """
    import os
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'), static_folder=os.path.join(basedir, 'static'))
    
    # Cargar configuración
    from app.config.config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Inicializar extensiones
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Configurar Login Manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    # Crear carpetas de uploads si no existen
    import os
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Registrar manejadores de errores
    register_error_handlers(app)
    
    # Registrar filtros de plantilla
    register_template_filters(app)
    
    # Cargar usuario para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.usuario import Usuario
        return Usuario.query.get(int(user_id))
    
    # ── SEGURIDAD: Headers en cada respuesta ──
    @app.after_request
    def add_security_headers(response):
        # Protección contra XSS, Clickjacking y Sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        # HSTS para forzar HTTPS (previene ataques MITM)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # CSP Básico para mitigar inyecciones XSS
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https:;"
        
        # Evitar que se cachee info sensible (Ataques de navegación hacia atrás)
        path_str = str(request.path)
        if any(ruta in path_str for ruta in ['/auth/', '/cliente/', '/admin/', '/artista/']):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # ── SEGURIDAD: Protección Integral (Brute Force y DoS) ──
    request_history = {}
    
    @app.before_request
    def check_rate_limit():
        from flask import request as req, abort
        import time
        
        # Ignorar recursos estáticos para no agotar el rate limit
        if req.path.startswith('/static/'):
            return
            
        # Extraer IP real si está detrás de un proxy
        ip = req.headers.get('X-Forwarded-For', req.remote_addr).split(',')[0].strip()
        now = time.time()
        
        # Limpieza de historial (mantener últimos 15 min)
        request_history[ip] = [t for t in request_history.get(ip, []) if now - t < 900]
        historial_ip = request_history[ip]
        
        # 1. Protección de Autenticación (Anti Brute-Force y Credential Stuffing)
        rutas_criticas = ['/auth/login', '/auth/register', '/auth/cambiar-password', '/cliente/seguridad']
        if req.method == 'POST' and any(req.path.endswith(r) for r in rutas_criticas):
            intentos_auth = len([t for t in historial_ip if now - t < 300]) # Intentos en 5 mins
            if intentos_auth >= 10:
                abort(429, description="Múltiples intentos fallidos. Bloqueo temporal por seguridad.")
                
        # 2. Protección general Anti-Scraping / DoS (Máx 500 reqs / 15 min por IP)
        if len(historial_ip) >= 500:
            abort(429, description="Tráfico inusual detectado. Has sido limitado.")
            
        # Registrar petición actual
        request_history.setdefault(ip, []).append(now)
        
        # 3. Protección contra Payloads masivos
        if req.content_length and req.content_length > 16 * 1024 * 1024:
            abort(413, description="El tamaño de la solicitud excede el límite permitido.")
    
    return app

def register_blueprints(app):
    """Registrar todos los blueprints de la aplicación"""
    
    # Blueprint de autenticación
    from app.controllers.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Blueprint de artistas
    from app.controllers.artista import artista_bp
    app.register_blueprint(artista_bp, url_prefix='/artista')
    
    # Blueprint de clientes
    from app.controllers.cliente import cliente_bp
    app.register_blueprint(cliente_bp, url_prefix='/cliente')
    
    # Blueprint de administración
    from app.controllers.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Blueprint público (home, explorar, etc.)
    from app.controllers.public import public_bp
    app.register_blueprint(public_bp)
    
    # Blueprint de API (para AJAX y futuras integraciones)
    from app.controllers.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

def register_error_handlers(app):
    """Registrar manejadores de errores personalizados"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def too_many_requests(error):
        from flask import render_template, request as req
        # Si es una petición API, devolver JSON
        if req.path.startswith('/api/') or req.content_type == 'application/json':
            return jsonify({'error': 'Demasiadas solicitudes. Intenta de nuevo más tarde.'}), 429
        try:
            return render_template('errors/429.html'), 429
        except Exception:
            return '<h1>429 - Demasiadas solicitudes</h1><p>Has realizado demasiadas solicitudes. Espera unos minutos.</p>', 429
    
    @app.errorhandler(413)
    def payload_too_large(error):
        from flask import request as req
        if req.path.startswith('/api/') or req.content_type == 'application/json':
            return jsonify({'error': 'El archivo es demasiado grande.'}), 413
        try:
            return render_template('errors/413.html'), 413
        except Exception:
            return '<h1>413 - Archivo demasiado grande</h1><p>El archivo supera el límite permitido de 16MB.</p>', 413

def register_template_filters(app):
    """Registrar filtros personalizados para plantillas"""
    
    @app.template_filter('currency')
    def currency_filter(value):
        """Formatear número como moneda"""
        try:
            return f"${value:,.2f}"
        except (ValueError, TypeError):
            return "$0.00"
    
    @app.template_filter('date')
    def date_filter(value, format='%d/%m/%Y'):
        """Formatear fecha"""
        if value is None:
            return ""
        try:
            return value.strftime(format)
        except (ValueError, TypeError, AttributeError):
            return str(value)
    
    @app.template_filter('truncate_words')
    def truncate_words_filter(s, num_words=20, suffix='...'):
        """Truncar texto por palabras"""
        try:
            words = s.split()
            if len(words) <= num_words:
                return s
            return ' '.join(words[:num_words]) + suffix
        except (ValueError, TypeError):
            return s
