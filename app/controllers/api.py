from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.factories.service_factory import get_service_factory

# Crear blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/health')
def health_check():
    """
    Endpoint para verificar salud del API
    """
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'service': 'art-platform-api'
    })

@api_bp.route('/stats')
def stats():
    """
    Estadísticas públicas de la plataforma
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    obra_service = service_factory.get_obra_service()
    categoria_service = service_factory.get_categoria_service()
    
    stats = {
        'artistas_count': usuario_service.count({'rol': 'artista'}),
        'obras_count': obra_service.count({'visible': True}),
        'categorias_count': categoria_service.count(),
        'productos_disponibles': 0  # TODO: Implementar cuando tengamos productos
    }
    
    return jsonify(stats)

@api_bp.route('/categorias')
def api_categorias():
    """
    API para obtener todas las categorías
    """
    service_factory = get_service_factory()
    categoria_service = service_factory.get_categoria_service()
    
    categorias = categoria_service.get_all()
    
    return jsonify({
        'categorias': [categoria.to_dict() for categoria in categorias]
    })

@api_bp.route('/categorias/<int:categoria_id>')
def api_categoria_detalle(categoria_id):
    """
    API para obtener detalles de una categoría
    """
    service_factory = get_service_factory()
    categoria_service = service_factory.get_categoria_service()
    
    categoria, obras = categoria_service.get_with_obras(categoria_id, limit=12)
    
    if not categoria:
        return jsonify({'error': 'Categoría no encontrada'}), 404
    
    return jsonify({
        'categoria': categoria.to_dict(),
        'obras': [obra.to_dict() for obra in obras]
    })

@api_bp.route('/obras')
def api_obras():
    """
    API para obtener obras públicas
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    # Obtener parámetros (con límites de seguridad)
    limit = min(request.args.get('limit', 20, type=int), 100)
    offset = max(request.args.get('offset', 0, type=int), 0)
    categoria_id = request.args.get('categoria_id', type=int)
    artista_id = request.args.get('artista_id', type=int)
    
    # Obtener obras
    obras = obra_service.get_publicas(limit=limit, offset=offset, 
                                    categoria_id=categoria_id, artista_id=artista_id)
    
    return jsonify({
        'obras': [obra.to_dict() for obra in obras],
        'total': len(obras),
        'limit': limit,
        'offset': offset
    })

@api_bp.route('/obras/<int:obra_id>')
def api_obra_detalle(obra_id):
    """
    API para obtener detalles de una obra
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    obra = obra_service.get_by_id(obra_id)
    
    if not obra or not obra.is_visible():
        return jsonify({'error': 'Obra no encontrada'}), 404
    
    return jsonify(obra.to_dict())

@api_bp.route('/obras/buscar')
def api_buscar_obras():
    """
    API para buscar obras
    """
    termino = request.args.get('q', '').strip()
    if len(termino) > 100: termino = termino[:100]
    limit = min(request.args.get('limit', 20, type=int), 100)
    
    if not termino:
        return jsonify({'error': 'Término de búsqueda requerido'}), 400
    
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    obras = obra_service.buscar_obras(termino, limit=limit)
    
    return jsonify({
        'obras': [obra.to_dict() for obra in obras],
        'termino': termino,
        'total': len(obras)
    })

@api_bp.route('/artistas')
def api_artistas():
    """
    API para obtener artistas
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    # Obtener parámetros (con límites de seguridad)
    limit = min(request.args.get('limit', 20, type=int), 100)
    offset = max(request.args.get('offset', 0, type=int), 0)
    
    # Obtener artistas
    artistas = usuario_service.get_artistas_activos(limit=limit, offset=offset)
    
    return jsonify({
        'artistas': [artista.to_dict() for artista in artistas],
        'total': len(artistas),
        'limit': limit,
        'offset': offset
    })

@api_bp.route('/artistas/<int:artista_id>')
def api_artista_detalle(artista_id):
    """
    API para obtener detalles de un artista
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    obra_service = service_factory.get_obra_service()
    
    artista = usuario_service.get_by_id(artista_id)
    
    if not artista or not artista.is_artista() or not artista.is_active():
        return jsonify({'error': 'Artista no encontrado'}), 404
    
    # Obtener obras del artista
    obras = obra_service.get_by_artista(artista_id, visible_only=True, limit=12)
    
    # Obtener estadísticas
    stats = {
        'obras_count': obra_service.get_count_by_artista(artista_id),
        'seguidores_count': usuario_service.get_seguidores_count(artista_id)
    }
    
    return jsonify({
        'artista': artista.to_dict(),
        'obras': [obra.to_dict() for obra in obras],
        'stats': stats
    })

@api_bp.route('/artistas/buscar')
def api_buscar_artistas():
    """
    API para buscar artistas
    """
    termino = request.args.get('q', '').strip()
    if len(termino) > 100: termino = termino[:100]
    limit = min(request.args.get('limit', 20, type=int), 100)
    
    if not termino:
        return jsonify({'error': 'Término de búsqueda requerido'}), 400
    
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    artistas = usuario_service.buscar_usuarios(termino, rol='artista', limit=limit)
    
    return jsonify({
        'artistas': [artista.to_dict() for artista in artistas],
        'termino': termino,
        'total': len(artistas)
    })

# Endpoints que requieren autenticación
@api_bp.route('/usuario/perfil')
@login_required
def api_perfil_usuario():
    """
    API para obtener perfil del usuario actual
    """
    return jsonify(current_user.to_dict())

@api_bp.route('/usuario/favoritos/obras')
@login_required
def api_favoritos_obras():
    """
    API para obtener obras favoritas del usuario
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    obras = obra_service.get_favoritos_usuario(current_user.id_usuario)
    
    return jsonify({
        'obras': [obra.to_dict() for obra in obras],
        'total': len(obras)
    })

@api_bp.route('/usuario/favoritos/artistas')
@login_required
def api_favoritos_artistas():
    """
    API para obtener artistas seguidos por el usuario
    """
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    artistas = usuario_service.get_siguiendo(current_user.id_usuario)
    
    return jsonify({
        'artistas': [artista.to_dict() for artista in artistas],
        'total': len(artistas)
    })

@api_bp.route('/usuario/favoritos/obras/<int:obra_id>', methods=['POST'])
@login_required
def api_agregar_favorito_obra(obra_id):
    """
    API para agregar obra a favoritos
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    exitoso = obra_service.agregar_favorito(current_user.id_usuario, obra_id)
    
    if exitoso:
        return jsonify({
            'mensaje': 'Obra agregada a favoritos',
            'exitoso': True
        })
    else:
        return jsonify({
            'error': 'La obra ya está en favoritos o ocurrió un error',
            'exitoso': False
        }), 400

@api_bp.route('/usuario/favoritos/obras/<int:obra_id>', methods=['DELETE'])
@login_required
def api_quitar_favorito_obra(obra_id):
    """
    API para quitar obra de favoritos
    """
    service_factory = get_service_factory()
    obra_service = service_factory.get_obra_service()
    
    exitoso = obra_service.quitar_favorito(current_user.id_usuario, obra_id)
    
    if exitoso:
        return jsonify({
            'mensaje': 'Obra quitada de favoritos',
            'exitoso': True
        })
    else:
        return jsonify({
            'error': 'La obra no estaba en favoritos o ocurrió un error',
            'exitoso': False
        }), 400

@api_bp.route('/usuario/seguir-artista/<int:artista_id>', methods=['POST'])
@login_required
def api_seguir_artista(artista_id):
    """
    API para seguir a un artista
    """
    if not current_user.is_cliente():
        return jsonify({'error': 'Solo los clientes pueden seguir artistas'}), 403
    
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    exitoso = usuario_service.seguir_artista(current_user.id_usuario, artista_id)
    
    if exitoso:
        return jsonify({
            'mensaje': 'Ahora sigues a este artista',
            'exitoso': True
        })
    else:
        return jsonify({
            'error': 'Ya sigues a este artista o ocurrió un error',
            'exitoso': False
        }), 400

@api_bp.route('/usuario/seguir-artista/<int:artista_id>', methods=['DELETE'])
@login_required
def api_dejar_seguir_artista(artista_id):
    """
    API para dejar de seguir a un artista
    """
    if not current_user.is_cliente():
        return jsonify({'error': 'Solo los clientes pueden seguir artistas'}), 403
    
    service_factory = get_service_factory()
    usuario_service = service_factory.get_usuario_service()
    
    exitoso = usuario_service.dejar_de_seguir_artista(current_user.id_usuario, artista_id)
    
    if exitoso:
        return jsonify({
            'mensaje': 'Has dejado de seguir a este artista',
            'exitoso': True
        })
    else:
        return jsonify({
            'error': 'No seguías a este artista o ocurrió un error',
            'exitoso': False
        }), 400

# Manejadores de errores para la API
@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Recurso no encontrado'}), 404

@api_bp.errorhandler(400)
def api_bad_request(error):
    return jsonify({'error': 'Solicitud inválida'}), 400

@api_bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500

@api_bp.errorhandler(403)
def api_forbidden(error):
    return jsonify({'error': 'Acceso denegado'}), 403
