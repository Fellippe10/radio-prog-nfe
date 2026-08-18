const API_URL = '/api';

// Intercepta todas as requisições fetch para injetar a senha
const originalFetch = window.fetch;
window.fetch = async function() {
    let [resource, config] = arguments;
    if (!config) config = {};
    if (!config.headers) config.headers = {};
    
    // Pega o token salvo no navegador
    const token = localStorage.getItem('auth_token');
    if (token) {
        config.headers['Authorization'] = `Basic ${token}`;
    }
    
    const response = await originalFetch(resource, config);
    
    // Se o backend disser "Acesso Negado", exibe a tela de login
    if (response.status === 401) {
        localStorage.removeItem('auth_token');
        document.getElementById('login-screen').style.display = 'flex';
        document.getElementById('main-app').style.display = 'none';
    }
    return response;
};

// Função para o botão Entrar
window.realizarLogin = async function(e) {
    e.preventDefault();
    const user = document.getElementById('username').value;
    const pass = document.getElementById('password').value;
    
    // Cria o token Base64 (Basic Auth)
    const token = btoa(user + ':' + pass);
    localStorage.setItem('auth_token', token);
    
    // Tenta carregar os clientes para ver se a senha está certa
    const res = await fetch(`${API_URL}/clientes`);
    if (res.ok) {
        // Se deu certo, esconde o login e mostra o app
        document.getElementById('login-screen').style.display = 'none';
        document.getElementById('main-app').style.display = 'block';
        loadClientes();
    } else {
        showToast('Usuário ou senha incorretos!', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadClientes();

    document.getElementById('clienteForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const clienteData = {
            nome: document.getElementById('nome').value,
            cnpj: document.getElementById('cnpj').value,
            email: document.getElementById('email').value,
            endereco: {
                logradouro: document.getElementById('logradouro').value,
                numero: document.getElementById('numero').value,
                complemento: document.getElementById('complemento').value,
                bairro: document.getElementById('bairro').value,
                cidade: document.getElementById('cidade').value,
                uf: document.getElementById('uf').value,
                cep: document.getElementById('cep').value
            },
            servico_codigo: document.getElementById('servico_codigo').value,
            servico_descricao: document.getElementById('servico_descricao').value,
            servico_valor: parseFloat(document.getElementById('servico_valor').value),
            servico_aliquota: parseFloat(document.getElementById('servico_aliquota').value)
        };

        try {
            const response = await fetch(`${API_URL}/clientes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(clienteData)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Erro ao salvar cliente');
            }
            
            showToast('Cliente salvo com sucesso!', 'success');
            document.getElementById('clienteForm').reset();
            // restore defaults
            document.getElementById('servico_codigo').value = "121401";
            document.getElementById('servico_descricao').value = "Radio customizada";
            document.getElementById('servico_valor').value = "1.00";
            document.getElementById('servico_aliquota').value = "6.0";
            
            loadClientes();
        } catch (error) {
            showToast(error.message, 'error');
        }
    });

    // Modal: salvar edição
    document.getElementById('editForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const clienteId = document.getElementById('edit_id').value;

        const clienteData = {
            nome: document.getElementById('edit_nome').value,
            cnpj: document.getElementById('edit_cnpj').value,
            email: document.getElementById('edit_email').value,
            endereco: {
                logradouro: document.getElementById('edit_logradouro').value,
                numero: document.getElementById('edit_numero').value,
                complemento: document.getElementById('edit_complemento').value,
                bairro: document.getElementById('edit_bairro').value,
                cidade: document.getElementById('edit_cidade').value,
                uf: document.getElementById('edit_uf').value,
                cep: document.getElementById('edit_cep').value
            },
            servico_codigo: document.getElementById('edit_servico_codigo').value,
            servico_descricao: document.getElementById('edit_servico_descricao').value,
            servico_valor: parseFloat(document.getElementById('edit_servico_valor').value),
            servico_aliquota: parseFloat(document.getElementById('edit_servico_aliquota').value)
        };

        try {
            const response = await fetch(`${API_URL}/clientes/${clienteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(clienteData)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Erro ao atualizar cliente');
            }

            showToast('Cliente atualizado com sucesso!', 'success');
            closeModal();
            loadClientes();
        } catch (error) {
            showToast(error.message, 'error');
        }
    });

    // Fechar modal ao clicar fora
    document.getElementById('editModal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('editModal')) {
            closeModal();
        }
    });
});

async function loadClientes() {
    try {
        const response = await fetch(`${API_URL}/clientes`);
        const clientes = await response.json();
        
        const tbody = document.querySelector('#clientesTable tbody');
        tbody.innerHTML = '';
        
        clientes.forEach(cliente => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${cliente.nome}</td>
                <td>${cliente.cnpj}</td>
                <td>${cliente.email}</td>
                <td>${cliente.servico_descricao} (R$ ${cliente.servico_valor})</td>
                <td class="actions-cell">
                    <button class="btn-action" onclick="emitirNota(${cliente.id}, this)">
                        Emitir Nota
                    </button>
                    <button class="btn-edit" onclick='editarCliente(${JSON.stringify(cliente)})'>
                        ✏️ Editar
                    </button>
                    <button class="btn-delete" onclick="removerCliente(${cliente.id}, '${cliente.nome.replace(/'/g, "\\'")}')">
                        🗑️ Remover
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Erro ao carregar clientes:', error);
    }
}

function editarCliente(cliente) {
    document.getElementById('edit_id').value = cliente.id;
    document.getElementById('edit_nome').value = cliente.nome;
    document.getElementById('edit_cnpj').value = cliente.cnpj;
    document.getElementById('edit_email').value = cliente.email;
    document.getElementById('edit_logradouro').value = cliente.endereco.logradouro;
    document.getElementById('edit_numero').value = cliente.endereco.numero;
    document.getElementById('edit_complemento').value = cliente.endereco.complemento || '';
    document.getElementById('edit_bairro').value = cliente.endereco.bairro;
    document.getElementById('edit_cidade').value = cliente.endereco.cidade;
    document.getElementById('edit_uf').value = cliente.endereco.uf;
    document.getElementById('edit_cep').value = cliente.endereco.cep;
    document.getElementById('edit_servico_codigo').value = cliente.servico_codigo;
    document.getElementById('edit_servico_descricao').value = cliente.servico_descricao;
    document.getElementById('edit_servico_valor').value = cliente.servico_valor;
    document.getElementById('edit_servico_aliquota').value = cliente.servico_aliquota;

    document.getElementById('editModal').classList.add('show');
}

function closeModal() {
    document.getElementById('editModal').classList.remove('show');
}

async function removerCliente(clienteId, nome) {
    if (!confirm(`Tem certeza que deseja remover o cliente "${nome}"?`)) return;

    try {
        const response = await fetch(`${API_URL}/clientes/${clienteId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro ao remover cliente');
        }

        showToast('Cliente removido com sucesso!', 'success');
        loadClientes();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function emitirNota(clienteId, btnElement) {
    const originalText = btnElement.innerText;
    btnElement.innerText = 'Emitindo...';
    btnElement.disabled = true;

    try {
        const response = await fetch(`${API_URL}/emitir-nota/${clienteId}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Erro ao emitir nota');
        }
        
        showToast('Nota enviada ao n8n com sucesso!', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btnElement.innerText = originalText;
        btnElement.disabled = false;
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

async function emitirTodasNotas(btnElement) {
    if (!confirm('Tem certeza que deseja emitir notas para TODOS os clientes?')) return;

    const originalText = btnElement.innerText;
    btnElement.innerText = '⏳ Emitindo...';
    btnElement.disabled = true;

    try {
        const response = await fetch(`${API_URL}/emitir-notas-lote`, {
            method: 'POST'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Erro ao emitir notas em lote');
        }

        showToast(data.message, 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btnElement.innerText = originalText;
        btnElement.disabled = false;
    }
}

// ==========================================
// LÓGICA DAS ABAS E NOTAS
// ==========================================

function switchTab(tabId) {
    // Esconder todas as seções
    document.getElementById('clientes-section').style.display = 'none';
    document.getElementById('notas-section').style.display = 'none';
    
    // Tirar a classe active dos botões
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    // Mostrar a seção atual
    document.getElementById(`${tabId}-section`).style.display = 'block';
    
    // Ativar o botão que foi clicado (usando a constante global de evento)
    if (window.event) {
        window.event.currentTarget.classList.add('active');
    }

    if (tabId === 'notas') {
        loadNotas();
    }
}

async function loadNotas() {
    try {
        const dataFiltro = document.getElementById('filtroDataNotas')?.value;
        let url = `${API_URL}/notas`;
        if (dataFiltro) {
            url += `?data_filtro=${dataFiltro}`;
        }

        const response = await fetch(url);
        
        if (response.status === 401) {
            alert('Sessão expirada. Recarregue a página.');
            return;
        }
        
        const notas = await response.json();
        const tbody = document.querySelector('#notasTable tbody');
        tbody.innerHTML = '';

        if (notas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Nenhuma nota registrada no histórico ainda.</td></tr>';
            return;
        }

        notas.forEach(nota => {
            const tr = document.createElement('tr');
            // Adiciona o "Z" no final para indicar que o horário vindo do Python é UTC
            const dataEmissao = new Date(nota.data_emissao + "Z").toLocaleString('pt-BR');

            tr.innerHTML = `
                <td>${dataEmissao}</td>
                <td><span class="badge" style="background: var(--primary-color); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;">${nota.competencia}</span></td>
                <td style="font-weight: 500;">${nota.cliente_nome}</td>
                <td>${nota.cliente_cnpj}</td>
                <td class="actions-cell">
                    <a href="${nota.pdf_url}" target="_blank" class="btn-batch" style="text-decoration: none; display: inline-block; padding: 0.4rem 0.8rem;">📄 Ver PDF</a>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Erro ao carregar notas", error);
        showToast('Erro ao carregar notas', 'error');
    }
}

// ==========================================
// PESQUISA DE CLIENTES
// ==========================================

function pesquisarClientes() {
    const input = document.getElementById('filtroClientes').value.toLowerCase();
    const tbody = document.querySelector('#clientesTable tbody');
    const trs = tbody.getElementsByTagName('tr');

    for (let i = 0; i < trs.length; i++) {
        const tdNome = trs[i].getElementsByTagName('td')[0];
        const tdCnpj = trs[i].getElementsByTagName('td')[1];
        
        if (tdNome || tdCnpj) {
            const nomeValor = tdNome.textContent || tdNome.innerText;
            const cnpjValor = tdCnpj.textContent || tdCnpj.innerText;
            
            if (nomeValor.toLowerCase().indexOf(input) > -1 || cnpjValor.toLowerCase().indexOf(input) > -1) {
                trs[i].style.display = "";
            } else {
                trs[i].style.display = "none";
            }
        }
    }
}
