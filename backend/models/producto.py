from datetime import datetime

# La instancia db debe ser importada desde donde se creó
def get_producto_model(db):
    class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    unidad = db.Column(db.String(20), nullable=False)
    cantidad_disponible = db.Column(db.Float, nullable=False, default=0)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    lote = db.Column(db.String(50), nullable=True)

    componentes = db.relationship('RecetaComponente', back_populates='producto')

    def __repr__(self):
        return f'<Producto {self.nombre}>'