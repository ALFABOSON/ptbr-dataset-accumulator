# 🇧🇷 Acumulador de Conteúdo PT-BR para Datasets

Sistema automático para garimpar conteúdo em português brasileiro da web e salvar no Google Drive, construindo um dataset de alta qualidade para NLP, RAG e fine-tuning de LLMs.

## ✨ Funcionalidades

- **Garimpa** notícias e textos de fontes confiáveis em PT-BR (G1, Folha, BBC Brasil etc.)
- Extrai texto limpo com `trafilatura` + fallback
- Filtra automaticamente por idioma (só português brasileiro)
- Evita duplicatas
- Salva em formato JSONL particionado (pronto para datasets)
- Gera relatórios diários automáticos
- Fácil de usar no Google Colab (gratuito)
- Preparado para automação total com GitHub Actions

## 🚀 Início Rápido (Google Colab - Recomendado)

1. Acesse [Google Colab](https://colab.research.google.com)
2. Crie um novo notebook
3. Cole todo o conteúdo do arquivo `acumulador_ptbr_dataset.py`
4. Rode a célula
5. Autorize o acesso ao seu Google Drive quando solicitado

O sistema vai criar automaticamente a pasta `Datasets_PTBR` no seu Drive com:
- `raw_data/` → arquivos JSONL com os textos
- `state/` → controle de URLs já coletadas
- `reports/` → resumos diários

## 🔧 Configuração para Automação Total (GitHub Actions + GCP)

Para rodar todos os dias automaticamente sem precisar abrir o Colab:

### Passo 1: Crie uma Service Account no Google Cloud

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto ou use um existente
3. Ative a API do Google Drive: `APIs & Services > Library > Google Drive API > Enable`
4. Va em `IAM & Admin > Service Accounts > Create Service Account`
5. Dê um nome (ex: `ptbr-dataset-accumulator`)
6. Crie a conta e depois clique em "Keys" > "Add Key" > "Create new key" > JSON
7. Baixe o arquivo JSON (guarde com segurança!)

### Passo 2: Compartilhe a pasta do Drive com a Service Account

1. No Google Drive, abra a pasta `Datasets_PTBR`
2. Clique em "Compartilhar"
3. Cole o e-mail da Service Account (está no JSON baixado, campo `client_email`)
4. Dê permissão de **Editor**

### Passo 3: Configure no GitHub

1. No seu repositório GitHub, vá em **Settings > Secrets and variables > Actions**
2. Crie um novo secret chamado `GCP_SERVICE_ACCOUNT_KEY`
3. Cole o conteúdo completo do arquivo JSON da Service Account

### Passo 4: O workflow já está configurado

O arquivo `.github/workflows/daily_accumulator.yml` está pronto. Ele roda todo dia às 6h da manhã (horário de Brasília) e executa o script.

> **Nota**: Para a versão completa em CI, é necessário adaptar ligeiramente o script para usar autenticação via Service Account em vez de `drive.mount`. Posso fazer essa versão se pedir.

## 🧠 Limpeza e Qualidade do Dataset

Após acumular vários dias de dados, rode o script `limpar_e_dedup_dataset.py` para:
- Remover duplicatas
- Limpar textos
- Gerar versão consolidada em Parquet ou JSONL único

## 📁 Estrutura do Projeto

```
ptbr-dataset-accumulator/
├── acumulador_ptbr_dataset.py   # Script principal (Colab)
├── limpar_e_dedup_dataset.py     # Script de limpeza
├── requirements.txt
├── .github/workflows/          # Automação
├── README.md
└── setup/
```

## 🚨 Fontes Atuais

- G1 (geral, Brasil, Tecnologia)
- Folha de S.Paulo (Em cima da hora, Política, Mundo)
- BBC News Brasil

Adicione mais fontes facilmente editando o dicionário `SOURCES` no script.

## ⚠️ Avisos Importantes

- Respeite os termos de serviço dos sites e `robots.txt`
- Use com moderação (tem `sleep` entre requisições)
- Para datasets comerciais ou de larga escala, considere fontes abertas ou APIs oficiais

## 🙏 Contribua

Pull requests são bem-vindos! Adicionar novas fontes, melhorar a extração de texto ou adicionar filtros de qualidade são ótimas contribuições.

---

Feito com ❤️ por Grok para construir datasets brasileiros de qualidade.