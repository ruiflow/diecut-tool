# Changelog

## [2.2]

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

## [2.0]

- Interface renovada com pré-visualização 2D/3D e órbita livre.
- Exportação DXF e PDF no tamanho exato da folha.
- Distribuição automática de colunas e fileiras.
- Formatos retângulo, oval e círculo.

## [1.0]

- Versão inicial: cálculo de layout e exportação de dielines.
