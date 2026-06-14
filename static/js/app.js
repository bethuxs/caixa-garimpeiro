// ============================================================================
// GARIMPEIRO DE IMÓVEIS - JavaScript
// ============================================================================

function escapeHTML(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function escapeAttribute(value) {
    return escapeHTML(value);
}

function safeUrl(value) {
    try {
        const url = new URL(String(value ?? ''), window.location.origin);
        if (url.protocol === 'http:' || url.protocol === 'https:') {
            return escapeAttribute(url.href);
        }
    } catch (error) {
        // Invalid URLs fall through to the harmless placeholder.
    }
    return '#';
}

async function carregarCidades() {
    try {
        const response = await fetch('/api/cidades');
        const data = await response.json();
        
        if (data.sucesso) {
            const select = document.getElementById('filtro-cidade');
            data.cidades.forEach(cidade => {
                const option = document.createElement('option');
                option.value = cidade;
                option.textContent = cidade;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar cidades:', error);
    }
}

async function carregarBairros() {
    try {
        const response = await fetch('/api/bairros');
        const data = await response.json();
        
        if (data.sucesso) {
            const select = document.getElementById('filtro-bairro');
            data.bairros.forEach(bairro => {
                const option = document.createElement('option');
                option.value = bairro;
                option.textContent = bairro;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar bairros:', error);
    }
}

async function carregarModalidades() {
    try {
        const response = await fetch('/api/modalidades');
        const data = await response.json();

        if (data.sucesso) {
            const select = document.getElementById('filtro-modalidade');
            data.modalidades.forEach(modalidade => {
                const option = document.createElement('option');
                option.value = modalidade;
                option.textContent = modalidade;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar modalidades:', error);
    }
}

async function carregarImoveis() {
    try {
        const params = new URLSearchParams({
            page: paginaAtual,
            limit: imovelsPorPagina,
            cidade: filtrosBuscaAtivos.cidade || '',
            bairro: filtrosBuscaAtivos.bairro || '',
            modalidade: filtrosBuscaAtivos.modalidade || '',
            preco_min: filtrosBuscaAtivos.preco_min || 0,
            preco_max: filtrosBuscaAtivos.preco_max || 999999999,
            ordenar: filtrosBuscaAtivos.ordenar || 'data_insercao_desc'
        });

        const response = await fetch(`/api/imoveis?${params}`);
        const data = await response.json();

        if (data.sucesso) {
            renderizarImoveis(data.imoveis);
            atualizarPaginacao(data.total);
            document.getElementById('total-encontrados').textContent = 
                `${data.total} imóvel(eis) encontrado(s)`;
        }
    } catch (error) {
        console.error('Erro ao carregar imóveis:', error);
        document.getElementById('imoveis-container').innerHTML = 
            '<div class="alert alert-danger">Erro ao carregar imóveis</div>';
    }
}

function renderizarImoveis(imoveis) {
    const container = document.getElementById('imoveis-container');
    
    if (imoveis.length === 0) {
        container.innerHTML = '<div class="alert alert-danger" style="grid-column: 1/-1;">Nenhum imóvel encontrado</div>';
        return;
    }

    container.innerHTML = imoveis.map(imovel => `
        <div class="imovel-card" data-id="${escapeAttribute(imovel.id_imovel)}">
            <div class="imovel-header">
                <div class="imovel-id">ID: ${escapeHTML(imovel.id_imovel)}</div>
                <div class="imovel-bairro">${escapeHTML(imovel.bairro)}</div>
            </div>
            <div class="imovel-body">
                <div class="imovel-preco">${escapeHTML(imovel.preco_formatado)}</div>
                
                <div class="imovel-campo">
                    <div class="imovel-label">Cidade</div>
                    <div class="imovel-valor">${escapeHTML(imovel.cidade)}</div>
                </div>

                <div class="imovel-campo">
                    <div class="imovel-label">Modalidade</div>
                    <div class="imovel-valor">${escapeHTML(imovel.modalidade)}</div>
                </div>

                <div class="imovel-campo">
                    <div class="imovel-label">Descrição</div>
                    <div class="imovel-descricao">${escapeHTML(imovel.descricao)}</div>
                </div>

                <div class="imovel-campo">
                    <div class="imovel-label">Inserido em</div>
                    <div class="imovel-valor">${escapeHTML(imovel.data_insercao)}</div>
                </div>

                <div class="imovel-footer">
                    <button class="btn btn-primary" data-action="detalhes" data-id="${escapeAttribute(imovel.id_imovel)}">
                        📋 Ver Detalhes
                    </button>
                    <a href="${safeUrl(imovel.link)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">
                        🔗 Ir para Caixa
                    </a>
                </div>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.imovel-card').forEach(card => {
        card.addEventListener('click', () => mostrarDetalhes(card.dataset.id));
    });

    container.querySelectorAll('[data-action="detalhes"]').forEach(button => {
        button.addEventListener('click', event => {
            event.stopPropagation();
            mostrarDetalhes(button.dataset.id);
        });
    });

    container.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', event => event.stopPropagation());
    });
}

function atualizarPaginacao(total) {
    const totalPaginas = Math.ceil(total / imovelsPorPagina);
    const paginacaoDiv = document.getElementById('paginacao');
    
    if (totalPaginas > 1) {
        paginacaoDiv.style.display = 'flex';
        document.getElementById('info-pagina').textContent = 
            `Página ${paginaAtual} de ${totalPaginas}`;
        
        document.getElementById('btn-anterior').style.display = 
            paginaAtual > 1 ? 'block' : 'none';
        document.getElementById('btn-proximo').style.display = 
            paginaAtual < totalPaginas ? 'block' : 'none';
    } else {
        paginacaoDiv.style.display = 'none';
    }
}

function aplicarFiltros() {
    filtrosBuscaAtivos.cidade = document.getElementById('filtro-cidade').value;
    filtrosBuscaAtivos.bairro = document.getElementById('filtro-bairro').value;
    filtrosBuscaAtivos.modalidade = document.getElementById('filtro-modalidade').value;
    filtrosBuscaAtivos.preco_min = 
        parseFloat(document.getElementById('filtro-preco-min').value) || 0;
    filtrosBuscaAtivos.preco_max = 
        parseFloat(document.getElementById('filtro-preco-max').value) || 999999999;
    filtrosBuscaAtivos.ordenar = document.getElementById('filtro-ordenar').value;
    
    carregarImoveis();
}

async function mostrarDetalhes(idImovel) {
    try {
        const response = await fetch(`/api/imovel/${idImovel}`);
        const data = await response.json();

        if (data.sucesso) {
            const imovel = data.imovel;
            const modal = document.getElementById('modal-detalhe');
            
            modal.querySelector('#modal-body').innerHTML = `
                <h2>${escapeHTML(imovel.bairro)}</h2>
                
                <div class="modal-preco">${escapeHTML(imovel.preco_formatado)}</div>

                <div class="modal-campo">
                    <div class="modal-label">ID do Imóvel</div>
                    <div class="modal-valor">${escapeHTML(imovel.id_imovel)}</div>
                </div>

                <div class="modal-campo">
                    <div class="modal-label">Código</div>
                    <div class="modal-valor">${escapeHTML(imovel.codigo)}</div>
                </div>

                <div class="modal-campo">
                    <div class="modal-label">Cidade</div>
                    <div class="modal-valor">${escapeHTML(imovel.cidade)}</div>
                </div>

                <div class="modal-campo">
                    <div class="modal-label">Modalidade</div>
                    <div class="modal-valor">${escapeHTML(imovel.modalidade)}</div>
                </div>

                <div class="modal-campo">
                    <div class="modal-label">Descrição</div>
                    <div class="modal-valor">${escapeHTML(imovel.descricao)}</div>
                </div>

                <div class="modal-campo">
                    <div class="modal-label">Data de Captura</div>
                    <div class="modal-valor">${escapeHTML(imovel.data_captura)}</div>
                </div>

                <div class="modal-campo">
                    <div class="modal-label">Data de Inserção</div>
                    <div class="modal-valor">${escapeHTML(imovel.data_insercao)}</div>
                </div>

                <a href="${safeUrl(imovel.link)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary modal-link">
                    🔗 Acessar Portal Caixa
                </a>
            `;
            
            modal.style.display = 'block';
        }
    } catch (error) {
        console.error('Erro ao buscar detalhes:', error);
    }
}

async function carregarEstatisticas() {
    try {
        const response = await fetch('/api/estatisticas');
        const data = await response.json();

        if (data.sucesso) {
            // Top 10 bairros
            const topBairros = document.getElementById('top-bairros');
            topBairros.innerHTML = data.bairros.map(b => `
                <li>
                    <strong>${escapeHTML(b.bairro)}</strong>
                    <span>${escapeHTML(b.total)}</span>
                </li>
            `).join('');

            // Cidades
            const cidades = document.getElementById('cidades');
            cidades.innerHTML = data.cidades.map(c => `
                <li>
                    <strong>${escapeHTML(c.cidade)}</strong>
                    <span>${escapeHTML(c.total)}</span>
                </li>
            `).join('');

            // Modalidades
            const modalidades = document.getElementById('modalidades');
            modalidades.innerHTML = data.modalidades.map(m => `
                <li>
                    <strong>${escapeHTML(m.modalidade)}</strong>
                    <span>${escapeHTML(m.total)}</span>
                </li>
            `).join('');
        }
    } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
    }
}

async function exportarJSON() {
    try {
        const response = await fetch('/api/exportar');
        const data = await response.json();

        if (data.sucesso) {
            // Criar blob com dados JSON
            const jsonString = JSON.stringify(data.imoveis, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json' });
            
            // Criar URL de download
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `garimpeiro-imoveis-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }
    } catch (error) {
        console.error('Erro ao exportar JSON:', error);
        alert('Erro ao exportar dados');
    }
}
