#!/usr/bin/env python3
"""
Script de Limpeza e Deduplicação do Dataset PT-BR
==================================================

Uso:
  python limpar_e_dedup_dataset.py --input /caminho/raw_data --output /caminho/clean

Funcionalidades:
- Carrega todos os JSONL
- Remove duplicatas por URL e por similaridade básica de texto
- Limpa textos (espaços extras, etc.)
- Gera relatório de qualidade
- Salva em formato consolidado (JSONL ou Parquet)
"""

import os
import json
import argparse
from collections import defaultdict
import hashlib

import pandas as pd


def load_all_jsonl(input_dir: str) -> pd.DataFrame:
    """Carrega todos os arquivos .jsonl de um diretório recursivamente."""
    all_records = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.jsonl'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            all_records.append(json.loads(line))
    return pd.DataFrame(all_records)


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicatas por URL e hash do texto."""
    initial_count = len(df)
    
    # Por URL (exato)
    df = df.drop_duplicates(subset=['url'], keep='first')
    
    # Por hash do texto (similaridade exata)
    df['text_hash'] = df['text'].apply(lambda x: hashlib.md5(str(x).encode('utf-8')).hexdigest())
    df = df.drop_duplicates(subset=['text_hash'], keep='first')
    df = df.drop(columns=['text_hash'])
    
    removed = initial_count - len(df)
    print(f"Duplicatas removidas: {removed} ({removed/initial_count*100:.1f}%)")
    return df


def clean_text(text: str) -> str:
    """Limpeza básica de texto."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    # Remove múltiplos espaços e quebras de linha excessivas
    text = ' '.join(text.split())
    return text


def main():
    parser = argparse.ArgumentParser(description="Limpa e deduplica o dataset PT-BR")
    parser.add_argument("--input", required=True, help="Pasta com os JSONL raw (ex: Datasets_PTBR/raw_data)")
    parser.add_argument("--output", required=True, help="Pasta de saída para o dataset limpo")
    parser.add_argument("--format", choices=["jsonl", "parquet"], default="jsonl", help="Formato de saída")
    args = parser.parse_args()

    print("Carregando dados...")
    df = load_all_jsonl(args.input)
    print(f"Total de registros carregados: {len(df)}")

    print("Removendo duplicatas...")
    df = remove_duplicates(df)

    print("Limpando textos...")
    df['text'] = df['text'].apply(clean_text)
    df = df[df['text'].str.len() > 200]  # Remove textos muito curtos após limpeza

    os.makedirs(args.output, exist_ok=True)

    if args.format == "jsonl":
        output_file = os.path.join(args.output, "dataset_ptbr_clean.jsonl")
        df.to_json(output_file, orient='records', lines=True, force_ascii=False)
    else:
        output_file = os.path.join(args.output, "dataset_ptbr_clean.parquet")
        df.to_parquet(output_file, index=False)

    print(f"\n✅ Dataset limpo salvo em: {output_file}")
    print(f"Total final: {len(df)} artigos")
    print(f"Fontes: {df['source'].value_counts().to_dict()}")

if __name__ == "__main__":
    main()
