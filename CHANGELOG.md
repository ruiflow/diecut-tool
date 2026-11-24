# Changelog

## [4]

### Adicionado

- **Otimização do percurso como prioridade**: cinco estratégias —
  **Proximidade+**, **Zigue-zague**, **Colunas**, **Espiral** e **Por etiqueta**.
- **Objetivos de otimização**: menos distância, menos elevações, mais rápido ou
  equilibrado, aplicados à ordenação e às melhorias locais.
- **Ponto de início** configurável: canto superior/inferior esquerdo ou direito,
  ou centro da folha.
- **Comparação de percursos**: calcula todas as estratégias e mostra corte,
  deslocamento, ligações, elevações, tempo estimado e pontuação; a melhor é
  aplicada com um clique.
- **Importação de DXF e PDF vetorial** (`Ctrl+I`): o ficheiro importado torna-se
  o documento ativo, com pré-visualização 2D/3D, simulação, comparação de
  percursos e exportação. Camadas do DXF selecionáveis; páginas do PDF
  selecionáveis; curvas de Bézier achatadas automaticamente.
- **Diálogo “Acerca de”** (`F1`) com versão, ambiente, ligações para repositório
  e releases, créditos a **OpenCode**, **DeepSeek** e **Rui Flow** e lista de
  tecnologias.
- Exportação do documento importado em PDF vetorial e DXF (layer `IMPORTADO`).
- Nova dependência: `pdfplumber` (leitura de PDF vetorial).

### Alterado

- “Manter lâmina em baixo” passa a chamar-se **“Fundir contornos”**.
- A estimativa de tempo usa velocidades de corte/deslocamento e tempo por
  elevação, apresentada na comparação e na simulação.
- A estratégia passou de botão segmentado para lista, com objetivo e início em
  listas próprias.

### Corrigido

- `_per_label_plan` chamava `_open_contour_points` com um ponto em vez de um
  índice.
- Importação de PDF respeita a orientação das coordenadas e deteta contornos
  fechados.

## [3]

### Adicionado

- Percurso de corte configurável por **proximidade** (vizinho mais próximo +
  2-opt) ou **zigue-zague** (linha a linha, com serpentina entre contornos
  encostados).
- Grafo de arestas únicas: contornos que se tocam são cortados num só percurso,
  sem passar duas vezes sobre a mesma aresta.
- Estatísticas da simulação: comprimento cortado, ligações, deslocamento e
  número de elevações.
- Guardar o percurso otimizado em DXF (layers `CORTE` e `DESLOCAMENTO`) ou PDF.

### Alterado

- Estrutura do repositório simplificada: aplicação na raiz, legado em
  `legacy/`, automação em `scripts/` e documentação em `docs/`.
- Esquema de versões normalizado para **v1, v2 e v3** (antes v1.0, v2.0 e
  v2.2), incluindo aplicação, executáveis, tags e releases.

## [2]

- Interface renovada com pré-visualização 2D/3D e órbita livre.
- Exportação DXF e PDF no tamanho exato da folha.
- Distribuição automática de colunas e fileiras.
- Formatos retângulo, oval e círculo.

## [1]

- Versão inicial: cálculo de layout e exportação de dielines.
