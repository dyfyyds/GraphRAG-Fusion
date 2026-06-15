#!/usr/bin/env bash
# 批量上传测试语料（遵守上传限流 10次/分钟）
# 用法: bash scripts/upload_corpus.sh [目录1] [目录2] ...
# 默认上传企业 PDF + 制度文件 md 两个目录
set -uo pipefail

API="${API:-http://localhost:8080}"
USER="${RAG_USER:-admin}"
PASS="${RAG_PASS:-admin123}"
BATCH=9          # 每批数量(留1个余量防止边界429)
BATCH_SLEEP=62   # 批间隔秒数

DIRS=("$@")
if [ ${#DIRS[@]} -eq 0 ]; then
  DIRS=("D:/obsidian/RAG/RAG/企业" "D:/obsidian/RAG/RAG/制度文件")
fi

TOKEN=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
if [ -z "$TOKEN" ]; then echo "登录失败"; exit 1; fi
echo "登录成功"

count=0; ok=0; fail=0
for dir in "${DIRS[@]}"; do
  while IFS= read -r -d '' file; do
    resp=$(curl -s -X POST "$API/api/documents/upload" -H "Authorization: Bearer $TOKEN" -F "file=@$file")
    if echo "$resp" | grep -q '"document_id"'; then
      status=$(echo "$resp" | python -c "import sys,json;d=json.load(sys.stdin);print(d.get('status'),d.get('document_id'))" 2>/dev/null)
      if echo "$status" | grep -q "failed"; then
        fail=$((fail+1)); echo "[失败] $(basename "$file") -> $resp"
      else
        ok=$((ok+1)); echo "[OK $status] $(basename "$file")"
      fi
    elif echo "$resp" | grep -q "429\|过于频繁"; then
      echo "[限流] 等待 ${BATCH_SLEEP}s 后重试 $(basename "$file")"
      sleep $BATCH_SLEEP
      resp=$(curl -s -X POST "$API/api/documents/upload" -H "Authorization: Bearer $TOKEN" -F "file=@$file")
      echo "$resp" | grep -q '"document_id"' && { ok=$((ok+1)); echo "[OK-重试] $(basename "$file")"; } || { fail=$((fail+1)); echo "[失败] $(basename "$file") -> $resp"; }
    else
      fail=$((fail+1)); echo "[失败] $(basename "$file") -> $resp"
    fi
    count=$((count+1))
    if [ $((count % BATCH)) -eq 0 ]; then
      echo "--- 已提交 $count 个，等待 ${BATCH_SLEEP}s 避开限流 ---"
      sleep $BATCH_SLEEP
    fi
  done < <(find "$dir" -maxdepth 1 -type f \( -iname "*.md" -o -iname "*.pdf" -o -iname "*.docx" -o -iname "*.txt" \) -print0)
done
echo "上传完成: 成功 $ok / 失败 $fail / 共 $count"
