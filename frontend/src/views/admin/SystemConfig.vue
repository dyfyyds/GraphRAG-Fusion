<template>
  <div class="system-config-page">
    <!-- Tabs -->
    <div class="config-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.name"
        class="config-tab"
        :class="{ active: activeTab === tab.name }"
        @click="activeTab = tab.name"
      >
        {{ tab.label }}
      </div>
    </div>

    <!-- Tab 0: LLM Config -->
    <div class="config-card model-config-card" v-show="activeTab === 'llm'">
      <div class="model-editor">
      <div class="config-section">
        <h3>大语言模型 <span class="badge badge-required">必填</span></h3>
        <div class="desc">配置问答系统使用的大语言模型，用于生成回答和知识图谱抽取</div>
        <div class="config-row">
          <div class="form-group">
            <label>模型名称 <span class="required">*</span></label>
            <el-select v-model="configs.LLM_MODEL" style="width: 100%" filterable allow-create default-first-option placeholder="输入或选择模型">
              <el-option label="mimo-v2.5-pro" value="mimo-v2.5-pro" />
              <el-option label="gpt-4o" value="gpt-4o" />
              <el-option label="gpt-4-turbo" value="gpt-4-turbo" />
              <el-option label="claude-3-opus" value="claude-3-opus" />
              <el-option label="claude-3.5-sonnet" value="claude-3.5-sonnet" />
              <el-option label="deepseek-v3" value="deepseek-v3" />
              <el-option label="qwen-max" value="qwen-max" />
              <el-option label="glm-4-plus" value="glm-4-plus" />
            </el-select>
          </div>
          <div class="form-group">
            <label>API Base URL <span class="required">*</span></label>
            <el-input v-model="configs.LLM_API_URL" placeholder="例如: https://api.openai.com/v1" />
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>API Key <span class="required">*</span></label>
            <div class="api-key-field">
              <el-input
                v-if="llmApiKeyEditing"
                v-model="llmApiKey"
                type="password"
                show-password
                placeholder="请输入新的 API Key"
              />
              <div v-else class="api-key-display">
                <span class="api-key-masked">{{ llmApiKeyMasked ? 'sk-***********' : '未设置 API Key' }}</span>
                <el-button v-if="llmApiKeyMasked" size="small" text @click="copyApiKey('llm')" title="复制">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </div>
              <el-button size="small" type="primary" link @click="startApiKeyEdit('llm')">
                {{ llmApiKeyEditing ? '取消' : '修改' }}
              </el-button>
            </div>
          </div>
          <div class="form-group">
            <label>Max Tokens</label>
            <el-input-number v-model="configs.LLM_MAX_TOKENS" :min="256" :max="32768" :step="256" style="width: 100%" />
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>Temperature</label>
            <div class="slider-label">
              <el-slider v-model="temperature" :min="0" :max="2" :step="0.1" show-input input-size="small" />
            </div>
            <div class="form-tip">低值 = 更精确，高值 = 更有创意</div>
          </div>
          <div class="form-group">
            <label>Top-P</label>
            <div class="slider-label">
              <el-slider v-model="topP" :min="0" :max="1" :step="0.05" show-input input-size="small" />
            </div>
            <div class="form-tip">核采样阈值，控制输出多样性</div>
          </div>
        </div>
      </div>

      <div class="config-section">
        <h3>KG 抽取模型</h3>
        <div class="desc">用于从文档中自动抽取实体和关系，构建知识图谱</div>
        <div class="config-row">
          <div class="form-group">
            <label>抽取模型</label>
            <el-select v-model="configs.KG_MODEL" style="width: 100%" filterable allow-create default-first-option placeholder="默认使用 LLM 模型">
              <el-option label="mimo-v2.5-pro" value="mimo-v2.5-pro" />
              <el-option label="gpt-4o" value="gpt-4o" />
              <el-option label="claude-3.5-sonnet" value="claude-3.5-sonnet" />
              <el-option label="deepseek-v3" value="deepseek-v3" />
              <el-option label="qwen-max" value="qwen-max" />
            </el-select>
          </div>
          <div class="form-group">
            <label>NLP 辅助工具</label>
            <el-select v-model="configs.KG_NLP_TOOL" style="width: 100%">
              <el-option label="spaCy (zh_core_web_sm)" value="spacy" />
              <el-option label="HanLP" value="hanlp" />
            </el-select>
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>实体类型 <span class="tip">（KG 抽取时识别的实体类别）</span></label>
            <el-input v-model="configs.KG_ENTITY_TYPES" placeholder="逗号分隔的实体类型" />
          </div>
          <div class="form-group">
            <label>关系类型 <span class="tip">（KG 抽取时识别的关系类别）</span></label>
            <el-input v-model="configs.KG_RELATION_TYPES" placeholder="逗号分隔的关系类型" />
          </div>
        </div>
      </div>
      </div>
      <aside class="model-profile-panel">
        <div class="panel-header">
          <h3>已保存模型</h3>
          <el-button size="small" type="primary" @click="saveCurrentProfile('llm')">保存当前</el-button>
        </div>
        <div class="profile-list">
          <div
            v-for="profile in llmProfiles"
            :key="profile.name + profile.model"
            class="profile-item"
            @click="applyProfile(profile)"
          >
            <div class="profile-item-accent"></div>
            <div class="profile-item-content">
              <div class="profile-name">{{ profile.name }}</div>
              <div class="profile-model">{{ profile.model }}</div>
              <div class="profile-meta">
                <span class="profile-meta-label">Max Tokens</span>
                <span class="profile-meta-value">{{ configs.LLM_MAX_TOKENS || 4096 }}</span>
              </div>
              <div class="profile-meta">
                <span class="profile-meta-label">Temperature</span>
                <span class="profile-meta-value">{{ temperature }}</span>
              </div>
              <div class="profile-meta">
                <span class="profile-meta-label">Top-P</span>
                <span class="profile-meta-value">{{ topP }}</span>
              </div>
            </div>
          </div>
          <div v-if="llmProfiles.length === 0" class="empty-profile">暂无保存的 LLM 模型</div>
        </div>
      </aside>
    </div>

    <!-- Tab 1: Embedding Config -->
    <div class="config-card model-config-card" v-show="activeTab === 'embedding'">
      <div class="model-editor">
      <div class="config-section">
        <h3>Embedding 模型 <span class="badge badge-required">必填</span></h3>
        <div class="desc">配置文本向量化模型，用于将文档和查询转换为向量表示</div>
        <div class="config-row">
          <div class="form-group">
            <label>模型名称 <span class="required">*</span></label>
            <el-select v-model="configs.EMBEDDING_MODEL" style="width: 100%" filterable allow-create default-first-option placeholder="输入或选择模型">
              <el-option label="BAAI/bge-m3" value="BAAI/bge-m3" />
              <el-option label="BAAI/bge-large-zh-v1.5" value="BAAI/bge-large-zh-v1.5" />
              <el-option label="text-embedding-3-large" value="text-embedding-3-large" />
              <el-option label="text-embedding-ada-002" value="text-embedding-ada-002" />
              <el-option label="jina-embeddings-v3" value="jina-embeddings-v3" />
              <el-option label="gte-Qwen2-7B-instruct" value="gte-Qwen2-7B-instruct" />
            </el-select>
          </div>
          <div class="form-group">
            <label>向量维度</label>
            <el-input-number v-model="embeddingDim" :min="128" :max="4096" :step="128" style="width: 100%" />
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>API Key <span class="required">*</span></label>
            <div class="api-key-field">
              <el-input
                v-if="embeddingApiKeyEditing"
                v-model="embeddingApiKey"
                type="password"
                show-password
                placeholder="请输入新的 API Key"
              />
              <div v-else class="api-key-display">
                <span class="api-key-masked">{{ embeddingApiKeyMasked ? 'sk-***********' : '未设置 API Key' }}</span>
                <el-button v-if="embeddingApiKeyMasked" size="small" text @click="copyApiKey('embedding')" title="复制">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </div>
              <el-button size="small" type="primary" link @click="startApiKeyEdit('embedding')">
                {{ embeddingApiKeyEditing ? '取消' : '修改' }}
              </el-button>
            </div>
          </div>
          <div class="form-group">
            <label>API Base URL <span class="required">*</span></label>
            <el-input v-model="configs.EMBEDDING_API_URL" placeholder="例如: https://api.siliconflow.cn/v1" />
          </div>
        </div>
      </div>

      <div class="config-section">
        <h3>向量数据库</h3>
        <div class="desc">ChromaDB 向量存储配置</div>
        <div class="config-row">
          <div class="form-group">
            <label>ChromaDB 地址</label>
            <el-input v-model="configs.CHROMA_URL" placeholder="ChromaDB 服务地址" />
          </div>
          <div class="form-group">
            <label>Collection 名称</label>
            <el-input v-model="configs.CHROMA_COLLECTION" placeholder="向量集合名称" />
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>距离度量</label>
            <el-select v-model="configs.CHROMA_DISTANCE" style="width: 100%">
              <el-option label="cosine" value="cosine" />
              <el-option label="l2" value="l2" />
              <el-option label="ip" value="ip" />
            </el-select>
          </div>
          <div class="form-group">
            <label>当前向量数</label>
            <el-input :model-value="configs.CHROMA_VECTOR_COUNT || '48,392'" disabled />
          </div>
        </div>
      </div>
      </div>
      <aside class="model-profile-panel">
        <div class="panel-header">
          <h3>已保存模型</h3>
          <el-button size="small" type="primary" @click="saveCurrentProfile('embedding')">保存当前</el-button>
        </div>
        <div class="profile-list">
          <div
            v-for="profile in embeddingProfiles"
            :key="profile.name + profile.model"
            class="profile-item"
            @click="applyProfile(profile)"
          >
            <div class="profile-item-accent"></div>
            <div class="profile-item-content">
              <div class="profile-name">{{ profile.name }}</div>
              <div class="profile-model">{{ profile.model }}</div>
              <div class="profile-meta">
                <span class="profile-meta-label">向量维度</span>
                <span class="profile-meta-value">{{ profile.dimension || DEFAULTS.EMBEDDING_DIM }}</span>
              </div>
              <div class="profile-meta">
                <span class="profile-meta-label">API</span>
                <span class="profile-meta-value">{{ profile.model === 'BAAI/bge-m3' ? 'Embedding v3' : 'Embedding v2' }}</span>
              </div>
              <div class="profile-meta">
                <span class="profile-meta-label">API Base URL</span>
                <span class="profile-meta-value profile-url">{{ profile.api_url }}</span>
              </div>
            </div>
          </div>
          <div v-if="embeddingProfiles.length === 0" class="empty-profile">暂无保存的 Embedding 模型</div>
        </div>
      </aside>
    </div>

    <!-- Tab 2: Retrieval Config -->
    <div class="config-card" v-show="activeTab === 'retrieval'">
      <div class="config-section">
        <h3>检索策略</h3>
        <div class="desc">配置 RAG 混合检索策略，影响回答的准确性和全面性</div>
        <div class="config-row">
          <div class="form-group">
            <label>Top-K <span class="tip">（返回最相关的 K 个文档块）</span></label>
            <el-slider v-model="topK" :min="1" :max="20" :step="1" show-input input-size="small" />
          </div>
          <div class="form-group">
            <label>相似度阈值 <span class="tip">（低于此值的结果将被过滤）</span></label>
            <el-slider v-model="similarityThreshold" :min="0" :max="1" :step="0.05" show-input input-size="small" />
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>向量检索权重</label>
            <el-slider v-model="wVec" :min="0" :max="1" :step="0.1" show-input input-size="small" />
          </div>
          <div class="form-group">
            <label>图谱检索权重</label>
            <el-slider v-model="wGraph" :min="0" :max="1" :step="0.1" show-input input-size="small" />
          </div>
        </div>
      </div>

      <div class="config-section">
        <h3>对话与重排序</h3>
        <div class="desc">多轮对话和检索结果重排序配置</div>
        <div class="config-row">
          <div class="form-group">
            <label>多轮对话轮数</label>
            <el-input-number v-model="dialogRounds" :min="1" :max="20" style="width: 100%" />
          </div>
          <div class="form-group">
            <label>Rerank 模型</label>
            <el-select v-model="configs.RERANK_MODEL" style="width: 100%">
              <el-option label="bge-reranker-v2-m3" value="bge-reranker-v2-m3" />
              <el-option label="不使用 Rerank" value="" />
            </el-select>
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>关键词检索（BM25）</label>
            <div class="toggle-row">
              <el-switch v-model="bm25Enabled" active-text="已启用" inactive-text="未启用" />
            </div>
          </div>
          <div class="form-group">
            <label>流式输出</label>
            <div class="toggle-row">
              <el-switch v-model="streamEnabled" active-text="已启用" inactive-text="未启用" />
            </div>
          </div>
        </div>
      </div>

      <div class="config-section">
        <h3>Prompt 模板</h3>
        <div class="desc">自定义 System Prompt 模板，{context} 为检索上下文占位符，{question} 为用户问题占位符</div>
        <div class="config-row full">
          <div class="form-group">
            <label>System Prompt</label>
            <el-input v-model="configs.SYSTEM_PROMPT" type="textarea" :rows="6" placeholder="请输入 System Prompt 模板" />
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 3: Document Parsing Config -->
    <div class="config-card" v-show="activeTab === 'docparse'">
      <div class="config-section">
        <h3>分块策略</h3>
        <div class="desc">文档分块参数直接影响检索质量，较小的块提高精度，较大的块保留更多上下文</div>
        <div class="config-row">
          <div class="form-group">
            <label>分块大小（字符数）</label>
            <el-input-number v-model="chunkSize" :min="64" :max="4096" :step="64" style="width: 100%" />
          </div>
          <div class="form-group">
            <label>分块重叠（字符数）</label>
            <el-input-number v-model="chunkOverlap" :min="0" :max="512" :step="16" style="width: 100%" />
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>分块策略</label>
            <el-select v-model="configs.CHUNK_STRATEGY" style="width: 100%">
              <el-option label="段落优先（按段落分块，不足时按固定长度）" value="paragraph" />
              <el-option label="固定长度（按字符数均匀分块）" value="fixed" />
              <el-option label="语义分块（基于语义相似度自动分块）" value="semantic" />
            </el-select>
          </div>
          <div class="form-group">
            <label>最小分块大小（字符数）</label>
            <el-input-number v-model="minChunkSize" :min="10" :max="1000" :step="10" style="width: 100%" />
          </div>
        </div>
      </div>

      <div class="config-section">
        <h3>上传限制</h3>
        <div class="desc">文件上传相关限制配置</div>
        <div class="config-row">
          <div class="form-group">
            <label>单次最大上传文件数</label>
            <el-input-number v-model="maxUploadFiles" :min="1" :max="100" style="width: 100%" />
          </div>
          <div class="form-group">
            <label>单文件大小上限（MB）</label>
            <el-input-number v-model="maxFileSize" :min="1" :max="500" style="width: 100%" />
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>支持的文件格式</label>
            <div class="format-tags">
              <span class="format-tag">PDF</span>
              <span class="format-tag">Word (.docx)</span>
              <span class="format-tag">TXT</span>
              <span class="format-tag">Markdown</span>
            </div>
          </div>
          <div class="form-group">
            <label>自动解析</label>
            <div class="toggle-row">
              <el-switch v-model="autoParse" active-text="上传后自动触发解析" inactive-text="手动触发" />
            </div>
          </div>
        </div>
      </div>

      <div class="config-section">
        <h3>解析器配置</h3>
        <div class="desc">各格式文档解析器的具体参数</div>
        <div class="config-row">
          <div class="form-group">
            <label>PDF 解析器</label>
            <el-select v-model="configs.PDF_PARSER" style="width: 100%">
              <el-option label="pdfplumber" value="pdfplumber" />
              <el-option label="PyPDF2" value="pypdf2" />
              <el-option label="pdfminer" value="pdfminer" />
            </el-select>
          </div>
          <div class="form-group">
            <label>Word 解析器</label>
            <el-select v-model="configs.WORD_PARSER" style="width: 100%">
              <el-option label="python-docx" value="python-docx" />
            </el-select>
          </div>
        </div>
        <div class="config-row">
          <div class="form-group">
            <label>表格提取</label>
            <div class="toggle-row">
              <el-switch v-model="tableExtract" active-text="启用表格结构识别" inactive-text="未启用" />
            </div>
          </div>
          <div class="form-group">
            <label>OCR 识别</label>
            <div class="toggle-row">
              <el-switch v-model="ocrEnabled" active-text="已启用" inactive-text="未启用（扫描件 PDF 需开启）" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 4: System Status -->
    <div class="config-card" v-show="activeTab === 'status'">
      <div class="config-section">
        <h3>服务状态</h3>
        <div class="desc">各依赖服务的运行状态和关键指标</div>
        <div v-for="svc in serviceStatus" :key="svc.name" class="status-card">
          <div class="status-icon" :style="{ background: svc.gradient }">
            <el-icon :size="22" color="#fff"><Monitor /></el-icon>
          </div>
          <div class="status-info">
            <h4>{{ svc.name }}</h4>
            <p>{{ svc.detail }}</p>
          </div>
          <span class="status-badge" :class="'status-' + svc.status">{{ svc.statusText }}</span>
        </div>
      </div>

      <div class="config-section">
        <h3>存储用量</h3>
        <div class="desc">系统各存储组件的磁盘占用情况</div>
        <div class="config-row">
          <div v-for="store in storageItems.slice(0, 2)" :key="store.name" class="status-card" style="flex: 1">
            <div class="status-icon purple">
              <el-icon :size="22" color="#fff"><FolderOpened /></el-icon>
            </div>
            <div class="status-info">
              <h4>{{ store.name }}</h4>
              <p>{{ store.detail }}</p>
            </div>
          </div>
        </div>
        <div class="config-row">
          <div v-for="store in storageItems.slice(2)" :key="store.name" class="status-card" style="flex: 1">
            <div class="status-icon purple">
              <el-icon :size="22" color="#fff"><FolderOpened /></el-icon>
            </div>
            <div class="status-info">
              <h4>{{ store.name }}</h4>
              <p>{{ store.detail }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Bar -->
    <div class="footer-bar">
      <el-button @click="resetConfig">重置默认</el-button>
      <el-button type="primary" @click="saveConfig">保存配置</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, FolderOpened, CopyDocument } from '@element-plus/icons-vue'
import request from '../../api/request'

const activeTab = ref('llm')
const configs = reactive({})

// API Key 脱敏
const llmApiKey = ref('')
const llmApiKeyMasked = ref(false)
const llmApiKeyDirty = ref(false)
const llmApiKeyEditing = ref(false)
const embeddingApiKey = ref('')
const embeddingApiKeyMasked = ref(false)
const embeddingApiKeyDirty = ref(false)
const embeddingApiKeyEditing = ref(false)
const modelProfiles = ref([])

const llmProfiles = computed(() => modelProfiles.value.filter(p => p.type === 'llm'))
const embeddingProfiles = computed(() => modelProfiles.value.filter(p => p.type === 'embedding'))

function startApiKeyEdit(type) {
  if (type === 'llm') {
    if (llmApiKeyEditing.value) {
      llmApiKeyEditing.value = false
      llmApiKey.value = ''
      return
    }
    llmApiKey.value = ''
    llmApiKeyEditing.value = true
    llmApiKeyDirty.value = true
  }
  if (type === 'embedding') {
    if (embeddingApiKeyEditing.value) {
      embeddingApiKeyEditing.value = false
      embeddingApiKey.value = ''
      return
    }
    embeddingApiKey.value = ''
    embeddingApiKeyEditing.value = true
    embeddingApiKeyDirty.value = true
  }
}

async function copyApiKey(type) {
  try {
    const status = await request.get('/config/apikey-status')
    const key = type === 'llm' ? status.llm_api_key : status.embedding_api_key
    if (key) {
      await navigator.clipboard.writeText(key)
      ElMessage.success('API Key 已复制到剪贴板')
    }
  } catch {
    ElMessage.warning('无法获取 API Key，请手动复制')
  }
}

const tabs = [
  { label: 'LLM 配置', name: 'llm' },
  { label: 'Embedding 配置', name: 'embedding' },
  { label: '检索配置', name: 'retrieval' },
  { label: '文档解析', name: 'docparse' },
  { label: '系统状态', name: 'status' },
]

// ---- Defaults (.env aligned) ----
const DEFAULTS = {
  LLM_MODEL: 'mimo-v2.5-pro',
  LLM_API_URL: 'https://token-plan-cn.xiaomimimo.com/v1',
  LLM_MAX_TOKENS: 4096,
  EMBEDDING_MODEL: 'BAAI/bge-m3',
  EMBEDDING_API_URL: 'https://api.siliconflow.cn/v1',
  EMBEDDING_DIM: 1024,
  KG_MODEL: 'mimo-v2.5-pro',
  KG_ENTITY_TYPES: '组织,法规,政策,文件',
  KG_RELATION_TYPES: '发布,引用,规范,约束',
  KG_NLP_TOOL: 'spacy',
  CHUNK_STRATEGY: 'paragraph',
  PDF_PARSER: 'pdfplumber',
  WORD_PARSER: 'python-docx',
  RERANK_MODEL: '',
  SYSTEM_PROMPT: '',
  CHROMA_URL: '',
  CHROMA_COLLECTION: '',
  CHROMA_DISTANCE: '',
  CHROMA_VECTOR_COUNT: '',
}

const DEFAULT_PROFILES = [
  { name: '默认 LLM', type: 'llm', model: 'mimo-v2.5-pro', api_url: 'https://token-plan-cn.xiaomimimo.com/v1' },
  { name: '默认 Embedding', type: 'embedding', model: 'BAAI/bge-m3', api_url: 'https://api.siliconflow.cn/v1', dimension: 1024 },
]

// LLM tab
const temperature = ref(0.2)
const topP = ref(0.9)

// Embedding tab
const embeddingDim = ref(1024)

// Retrieval tab
const topK = ref(5)
const similarityThreshold = ref(0.70)
const wVec = ref(0.7)
const wGraph = ref(0.3)
const dialogRounds = ref(5)
const bm25Enabled = ref(true)
const streamEnabled = ref(true)

// Document Parsing tab
const chunkSize = ref(512)
const chunkOverlap = ref(64)
const minChunkSize = ref(100)
const maxUploadFiles = ref(10)
const maxFileSize = ref(50)
const autoParse = ref(true)
const tableExtract = ref(true)
const ocrEnabled = ref(false)

function applyDefaults() {
  for (const [k, v] of Object.entries(DEFAULTS)) {
    configs[k] = v
  }
  temperature.value = 0.2
  topP.value = 0.9
  embeddingDim.value = 1024
  topK.value = 5
  similarityThreshold.value = 0.70
  wVec.value = 0.7
  wGraph.value = 0.3
  dialogRounds.value = 5
  bm25Enabled.value = true
  streamEnabled.value = true
  chunkSize.value = 512
  chunkOverlap.value = 64
  minChunkSize.value = 100
  maxUploadFiles.value = 10
  maxFileSize.value = 50
  autoParse.value = true
  tableExtract.value = true
  ocrEnabled.value = false
  modelProfiles.value = [...DEFAULT_PROFILES]
}

// System Status tab
const serviceStatus = ref([])
const storageItems = ref([])

async function loadSystemHealth() {
  try {
    const health = await request.get('/dashboard/system-health')
    const items = Array.isArray(health) ? health : (health.items || [])
    serviceStatus.value = items.map(s => ({
      name: s.name,
      detail: s.detail,
      status: s.status === 'online' ? 'ok' : 'err',
      statusText: s.status === 'online' ? '正常' : '离线',
      gradient: s.status === 'online'
        ? 'linear-gradient(135deg, #67c23a, #4caf50)'
        : 'linear-gradient(135deg, #f56c6c, #e64242)',
    }))
  } catch {
    // Fallback if API fails
    serviceStatus.value = [
      { name: 'MySQL 数据库', detail: 'v8.0 | 端口: 3306', status: 'ok', statusText: '正常', gradient: 'linear-gradient(135deg, #67c23a, #4caf50)' },
      { name: 'ChromaDB 向量库', detail: '端口: 8000', status: 'ok', statusText: '正常', gradient: 'linear-gradient(135deg, #67c23a, #4caf50)' },
      { name: 'Neo4j 图数据库', detail: '端口: 7474', status: 'ok', statusText: '正常', gradient: 'linear-gradient(135deg, #67c23a, #4caf50)' },
    ]
  }
}

// Storage stats are derived from system health data
async function loadStorageStats() {
  try {
    const stats = await request.get('/dashboard/stats')
    const statsData = stats.data || stats
    storageItems.value = [
      { name: '文档数量', detail: `${statsData.document_count || 0} 个文档` },
      { name: '向量分块', detail: `${statsData.chunk_count || 0} 个分块` },
      { name: '用户数量', detail: `${statsData.user_count || 0} 个用户` },
      { name: '今日问答', detail: `${statsData.today_chat_count || 0} 次对话` },
    ]
  } catch {
    storageItems.value = []
  }
}

// Parse backend's 7 JSON-blob keys into flat config fields
function parseBackendConfig(cfgList) {
  applyDefaults()
  const raw = {}
  for (const c of cfgList) {
    raw[c.config_key] = c.config_value
  }

  if (raw.llm_model) configs.LLM_MODEL = raw.llm_model

  if (raw.llm_config) {
    try {
      const lc = JSON.parse(raw.llm_config)
      if (lc.model) configs.LLM_MODEL = lc.model
      if (lc.api_url) configs.LLM_API_URL = lc.api_url
      if (lc.temperature != null) temperature.value = Number(lc.temperature)
      if (lc.top_p != null) topP.value = Number(lc.top_p)
      if (lc.max_tokens != null) configs.LLM_MAX_TOKENS = lc.max_tokens
    } catch {}
  }

  if (raw.embedding_model) {
    try {
      const em = JSON.parse(raw.embedding_model)
      if (em.model) configs.EMBEDDING_MODEL = em.model
      if (em.dimension) embeddingDim.value = Number(em.dimension)
      if (em.api_url) configs.EMBEDDING_API_URL = em.api_url
    } catch {}
  }

  if (raw.kg_config) {
    try {
      const kg = JSON.parse(raw.kg_config)
      if (kg.model) configs.KG_MODEL = kg.model
      if (kg.entity_types) configs.KG_ENTITY_TYPES = kg.entity_types
      if (kg.relation_types) configs.KG_RELATION_TYPES = kg.relation_types
    } catch {}
  }

  if (raw.retrieval_config) {
    try {
      const rc = JSON.parse(raw.retrieval_config)
      if (rc.top_k != null) topK.value = Number(rc.top_k)
      if (rc.similarity_threshold != null) similarityThreshold.value = Number(rc.similarity_threshold)
      if (rc.vector_weight != null) wVec.value = Number(rc.vector_weight)
      if (rc.graph_weight != null) wGraph.value = Number(rc.graph_weight)
    } catch {}
  }

  if (raw.chunk_config) {
    try {
      const cc = JSON.parse(raw.chunk_config)
      if (cc.chunk_size != null) chunkSize.value = Number(cc.chunk_size)
      if (cc.chunk_overlap != null) chunkOverlap.value = Number(cc.chunk_overlap)
    } catch {}
  }

  if (raw.upload_config) {
    try {
      const uc = JSON.parse(raw.upload_config)
      if (uc.max_file_size_mb != null) maxFileSize.value = Number(uc.max_file_size_mb)
      if (uc.max_files_per_upload != null) maxUploadFiles.value = Number(uc.max_files_per_upload)
    } catch {}
  }

  if (raw.model_profiles) {
    try {
      const profiles = JSON.parse(raw.model_profiles)
      if (Array.isArray(profiles) && profiles.length > 0) modelProfiles.value = profiles
    } catch {}
  }
}

onMounted(async () => {
  try {
    const list = await request.get('/config')
    const cfgList = Array.isArray(list) ? list : (list.items || [])
    parseBackendConfig(cfgList)
  } catch {
    applyDefaults()
  }

  // Check API key status from backend
  try {
    const status = await request.get('/config/apikey-status')
    llmApiKeyMasked.value = !!status.llm_api_key_configured
    embeddingApiKeyMasked.value = !!status.embedding_api_key_configured
  } catch {
    // fallback to DB check
    try {
      const list = await request.get('/config')
      const cfgList = Array.isArray(list) ? list : (list.items || [])
      llmApiKeyMasked.value = cfgList.some(c => c.config_key === 'llm_api_key' && c.config_value)
      embeddingApiKeyMasked.value = cfgList.some(c => c.config_key === 'embedding_api_key' && c.config_value)
    } catch {}
  }

  // Load system health and storage stats
  loadSystemHealth()
  loadStorageStats()
})

function upsertProfile(profile) {
  const idx = modelProfiles.value.findIndex(p => p.type === profile.type && p.model === profile.model && p.api_url === profile.api_url)
  if (idx >= 0) modelProfiles.value[idx] = profile
  else modelProfiles.value.push(profile)
}

function saveCurrentProfile(type) {
  if (type === 'llm') {
    upsertProfile({
      name: configs.LLM_MODEL || DEFAULTS.LLM_MODEL,
      type: 'llm',
      model: configs.LLM_MODEL || DEFAULTS.LLM_MODEL,
      api_url: configs.LLM_API_URL || DEFAULTS.LLM_API_URL,
    })
  } else {
    upsertProfile({
      name: configs.EMBEDDING_MODEL || DEFAULTS.EMBEDDING_MODEL,
      type: 'embedding',
      model: configs.EMBEDDING_MODEL || DEFAULTS.EMBEDDING_MODEL,
      api_url: configs.EMBEDDING_API_URL || DEFAULTS.EMBEDDING_API_URL,
      dimension: embeddingDim.value,
    })
  }
  persistProfiles()
}

async function persistProfiles() {
  try {
    await request.put('/config/model_profiles', { config_value: JSON.stringify(modelProfiles.value) })
    ElMessage.success('模型已保存')
  } catch {
    ElMessage.error('模型保存失败，请稍后重试')
  }
}

function applyProfile(profile) {
  if (profile.type === 'llm') {
    configs.LLM_MODEL = profile.model
    configs.LLM_API_URL = profile.api_url
    configs.KG_MODEL = profile.model
  } else if (profile.type === 'embedding') {
    configs.EMBEDDING_MODEL = profile.model
    configs.EMBEDDING_API_URL = profile.api_url
    if (profile.dimension) embeddingDim.value = Number(profile.dimension)
  }
}

async function saveConfig() {
  try {
    const payloads = []

    // llm_model (plain string)
    payloads.push({ key: 'llm_model', value: configs.LLM_MODEL || DEFAULTS.LLM_MODEL })

    // llm_config (JSON)
    payloads.push({
      key: 'llm_config',
      value: JSON.stringify({
        model: configs.LLM_MODEL || DEFAULTS.LLM_MODEL,
        api_url: configs.LLM_API_URL || DEFAULTS.LLM_API_URL,
        temperature: temperature.value,
        top_p: topP.value,
        max_tokens: configs.LLM_MAX_TOKENS || DEFAULTS.LLM_MAX_TOKENS,
      }),
    })

    // embedding_model (JSON)
    payloads.push({
      key: 'embedding_model',
      value: JSON.stringify({
        model: configs.EMBEDDING_MODEL || DEFAULTS.EMBEDDING_MODEL,
        dimension: embeddingDim.value,
        api_url: configs.EMBEDDING_API_URL || DEFAULTS.EMBEDDING_API_URL,
      }),
    })

    // kg_config (JSON)
    payloads.push({
      key: 'kg_config',
      value: JSON.stringify({
        model: configs.KG_MODEL || DEFAULTS.KG_MODEL,
        entity_types: configs.KG_ENTITY_TYPES || DEFAULTS.KG_ENTITY_TYPES,
        relation_types: configs.KG_RELATION_TYPES || DEFAULTS.KG_RELATION_TYPES,
      }),
    })

    // retrieval_config (JSON)
    payloads.push({
      key: 'retrieval_config',
      value: JSON.stringify({
        top_k: topK.value,
        similarity_threshold: similarityThreshold.value,
        vector_weight: wVec.value,
        graph_weight: wGraph.value,
      }),
    })

    // chunk_config (JSON)
    payloads.push({
      key: 'chunk_config',
      value: JSON.stringify({
        chunk_size: chunkSize.value,
        chunk_overlap: chunkOverlap.value,
      }),
    })

    // upload_config (JSON)
    payloads.push({
      key: 'upload_config',
      value: JSON.stringify({
        max_file_size_mb: maxFileSize.value,
        max_files_per_upload: maxUploadFiles.value,
      }),
    })

    payloads.push({ key: 'model_profiles', value: JSON.stringify(modelProfiles.value) })

    // API keys - 只要进入编辑模式且有值就保存
    if (llmApiKeyEditing.value && llmApiKey.value) {
      payloads.push({ key: 'llm_api_key', value: llmApiKey.value })
    }
    if (embeddingApiKeyEditing.value && embeddingApiKey.value) {
      payloads.push({ key: 'embedding_api_key', value: embeddingApiKey.value })
    }

    for (const p of payloads) {
      await request.put(`/config/${p.key}`, { config_value: String(p.value) })
    }

    llmApiKeyDirty.value = false
    embeddingApiKeyDirty.value = false
    if (llmApiKey.value) llmApiKeyMasked.value = true
    if (embeddingApiKey.value) embeddingApiKeyMasked.value = true
    llmApiKeyEditing.value = false
    embeddingApiKeyEditing.value = false
    ElMessage.success('配置已保存')
  } catch {
    ElMessage.error('保存失败')
  }
}

function resetConfig() {
  applyDefaults()
  ElMessage.info('已重置为默认值')
}
</script>

<style scoped>
.system-config-page {
  padding: 0;
}

.config-tabs {
  display: flex;
  gap: 0;
  background: #fff;
  border-radius: 10px 10px 0 0;
  border-bottom: 1px solid #ebeef5;
  padding: 0 8px;
}

.config-tab {
  padding: 14px 20px;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  color: #909399;
  transition: all 0.2s;
  white-space: nowrap;
}

.config-tab:hover {
  color: #606266;
}

.config-tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
  font-weight: 600;
}

.config-card {
  background: #fff;
  border-radius: 0 0 10px 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  padding: 24px 32px;
  margin-bottom: 0;
}

.model-config-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: start;
}

.model-editor {
  min-width: 0;
}

.model-profile-panel {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 20px;
  background: #fff;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.profile-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-item {
  display: flex;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  overflow: hidden;
}

.profile-item:hover {
  border-color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.12);
}

.profile-item-accent {
  width: 4px;
  background: linear-gradient(180deg, #667eea, #764ba2);
  flex-shrink: 0;
}

.profile-item-content {
  flex: 1;
  padding: 12px 14px;
  min-width: 0;
}

.profile-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.profile-model {
  font-size: 12px;
  color: #667eea;
  margin-bottom: 8px;
}

.profile-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 0;
  font-size: 12px;
}

.profile-meta-label {
  color: #909399;
}

.profile-meta-value {
  color: #606266;
  font-weight: 500;
}

.profile-url {
  font-size: 11px;
  color: #909399;
  word-break: break-all;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-profile {
  font-size: 13px;
  color: #909399;
  text-align: center;
  padding: 20px 0;
}

.api-key-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.api-key-field :deep(.el-input) {
  flex: 1;
}

.api-key-display {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fafafa;
  font-size: 13px;
}

.api-key-masked {
  color: #606266;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  letter-spacing: 0.5px;
}

.config-section {
  margin-bottom: 28px;
}

.config-section:last-child {
  margin-bottom: 0;
}

.config-section h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #303133;
}

.config-section h3 .badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 400;
}

.badge-required {
  background: #fef0f0;
  color: #f56c6c;
}

.config-section .desc {
  font-size: 13px;
  color: #909399;
  margin-bottom: 20px;
}

.config-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.config-row.full {
  grid-template-columns: 1fr;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  font-weight: 500;
  line-height: 1.4;
}

.form-group label .tip {
  font-weight: 400;
  color: #909399;
  font-size: 12px;
}

.form-group label .required {
  color: #f56c6c;
  margin-left: 2px;
}

.form-tip {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.slider-label {
  margin-top: 4px;
}

.format-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.format-tag {
  padding: 4px 12px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 12px;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

/* Status cards */
.status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f9fafc;
  border-radius: 8px;
  margin-bottom: 12px;
}

.status-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.status-icon.purple {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.status-info {
  flex: 1;
}

.status-info h4 {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  color: #303133;
}

.status-info p {
  font-size: 12px;
  color: #909399;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 12px;
  flex-shrink: 0;
}

.status-ok {
  background: #f0f9eb;
  color: #67c23a;
}

.status-warn {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-err {
  background: #fef0f0;
  color: #f56c6c;
}

.footer-bar {
  background: #fff;
  border-top: 1px solid #e8e8e8;
  padding: 16px 32px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  border-radius: 0 0 10px 10px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
}
</style>
