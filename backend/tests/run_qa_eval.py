"""四大问题专项问答评测脚本（容器内运行，直接驱动 RAGEngine，绕过 HTTP/限流）。

用法:
    docker exec -w /app rag-backend python tests/run_qa_eval.py
    docker exec -w /app rag-backend python tests/run_qa_eval.py --filter 问题1
    docker exec -w /app rag-backend python tests/run_qa_eval.py --cases tests/qa_eval_cases.json

输出: 逐用例 PASS/FAIL 与指标，并写入 tests/qa_eval_results.json
"""
import argparse
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")

from app.core.rag_engine import RAGEngine  # noqa: E402


async def run_case(engine: RAGEngine, case: dict) -> dict:
    question = case["question"]
    result = {
        "id": case["id"],
        "issue": case["issue"],
        "question": question,
    }

    async def one_round() -> tuple[list, str, float, float]:
        t0 = time.time()
        sources, answer, t_retrieval = [], "", None
        async for event_type, data in engine.query(question):
            if event_type == "sources":
                sources = data or []
                t_retrieval = time.time() - t0
            elif event_type == "answer" and data:
                answer += data
        return sources, answer, (t_retrieval if t_retrieval is not None else time.time() - t0), time.time() - t0

    sources, answer, t_retrieval, t_total = await one_round()
    result["retrieval_seconds"] = round(t_retrieval, 2)
    result["total_seconds"] = round(t_total, 2)
    result["answer_preview"] = answer[:300]

    # 1) 关键词命中
    expected = case.get("expected_keywords", [])
    hits = [kw for kw in expected if kw in answer]
    missing = [kw for kw in expected if kw not in answer]
    ratio_required = float(case.get("min_hit_ratio", 0.6))
    keyword_pass = len(hits) >= max(1, int(len(expected) * ratio_required + 0.999)) if expected else True
    result["keyword_hits"] = hits
    result["keyword_missing"] = missing
    result["keyword_pass"] = keyword_pass

    # 2) 引用文档校验
    expected_docs = case.get("expected_doc_any") or []
    if expected_docs:
        doc_names = [s.get("document_name") or "" for s in sources]
        doc_pass = any(exp in name for exp in expected_docs for name in doc_names)
    else:
        doc_pass = True
    result["doc_pass"] = doc_pass
    result["source_docs"] = sorted({s.get("document_name") or "" for s in sources})[:6]

    # 3) 层级面包屑校验（问题2）：引用分块内容应携带【所属章节：...】
    if case.get("check_breadcrumb"):
        crumb_pass = any("【所属章节" in (s.get("chunk_content") or "") for s in sources)
        result["breadcrumb_pass"] = crumb_pass
    else:
        crumb_pass = True

    # 4) 图谱多跳路径探测（问题1）：直接调用 _graph_search 数路径条数
    if case.get("probe_graph"):
        try:
            graph_items = await engine._graph_search(question)
            paths = [item for item in graph_items if item.get("path")]
            entities = [item for item in graph_items if not item.get("path")]
            result["graph_entities"] = len(entities)
            result["graph_paths"] = len(paths)
            result["graph_path_samples"] = [item.get("content", "")[:80] for item in paths[:3]]
        except Exception as exc:  # 探测失败不判负
            result["graph_probe_error"] = str(exc)[:200]

    # 5) 重复提问（问题4）：第二次应命中向量缓存，检索更快
    if case.get("repeat"):
        _, _, t_retrieval2, _ = await one_round()
        result["retrieval_seconds_2nd"] = round(t_retrieval2, 2)
        result["cache_speedup"] = round(t_retrieval - t_retrieval2, 2)

    result["passed"] = bool(keyword_pass and doc_pass and crumb_pass)
    return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="tests/qa_eval_cases.json")
    parser.add_argument("--filter", default="", help="按 issue 关键字过滤，如 问题1")
    args = parser.parse_args()

    with open(args.cases, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    if args.filter:
        cases = [c for c in cases if args.filter in c.get("issue", "") or args.filter in c.get("id", "")]

    engine = RAGEngine()
    results = []
    for case in cases:
        print(f"\n=== {case['id']} [{case['issue']}] ===")
        print(f"Q: {case['question'][:60]}...")
        try:
            r = await run_case(engine, case)
        except Exception as exc:
            r = {"id": case["id"], "issue": case["issue"], "passed": False, "error": str(exc)[:300]}
        results.append(r)
        status = "PASS" if r.get("passed") else "FAIL"
        print(f"[{status}] 检索{r.get('retrieval_seconds', '?')}s 总耗时{r.get('total_seconds', '?')}s "
              f"关键词{len(r.get('keyword_hits', []))}/{len(r.get('keyword_hits', [])) + len(r.get('keyword_missing', []))} "
              f"文档{'√' if r.get('doc_pass') else '×'}")
        if r.get("keyword_missing"):
            print(f"  缺失关键词: {r['keyword_missing']}")
        if "breadcrumb_pass" in r:
            print(f"  面包屑: {'√' if r['breadcrumb_pass'] else '×'}")
        if "graph_paths" in r:
            print(f"  图谱: {r.get('graph_entities', 0)} 实体 / {r.get('graph_paths', 0)} 条推理路径")
            for s in r.get("graph_path_samples", []):
                print(f"    {s}")
        if "retrieval_seconds_2nd" in r:
            print(f"  二次检索: {r['retrieval_seconds_2nd']}s (缓存提速 {r['cache_speedup']}s)")

    passed = sum(1 for r in results if r.get("passed"))
    print(f"\n========== 汇总: {passed}/{len(results)} PASS ==========")
    with open("tests/qa_eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("结果已写入 tests/qa_eval_results.json")


if __name__ == "__main__":
    asyncio.run(main())
