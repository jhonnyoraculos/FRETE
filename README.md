# FRETE

Calculadora de frete JR em Streamlit, usando as planilhas locais da pasta `data/`.

## Rodar localmente

1. Instale as dependencias:

```powershell
pip install -r requirements.txt
```

2. Inicie o app:

```powershell
streamlit run streamlit_app.py
```

## Como os dados funcionam

- O app le as planilhas Excel diretamente da pasta `data/`.
- Se os arquivos mudarem enquanto o Streamlit estiver aberto, use o botao `Recarregar planilhas` na barra lateral.
- O arquivo `placas_permitidas.txt` continua sendo usado para limitar as placas exibidas na interface.

## Publicar no Streamlit Community Cloud

Para funcionar em deploy remoto, as planilhas da pasta `data/` precisam estar acessiveis ao servidor:

- opcao 1: incluir a pasta `data/` no repositorio
- opcao 2: buscar os arquivos de outra fonte acessivel pelo app

Do jeito atual, a pasta `data/` esta ignorada no Git para evitar publicar planilhas automaticamente.
