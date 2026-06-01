<template>
  <div class="system-config-page" v-loading="loading">
    <div class="config-hero">
      <div>
        <div class="eyebrow">Runtime Settings</div>
        <h2>系统配置中心</h2>
        <p>统一管理模型、检索、解析和运行状态，保存后实时写入后端配置。</p>
      </div>
      <div class="hero-status">
        <span class="status-dot" :class="{ ready: llmApiKeyReady && embeddingApiKeyReady }"></span>
        {{ llmApiKeyReady && embeddingApiKeyReady ? '核心密钥已配置' : '核心密钥待补全' }}
      </div>
    </div>

    <div class="config-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.name"
        class="config-tab"
        :class="{ active: activeTab === tab.name }"
        @click="activeTab = tab.name"
      >
        <el-icon><component :is="tab.icon" /></el-icon>
        <span>{{ tab.label }}</span>
      </div>
    </div>

    <!-- Tab 0: LLM Config -->
    <div v-if="activeTab === 'llm'" class="config-card model-config-card">
      <div class="model-editor">
      <div class="config-section">
        <h3>大语言模型 <span class="badge badge-required">必填</span></h3>
        <div class="desc">配置问答系统使用的大语言模型，用于生成回答和知识图谱抽取</div>
        <div class="config-row full">
          <div class="form-group">
            <label>配置名称 <span class="required">*</span></label>
            <el-input v-model="llmProfileName" placeholder="例如：生产环境 LLM" />
          </div>
        </div>
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
                <span class="api-key-masked">{{ llmApiKeyStatusText }}</span>
                <el-tag v-if="hasActiveProfileApiKey('llm')" size="small" type="success" effect="plain">已配置</el-tag>
              </div>
              <el-button size="small" type="primary" link @click="startApiKeyEdit('llm')">
                {{ llmApiKeyEditing ? '取消' : '修改' }}
              </el-button>
            </div>
            <div class="form-tip">API Key 将单独保存到当前模型配置，切换卡片时会使用对应配置的 Key。</div>
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
        <div class="config-row">
          <div class="form-group">
            <label>抽取文本长度（字符数）</label>
            <el-input-number v-model="kgMaxChars" :min="800" :max="8000" :step="100" style="width: 100%" />
            <div class="form-tip">越短越快，越长覆盖更多内容</div>
          </div>
        </div>
      </div>
      </div>
      <aside class="model-profile-panel">
        <div class="panel-header">
          <h3>已保存模型</h3>
          <div class="panel-actions">
            <el-button size="small" type="primary" @click="saveCurrentProfile('llm')">保存当前</el-button>
          </div>
        </div>
        <div class="profile-list">
          <div
            v-for="profile in llmProfiles"
            :key="profile.id || profile.name + profile.model"
            class="profile-item"
            :class="{ active: isActiveProfile(profile, 'llm') }"
            @click="applyProfile(profile)"
          >
            <div class="profile-item-accent"></div>
            <div class="profile-item-content">
              <div class="profile-name">{{ profile.name }}</div>
              <div class="profile-model">使用模型：{{ profile.model }}</div>
            </div>
          </div>
          <div v-if="llmProfiles.length === 0" class="empty-profile">暂无保存的 LLM 模型</div>
          <button class="add-profile-card" type="button" @click="startNewProfile('llm')">
            <el-icon><Plus /></el-icon>
            <span>新增 LLM 配置</span>
          </button>
        </div>
      </aside>
    </div>

    <!-- Tab 1: Embedding Config -->
    <div v-else-if="activeTab === 'embedding'" class="config-card model-config-card">
      <div class="model-editor">
      <div class="config-section">
        <h3>Embedding 模型 <span class="badge badge-required">必填</span></h3>
        <div class="desc">配置文本向量化模型，用于将文档和查询转换为向量表示</div>
        <div class="config-row full">
          <div class="form-group">
            <label>配置名称 <span class="required">*</span></label>
            <el-input v-model="embeddingProfileName" placeholder="例如：默认向量模型" />
          </div>
        </div>
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
                <span class="api-key-masked">{{ embeddingApiKeyStatusText }}</span>
                <el-tag v-if="hasActiveProfileApiKey('embedding')" size="small" type="success" effect="plain">已配置</el-tag>
              </div>
              <el-button size="small" type="primary" link @click="startApiKeyEdit('embedding')">
                {{ embeddingApiKeyEditing ? '取消' : '修改' }}
              </el-button>
            </div>
            <div class="form-tip">API Key 将单独保存到当前模型配置，切换卡片时会使用对应配置的 Key。</div>
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
          <div class="panel-actions">
            <el-button size="small" type="primary" @click="saveCurrentProfile('embedding')">保存当前</el-button>
          </div>
        </div>
        <div class="profile-list">
          <div
            v-for="profile in embeddingProfiles"
            :key="profile.id || profile.name + profile.model"
            class="profile-item"
            :class="{ active: isActiveProfile(profile, 'embedding') }"
            @click="applyProfile(profile)"
          >
            <div class="profile-item-accent"></div>
            <div class="profile-item-content">
              <div class="profile-name">{{ profile.name }}</div>
              <div class="profile-model">使用模型：{{ profile.model }}</div>
            </div>
          </div>
          <div v-if="embeddingProfiles.length === 0" class="empty-profile">暂无保存的 Embedding 模型</div>
          <button class="add-profile-card" type="button" @click="startNewProfile('embedding')">
            <el-icon><Plus /></el-icon>
            <span>新增 Embedding 配置</span>
          </button>
        </div>
      </aside>
    </div>

    <!-- Tab 2: Retrieval Config -->
    <div v-else-if="activeTab === 'retrieval'" class="config-card">
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
        <div class="weight-summary" :class="{ warning: !retrievalWeightsBalanced }">
          <span>权重合计 {{ retrievalWeightTotal.toFixed(1) }}</span>
          <el-button v-if="!retrievalWeightsBalanced" size="small" link type="primary" @click="normalizeRetrievalWeights">自动归一化</el-button>
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
    <div v-else-if="activeTab === 'docparse'" class="config-card">
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
    <div v-else-if="activeTab === 'status'" class="config-card">
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
      <div class="footer-hint">
        <el-icon><Check /></el-icon>
        <span>当前页：{{ activeTabLabel }}</span>
      </div>
      <div class="footer-actions">
        <el-button :icon="Refresh" @click="resetConfig">重置默认</el-button>
        <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Connection, Cpu, Document, FolderOpened, Monitor, Plus, Refresh, Search } from '@element-plus/icons-vue'
import request from '../../api/request'

const activeTab = ref('llm')
const configs = reactive({})
const loading = ref(false)
const saving = ref(false)

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
const profileApiKeyConfigured = reactive({})
const activeLlmProfileId = ref('')
const activeEmbeddingProfileId = ref('')
const llmProfileName = ref('默认 LLM')
const embeddingProfileName = ref('默认 Embedding')

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

const tabs = [
  { label: 'LLM 配置', name: 'llm', icon: Cpu },
  { label: 'Embedding 配置', name: 'embedding', icon: Connection },
  { label: '检索配置', name: 'retrieval', icon: Search },
  { label: '文档解析', name: 'docparse', icon: Document },
  { label: '系统状态', name: 'status', icon: Monitor },
]

const activeTabLabel = computed(() => tabs.find(tab => tab.name === activeTab.value)?.label || '')
const llmApiKeyReady = computed(() => hasActiveProfileApiKey('llm') || Boolean(llmApiKey.value))
const embeddingApiKeyReady = computed(() => hasActiveProfileApiKey('embedding') || Boolean(embeddingApiKey.value))
const llmApiKeyStatusText = computed(() => {
  if (!activeLlmProfileId.value) return '新配置需填写 API Key'
  return hasActiveProfileApiKey('llm') ? '当前配置已保存 API Key' : '当前配置未设置 API Key'
})
const embeddingApiKeyStatusText = computed(() => {
  if (!activeEmbeddingProfileId.value) return '新配置需填写 API Key'
  return hasActiveProfileApiKey('embedding') ? '当前配置已保存 API Key' : '当前配置未设置 API Key'
})
const retrievalWeightTotal = computed(() => Number(wVec.value || 0) + Number(wGraph.value || 0))
const retrievalWeightsBalanced = computed(() => Math.abs(retrievalWeightTotal.value - 1) < 0.001)

const DEFAULT_LLM_MAX_TOKENS = 4096
const DEFAULT_EMBEDDING_DIM = 1024

// ---- Defaults (.env aligned) ----
const DEFAULTS = {
  LLM_MODEL: 'mimo-v2.5-pro',
  LLM_API_URL: 'https://token-plan-cn.xiaomimimo.com/v1',
  LLM_MAX_TOKENS: DEFAULT_LLM_MAX_TOKENS,
  EMBEDDING_MODEL: 'BAAI/bge-m3',
  EMBEDDING_API_URL: 'https://api.siliconflow.cn/v1',
  EMBEDDING_DIM: DEFAULT_EMBEDDING_DIM,
  KG_MODEL: 'mimo-v2.5-pro',
  KG_ENTITY_TYPES: '组织,法规,政策,文件',
  KG_RELATION_TYPES: '发布,引用,规范,约束',
  KG_NLP_TOOL: 'spacy',
  CHUNK_STRATEGY: 'paragraph',
  PDF_PARSER: 'pdfplumber',
  WORD_PARSER: 'python-docx',
  RERANK_MODEL: '',
  SYSTEM_PROMPT: '',
  CHROMA_URL: 'http://chroma:8000',
  CHROMA_COLLECTION: 'documents',
  CHROMA_DISTANCE: 'cosine',
  CHROMA_VECTOR_COUNT: '',
}

const DEFAULT_PROFILES = [
  { id: 'default-llm', name: '默认 LLM', type: 'llm', model: 'mimo-v2.5-pro', api_url: 'https://token-plan-cn.xiaomimimo.com/v1', max_tokens: DEFAULT_LLM_MAX_TOKENS, temperature: 0.2, top_p: 0.9 },
  { id: 'default-embedding', name: '默认 Embedding', type: 'embedding', model: 'BAAI/bge-m3', api_url: 'https://api.siliconflow.cn/v1', dimension: DEFAULT_EMBEDDING_DIM },
]

// LLM tab
const temperature = ref(0.2)
const topP = ref(0.9)
const kgMaxChars = ref(4000)

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
  kgMaxChars.value = 4000
  embeddingDim.value = 1024
  llmProfileName.value = '默认 LLM'
  embeddingProfileName.value = '默认 Embedding'
  activeLlmProfileId.value = 'default-llm'
  activeEmbeddingProfileId.value = 'default-embedding'
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
  for (const key of Object.keys(profileApiKeyConfigured)) {
    delete profileApiKeyConfigured[key]
  }
  for (const c of cfgList) {
    raw[c.config_key] = c.config_value
    if ((c.config_key.startsWith('llm_profile_') || c.config_key.startsWith('embedding_profile_')) && c.config_key.endsWith('_api_key') && c.config_value) {
      profileApiKeyConfigured[c.config_key] = true
    }
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
      if (em.chroma_url) configs.CHROMA_URL = em.chroma_url
      if (em.chroma_collection) configs.CHROMA_COLLECTION = em.chroma_collection
      if (em.chroma_distance) configs.CHROMA_DISTANCE = em.chroma_distance
      if (em.chroma_vector_count != null) configs.CHROMA_VECTOR_COUNT = em.chroma_vector_count
    } catch {}
  }

  if (raw.kg_config) {
    try {
      const kg = JSON.parse(raw.kg_config)
      if (kg.model) configs.KG_MODEL = kg.model
      if (kg.entity_types) configs.KG_ENTITY_TYPES = kg.entity_types
      if (kg.relation_types) configs.KG_RELATION_TYPES = kg.relation_types
      if (kg.nlp_tool) configs.KG_NLP_TOOL = kg.nlp_tool
      if (kg.max_chars != null) kgMaxChars.value = Number(kg.max_chars)
    } catch {}
  }

  if (raw.retrieval_config) {
    try {
      const rc = JSON.parse(raw.retrieval_config)
      if (rc.top_k != null) topK.value = Number(rc.top_k)
      if (rc.similarity_threshold != null) similarityThreshold.value = Number(rc.similarity_threshold)
      if (rc.vector_weight != null) wVec.value = Number(rc.vector_weight)
      if (rc.graph_weight != null) wGraph.value = Number(rc.graph_weight)
      if (rc.dialog_rounds != null) dialogRounds.value = Number(rc.dialog_rounds)
      if (rc.rerank_model != null) configs.RERANK_MODEL = rc.rerank_model
      if (rc.bm25_enabled != null) bm25Enabled.value = Boolean(rc.bm25_enabled)
      if (rc.stream_enabled != null) streamEnabled.value = Boolean(rc.stream_enabled)
      if (rc.system_prompt != null) configs.SYSTEM_PROMPT = rc.system_prompt
    } catch {}
  }

  if (raw.chunk_config) {
    try {
      const cc = JSON.parse(raw.chunk_config)
      if (cc.chunk_size != null) chunkSize.value = Number(cc.chunk_size)
      if (cc.chunk_overlap != null) chunkOverlap.value = Number(cc.chunk_overlap)
      if (cc.min_chunk_size != null) minChunkSize.value = Number(cc.min_chunk_size)
      if (cc.strategy) configs.CHUNK_STRATEGY = cc.strategy
    } catch {}
  }

  if (raw.upload_config) {
    try {
      const uc = JSON.parse(raw.upload_config)
      if (uc.max_file_size_mb != null) maxFileSize.value = Number(uc.max_file_size_mb)
      if (uc.max_files_per_upload != null) maxUploadFiles.value = Number(uc.max_files_per_upload)
      if (uc.auto_parse != null) autoParse.value = Boolean(uc.auto_parse)
      if (uc.pdf_parser) configs.PDF_PARSER = uc.pdf_parser
      if (uc.word_parser) configs.WORD_PARSER = uc.word_parser
      if (uc.table_extract != null) tableExtract.value = Boolean(uc.table_extract)
      if (uc.ocr_enabled != null) ocrEnabled.value = Boolean(uc.ocr_enabled)
      if (Array.isArray(uc.allowed_formats) && uc.allowed_formats.length) configs.ALLOWED_FORMATS = uc.allowed_formats.join(',')
    } catch {}
  }

  if (raw.model_profiles) {
    try {
      const profiles = JSON.parse(raw.model_profiles)
      if (Array.isArray(profiles) && profiles.length > 0) modelProfiles.value = profiles
    } catch {}
  }

  const currentLlmProfile = llmProfiles.value.find(p => p.model === configs.LLM_MODEL && p.api_url === configs.LLM_API_URL) || llmProfiles.value[0]
  if (currentLlmProfile) {
    activeLlmProfileId.value = ensureProfileId(currentLlmProfile)
    llmProfileName.value = currentLlmProfile.name || configs.LLM_MODEL || 'LLM 配置'
    llmApiKeyMasked.value = hasActiveProfileApiKey('llm')
  }

  const currentEmbeddingProfile = embeddingProfiles.value.find(p => p.model === configs.EMBEDDING_MODEL && p.api_url === configs.EMBEDDING_API_URL) || embeddingProfiles.value[0]
  if (currentEmbeddingProfile) {
    activeEmbeddingProfileId.value = ensureProfileId(currentEmbeddingProfile)
    embeddingProfileName.value = currentEmbeddingProfile.name || configs.EMBEDDING_MODEL || 'Embedding 配置'
    embeddingApiKeyMasked.value = hasActiveProfileApiKey('embedding')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const list = await request.get('/config')
    const cfgList = Array.isArray(list) ? list : (list.items || [])
    parseBackendConfig(cfgList)
  } catch {
    applyDefaults()
  }

  // Load system health and storage stats
  await Promise.all([loadSystemHealth(), loadStorageStats()])
  loading.value = false
})

function createProfileId(type) {
  return `${type}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function profileApiKeyKey(type, profileId) {
  return profileId ? `${type}_profile_${profileId}_api_key` : ''
}

function hasActiveProfileApiKey(type) {
  const profileId = type === 'llm' ? activeLlmProfileId.value : activeEmbeddingProfileId.value
  const key = profileApiKeyKey(type, profileId)
  return Boolean(key && profileApiKeyConfigured[key])
}

function setProfileApiKeyConfigured(type, profileId, configured = true) {
  const key = profileApiKeyKey(type, profileId)
  if (key) profileApiKeyConfigured[key] = configured
}

function profileKey(profile) {
  return profile.id || `${profile.type}:${profile.model}:${profile.api_url}`
}

function ensureProfileId(profile) {
  if (!profile.id) profile.id = createProfileId(profile.type)
  return profile.id
}

function isActiveProfile(profile, type) {
  const activeId = type === 'llm' ? activeLlmProfileId.value : activeEmbeddingProfileId.value
  return Boolean(activeId) && profileKey(profile) === activeId
}

function upsertProfile(profile) {
  const nextProfile = { ...profile, id: profile.id || createProfileId(profile.type) }
  const idx = modelProfiles.value.findIndex(p => {
    if (nextProfile.id && p.id) return p.id === nextProfile.id
    return p.type === nextProfile.type && p.model === nextProfile.model && p.api_url === nextProfile.api_url
  })
  if (idx >= 0) modelProfiles.value[idx] = nextProfile
  else modelProfiles.value.push(nextProfile)
  if (nextProfile.type === 'llm') activeLlmProfileId.value = nextProfile.id
  else activeEmbeddingProfileId.value = nextProfile.id
  return nextProfile
}

function buildCurrentProfile(type) {
  if (type === 'llm') {
    const name = llmProfileName.value.trim()
    if (!name) {
      ElMessage.warning('请填写 LLM 配置名称')
      return null
    }
    return {
      id: activeLlmProfileId.value || '',
      name,
      type: 'llm',
      model: configs.LLM_MODEL || DEFAULTS.LLM_MODEL,
      api_url: configs.LLM_API_URL || DEFAULTS.LLM_API_URL,
      max_tokens: configs.LLM_MAX_TOKENS || DEFAULTS.LLM_MAX_TOKENS,
      temperature: temperature.value,
      top_p: topP.value,
    }
  }

  const name = embeddingProfileName.value.trim()
  if (!name) {
    ElMessage.warning('请填写 Embedding 配置名称')
    return null
  }
  return {
    id: activeEmbeddingProfileId.value || '',
    name,
    type: 'embedding',
    model: configs.EMBEDDING_MODEL || DEFAULTS.EMBEDDING_MODEL,
    api_url: configs.EMBEDDING_API_URL || DEFAULTS.EMBEDDING_API_URL,
    dimension: embeddingDim.value,
  }
}

function syncCurrentProfile(type) {
  const profile = buildCurrentProfile(type)
  if (!profile) return false
  return upsertProfile(profile)
}

async function deleteProfile(profile) {
  const previousProfiles = modelProfiles.value.map(p => ({ ...p }))
  const previousLlmId = activeLlmProfileId.value
  const previousEmbeddingId = activeEmbeddingProfileId.value
  const key = profileKey(profile)
  modelProfiles.value = modelProfiles.value.filter(p => {
    return profileKey(p) !== key
  })
  if (profile.type === 'llm' && activeLlmProfileId.value === key) startNewProfile('llm')
  if (profile.type === 'embedding' && activeEmbeddingProfileId.value === key) startNewProfile('embedding')
  const saved = await persistProfiles('模型配置删除失败')
  if (!saved) {
    modelProfiles.value = previousProfiles
    activeLlmProfileId.value = previousLlmId
    activeEmbeddingProfileId.value = previousEmbeddingId
  }
}

function startNewProfile(type) {
  if (type === 'llm') {
    activeLlmProfileId.value = ''
    llmApiKey.value = ''
    llmApiKeyMasked.value = false
    llmApiKeyEditing.value = true
    llmProfileName.value = '新的 LLM 配置'
    configs.LLM_MODEL = DEFAULTS.LLM_MODEL
    configs.LLM_API_URL = DEFAULTS.LLM_API_URL
    configs.LLM_MAX_TOKENS = DEFAULTS.LLM_MAX_TOKENS
    configs.KG_MODEL = DEFAULTS.KG_MODEL
    temperature.value = 0.2
    topP.value = 0.9
  } else {
    activeEmbeddingProfileId.value = ''
    embeddingApiKey.value = ''
    embeddingApiKeyMasked.value = false
    embeddingApiKeyEditing.value = true
    embeddingProfileName.value = '新的 Embedding 配置'
    configs.EMBEDDING_MODEL = DEFAULTS.EMBEDDING_MODEL
    configs.EMBEDDING_API_URL = DEFAULTS.EMBEDDING_API_URL
    embeddingDim.value = DEFAULTS.EMBEDDING_DIM
  }
}

async function saveCurrentProfile(type) {
  const previousProfiles = modelProfiles.value.map(p => ({ ...p }))
  const previousLlmId = activeLlmProfileId.value
  const previousEmbeddingId = activeEmbeddingProfileId.value
  const previousKeyStatus = { ...profileApiKeyConfigured }
  const isCreating = type === 'llm' ? !activeLlmProfileId.value : !activeEmbeddingProfileId.value

  const profile = syncCurrentProfile(type)
  if (!profile) return

  const apiKeyValue = type === 'llm' ? llmApiKey.value.trim() : embeddingApiKey.value.trim()
  const apiKeyConfigured = profileApiKeyConfigured[profileApiKeyKey(type, profile.id)]
  if (!apiKeyConfigured && !apiKeyValue) {
    ElMessage.warning(type === 'llm' ? '请填写当前 LLM 配置的 API Key' : '请填写当前 Embedding 配置的 API Key')
    modelProfiles.value = previousProfiles
    activeLlmProfileId.value = previousLlmId
    activeEmbeddingProfileId.value = previousEmbeddingId
    return
  }

  try {
    if (apiKeyValue) {
      await request.put(`/config/${profileApiKeyKey(type, profile.id)}`, { config_value: apiKeyValue })
      setProfileApiKeyConfigured(type, profile.id, true)
      if (type === 'llm') {
        llmApiKey.value = ''
        llmApiKeyEditing.value = false
        llmApiKeyMasked.value = true
      } else {
        embeddingApiKey.value = ''
        embeddingApiKeyEditing.value = false
        embeddingApiKeyMasked.value = true
      }
    }
    await persistProfilesRaw()
    ElMessage.success('模型已保存')
  } catch (error) {
    modelProfiles.value = previousProfiles
    activeLlmProfileId.value = previousLlmId
    activeEmbeddingProfileId.value = previousEmbeddingId
    for (const key of Object.keys(profileApiKeyConfigured)) delete profileApiKeyConfigured[key]
    Object.assign(profileApiKeyConfigured, previousKeyStatus)
    ElMessage.error(`${isCreating ? '新建配置失败' : '模型配置保存失败'}：${getErrorMessage(error, '请检查后端服务')}`)
  }
}

function getErrorMessage(error, fallback = '操作失败') {
  const data = error?.response?.data
  if (typeof data === 'string') return data
  if (data?.detail) {
    if (Array.isArray(data.detail)) {
      return data.detail.map(item => item.msg || JSON.stringify(item)).join('；')
    }
    return String(data.detail)
  }
  if (data?.message) return String(data.message)
  if (error?.message) return error.message
  return fallback
}

async function persistProfiles(failurePrefix = '模型保存失败') {
  try {
    await persistProfilesRaw()
    ElMessage.success('模型已保存')
    return true
  } catch (error) {
    ElMessage.error(`${failurePrefix}：${getErrorMessage(error, '请检查登录状态或后端服务')}`)
    return false
  }
}

async function persistProfilesRaw() {
  await request.put('/config/model_profiles', { config_value: JSON.stringify(modelProfiles.value) })
}

function applyProfile(profile) {
  const profileId = ensureProfileId(profile)
  if (profile.type === 'llm') {
    activeLlmProfileId.value = profileId
    llmApiKey.value = ''
    llmApiKeyMasked.value = hasActiveProfileApiKey('llm')
    llmApiKeyEditing.value = false
    llmProfileName.value = profile.name || profile.model || 'LLM 配置'
    configs.LLM_MODEL = profile.model
    configs.LLM_API_URL = profile.api_url
    configs.KG_MODEL = profile.model
    if (profile.max_tokens) configs.LLM_MAX_TOKENS = Number(profile.max_tokens)
    if (profile.temperature != null) temperature.value = Number(profile.temperature)
    if (profile.top_p != null) topP.value = Number(profile.top_p)
  } else if (profile.type === 'embedding') {
    activeEmbeddingProfileId.value = profileId
    embeddingApiKey.value = ''
    embeddingApiKeyMasked.value = hasActiveProfileApiKey('embedding')
    embeddingApiKeyEditing.value = false
    embeddingProfileName.value = profile.name || profile.model || 'Embedding 配置'
    configs.EMBEDDING_MODEL = profile.model
    configs.EMBEDDING_API_URL = profile.api_url
    if (profile.dimension) embeddingDim.value = Number(profile.dimension)
  }
}

function normalizeRetrievalWeights() {
  const total = retrievalWeightTotal.value
  if (!total) {
    wVec.value = 0.7
    wGraph.value = 0.3
    return
  }
  wVec.value = Number((Number(wVec.value) / total).toFixed(1))
  wGraph.value = Number((1 - wVec.value).toFixed(1))
}

function validateConfig() {
  if (!configs.LLM_MODEL || !configs.LLM_API_URL) {
    activeTab.value = 'llm'
    ElMessage.warning('请补全 LLM 模型名称和 API Base URL')
    return false
  }
  if (!llmApiKeyReady.value) {
    activeTab.value = 'llm'
    ElMessage.warning('请配置 LLM API Key')
    return false
  }
  if (!configs.EMBEDDING_MODEL || !configs.EMBEDDING_API_URL) {
    activeTab.value = 'embedding'
    ElMessage.warning('请补全 Embedding 模型名称和 API Base URL')
    return false
  }
  if (!embeddingApiKeyReady.value) {
    activeTab.value = 'embedding'
    ElMessage.warning('请配置 Embedding API Key')
    return false
  }
  if (!retrievalWeightsBalanced.value) {
    normalizeRetrievalWeights()
  }
  return true
}

async function saveConfig() {
  const previousProfiles = modelProfiles.value.map(p => ({ ...p }))
  const previousLlmId = activeLlmProfileId.value
  const previousEmbeddingId = activeEmbeddingProfileId.value
  const previousKeyStatus = { ...profileApiKeyConfigured }
  const payloads = []
  let llmProfile = null
  let embeddingProfile = null
  let llmKeyRef = ''
  let embeddingKeyRef = ''
  let nextLlmApiKey = ''
  let nextEmbeddingApiKey = ''

  if (activeTab.value === 'llm') {
    if (!configs.LLM_MODEL || !configs.LLM_API_URL) {
      ElMessage.warning('请补全 LLM 模型名称和 API Base URL')
      return
    }
    llmProfile = syncCurrentProfile('llm')
    if (!llmProfile) return
    llmKeyRef = profileApiKeyKey('llm', llmProfile.id)
    nextLlmApiKey = llmApiKey.value.trim()
    if (!profileApiKeyConfigured[llmKeyRef] && !nextLlmApiKey) {
      ElMessage.warning('请填写当前 LLM 配置的 API Key')
      modelProfiles.value = previousProfiles
      activeLlmProfileId.value = previousLlmId
      return
    }
    payloads.push({ key: 'llm_model', value: configs.LLM_MODEL || DEFAULTS.LLM_MODEL })
    payloads.push({
      key: 'llm_config',
      value: JSON.stringify({
        model: configs.LLM_MODEL || DEFAULTS.LLM_MODEL,
        api_url: configs.LLM_API_URL || DEFAULTS.LLM_API_URL,
        temperature: temperature.value,
        top_p: topP.value,
        max_tokens: configs.LLM_MAX_TOKENS || DEFAULTS.LLM_MAX_TOKENS,
        api_key_ref: llmKeyRef,
      }),
    })
    payloads.push({
      key: 'kg_config',
      value: JSON.stringify({
        model: configs.KG_MODEL || DEFAULTS.KG_MODEL,
        entity_types: configs.KG_ENTITY_TYPES || DEFAULTS.KG_ENTITY_TYPES,
        relation_types: configs.KG_RELATION_TYPES || DEFAULTS.KG_RELATION_TYPES,
        nlp_tool: configs.KG_NLP_TOOL || DEFAULTS.KG_NLP_TOOL,
        max_chars: kgMaxChars.value,
      }),
    })
    payloads.push({ key: 'model_profiles', value: JSON.stringify(modelProfiles.value) })
    if (nextLlmApiKey) payloads.push({ key: llmKeyRef, value: nextLlmApiKey })
  } else if (activeTab.value === 'embedding') {
    if (!configs.EMBEDDING_MODEL || !configs.EMBEDDING_API_URL) {
      ElMessage.warning('请补全 Embedding 模型名称和 API Base URL')
      return
    }
    embeddingProfile = syncCurrentProfile('embedding')
    if (!embeddingProfile) return
    embeddingKeyRef = profileApiKeyKey('embedding', embeddingProfile.id)
    nextEmbeddingApiKey = embeddingApiKey.value.trim()
    if (!profileApiKeyConfigured[embeddingKeyRef] && !nextEmbeddingApiKey) {
      ElMessage.warning('请填写当前 Embedding 配置的 API Key')
      modelProfiles.value = previousProfiles
      activeEmbeddingProfileId.value = previousEmbeddingId
      return
    }
    payloads.push({
      key: 'embedding_model',
      value: JSON.stringify({
        model: configs.EMBEDDING_MODEL || DEFAULTS.EMBEDDING_MODEL,
        dimension: embeddingDim.value,
        api_url: configs.EMBEDDING_API_URL || DEFAULTS.EMBEDDING_API_URL,
        chroma_url: configs.CHROMA_URL || DEFAULTS.CHROMA_URL,
        chroma_collection: configs.CHROMA_COLLECTION || DEFAULTS.CHROMA_COLLECTION,
        chroma_distance: configs.CHROMA_DISTANCE || DEFAULTS.CHROMA_DISTANCE,
        chroma_vector_count: configs.CHROMA_VECTOR_COUNT || DEFAULTS.CHROMA_VECTOR_COUNT,
        api_key_ref: embeddingKeyRef,
      }),
    })
    payloads.push({ key: 'model_profiles', value: JSON.stringify(modelProfiles.value) })
    if (nextEmbeddingApiKey) payloads.push({ key: embeddingKeyRef, value: nextEmbeddingApiKey })
  } else if (activeTab.value === 'retrieval') {
    if (!retrievalWeightsBalanced.value) {
      normalizeRetrievalWeights()
    }
    payloads.push({
      key: 'retrieval_config',
      value: JSON.stringify({
        top_k: topK.value,
        similarity_threshold: similarityThreshold.value,
        vector_weight: wVec.value,
        graph_weight: wGraph.value,
        dialog_rounds: dialogRounds.value,
        rerank_model: configs.RERANK_MODEL || DEFAULTS.RERANK_MODEL,
        bm25_enabled: bm25Enabled.value,
        stream_enabled: streamEnabled.value,
        system_prompt: configs.SYSTEM_PROMPT || DEFAULTS.SYSTEM_PROMPT,
      }),
    })
  } else if (activeTab.value === 'docparse') {
    payloads.push({
      key: 'chunk_config',
      value: JSON.stringify({
        chunk_size: chunkSize.value,
        chunk_overlap: chunkOverlap.value,
        min_chunk_size: minChunkSize.value,
        strategy: configs.CHUNK_STRATEGY || DEFAULTS.CHUNK_STRATEGY,
      }),
    })
    payloads.push({
      key: 'upload_config',
      value: JSON.stringify({
        max_file_size_mb: maxFileSize.value,
        max_files_per_upload: maxUploadFiles.value,
        auto_parse: autoParse.value,
        allowed_formats: ['pdf', 'docx', 'txt', 'md'],
        pdf_parser: configs.PDF_PARSER || DEFAULTS.PDF_PARSER,
        word_parser: configs.WORD_PARSER || DEFAULTS.WORD_PARSER,
        table_extract: tableExtract.value,
        ocr_enabled: ocrEnabled.value,
      }),
    })
  } else {
    ElMessage.info('系统状态页无需保存配置')
    return
  }

  saving.value = true
  try {
    for (const p of payloads) {
      await request.put(`/config/${p.key}`, { config_value: String(p.value) })
    }

    if (llmProfile && nextLlmApiKey) {
      setProfileApiKeyConfigured('llm', llmProfile.id, true)
      llmApiKeyDirty.value = false
      llmApiKeyMasked.value = true
      llmApiKey.value = ''
      llmApiKeyEditing.value = false
    }
    if (embeddingProfile && nextEmbeddingApiKey) {
      setProfileApiKeyConfigured('embedding', embeddingProfile.id, true)
      embeddingApiKeyDirty.value = false
      embeddingApiKeyMasked.value = true
      embeddingApiKey.value = ''
      embeddingApiKeyEditing.value = false
    }
    ElMessage.success('配置已保存')
  } catch (error) {
    modelProfiles.value = previousProfiles
    activeLlmProfileId.value = previousLlmId
    activeEmbeddingProfileId.value = previousEmbeddingId
    for (const key of Object.keys(profileApiKeyConfigured)) delete profileApiKeyConfigured[key]
    Object.assign(profileApiKeyConfigured, previousKeyStatus)
    ElMessage.error(`保存失败：${getErrorMessage(error, '请检查登录状态、网络或后端服务')}`)
  } finally {
    saving.value = false
  }
}

function resetConfig() {
  applyDefaults()
  ElMessage.info('已重置为默认值')
}
</script>

<style scoped>
.system-config-page {
  min-height: 100%;
  padding: 0 0 88px;
  color: #1f2937;
}

.config-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 24px;
  margin-bottom: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.eyebrow {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
  text-transform: uppercase;
  letter-spacing: 0;
}

.config-hero h2 {
  margin: 0 0 8px;
  font-size: 22px;
  line-height: 1.25;
  color: #111827;
}

.config-hero p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.hero-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  font-size: 13px;
  color: #374151;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f59e0b;
}

.status-dot.ready {
  background: #16a34a;
}

.config-tabs {
  display: flex;
  gap: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
  margin-bottom: 14px;
  overflow-x: auto;
}

.config-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 38px;
  padding: 0 14px;
  font-size: 14px;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 6px;
  color: #6b7280;
  transition: color 0.18s, background 0.18s, border-color 0.18s;
  white-space: nowrap;
}

.config-tab:hover {
  color: #111827;
  background: #f3f4f6;
}

.config-tab.active {
  color: #1d4ed8;
  border-color: #bfdbfe;
  background: #eff6ff;
  font-weight: 600;
}

.config-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
  padding: 24px;
  margin-bottom: 0;
}

.model-config-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
  align-items: start;
}

.model-editor {
  min-width: 0;
}

.model-profile-panel {
  position: sticky;
  top: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 18px;
  background: #f9fafb;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.panel-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.profile-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-item {
  display: flex;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
  overflow: hidden;
}

.profile-item:hover {
  border-color: #93c5fd;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.1);
  transform: translateY(-1px);
}

.profile-item.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.12);
}

.profile-item-accent {
  width: 4px;
  background: #2563eb;
  flex-shrink: 0;
}

.profile-item-content {
  flex: 1;
  padding: 14px 16px;
  min-width: 0;
}

.profile-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-model {
  font-size: 12px;
  color: #4b5563;
  word-break: break-all;
}

.add-profile-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  width: 100%;
  border: 1px dashed #93c5fd;
  border-radius: 8px;
  background: #ffffff;
  color: #2563eb;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.18s, border-color 0.18s;
}

.add-profile-card:hover {
  border-color: #2563eb;
  background: #eff6ff;
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
  color: #6b7280;
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
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #f9fafb;
  font-size: 13px;
}

.api-key-masked {
  color: #374151;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  letter-spacing: 0;
}

.config-section {
  padding-bottom: 24px;
  margin-bottom: 24px;
  border-bottom: 1px solid #f1f5f9;
}

.config-section:last-child {
  padding-bottom: 0;
  margin-bottom: 0;
  border-bottom: none;
}

.config-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin-top: 0;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #111827;
}

.config-section h3 .badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 400;
}

.badge-required {
  background: #fef2f2;
  color: #dc2626;
}

.config-section .desc {
  font-size: 13px;
  color: #6b7280;
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
  color: #374151;
  margin-bottom: 6px;
  font-weight: 500;
  line-height: 1.4;
}

.form-group label .tip {
  font-weight: 400;
  color: #6b7280;
  font-size: 12px;
}

.form-group label .required {
  color: #dc2626;
  margin-left: 2px;
}

.form-tip {
  font-size: 11px;
  color: #6b7280;
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
  background: #ecfdf5;
  color: #047857;
  border-radius: 4px;
  font-size: 12px;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.weight-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  background: #f0fdf4;
  color: #166534;
  font-size: 13px;
}

.weight-summary.warning {
  border-color: #fde68a;
  background: #fffbeb;
  color: #92400e;
}

/* Status cards */
.status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
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
  background: #2563eb;
}

.status-info {
  flex: 1;
}

.status-info h4 {
  font-size: 14px;
  font-weight: 500;
  margin-top: 0;
  margin-bottom: 4px;
  color: #111827;
}

.status-info p {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 12px;
  flex-shrink: 0;
}

.status-ok {
  background: #f0fdf4;
  color: #16a34a;
}

.status-warn {
  background: #fffbeb;
  color: #d97706;
}

.status-err {
  background: #fef2f2;
  color: #dc2626;
}

.footer-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  background: #fff;
  border: 1px solid #e5e7eb;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  border-radius: 8px;
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.06);
}

.footer-hint,
.footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.footer-hint {
  font-size: 13px;
  color: #4b5563;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  box-shadow: 0 0 0 1px #d1d5db inset;
}

:deep(.el-input__wrapper:hover),
:deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #93c5fd inset;
}

:deep(.el-slider__bar) {
  background-color: #2563eb;
}

:deep(.el-slider__button) {
  border-color: #2563eb;
}

@media (max-width: 1100px) {
  .model-config-card {
    grid-template-columns: 1fr;
  }

  .model-profile-panel {
    position: static;
  }
}

@media (max-width: 760px) {
  .config-hero,
  .footer-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .config-row {
    grid-template-columns: 1fr;
  }

  .config-card {
    padding: 18px;
  }

  .api-key-field {
    align-items: stretch;
    flex-direction: column;
  }

  .footer-actions {
    justify-content: flex-end;
  }

  .panel-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .panel-actions {
    justify-content: flex-start;
  }
}
</style>
