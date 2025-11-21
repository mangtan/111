"""
文档上传/文本抽取（基础版）
支持：PDF（可编辑），TXT直读。扫描件PDF后续可接OCR。
"""
from __future__ import annotations

import os
from typing import Tuple, List

def _normalize_space(s: str) -> str:
    return "\n".join(line.strip() for line in s.splitlines() if line.strip())

def split_into_chunks(text: str, chunk_chars: int = 800, overlap: int = 120) -> List[str]:
    """将长文本按字符数切块，尽量在段落边界切分。"""
    t = _normalize_space(text)
    paras = t.split("\n")
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for p in paras:
        if cur_len + len(p) + 1 <= chunk_chars:
            cur.append(p); cur_len += len(p) + 1
        else:
            if cur:
                chunks.append("\n".join(cur))
            # 处理重叠：将末尾一部分带入下一块
            if overlap > 0 and chunks:
                tail = chunks[-1][-overlap:]
                cur = [tail, p]
                cur_len = len(tail) + len(p) + 1
            else:
                cur = [p]; cur_len = len(p)
    if cur:
        chunks.append("\n".join(cur))
    return chunks

def rag_select(text: str, queries: List[str], per_query: int = 3, max_chars: int = 6000) -> str:
    """在单文档内做简易RAG：按TF-IDF在chunk级别选与查询最相关的片段，合并返回。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    chunks = split_into_chunks(text, chunk_chars=800, overlap=120)
    if not chunks:
        return text[:max_chars]
    vec = TfidfVectorizer(max_features=768)
    X = vec.fit_transform(chunks)
    selected_idx: List[int] = []
    import numpy as np
    for q in queries:
        qv = vec.transform([q])
        sims = (X @ qv.T).toarray().ravel()
        top = np.argsort(sims)[-per_query:][::-1]
        for i in top:
            if i not in selected_idx:
                selected_idx.append(int(i))
    # 组装文本，保留顺序
    selected_idx.sort()
    out_parts: List[str] = []
    for k, i in enumerate(selected_idx, 1):
        part = chunks[i]
        out_parts.append(f"【片段{k}】\n{part}\n")
        if sum(len(p) for p in out_parts) >= max_chars:
            break
    return "\n".join(out_parts)[:max_chars]


def extract_text(file_path: str) -> Tuple[str, int]:
    """从文件中抽取文本（基础版）。返回(text, pages)。
    - PDF: 使用 pdfminer.six
    - TXT: 直接读取
    其他类型暂不支持。
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(), 1
    if ext == '.pdf':
        try:
            from pdfminer.high_level import extract_text as pdf_extract_text
            from pdfminer.pdfpage import PDFPage
            # 页数
            with open(file_path, 'rb') as f:
                pages = sum(1 for _ in PDFPage.get_pages(f))
            text = pdf_extract_text(file_path) or ''
            return text, int(pages or 0)
        except Exception as e:
            raise RuntimeError(f'PDF文本提取失败: {e}')
    raise RuntimeError(f'不支持的文件类型: {ext}')
