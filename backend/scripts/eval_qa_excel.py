"""Evaluate RAG retrieval against a local Q&A Excel workbook.

The workbook is only an evaluation source. It is not uploaded or indexed.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.embedding_client import get_embedding_client  # noqa: E402
from app.core.rag_engine import CONTEXT_TOP_K, KEYWORD_TOP_K, VECTOR_TOP_K, RAGEngine  # noqa: E402


NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
HEADER_ALIASES = {
    "question": ("留言问题", "问题", "咨询问题", "用户问题"),
    "answer": ("留言回复", "回复", "答复", "答案"),
    "basis": ("政策法规依据", "法规依据", "政策依据", "依据", "参考依据"),
    "complexity": ("复杂程度", "类型", "分类"),
}
BRANCH_COMPANY_EXPECTED_TERMS = (
    "第二十二条",
    "资质证明文件",
    "业绩情况",
    "分公司不具有法人资格",
    "民事责任由公司承担",
    "招标文件中没有规定的评标标准不得作为评审的依据",
)
REFUSAL_PATTERNS = (
    "未找到相关信息",
    "无法回答",
    "参考资料不足",
    "知识库中未找到",
)
ANSWER_STOPWORDS = {
    "可以",
    "是否",
    "根据",
    "规定",
    "有关",
    "相关",
    "情况",
    "问题",
    "进行",
    "认定",
    "提供",
    "材料",
    "采购",
}


@dataclass(frozen=True)
class QARecord:
    row_number: int
    question: str
    answer: str
    basis: str
    complexity: str


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def _col_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if not match:
        return 0
    index = 0
    for ch in match.group(1):
        index = index * 26 + ord(ch) - ord("A") + 1
    return index - 1


def _shared_strings(workbook: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("main:si", NS):
        strings.append("".join(node.text or "" for node in item.findall(".//main:t", NS)))
    return strings


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NS))

    value_node = cell.find("main:v", NS)
    if value_node is None or value_node.text is None:
        return ""

    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return value
    return value


def _sheet_rows(workbook: ZipFile, sheet_name: str, shared_strings: list[str]) -> list[tuple[int, list[str]]]:
    root = ET.fromstring(workbook.read(sheet_name))
    rows = []
    for row_node in root.findall(".//main:sheetData/main:row", NS):
        row_number = int(row_node.attrib.get("r", len(rows) + 1))
        values: dict[int, str] = {}
        for cell in row_node.findall("main:c", NS):
            values[_col_index(cell.attrib.get("r", ""))] = _cell_value(cell, shared_strings)
        if not values:
            continue
        width = max(values) + 1
        row = [_clean(values.get(index, "")) for index in range(width)]
        if any(row):
            rows.append((row_number, row))
    return rows


def _header_map(row: list[str]) -> dict[str, int]:
    normalized = [cell.lower() for cell in row]
    result = {}
    for key, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower in normalized:
                result[key] = normalized.index(alias_lower)
                break
    return result


def read_qa_records(excel_path: Path) -> list[QARecord]:
    records: list[QARecord] = []
    with ZipFile(excel_path) as workbook:
        shared_strings = _shared_strings(workbook)
        sheet_names = [
            name for name in workbook.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        ]
        for sheet_name in sheet_names:
            rows = _sheet_rows(workbook, sheet_name, shared_strings)
            for offset, (_, row) in enumerate(rows[:10]):
                headers = _header_map(row)
                if "question" not in headers or "answer" not in headers:
                    continue
                for row_number, data_row in rows[offset + 1:]:
                    question = _value(data_row, headers.get("question"))
                    answer = _value(data_row, headers.get("answer"))
                    if not question or not answer:
                        continue
                    records.append(
                        QARecord(
                            row_number=row_number,
                            question=question,
                            answer=answer,
                            basis=_value(data_row, headers.get("basis")),
                            complexity=_value(data_row, headers.get("complexity")),
                        )
                    )
                break
    return records


def _value(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index]


def _expected_terms(record: QARecord) -> tuple[str, ...]:
    if "总公司" in record.question and "分公司" in record.question:
        return BRANCH_COMPANY_EXPECTED_TERMS
    terms = []
    legal_patterns = (
        r"《[^》]+》",
        r"第[一二三四五六七八九十百0-9]+条",
        r"[\u4e00-\u9fff]{1,12}[〔\[]\d{4}[〕\]]\d+号",
        r"财政部令第\d+号",
        r"国务院令第\d+号",
    )
    for term in re.findall("|".join(legal_patterns), record.basis):
        if len(term) >= 3 and term not in terms:
            terms.append(term)
    if not terms:
        for term in re.findall(r"[\u4e00-\u9fff]{6,18}", record.basis):
            if term not in terms:
                terms.append(term)
    return tuple(terms[:8])


def _answer_keywords(record: QARecord) -> tuple[str, ...]:
    terms = []
    text = f"{record.question}\n{record.answer}\n{record.basis}"
    for term in re.findall(r"《[^》]+》|第[一二三四五六七八九十百0-9]+条|[\u4e00-\u9fff]{3,12}", text):
        term = term.strip()
        if term in ANSWER_STOPWORDS or len(term) < 3:
            continue
        if term not in terms:
            terms.append(term)
    if "总公司" in record.question and "分公司" in record.question:
        for term in ("可以认可", "应予认定", "招标文件", "没有特别要求", "总公司授权", "合同", "社保"):
            if term not in terms:
                terms.insert(0, term)
    return tuple(terms[:20])


async def _retrieval(engine: RAGEngine, question: str) -> list[dict]:
    try:
        embedding = await get_embedding_client().embed(question)
        vector_results = await engine._vector_search(embedding, top_k=VECTOR_TOP_K)
    except Exception as exc:
        print(f"[WARN] vector search failed: {exc}", file=sys.stderr)
        vector_results = []
    keyword_results = await engine._keyword_search(question, top_k=KEYWORD_TOP_K)
    fused = [
        item for item in engine._rrf_fusion(vector_results, [], keyword_results)
        if item.get("document_name")
    ]
    return await engine._expand_neighbor_chunks(fused, limit=CONTEXT_TOP_K)


async def _answer(engine: RAGEngine, question: str) -> str:
    chunks = []
    async for event, data in engine.query(question):
        if event == "answer" and data:
            chunks.append(str(data))
    return "".join(chunks)


def _classify_failure(
    expected_terms: tuple[str, ...],
    missing_terms: list[str],
    generated_answer: str,
    answer_coverage: float,
    skip_answer: bool,
) -> str:
    if missing_terms and len(missing_terms) >= max(1, len(expected_terms) // 2):
        return "召回失败"
    if missing_terms:
        return "依据不足"
    if skip_answer:
        return ""
    if any(pattern in generated_answer for pattern in REFUSAL_PATTERNS):
        return "提示词拒答"
    if generated_answer and answer_coverage < 0.25:
        return "答案偏离"
    if not generated_answer:
        return "未生成答案"
    return ""


def _source_payload(engine: RAGEngine, item: dict) -> dict:
    return {
        "document_id": item.get("document_id"),
        "document_name": item.get("document_name"),
        "page_number": item.get("page_number"),
        "chunk_index": item.get("chunk_index"),
        "source": item.get("source"),
        "retrieval_sources": item.get("retrieval_sources", []),
        "score": item.get("score", 0),
        "distance": item.get("distance"),
        "keyword_hits": item.get("keyword_hits", 0),
        "keyword_term_count": item.get("keyword_term_count", 0),
        "rrf_score": round(float(item.get("score", 0)), 6),
        "display_score": round(float(engine._display_score(item) or 0), 6),
        "vector_similarity": item.get("vector_similarity"),
        "keyword_score": item.get("keyword_score", 0),
        "matched_terms": item.get("matched_terms", []),
        "content": item.get("content", ""),
    }


async def _evaluate_record(engine: RAGEngine, record: QARecord, top_n: int, skip_answer: bool) -> dict:
    results = await _retrieval(engine, record.question)
    top_results = results[:top_n]
    combined = "\n".join(
        f"{item.get('document_name', '')}\n{item.get('content', '')}"
        for item in top_results
    )
    expected_terms = _expected_terms(record)
    found = [term for term in expected_terms if term in combined]
    missing = [term for term in expected_terms if term not in combined]
    generated_answer = "" if skip_answer else await _answer(engine, record.question)
    answer_terms = _answer_keywords(record)
    answer_found = [term for term in answer_terms if term in generated_answer]
    answer_coverage = len(answer_found) / max(len(answer_terms), 1)
    refused = any(pattern in generated_answer for pattern in REFUSAL_PATTERNS)
    failure_type = _classify_failure(expected_terms, missing, generated_answer, answer_coverage, skip_answer)

    return {
        "row_number": record.row_number,
        "question": record.question,
        "expected_answer": record.answer,
        "expected_basis": record.basis,
        "complexity": record.complexity,
        "expected_terms": list(expected_terms),
        "found_terms": found,
        "missing_terms": missing,
        "basis_recall": len(found) / max(len(expected_terms), 1),
        "answer_keywords": list(answer_terms),
        "answer_found_keywords": answer_found,
        "answer_keyword_coverage": answer_coverage,
        "refused": refused,
        "failure_type": failure_type,
        "generated_answer": generated_answer,
        "top_results": [_source_payload(engine, item) for item in top_results],
    }


def _print_record(record: QARecord) -> None:
    print(f"Excel row: {record.row_number}")
    print(f"Question: {record.question}")
    print(f"Expected answer: {record.answer}")
    print(f"Expected basis: {record.basis}")
    if record.complexity:
        print(f"Complexity: {record.complexity}")


def _print_results(engine: RAGEngine, results: list[dict], top_n: int, expected_terms: tuple[str, ...]) -> None:
    combined = "\n".join(
        f"{item.get('document_name', '')}\n{item.get('content', '')}"
        for item in results[:top_n]
    )
    found = [term for term in expected_terms if term in combined]
    missing = [term for term in expected_terms if term not in combined]
    print("\nRetrieval coverage:")
    print(json.dumps({"found": found, "missing": missing}, ensure_ascii=False, indent=2))
    print(f"\nTop {top_n} retrieval results:")
    for index, item in enumerate(results[:top_n], start=1):
        print(
            f"{index}. doc={item.get('document_id')} chunk={item.get('chunk_index')} "
            f"score={item.get('score', 0):.4f} display={engine._display_score(item):.3f} "
            f"sources={item.get('retrieval_sources')} name={item.get('document_name')}"
        )
        print((item.get("content") or "").replace("\n", " ")[:320])


def _summarize(evaluations: list[dict], skip_answer: bool) -> dict:
    total = len(evaluations)
    if not total:
        return {
            "total": 0,
            "answerable_rate": 0,
            "refusal_rate": 0,
            "basis_recall_rate": 0,
            "answer_keyword_coverage_rate": 0,
            "failures": [],
        }
    failures = [
        {
            "row_number": item["row_number"],
            "failure_type": item["failure_type"],
            "missing_terms": item["missing_terms"],
            "basis_recall": item["basis_recall"],
            "answer_keyword_coverage": item["answer_keyword_coverage"],
            "question": item["question"],
        }
        for item in evaluations
        if item["failure_type"]
    ]
    return {
        "total": total,
        "answerable_rate": sum(1 for item in evaluations if not item["refused"]) / total if not skip_answer else None,
        "refusal_rate": sum(1 for item in evaluations if item["refused"]) / total if not skip_answer else None,
        "basis_recall_rate": sum(item["basis_recall"] for item in evaluations) / total,
        "answer_keyword_coverage_rate": (
            sum(item["answer_keyword_coverage"] for item in evaluations) / total if not skip_answer else None
        ),
        "failure_count": len(failures),
        "failures": failures,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", required=True, help="Path to the local QA workbook")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--row", type=int, help="Excel row number to evaluate")
    mode.add_argument("--all", action="store_true", help="Evaluate all valid question/answer rows")
    parser.add_argument("--top-n", type=int, default=8)
    parser.add_argument("--skip-answer", action="store_true", help="Only print retrieval results")
    parser.add_argument("--output", help="Write a JSON report to this path")
    args = parser.parse_args()

    records = read_qa_records(Path(args.excel))
    engine = RAGEngine()

    if args.all:
        selected_records = records
    else:
        row_number = args.row or 2
        record = next((item for item in records if item.row_number == row_number), None)
        if record is None:
            raise SystemExit(f"Row {row_number} was not found in {args.excel}")
        selected_records = [record]

    evaluations = []
    for index, record in enumerate(selected_records, start=1):
        if args.all:
            print(f"[{index}/{len(selected_records)}] row {record.row_number}: {record.question[:80]}")
        evaluation = await _evaluate_record(engine, record, args.top_n, args.skip_answer)
        evaluations.append(evaluation)

        if not args.all:
            _print_record(record)
            _print_results(engine, evaluation["top_results"], args.top_n, _expected_terms(record))
            if not args.skip_answer:
                print("\nGenerated answer:")
                print(evaluation["generated_answer"])

    summary = _summarize(evaluations, args.skip_answer)
    report = {"summary": summary, "items": evaluations}

    if args.all:
        print("\nSummary:")
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nReport written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
