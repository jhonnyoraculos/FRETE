# FRETE

Calculadora de frete JR em formato web, pronta para publicar no GitHub Pages.

## Publicacao no GitHub Pages

1. Envie os arquivos para este repositorio.
2. No GitHub, abra `Settings > Pages`.
3. Em `Build and deployment`, selecione `Deploy from a branch`.
4. Escolha a branch `main` e a pasta `/ (root)`.

## Atualizacao da base

Quando as planilhas locais mudarem, gere novamente o arquivo usado pelo site:

```powershell
python build_web_data.py
```

Depois disso, envie o `web-data.js` atualizado para o GitHub.
