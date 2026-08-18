from pydantic import BaseModel
from typing import Optional

class EnderecoSchema(BaseModel):
    logradouro: str
    numero: str
    complemento: Optional[str] = ""
    bairro: str
    cidade: str
    uf: str
    cep: str

class ClienteCreate(BaseModel):
    nome: str
    cnpj: str
    email: str
    endereco: EnderecoSchema
    servico_codigo: str = "121401"
    servico_descricao: str = "Radio customizada"
    servico_valor: float = 1.00
    servico_aliquota: float = 6.0

class ClienteResponse(ClienteCreate):
    id: int

    class Config:
        from_attributes = True

from datetime import datetime

class WebhookNotaPayload(BaseModel):
    cnpj: str
    pdf_url: str

class NotaEmitidaResponse(BaseModel):
    id: int
    cliente_id: int
    competencia: str
    pdf_url: str
    data_emissao: datetime
    cliente_nome: str
    cliente_cnpj: str

    class Config:
        from_attributes = True

