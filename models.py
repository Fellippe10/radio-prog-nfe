from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    cnpj = Column(String, unique=True, index=True)
    email = Column(String)
    
    # Endereco
    logradouro = Column(String)
    numero = Column(String)
    complemento = Column(String)
    bairro = Column(String)
    cidade = Column(String)
    uf = Column(String)
    cep = Column(String)

    # Defaults para Servico e Valores
    servico_codigo = Column(String, default="121401")
    servico_descricao = Column(String, default="Radio customizada")
    servico_valor = Column(Float, default=1.00)
    servico_aliquota = Column(Float, default=6.0)

    # Relacionamento com as Notas
    notas = relationship("NotaEmitida", back_populates="cliente")

class NotaEmitida(Base):
    __tablename__ = "notas_emitidas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    competencia = Column(String) # ex: '08/2026'
    pdf_url = Column(String)
    data_emissao = Column(DateTime, default=datetime.datetime.utcnow)

    cliente = relationship("Cliente", back_populates="notas")
