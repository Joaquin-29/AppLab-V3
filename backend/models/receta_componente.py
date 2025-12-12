import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db

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