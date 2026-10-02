#!/bin/sh
# Teste de fumaça contra o ambiente no ar (docker compose up), com os dados reais do IBGE.
# Uso: sh tests/smoke.sh [url-da-api] [url-do-painel]
set -eu

API="${1:-http://localhost:8000}"
PAINEL="${2:-http://localhost:8501}"
FALHAS=0

verificar() {
    if [ "$2" = "$3" ]; then echo "  ok     $1 ($3)"; else echo "  FALHOU $1: esperado $2, obtido $3"; FALHAS=$((FALHAS + 1)); fi
}
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
contem() { curl -s "$1" | grep -q "$2" && echo sim || echo não; }

echo "Smoke test: API $API · painel $PAINEL"
verificar "health check" 200 "$(status "$API/health")"
verificar "documentação OpenAPI" 200 "$(status "$API/openapi.json")"
verificar "dados de GO, MT e MS carregados" sim "$(contem "$API/metadados" '"ufs":\["GO","MS","MT"\]')"
verificar "ranking de bovinos em GO" sim "$(contem "$API/ufs/GO/ranking?limite=3" '"posicao":1')"
verificar "evolução com variação anual" sim "$(contem "$API/ufs/MT/evolucao" '"variacao_percentual"')"
verificar "busca sem acento" sim "$(contem "$API/municipios?nome=goiania" 'Goiânia')"
verificar "UF inválida" 422 "$(status "$API/ufs/XX/ranking")"
verificar "painel no ar" 200 "$(status "$PAINEL/_stcore/health")"

[ "$FALHAS" -eq 0 ] || { echo "$FALHAS verificação(ões) falharam."; exit 1; }
echo "Tudo certo."
