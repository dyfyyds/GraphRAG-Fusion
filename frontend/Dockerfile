# ============================================================
#  前端多阶段构建：Node 构建 -> Nginx 托管
# ============================================================

# ---------- 阶段 1：构建 ----------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --registry=https://registry.npmmirror.com

COPY . .
RUN npm run build

# ---------- 阶段 2：运行 ----------
FROM nginx:alpine

# 移除默认配置，使用 SPA 配置
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
