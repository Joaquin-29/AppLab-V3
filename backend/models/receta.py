import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db

class Receta(db.Model):
    __tablename__ = 'recetas'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    componentes = db.relationship('RecetaComponente', back_populates='receta', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Receta {self.nombre}>'