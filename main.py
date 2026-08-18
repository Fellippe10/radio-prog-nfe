import os
import secrets
from datetime import datetime, timedelta
from calendar import monthrange
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import httpx

import models, schemas
from database import engine, get_db

# Cria as tabelas
models.Base.metadata.create_all(bind=engine)

security = HTTPBasic(auto_error=False)

# Substitua 'admin' e 'admin' pelo usuário e senha que desejar
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "radiopop"

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
            # REMOVIDO: headers={"WWW-Authenticate": "Basic"}
        )
    
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso Negado",
            # REMOVIDO: headers={"WWW-Authenticate": "Basic"}
        )
    return credentials.username

# Removido dependência global para permitir o webhook público
app = FastAPI(title="Emissão de Notas n8n")

N8N_WEBHOOK_URL = "https://n8n.nextload.com.br/webhook/d03a3015-f158-4564-aff7-dddc77c6198c"

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/api/clientes", response_model=schemas.ClienteResponse, dependencies=[Depends(verify_credentials)])
def create_cliente(cliente: schemas.ClienteCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Cliente).filter(models.Cliente.cnpj == cliente.cnpj).first()
    if existing:
        raise HTTPException(status_code=400, detail="CNPJ/CPF já cadastrado")

    db_cliente = models.Cliente(
        nome=cliente.nome,
        cnpj=cliente.cnpj,
        email=cliente.email,
        logradouro=cliente.endereco.logradouro,
        numero=cliente.endereco.numero,
        complemento=cliente.endereco.complemento,
        bairro=cliente.endereco.bairro,
        cidade=cliente.endereco.cidade,
        uf=cliente.endereco.uf,
        cep=cliente.endereco.cep,
        servico_codigo=cliente.servico_codigo,
        servico_descricao=cliente.servico_descricao,
        servico_valor=cliente.servico_valor,
        servico_aliquota=cliente.servico_aliquota
    )
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    
    return schemas.ClienteResponse(
        id=db_cliente.id,
        nome=db_cliente.nome,
        cnpj=db_cliente.cnpj,
        email=db_cliente.email,
        endereco=schemas.EnderecoSchema(
            logradouro=db_cliente.logradouro,
            numero=db_cliente.numero,
            complemento=db_cliente.complemento,
            bairro=db_cliente.bairro,
            cidade=db_cliente.cidade,
            uf=db_cliente.uf,
            cep=db_cliente.cep
        ),
        servico_codigo=db_cliente.servico_codigo,
        servico_descricao=db_cliente.servico_descricao,
        servico_valor=db_cliente.servico_valor,
        servico_aliquota=db_cliente.servico_aliquota
    )

@app.get("/api/clientes", response_model=list[schemas.ClienteResponse], dependencies=[Depends(verify_credentials)])
def read_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    clientes = db.query(models.Cliente).offset(skip).limit(limit).all()
    resultado = []
    for db_cliente in clientes:
        resultado.append(
            schemas.ClienteResponse(
                id=db_cliente.id,
                nome=db_cliente.nome,
                cnpj=db_cliente.cnpj,
                email=db_cliente.email,
                endereco=schemas.EnderecoSchema(
                    logradouro=db_cliente.logradouro,
                    numero=db_cliente.numero,
                    complemento=db_cliente.complemento,
                    bairro=db_cliente.bairro,
                    cidade=db_cliente.cidade,
                    uf=db_cliente.uf,
                    cep=db_cliente.cep
                ),
                servico_codigo=db_cliente.servico_codigo,
                servico_descricao=db_cliente.servico_descricao,
                servico_valor=db_cliente.servico_valor,
                servico_aliquota=db_cliente.servico_aliquota
            )
        )
    return resultado

@app.post("/api/emitir-nota/{cliente_id}", dependencies=[Depends(verify_credentials)])
async def emitir_nota(cliente_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    hoje = datetime.now()
    _, ultimo_dia = monthrange(hoje.year, hoje.month)
    data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    data_fim = hoje.replace(day=ultimo_dia).strftime("%Y-%m-%d")

    payload = {
        "tomador": {
            "nome": c.nome,
            "cnpj": c.cnpj,
            "email": c.email,
            "endereco": {
                "logradouro": c.logradouro,
                "numero": c.numero,
                "complemento": c.complemento or "",
                "bairro": c.bairro,
                "cidade": c.cidade,
                "uf": c.uf,
                "cep": c.cep
            }
        },
        "servico": {
            "codigo": c.servico_codigo,
            "descricao": c.servico_descricao,
            "evento": {
                "nome": c.servico_descricao,
                "dataInicio": data_inicio,
                "dataFim": data_fim
            }
        },
        "valores": {
            "total": c.servico_valor,
            "aliquotaIss": c.servico_aliquota
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(N8N_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            return {"status": "success", "message": "Nota fiscal enviada ao n8n com sucesso!"}
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Erro do n8n: {exc.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao comunicar com n8n: {str(e)}")

@app.put("/api/clientes/{cliente_id}", response_model=schemas.ClienteResponse, dependencies=[Depends(verify_credentials)])
def update_cliente(cliente_id: int, cliente: schemas.ClienteCreate, db: Session = Depends(get_db)):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Verifica CNPJ duplicado (excluindo o próprio cliente)
    existing = db.query(models.Cliente).filter(
        models.Cliente.cnpj == cliente.cnpj,
        models.Cliente.id != cliente_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="CNPJ/CPF já cadastrado em outro cliente")

    db_cliente.nome = cliente.nome
    db_cliente.cnpj = cliente.cnpj
    db_cliente.email = cliente.email
    db_cliente.logradouro = cliente.endereco.logradouro
    db_cliente.numero = cliente.endereco.numero
    db_cliente.complemento = cliente.endereco.complemento
    db_cliente.bairro = cliente.endereco.bairro
    db_cliente.cidade = cliente.endereco.cidade
    db_cliente.uf = cliente.endereco.uf
    db_cliente.cep = cliente.endereco.cep
    db_cliente.servico_codigo = cliente.servico_codigo
    db_cliente.servico_descricao = cliente.servico_descricao
    db_cliente.servico_valor = cliente.servico_valor
    db_cliente.servico_aliquota = cliente.servico_aliquota

    db.commit()
    db.refresh(db_cliente)

    return schemas.ClienteResponse(
        id=db_cliente.id,
        nome=db_cliente.nome,
        cnpj=db_cliente.cnpj,
        email=db_cliente.email,
        endereco=schemas.EnderecoSchema(
            logradouro=db_cliente.logradouro,
            numero=db_cliente.numero,
            complemento=db_cliente.complemento,
            bairro=db_cliente.bairro,
            cidade=db_cliente.cidade,
            uf=db_cliente.uf,
            cep=db_cliente.cep
        ),
        servico_codigo=db_cliente.servico_codigo,
        servico_descricao=db_cliente.servico_descricao,
        servico_valor=db_cliente.servico_valor,
        servico_aliquota=db_cliente.servico_aliquota
    )

@app.delete("/api/clientes/{cliente_id}", dependencies=[Depends(verify_credentials)])
def delete_cliente(cliente_id: int, db: Session = Depends(get_db)):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    db.delete(db_cliente)
    db.commit()
    return {"status": "success", "message": "Cliente removido com sucesso"}

@app.post("/api/emitir-notas-lote", dependencies=[Depends(verify_credentials)])
async def emitir_notas_lote(db: Session = Depends(get_db)):
    clientes = db.query(models.Cliente).all()
    if not clientes:
        raise HTTPException(status_code=400, detail="Nenhum cliente cadastrado")

    hoje = datetime.now()
    _, ultimo_dia = monthrange(hoje.year, hoje.month)
    data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
    data_fim = hoje.replace(day=ultimo_dia).strftime("%Y-%m-%d")

    notas = []
    for c in clientes:
        notas.append({
            "tomador": {
                "nome": c.nome,
                "cnpj": c.cnpj,
                "email": c.email,
                "endereco": {
                    "logradouro": c.logradouro,
                    "numero": c.numero,
                    "complemento": c.complemento or "",
                    "bairro": c.bairro,
                    "cidade": c.cidade,
                    "uf": c.uf,
                    "cep": c.cep
                }
            },
            "servico": {
                "codigo": c.servico_codigo,
                "descricao": c.servico_descricao,
                "evento": {
                    "nome": c.servico_descricao,
                    "dataInicio": data_inicio,
                    "dataFim": data_fim
                }
            },
            "valores": {
                "total": c.servico_valor,
                "aliquotaIss": c.servico_aliquota
            }
        })

    payload = {
        "total_notas": len(notas),
        "notas": notas
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(N8N_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            return {
                "status": "success",
                "message": f"{len(notas)} notas enviadas ao n8n com sucesso!",
                "total": len(notas)
            }
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Erro do n8n: {exc.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao comunicar com n8n: {str(e)}")

# ==========================================
# ROTAS PARA HISTÓRICO DE NOTAS
# ==========================================

@app.post("/api/webhook/nota-emitida")
def webhook_nota_emitida(payload: schemas.WebhookNotaPayload, db: Session = Depends(get_db)):
    # Rota pública para o n8n chamar
    cliente = db.query(models.Cliente).filter(models.Cliente.cnpj == payload.cnpj).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado pelo CNPJ")
    
    hoje = datetime.now()
    competencia_atual = f"{hoje.month:02d}/{hoje.year}"
    
    # Salvar o registro da nota no banco
    nova_nota = models.NotaEmitida(
        cliente_id=cliente.id,
        competencia=competencia_atual,
        pdf_url=payload.pdf_url
    )
    db.add(nova_nota)
    db.commit()
    db.refresh(nova_nota)
    
    return {"status": "success", "message": "Nota registrada com sucesso"}

from sqlalchemy import func
from typing import Optional

@app.get("/api/notas", response_model=list[schemas.NotaEmitidaResponse], dependencies=[Depends(verify_credentials)])
def list_notas(data_filtro: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.NotaEmitida)
    
    if data_filtro:
        try:
            # O usuário escolhe a data local (ex: 2026-08-17)
            # Como o banco salva em UTC, a meia-noite do Brasil (UTC-3)
            # equivale às 03:00 da manhã do mesmo dia no UTC.
            from datetime import datetime, timedelta
            
            data_local = datetime.strptime(data_filtro, "%Y-%m-%d")
            start_utc = data_local + timedelta(hours=3)
            end_utc = start_utc + timedelta(days=1)
            
            query = query.filter(
                models.NotaEmitida.data_emissao >= start_utc,
                models.NotaEmitida.data_emissao < end_utc
            )
        except ValueError:
            pass # Ignora se vier uma data inválida
        
    notas = query.order_by(models.NotaEmitida.data_emissao.desc()).all()
    resultado = []
    for n in notas:
        resultado.append(
            schemas.NotaEmitidaResponse(
                id=n.id,
                cliente_id=n.cliente_id,
                competencia=n.competencia,
                pdf_url=n.pdf_url,
                data_emissao=n.data_emissao,
                cliente_nome=n.cliente.nome if n.cliente else "Cliente Removido",
                cliente_cnpj=n.cliente.cnpj if n.cliente else "N/A"
            )
        )
    return resultado
