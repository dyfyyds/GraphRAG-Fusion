"""
Generate 3D Semantic Cosmos data from concept text.

Input JSON format:
[
  {"id": "node-1", "name": "意识", "description": "主体对自身和外界的觉察", "weight": 9},
  {"id": "node-2", "name": "正义", "description": "社会公平与权利秩序", "weight": 8}
]

Usage:
  python generate_cosmos.py --input concepts.json --output cosmos_data.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import umap
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity


CATEGORIES: dict[str, dict[str, str]] = {
    "Society": {"label": "社会", "color": "#FACC15", "anchor": "社会 制度 公平 权利 规则 群体 组织"},
    "Self": {"label": "自我", "color": "#7DD3FC", "anchor": "自我 意识 身份 记忆 主体 个人 心智"},
    "Nature": {"label": "自然", "color": "#86EFAC", "anchor": "自然 生命 生态 海洋 森林 时间 环境"},
    "Emotion": {"label": "情绪", "color": "#F9A8D4", "anchor": "情绪 爱 恐惧 希望 愤怒 感受 亲密"},
    "Abstract": {"label": "抽象", "color": "#C4B5FD", "anchor": "抽象 真理 自由 意义 逻辑 存在 哲学"},
    "Knowledge": {"label": "知识", "color": "#93C5FD", "anchor": "知识 语言 算法 模型 学习 科学 信息"},
    "Art": {"label": "艺术", "color": "#FB7185", "anchor": "艺术 音乐 诗歌 图像 审美 表达 风格"},
    "Creation": {"label": "创造", "color": "#5EEAD4", "anchor": "创造 设计 代码 发明 构建 工程 产品"},
}


def load_items(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "nodes" in data:
        data = data["nodes"]
    if not isinstance(data, list):
        raise ValueError("Input must be a list of nodes or an object with a nodes field.")
    return data


def normalize_coordinates(points: np.ndarray, scale: float = 92.0) -> np.ndarray:
    """Scale UMAP coordinates into roughly [-100, 100] without destroying shape."""
    centered = points - points.mean(axis=0, keepdims=True)
    max_abs = np.abs(centered).max()
    if max_abs < 1e-9:
        return centered
    return centered / max_abs * scale


def assign_categories(
    node_embeddings: np.ndarray,
    category_embeddings: np.ndarray,
    category_names: list[str],
) -> list[str]:
    """
    Assign each node to the closest macro semantic category.

    KMeans is still fitted so future callers can inspect cluster structure, but
    final labels use anchor similarity to keep category names stable across runs.
    """
    cluster_count = min(len(category_names), len(node_embeddings))
    if cluster_count >= 2:
        KMeans(n_clusters=cluster_count, n_init="auto", random_state=42).fit(node_embeddings)

    sims = cosine_similarity(node_embeddings, category_embeddings)
    return [category_names[int(np.argmax(row))] for row in sims]


def build_cosmos(input_path: Path, output_path: Path, model_name: str) -> None:
    items = load_items(input_path)
    texts = [
        f"{item.get('name', '')}。{item.get('description', '')}".strip()
        for item in items
    ]

    model = SentenceTransformer(model_name)
    node_embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    category_names = list(CATEGORIES)
    category_texts = [CATEGORIES[name]["anchor"] for name in category_names]
    category_embeddings = model.encode(category_texts, normalize_embeddings=True)

    reducer = umap.UMAP(
        n_components=3,
        n_neighbors=max(2, min(12, len(items) - 1)),
        min_dist=0.18,
        metric="cosine",
        random_state=42,
    )
    coords = normalize_coordinates(reducer.fit_transform(node_embeddings))
    categories = assign_categories(node_embeddings, category_embeddings, category_names)

    nodes: list[dict[str, Any]] = []
    for index, item in enumerate(items):
      category = categories[index]
      weight = item.get("weight", 5)
      try:
          weight = int(weight)
      except (TypeError, ValueError):
          weight = 5

      nodes.append({
          "id": item.get("id") or f"node-{index + 1}",
          "name": item.get("name") or f"概念{index + 1}",
          "category": category,
          "weight": max(1, min(10, weight)),
          "description": item.get("description", ""),
          "x": round(float(coords[index, 0]), 3),
          "y": round(float(coords[index, 1]), 3),
          "z": round(float(coords[index, 2]), 3),
      })

    payload = {
        "schema_version": "1.0",
        "name": "Semantic Cosmos",
        "categories": {
            name: {"label": meta["label"], "color": meta["color"]}
            for name, meta in CATEGORIES.items()
        },
        "nodes": nodes,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Semantic Cosmos 3D graph data.")
    parser.add_argument("--input", required=True, type=Path, help="Input concept JSON file.")
    parser.add_argument("--output", required=True, type=Path, help="Output cosmos_data.json path.")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()
    build_cosmos(args.input, args.output, args.model)


if __name__ == "__main__":
    main()
