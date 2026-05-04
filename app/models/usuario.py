from datetime import datetime
from flask_login import UserMixin
from app.factories.app_factory import db

# Tablas de asociación
favoritos_obras = db.Table('favoritos_obras',
    db.Column('id_usuario', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('id_obra', db.Integer, db.ForeignKey('obras.id_obra'), primary_key=True),
    db.Column('fecha_agregado', db.DateTime, default=datetime.utcnow)
)

favoritos_artistas = db.Table('favoritos_artistas',
    db.Column('id_usuario', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('id_artista', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('fecha_seguimiento', db.DateTime, default=datetime.utcnow)
)

bandeja_newsletter = db.Table('bandeja_newsletter',
    db.Column('id_usuario', db.Integer, db.ForeignKey('usuarios.id_usuario'), primary_key=True),
    db.Column('id_newsletter', db.Integer, db.ForeignKey('newsletters.id_newsletter'), primary_key=True),
    db.Column('fecha_envio', db.DateTime, default=datetime.utcnow),
    db.Column('leido', db.Boolean, default=False)
)

class Usuario(UserMixin, db.Model):
    """
    Modelo de Usuario basado en el script de base de datos
    Tabla: usuarios
    """
    __tablename__ = 'usuarios'
    
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)  # hash seguro (bcrypt)
    rol = db.Column(db.String(20), nullable=False, default='cliente')  # admin, artista, cliente
    biografia = db.Column(db.Text)
    foto_perfil = db.Column(db.String(255))
    foto_banner = db.Column(db.String(255))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='activo')  # activo, bloqueado
    
    # Relaciones
    obras = db.relationship('Obra', backref='artista', lazy='dynamic', 
                           cascade='all, delete-orphan')
    productos = db.relationship('Producto', backref='artista', lazy='dynamic',
                               cascade='all, delete-orphan')
    entradas_blog = db.relationship('EntradaBlog', backref='artista', lazy='dynamic',
                                    cascade='all, delete-orphan')
    comentarios_blog = db.relationship('ComentarioBlog', backref='usuario', lazy='dynamic',
                                       cascade='all, delete-orphan')
    
    # Relaciones de favoritos
    obras_favoritas = db.relationship('Obra', secondary='favoritos_obras',
                                     lazy='subquery',
                                     backref=db.backref('usuarios_favoritos', lazy='dynamic'))
    artistas_seguidos = db.relationship('Usuario', 
                                       secondary='favoritos_artistas',
                                       primaryjoin=(id_usuario == favoritos_artistas.c.id_usuario),
                                       secondaryjoin=(id_usuario == favoritos_artistas.c.id_artista),
                                       lazy='subquery',
                                       backref=db.backref('seguidores', lazy='dynamic'))
    
    # Relaciones de newsletters
    suscripciones_enviadas = db.relationship('Newsletter', backref='artista', lazy='dynamic',
                                           cascade='all, delete-orphan')
    suscripciones_recibidas = db.relationship('Newsletter', 
                                             secondary='bandeja_newsletter',
                                             lazy='subquery',
                                             backref=db.backref('destinatarios', lazy='dynamic'))
    
    # Relaciones de comercio
    direcciones = db.relationship('Direccion', backref='usuario', lazy='dynamic',
                                 cascade='all, delete-orphan')
    ordenes_cliente = db.relationship('Orden', foreign_keys='Orden.id_cliente',
                                      backref='cliente', lazy='dynamic',
                                      cascade='all, delete-orphan')
    
    # Relaciones de moodboards
    lienzos = db.relationship('Lienzo', backref='usuario', lazy='dynamic',
                             cascade='all, delete-orphan')
    
    def get_id(self):
        """Override requerido por Flask-Login para identificar al usuario"""
        return str(self.id_usuario)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'
    
    def to_dict(self):
        """Convertir usuario a diccionario para API responses"""
        return {
            'id_usuario': self.id_usuario,
            'nombre': self.nombre,
            'username': self.username,
            'email': self.email,
            'rol': self.rol,
            'biografia': self.biografia,
            'foto_perfil': self.foto_perfil,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
            'estado': self.estado
        }
    
    def is_admin(self):
        """Verificar si es administrador"""
        return self.rol == 'admin'
    
    def is_artista(self):
        """Verificar si es artista"""
        return self.rol == 'artista'
    
    def is_cliente(self):
        """Verificar si es cliente"""
        return self.rol == 'cliente'
    
    def is_active(self):
        """Verificar si el usuario está activo"""
        return self.estado == 'activo'
    
    def get_obras_count(self):
        """Obtener cantidad de obras publicadas"""
        return self.obras.filter_by(visible=True).count()
    
    def get_productos_count(self):
        """Obtener cantidad de productos disponibles"""
        return self.productos.filter(Producto.stock > 0).count()
    
    def get_seguidores_count(self):
        """Obtener cantidad de seguidores"""
        return self.seguidores.count()
    
    def get_siguiendo_count(self):
        """Obtener cantidad de artistas que sigue"""
        return self.artistas_seguidos.count()

