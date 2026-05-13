from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.factories.service_factory import get_service_factory
from functools import wraps

# Crear blueprint
admin_bp = Blueprint('admin', __name__)

def requiere_admin(f):
    """Decorador para requerir rol de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Esta página es solo para administradores', 'error')
            return redirect(url_for('public.home'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@requiere_admin
def dashboard():
    """
    Dashboard de administración
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    obra_service = service_factory.get_obra_service()
    producto_service = service_factory.get_producto_service()
    categoria_service = service_factory.get_categoria_service()
    
    # Obtener estadísticas generales (formato anidado para el template)
    stats = {
        'usuarios': {
            'total': usuario_service.count(),
            'artistas': usuario_service.count({'rol': 'artista'}),
            'clientes': usuario_service.count({'rol': 'cliente'})
        },
        'obras': {
            'total': obra_service.count(),
            'visibles': obra_service.count({'estado': 'publicada'}),
            'nuevas_mes': 0 # TODO: implementar filtro por fecha
        },
        'productos': {
            'total': producto_service.count(),
            'disponibles': producto_service.count({'stock__gt': 0})
        },
        'categorias': {
            'total': categoria_service.count()
        }
    }
    
    # Obtener usuarios recientes
    usuarios_recientes = usuario_service.get_all(limit=5)
    
    # Obtener obras recientes
    obras_recientes = obra_service.get_all(limit=5)
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         usuarios_recientes=usuarios_recientes,
                         obras_recientes=obras_recientes)



@admin_bp.route('/usuarios')
@login_required
@requiere_admin
def usuarios():
    """
    Listado de usuarios
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    # Obtener filtros
    rol = request.args.get('rol', '').strip() or None
    estado = request.args.get('estado', '').strip() or None
    termino = request.args.get('q', '').strip()
    if len(termino) > 100: termino = termino[:100]
    
    # Construir filtros
    filtros = {}
    if rol:
        filtros['rol'] = rol
    if estado:
        filtros['estado'] = estado
    
    # Obtener usuarios
    if termino:
        usuarios = usuario_service.buscar_usuarios(termino, rol)
    else:
        usuarios = usuario_service.get_all(filters=filtros)
    
    return render_template('admin/usuarios.html', usuarios=usuarios, rol=rol, estado=estado)

@admin_bp.route('/usuarios/<int:usuario_id>')
@login_required
@requiere_admin
def detalle_usuario(usuario_id):
    """
    Detalle de usuario
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    # Obtener usuario
    usuario = usuario_service.get_by_id(usuario_id)
    
    if not usuario:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('admin.usuarios'))
    
    return render_template('admin/detalle_usuario.html', usuario=usuario)

@admin_bp.route('/usuarios/<int:usuario_id>/toggle-estado', methods=['POST'])
@login_required
@requiere_admin
def toggle_estado_usuario(usuario_id):
    """
    Cambiar estado de usuario (activo/bloqueado)
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    # Cambiar estado
    usuario_actualizado = usuario_service.toggle_estado(usuario_id, current_user.id_usuario)
    
    if usuario_actualizado:
        nuevo_estado = 'activado' if usuario_actualizado.estado == 'activo' else 'bloqueado'
        flash(f'Usuario {nuevo_estado} correctamente', 'success')
    else:
        flash('Error al cambiar estado del usuario', 'error')
    
    return redirect(url_for('admin.detalle_usuario', usuario_id=usuario_id))

@admin_bp.route('/obras')
@login_required
@requiere_admin
def obras():
    """
    Listado de obras
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    # Obtener filtros
    visible = request.args.get('visible')
    termino = request.args.get('q', '').strip()
    if len(termino) > 100: termino = termino[:100]
    
    # Construir filtros
    filtros = {}
    if visible is not None:
        filtros['visible'] = visible == 'true'
    
    # Obtener obras
    if termino:
        obras = obra_service.buscar_obras(termino)
    else:
        obras = obra_service.get_all(filters=filtros)
    
    return render_template('admin/obras.html', obras=obras, visible=visible)

@admin_bp.route('/obras/<int:obra_id>')
@login_required
@requiere_admin
def detalle_obra(obra_id):
    """
    Detalle de obra
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    # Obtener obra
    obra = obra_service.get_by_id(obra_id)
    
    if not obra:
        flash('Obra no encontrada', 'error')
        return redirect(url_for('admin.obras'))
    
    return render_template('admin/detalle_obra.html', obra=obra)

@admin_bp.route('/obras/<int:obra_id>/toggle-visibilidad', methods=['POST'])
@login_required
@requiere_admin
def toggle_visibilidad_obra(obra_id):
    """
    Cambiar visibilidad de obra
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    # Cambiar visibilidad
    exitoso, obra_actualizada = obra_service.toggle_visibilidad(obra_id, current_user.id_usuario)
    
    if exitoso:
        nuevo_estado = 'visible' if obra_actualizada.visible else 'oculta'
        flash(f'Obra marcada como {nuevo_estado}', 'success')
    else:
        flash('Error al cambiar visibilidad de la obra', 'error')
    
    return redirect(url_for('admin.detalle_obra', obra_id=obra_id))

@admin_bp.route('/productos')
@login_required
@requiere_admin
def productos():
    """
    Listado de productos
    """
    service_factory = get_service_factory()
    producto_service = service_factory.get_producto_service()
    
    # Obtener filtros
    disponible = request.args.get('disponible')
    termino = request.args.get('q', '')
    
    # Obtener productos
    if termino:
        productos = producto_service.buscar_productos(termino)
    elif disponible == 'true':
        productos = producto_service.get_disponibles()
    elif disponible == 'false':
        productos = producto_service.get_agotados()
    else:
        productos = producto_service.get_all()
    
    return render_template('admin/productos.html', productos=productos, disponible=disponible)

@admin_bp.route('/productos/<int:producto_id>')
@login_required
@requiere_admin
def detalle_producto(producto_id):
    """
    Detalle de producto
    """
    service_factory = get_service_factory()
    producto_service = service_factory.get_producto_service()
    
    # Obtener producto
    producto = producto_service.get_by_id(producto_id)
    
    if not producto:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('admin.productos'))
    
    # Obtener historial de stock
    historial_stock = producto_service.get_historial_stock(producto_id, limit=10)
    
    return render_template('admin/detalle_producto.html', 
                         producto=producto, 
                         historial_stock=historial_stock)

@admin_bp.route('/categorias')
@login_required
@requiere_admin
def categorias():
    """
    Listado de categorías
    """
    service_factory = get_service_factory()
    categoria_service = service_factory.get_categoria_service()
    
    # Obtener categorías con conteo de obras
    categorias_data = categoria_service.get_all_with_obras_count()
    
    return render_template('admin/categorias.html', categorias_data=categorias_data)

@admin_bp.route('/categorias/nueva', methods=['GET', 'POST'])
@login_required
@requiere_admin
def nueva_categoria():
    """
    Crear nueva categoría
    """
    if request.method == 'POST':
        # Obtener datos del formulario
        data = {
            'nombre': request.form.get('nombre'),
            'descripcion': request.form.get('descripcion', '')
        }
        
        # Validar datos
        errores = []
        if not data.get('nombre', '').strip():
            errores.append('El nombre es obligatorio')
        
        if not errores:
            service_factory = get_service_factory()
            categoria_service = service_factory.get_categoria_service()
            
            # Verificar si ya existe
            if categoria_service.name_exists(data['nombre']):
                errores.append('El nombre de categoría ya existe')
            else:
                # Crear categoría
                categoria = categoria_service.create(data)
                if categoria:
                    categoria_service.save()
                    flash('Categoría creada correctamente', 'success')
                    return redirect(url_for('admin.categorias'))
                else:
                    errores.append('Error al crear la categoría')
        
        for error in errores:
            flash(error, 'error')
    
    return render_template('admin/nueva_categoria.html')

@admin_bp.route('/auditoria')
@login_required
@requiere_admin
def auditoria():
    """
    Registro de auditoría
    """
    service_factory = get_service_factory()
    admin_service = service_factory.get_admin_service()
    
    # Obtener filtros
    tabla = request.args.get('tabla')
    accion = request.args.get('accion')
    
    # Obtener registros de auditoría
    registros = admin_service.get_auditoria_registros(tabla=tabla, accion=accion, limit=50)
    
    return render_template('admin/auditoria.html', registros=registros, tabla=tabla, accion=accion)

@admin_bp.route('/estadisticas')
@login_required
@requiere_admin
def estadisticas():
    """
    Estadísticas del sistema
    """
    service_factory = get_service_factory()
    admin_service = service_factory.get_admin_service()
    
    # Obtener estadísticas
    stats = admin_service.get_estadisticas_generales()
    
    return render_template('admin/estadisticas.html', stats=stats)

# API endpoints
@admin_bp.route('/api/estadisticas/usuarios-por-rol')
@login_required
@requiere_admin
def api_estadisticas_usuarios_por_rol():
    """
    API para obtener estadísticas de usuarios por rol
    """
    service_factory = get_service_factory()
    admin_service = service_factory.get_admin_service()
    
    datos = admin_service.get_usuarios_por_rol()
    
    return jsonify(datos)

@admin_bp.route('/api/estadisticas/obras-por-categoria')
@login_required
@requiere_admin
def api_estadisticas_obras_por_categoria():
    """
    API para obtener estadísticas de obras por categoría
    """
    service_factory = get_service_factory()
    admin_service = service_factory.get_admin_service()
    
    datos = admin_service.get_obras_por_categoria()
    
    return jsonify(datos)
