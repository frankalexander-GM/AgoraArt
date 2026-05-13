from flask_bcrypt import Bcrypt
from flask_login import login_user, logout_user, login_required
from app.models.usuario import Usuario

bcrypt = Bcrypt()

class AuthService:
    """
    Servicio de autenticación y autorización
    Maneja login, registro, y gestión de sesiones
    """
    
    def __init__(self, usuario_repository):
        """
        Inicializar servicio de autenticación
        
        Args:
            usuario_repository: Repositorio de usuarios
        """
        self.usuario_repo = usuario_repository
    
    def encriptar_password(self, password):
        """
        Encriptar contraseña usando bcrypt
        
        Args:
            password (str): Contraseña a encriptar
            
        Returns:
            str: Contraseña encriptada
        """
        return bcrypt.generate_password_hash(password).decode('utf-8')
    
    def verificar_password(self, password, password_hash):
        """
        Verificar contraseña contra hash
        
        Args:
            password (str): Contraseña a verificar
            password_hash (str): Hash almacenado
            
        Returns:
            bool: True si la contraseña es correcta
        """
        return bcrypt.check_password_hash(password_hash, password)
    
    def validar_email_duplicado(self, email, exclude_id=None):
        """
        Verificar si email ya está registrado
        
        Args:
            email (str): Email a verificar
            exclude_id (int): ID a excluir de la verificación
            
        Returns:
            bool: True si el email ya existe
        """
        return self.usuario_repo.email_exists(email, exclude_id)
    
    def validar_username_duplicado(self, username, exclude_id=None):
        """
        Verificar si username ya está registrado
        
        Args:
            username (str): Username a verificar
            exclude_id (int): ID a excluir de la verificación
            
        Returns:
            bool: True si el username ya existe
        """
        return self.usuario_repo.username_exists(username, exclude_id)
    
    def validar_datos_registro(self, data):
        """
        Validar datos de registro
        
        Args:
            data (dict): Datos del formulario
            
        Returns:
            tuple: (bool, list) - (es_valido, lista_errores)
        """
        errores = []
        
        # Validaciones básicas
        if not data.get('nombre', '').strip():
            errores.append('El nombre es obligatorio')
        elif len(data.get('nombre', '').strip()) > 100:
            errores.append('El nombre no puede superar los 100 caracteres')
        
        if not data.get('username', '').strip():
            errores.append('El username es obligatorio')
        elif len(data['username']) < 3:
            errores.append('El username debe tener al menos 3 caracteres')
        elif len(data['username']) > 50:
            errores.append('El username no puede superar los 50 caracteres')
        elif not data['username'].replace('_', '').replace('-', '').isalnum():
            errores.append('El username solo puede contener letras, números, guiones y guiones bajos')
        
        if not data.get('email', '').strip():
            errores.append('El email es obligatorio')
        elif '@' not in data['email'] or '.' not in data['email']:
            errores.append('El email no es válido')
        elif len(data['email']) > 150:
            errores.append('El email no puede superar los 150 caracteres')
        
        if not data.get('password', '').strip():
            errores.append('La contraseña es obligatoria')
        elif len(data['password']) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres')
        elif not any(c.isupper() for c in data['password']):
            errores.append('La contraseña debe contener al menos una letra mayúscula')
        elif not any(c.isdigit() for c in data['password']):
            errores.append('La contraseña debe contener al menos un número')
        elif not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in data['password']):
            errores.append('La contraseña debe contener al menos un carácter especial (!@#$%&*...)')
        
        # ── SEGURIDAD: Bloquear auto-registro como admin ──
        if not data.get('rol'):
            errores.append('El rol es obligatorio')
        elif data['rol'] not in ['artista', 'cliente']:
            errores.append('Rol no válido')
        
        # Validar longitud de biografía
        if len(data.get('biografia', '')) > 500:
            errores.append('La biografía no puede superar los 500 caracteres')
        
        # Validaciones de unicidad
        if data.get('email') and self.validar_email_duplicado(data['email']):
            errores.append('El email ya está registrado')
        
        if data.get('username') and self.validar_username_duplicado(data['username']):
            errores.append('El username ya está registrado')
        
        return (len(errores) == 0, errores)
    
    def registrar_usuario(self, data):
        """
        Registrar nuevo usuario
        
        Args:
            data (dict): Datos del usuario
            
        Returns:
            tuple: (bool, Usuario/None, list) - (exitoso, usuario, errores)
        """
        # Validar datos
        es_valido, errores = self.validar_datos_registro(data)
        if not es_valido:
            return (False, None, errores)
        
        try:
            # Encriptar contraseña
            password_hash = self.encriptar_password(data['password'])
            
            # Preparar datos para creación
            usuario_data = {
                'nombre': data['nombre'].strip(),
                'username': data['username'].strip().lower(),
                'email': data['email'].strip().lower(),
                'password': password_hash,
                'rol': data['rol'],
                'biografia': data.get('biografia', '').strip(),
                'estado': 'activo'
            }
            
            # Crear usuario sin registrar en auditoría (es un registro inicial)
            usuario = self.usuario_repo.create(usuario_data, registrar_auditoria=False)
            
            if usuario:
                self.usuario_repo.save()
                return (True, usuario, [])
            else:
                return (False, None, ['Error al crear el usuario'])
                
        except Exception as e:
            print(f"Error en registro: {e}")
            return (False, None, ['Error interno del servidor'])
    
    def login_usuario(self, email, password, remember=False):
        """
        Iniciar sesión de usuario
        
        Args:
            email (str): Email del usuario
            password (str): Contraseña del usuario
            remember (bool): Recordar sesión
            
        Returns:
            tuple: (bool, Usuario/None, str) - (exitoso, usuario, mensaje_error)
        """
        try:
            # Sanitizar email
            email_limpio = email.strip().lower() if email else ''
            if not email_limpio:
                return (False, None, 'Credenciales inválidas')
            
            # Buscar usuario por email
            usuario = self.usuario_repo.get_by_email(email_limpio)
            
            # ── SEGURIDAD: Mensaje genérico para prevenir enumeración de cuentas ──
            mensaje_generico = 'Email o contraseña incorrectos'
            
            if not usuario:
                return (False, None, mensaje_generico)
            
            if not usuario.is_active():
                return (False, None, 'Tu cuenta ha sido suspendida. Contacta al administrador.')
            
            # Verificar contraseña
            if not self.verificar_password(password, usuario.password):
                return (False, None, mensaje_generico)
            
            # Verificar 2FA
            if getattr(usuario, 'is_2fa_enabled', False):
                return (True, usuario, '2fa_required')
            
            # Iniciar sesión
            login_user(usuario, remember=remember)
            
            return (True, usuario, '')
            
        except Exception as e:
            print(f"Error en login: {e}")
            return (False, None, 'Error interno del servidor')
    
    def logout_usuario(self):
        """
        Cerrar sesión de usuario
        
        Returns:
            bool: True si se cerró correctamente
        """
        try:
            logout_user()
            return True
        except Exception as e:
            print(f"Error en logout: {e}")
            return False
    
    def cambiar_password(self, usuario_id, password_actual, password_nueva):
        """
        Cambiar contraseña de usuario
        
        Args:
            usuario_id (int): ID del usuario
            password_actual (str): Contraseña actual
            password_nueva (str): Contraseña nueva
            
        Returns:
            tuple: (bool, str) - (exitoso, mensaje)
        """
        try:
            # Obtener usuario
            usuario = self.usuario_repo.get_by_id(usuario_id)
            if not usuario:
                return (False, 'Usuario no encontrado')
            
            # Verificar contraseña actual
            if not self.verificar_password(password_actual, usuario.password):
                return (False, 'La contraseña actual es incorrecta')
            
            # Validar nueva contraseña con las mismas reglas de seguridad
            if len(password_nueva) < 8:
                return (False, 'La nueva contraseña debe tener al menos 8 caracteres')
            if not any(c.isupper() for c in password_nueva):
                return (False, 'La nueva contraseña debe contener al menos una mayúscula')
            if not any(c.isdigit() for c in password_nueva):
                return (False, 'La nueva contraseña debe contener al menos un número')
            if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password_nueva):
                return (False, 'La nueva contraseña debe contener al menos un carácter especial')
            
            # Actualizar contraseña
            password_hash = self.encriptar_password(password_nueva)
            actualizado = self.usuario_repo.update(
                usuario_id, 
                {'password': password_hash}, 
                usuario_id
            )
            
            if actualizado:
                self.usuario_repo.save()
                return (True, 'Contraseña actualizada correctamente')
            else:
                return (False, 'Error al actualizar la contraseña')
                
        except Exception as e:
            print(f"Error al cambiar contraseña: {e}")
            return (False, 'Error interno del servidor')
    
    def verificar_permiso(self, usuario, rol_requerido=None, rol_minimo=None):
        """
        Verificar permisos de usuario
        
        Args:
            usuario: Usuario actual
            rol_requerido (str): Rol específico requerido
            rol_minimo (str): Rol mínimo requerido (admin > artista > cliente)
            
        Returns:
            bool: True si tiene permiso
        """
        if not usuario or not usuario.is_active():
            return False
        
        if rol_requerido:
            return usuario.rol == rol_requerido
        
        if rol_minimo:
            jerarquia = {'cliente': 1, 'artista': 2, 'admin': 3}
            nivel_usuario = jerarquia.get(usuario.rol, 0)
            nivel_requerido = jerarquia.get(rol_minimo, 0)
            return nivel_usuario >= nivel_requerido
        
        return True

# Funciones de compatibilidad con código existente
def encriptar_password(password):
    """Función de compatibilidad para encriptar password"""
    return bcrypt.generate_password_hash(password).decode('utf-8')

def validar_email_duplicado(email, modelo_usuario):
    """Función de compatibilidad para validar email duplicado"""
    existe = modelo_usuario.query.filter_by(email=email).first()
    return existe is not None