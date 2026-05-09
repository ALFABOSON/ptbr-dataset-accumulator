#!/usr/bin/env python3
"""
Acumulador de Conteúdo em Português Brasileiro
================================================
Objetivo: Garimpar conteúdo de qualidade da web (foco em PT-BR) e salvar no Google Drive
          para construir um DATASET para NLP / LLMs.

Uso principal: Google Colab (recomendado)
Alternativa: Rodar localmente (comente a parte do drive.mount e ajuste paths)

Autor: Grok + Usuário
Data: Maio 2026
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Set, Optional

import feedparser
import trafilatura
import pandas as pd
from langdetect import detect, DetectorFactory, LangDetectException
import requests
from bs4 import BeautifulSoup

# ==================== CONFIGURAÇÕES ====================
DetectorFactory.seed = 0

# Caminho base no Google Drive (mude se quiser)
BASE_DRIVE_PATH = "/content/drive/MyDrive/Datasets_PTBR"

# Fontes RSS confiáveis em PT-BR (adicione/remova conforme necessário)
SOURCES = {
    "g1_geral": "https://g1.globo.com/dynamo/rss2.xml",
    "g1_brasil": "https://g1.globo.com/dynamo/brasil/rss2.xml",
    "g1_tecnologia": "https://g1.globo.com/dynamo/tecnologia/rss2.xml",
    "folha_emcimadahora": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
    "folha_politica": "https://feeds.folha.uol.com.br/poder/rss091.xml",
    "folha_mundo": "https://feeds.folha.uol.com.br/mundo/rss091.xml",
    "bbc_brasil": "https://feeds.bbci.co.uk/portuguese/rss.xml",
    # "agencia_brasil": "https://agenciabrasil.ebc.com.br/rss",  # descomente e teste
}

# Parâmetros de qualidade
MIN_WORD_COUNT = 120          # Mínimo de palavras para considerar o texto útil
MAX_ARTICLES_PER_SOURCE = 50  # Limite por execução (evita sobrecarga)
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 2.0  # Segundos - seja educado com os servidores

# User-Agent educado
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PTBR-Dataset-Accumulator/1.0; +https://github.com/seu-usuario/acumulador-ptbr)"
}

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AcumuladorPTBR")


def is_running_in_colab() -> bool:
    try:
        import google.colab
        return True
    except ImportError:
        return False


def setup_drive() -> str:
    """Monta o Google Drive e retorna o caminho base."""
    if is_running_in_colab():
        from google.colab import drive
        drive.mount('/content/drive')
        logger.info("Google Drive montado com sucesso.")
    else:
        logger.warning("Não está no Colab. Usando pasta local './Datasets_PTBR' como fallback.")
    
    base = BASE_DRIVE_PATH if is_running_in_colab() else "./Datasets_PTBR"
    os.makedirs(base, exist_ok=True)
    for sub in ["raw_data", "state", "reports"]:
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    return base


def get_seen_urls(state_path: str) -> Set[str]:
    path = os.path.join(state_path, "seen_urls.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_urls(seen: Set[str], state_path: str):
    path = os.path.join(state_path, "seen_urls.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen)), f, ensure_ascii=False, indent=2)
    logger.info(f"Estado salvo: {len(seen)} URLs vistas.")


def extract_clean_text(url: str) -> Optional[str]:
    """
    Tenta extrair o texto principal do artigo usando trafilatura (melhor qualidade).
    Fallback simples com BeautifulSoup se necessário.
    """
    try:
        # Método principal: trafilatura
        downloaded = trafilatura.fetch_url(url, timeout=REQUEST_TIMEOUT)
        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                include_formatting=False,
                favor_precision=True
            )
            if text and len(text.strip()) > 200:
                return text.strip()
    except Exception as e:
        logger.debug(f"trafilatura falhou em {url}: {e}")

    # Fallback simples
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            # Remove scripts, styles, etc.
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
            if len(text) > 300:
                return text.strip()
    except Exception as e:
        logger.debug(f"Fallback BeautifulSoup falhou em {url}: {e}")

    return None


def process_source(name: str, rss_url: str, seen_urls: Set[str]) -> List[Dict]:
    """Processa uma fonte RSS e retorna lista de artigos novos."""
    logger.info(f"Processando fonte: {name}")
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        logger.warning(f"Feed com problemas de parsing: {name}")
    
    new_articles = []
    count = 0

    for entry in feed.entries:
        if count >= MAX_ARTICLES_PER_SOURCE:
            break

        link = entry.get("link", "").strip()
        if not link or link in seen_urls:
            continue

        title = entry.get("title", "").strip()
        published = entry.get("published", entry.get("updated", ""))

        # Extrai texto completo
        full_text = extract_clean_text(link)
        if not full_text:
            # Fallback para summary do RSS
            full_text = entry.get("summary", "") or entry.get("description", "")
            if len(full_text) < 150:
                continue

        # Detecta idioma
        try:
            sample = full_text[:800]
            lang = detect(sample)
            if lang != "pt":
                continue
        except (LangDetectException, Exception):
            continue

        word_count = len(full_text.split())
        if word_count < MIN_WORD_COUNT:
            continue

        article = {
            "id": hashlib.md5(link.encode("utf-8")).hexdigest()[:16],
            "source": name,
            "url": link,
            "title": title,
            "published": published,
            "text": full_text,
            "word_count": word_count,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }

        new_articles.append(article)
        seen_urls.add(link)
        count += 1
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    logger.info(f"  → {len(new_articles)} artigos novos de {name}")
    return new_articles


def save_articles(articles: List[Dict], base_path: str):
    """Salva artigos em arquivos JSONL particionados por data e fonte."""
    if not articles:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    raw_dir = os.path.join(base_path, "raw_data")
    os.makedirs(raw_dir, exist_ok=True)

    # Agrupa por fonte
    by_source = {}
    for art in articles:
        by_source.setdefault(art["source"], []).append(art)

    for source, arts in by_source.items():
        filename = f"{source}_{today}.jsonl"
        filepath = os.path.join(raw_dir, filename)
        
        with open(filepath, "a", encoding="utf-8") as f:
            for art in arts:
                f.write(json.dumps(art, ensure_ascii=False) + "\n")
        
        logger.info(f"Salvo: {len(arts)} artigos em {filename}")


def generate_daily_report(articles: List[Dict], base_path: str):
    """Gera um relatório simples do dia."""
    if not articles:
        return

    report_dir = os.path.join(base_path, "reports")
    os.makedirs(report_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    
    df = pd.DataFrame(articles)
    summary = {
        "date": today,
        "total_articles": len(articles),
        "by_source": df.groupby("source").size().to_dict(),
        "total_words": int(df["word_count"].sum()),
        "avg_words_per_article": round(df["word_count"].mean(), 1),
        "sources_used": list(df["source"].unique())
    }

    report_path = os.path.join(report_dir, f"report_{today}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"Relatório do dia salvo em: {report_path}")
    logger.info(f"Resumo: {summary['total_articles']} artigos | {summary['total_words']} palavras totais")


def main():
    logger.info("=" * 60)
    logger.info("ACUMULADOR DE CONTEÚDO PT-BR - INICIANDO")
    logger.info("=" * 60)

    base_path = setup_drive()
    state_path = os.path.join(base_path, "state")
    seen_urls = get_seen_urls(state_path)

    all_new_articles = []

    for name, url in SOURCES.items():
        try:
            articles = process_source(name, url, seen_urls)
            all_new_articles.extend(articles)
        except Exception as e:
            logger.error(f"Erro ao processar {name}: {e}")

    if all_new_articles:
        save_articles(all_new_articles, base_path)
        generate_daily_report(all_new_articles, base_path)
        logger.info(f"\n✅ SUCESSO! {len(all_new_articles)} novos artigos adicionados ao dataset.")
    else:
        logger.info("\nNenhum artigo novo encontrado nesta execução.")

    save_seen_urls(seen_urls, state_path)
    logger.info("Execução finalizada com sucesso.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
