from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    unidad = db.Column(db.String(20), nullable=False)
    cantidad_disponible = db.Column(db.Integer, nullable=False, default=0)

    componentes = db.relationship('RecetaComponente', back_populates='producto')

    def __repr__(self):
        return f'<Producto {self.nombre}>'
    
class Receta(db.Model):
    __tablename__ = 'recetas'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    componentes = db.relationship('RecetaComponente', back_populates='receta', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Receta {self.nombre}>'
    
class RecetaComponente(db.Model):
    __tablename__ = 'receta_componentes'
    
    id = db.Column(db.Integer, primary_key=True)
    receta_id = db.Column(db.Integer, db.ForeignKey('recetas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad_necesaria = db.Column(db.Float, nullable=False)
    unidad = db.Column(db.String(20), nullable=False)

    receta = db.relationship('Receta', back_populates='componentes')
    producto = db.relationship('Producto', back_populates='componentes')

    def __repr__(self):
        return f'<RecetaComponente RecetaID: {self.receta_id}, ProductoID: {self.producto_id}, Cantidad: {self.cantidad_necesaria} {self.unidad}>'