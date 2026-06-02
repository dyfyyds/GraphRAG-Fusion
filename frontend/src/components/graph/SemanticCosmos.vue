<template>
  <div ref="mountRef" class="semantic-cosmos" aria-label="语义宇宙 HUD 3D 知识图谱">
    <!-- Top HUD: High-Tech Cyber Mode Switcher -->
    <div class="cosmos-header-hud">
      <div class="cosmos-logo">
        <h1 class="main-title">语义宇宙</h1>
        <span class="logo-accent">HUD v3.5</span>
      </div>
      <div class="cosmos-mode-switch">
        <button 
          :class="{ active: viewMode === 'cosmos' }" 
          @click="switchMode('cosmos')"
        >
          <span class="btn-indicator"></span>
          <span class="btn-text">语义宇宙 (SPHERE)</span>
        </button>
        <button 
          :class="{ active: viewMode === 'topology' }" 
          @click="switchMode('topology')"
        >
          <span class="btn-indicator"></span>
          <span class="btn-text">宇宙实验室 (NET)</span>
        </button>
      </div>
      <div class="system-time">
        <span class="time-label">SYS_SEC:</span>
        <span class="time-value">{{ systemTime }}</span>
      </div>
    </div>

    <!-- Left HUD: Glassmorphic Dimensions Sidebar -->
    <div class="cosmos-left-sidebar" :class="{ collapsed: leftSidebarCollapsed }">
      <button class="sidebar-toggle-btn" @click="toggleLeftSidebar">
        <span class="arrow-icon">{{ leftSidebarCollapsed ? '▶' : '◀' }}</span>
      </button>
      <div class="sidebar-content">
        <div class="hud-section-header">
          <div class="section-title-zh">学科分歧 / 维度</div>
          <div class="section-title-en">SUBJECT DIVERGENCE / GALAXIES</div>
        </div>
        <ul class="hud-category-list">
          <li 
            v-for="(galaxy, key) in GALAXIES" 
            :key="key" 
            class="hud-category-item"
            :style="{ '--galaxy-color': galaxy.color }"
          >
            <span class="hud-dot"></span>
            <div class="category-info">
              <span class="label-zh">{{ galaxy.name }}</span>
              <span class="label-en">{{ key.toUpperCase() }}</span>
            </div>
            <div class="category-stat">
              <span class="stat-num">{{ getCategoryCount(key) }}</span>
              <span class="stat-unit">NDS</span>
            </div>
          </li>
        </ul>
        <div class="sidebar-footer-stats">
          <div class="footer-stat-item">
            <span class="footer-stat-label">CLUSTER_NET:</span>
            <span class="footer-stat-val text-cyan">ACTIVE</span>
          </div>
          <div class="footer-stat-item">
            <span class="footer-stat-label">GRID_RESOLUTION:</span>
            <span class="footer-stat-val">50x50</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right HUD: Minimalist Glowing Data Panel -->
    <div 
      class="cosmos-right-panel" 
      :style="{ '--panel-glow-color': hudData.color }"
      :class="{ active: isNodeHovered }"
    >
      <div class="right-panel-border-glow"></div>
      <div class="panel-content">
        <div class="panel-node-header">
          <div class="panel-node-main">
            <span class="panel-node-title">{{ hudData.name }}</span>
            <span class="panel-node-subtitle">{{ hudData.typeLabel }} · {{ hudData.relationCount }} 条直接关系</span>
          </div>
          <span 
            class="panel-node-category"
            :style="{ color: hudData.color, borderColor: hudData.color + '40', background: hudData.color + '12' }"
          >
            {{ hudData.categoryLabel }}
          </span>
          <button class="panel-close-btn" title="关闭详情" @click.stop="closeDetailPanel">
            <svg viewBox="0 0 24 24"><path d="M18.3 5.71 12 12l6.3 6.29-1.41 1.41L10.59 13.41 4.29 19.71 2.88 18.3 9.17 12 2.88 5.71 4.29 4.29l6.3 6.3 6.3-6.3 1.41 1.42z"/></svg>
          </button>
        </div>

        <div class="hud-panel-section">
          <div class="panel-section-title">
            <span class="title-bracket">[</span> 实体描述 / DESCRIPTION <span class="title-bracket">]</span>
          </div>
          <p class="panel-text-etymology">{{ hudData.description }}</p>
        </div>

        <div class="hud-panel-section">
          <div class="panel-section-title">
            <span class="title-bracket">[</span> 直接关系 / DIRECT LINKS <span class="title-bracket">]</span>
          </div>
          <ul class="panel-memory-list">
            <li v-for="(point, idx) in hudData.relationItems" :key="idx" class="memory-item">
              <span class="memory-dot" :style="{ background: hudData.color }"></span>
              <span class="memory-text">{{ point }}</span>
            </li>
            <li v-if="!hudData.relationItems.length" class="panel-empty-text">暂无直接关系</li>
          </ul>
        </div>

        <div class="hud-panel-section">
          <div class="panel-section-title">
            <span class="title-bracket">[</span> 图谱属性 / GRAPH META <span class="title-bracket">]</span>
          </div>
          <div class="panel-meta-grid">
            <div class="meta-item"><span>ID</span><strong>{{ hudData.entityId }}</strong></div>
            <div class="meta-item"><span>权重</span><strong>{{ hudData.weight }}</strong></div>
            <div class="meta-item"><span>星系</span><strong>{{ hudData.categoryLabel }}</strong></div>
            <div class="meta-item"><span>类型</span><strong>{{ hudData.typeLabel }}</strong></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom-right Cyber Grid Emblem Overlay -->
    <div class="cosmos-bottom-right-hud">
      <div class="fps-hud">FPS: 60 / WebGL_GLOW</div>
      <svg class="sparkle-svg" viewBox="0 0 100 100">
        <path d="M50 0 L55 45 L100 50 L55 55 L50 100 L45 55 L0 50 L45 45 Z" fill="#ffffff" opacity="0.75"/>
        <circle cx="50" cy="50" r="3.5" fill="#ffffff"/>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { CSS2DObject, CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import gsap from 'gsap'

const props = defineProps({
  entities: { type: Array, default: () => [] },
  relations: { type: Array, default: () => [] },
  selectedEntity: { type: Object, default: null },
  maxNodes: { type: Number, default: 300 },
})

const emit = defineEmits(['select', 'hidden-count'])

const mountRef = ref(null)
const viewMode = ref('cosmos') // 'cosmos' (spheres) or 'topology' (neural net)
const leftSidebarCollapsed = ref(false)
const isNodeHovered = ref(false)
const systemTime = ref('00:00:00')

// Category metadata
const GALAXIES = {
  Society: { name: '社会', color: '#38bdf8', center: [-62, 20, 18] },
  Self: { name: '自我', color: '#fbbf24', center: [-48, -22, -8] },
  Nature: { name: '自然', color: '#34d399', center: [0, 38, -10] },
  Emotion: { name: '情绪', color: '#fb7185', center: [-6, -42, 18] },
  Abstract: { name: '抽象', color: '#a78bfa', center: [28, 8, 30] },
  Knowledge: { name: '知识', color: '#94a3b8', center: [58, 20, -16] },
  Art: { name: '艺术', color: '#f472b6', center: [42, -34, 8] },
  Creation: { name: '创造', color: '#22d3ee', center: [2, -4, -42] },
}

const TYPE_TO_GALAXY = {
  Product: 'Knowledge',
  Department: 'Society',
  Person: 'Self',
  Concept: 'Abstract',
  Process: 'Creation',
  Document: 'Knowledge',
  Policy: 'Society',
  Rule: 'Society',
  Event: 'Emotion',
}

const galaxyKeys = Object.keys(GALAXIES)
const nodeObjects = new Map()
let labelObjects = []
const focusTarget = new THREE.Vector3(0, 0, 0)
const cameraTarget = new THREE.Vector3(0, 0, 185)
const labelWorldPos = new THREE.Vector3()
const labelAnchorPos = new THREE.Vector3()
const labelScreenPos = new THREE.Vector3()
const cameraFocusDir = new THREE.Vector3()
const pickWorldPos = new THREE.Vector3()
const pickScreenPos = new THREE.Vector3()
const pickRadiusPos = new THREE.Vector3()
const cameraRight = new THREE.Vector3()
const cameraUp = new THREE.Vector3()

let scene
let camera
let renderer
let labelRenderer
let labelLayer
let composer
let controls
let animationId = 0
let resizeObserver
let raycaster
let pointer
let dust
let nodeGroup
let linkGroup
let labelGroup
let flowGroup
let gridHelper
let nebulaGroup
let clockTimer
let isCameraAnimating = false

// Hover status
let hoveredNode = null

// Flow particles array for animating logical relationships
const flowParticles = []
const spriteTextureCache = new Map()

// Gesture click tracking to distinguish rotation drags from select clicks
let pointerDownTime = 0
const pointerDownPos = new THREE.Vector2()

// HUD Data Panel state
const hudData = ref({
  name: '系统自检',
  category: 'System',
  categoryLabel: 'SYS_LOAD',
  typeLabel: 'System',
  entityId: '-',
  relationCount: 0,
  weight: '0.0',
  color: '#06b6d4',
  description: '点击一个知识星球后显示企业知识图谱中的真实实体属性与直接关系。',
  relationItems: []
})

const graphNodes = computed(() => buildNodes(props.entities, props.relations))

// 3D Force Relaxation Layout to prevent clumping and overlap of planets/text labels
function runSimple3DForceLayout(nodes, relations, iterations = 130) {
  // 1. Initialize positions with a small noise around their galaxy centers if not preset
  nodes.forEach((node, index) => {
    if (hasCoordinates(node.raw)) return
    const galaxy = GALAXIES[node.category]
    const seed = hash(`${node.id || ''}:${node.name || ''}:${index}`)
    // Initial start within a tighter sphere around galaxy center
    node.position.set(
      galaxy.center[0] + signedNoise(seed, 1) * 18,
      galaxy.center[1] + signedNoise(seed, 2) * 18,
      galaxy.center[2] + signedNoise(seed, 3) * 18
    )
  })

  const nodeByName = new Map(nodes.map(n => [n.name, n]))
  
  // 2. Relaxation iterations
  for (let iter = 0; iter < iterations; iter++) {
    const displacements = nodes.map(() => new THREE.Vector3(0, 0, 0))
    
    // Repulsion between ALL node pairs (avoid clumping/overlapping)
    for (let i = 0; i < nodes.length; i++) {
      const nodeA = nodes[i]
      for (let j = i + 1; j < nodes.length; j++) {
        const nodeB = nodes[j]
        const dx = nodeA.position.x - nodeB.position.x
        const dy = nodeA.position.y - nodeB.position.y
        const dz = nodeA.position.z - nodeB.position.z
        
        let dist = Math.sqrt(dx*dx + dy*dy + dz*dz)
        if (dist < 0.1) dist = 0.1
        
        // Minimum separation distance based on physical planet radius
        const minSep = (visualRadius(nodeA) + visualRadius(nodeB)) * 4.0 + 22
        
        if (dist < minSep) {
          const force = (minSep - dist) / dist * 0.45 // repulsion strength
          const pushX = dx * force
          const pushY = dy * force
          const pushZ = dz * force
          
          displacements[i].x += pushX
          displacements[i].y += pushY
          displacements[i].z += pushZ
          
          displacements[j].x -= pushX
          displacements[j].y -= pushY
          displacements[j].z -= pushZ
        }
      }
    }
    
    // Attraction along logical relations/links
    for (const rel of relations) {
      const nodeA = nodeByName.get(rel.source)
      const nodeB = nodeByName.get(rel.target)
      if (!nodeA || !nodeB) continue
      
      const dx = nodeA.position.x - nodeB.position.x
      const dy = nodeA.position.y - nodeB.position.y
      const dz = nodeA.position.z - nodeB.position.z
      const dist = Math.sqrt(dx*dx + dy*dy + dz*dz)
      
      if (dist > 52) {
        const pull = (dist - 52) * 0.018
        const pullX = (dx / dist) * pull
        const pullY = (dy / dist) * pull
        const pullZ = (dz / dist) * pull
        
        const idxA = nodes.indexOf(nodeA)
        const idxB = nodes.indexOf(nodeB)
        
        displacements[idxA].x -= pullX
        displacements[idxA].y -= pullY
        displacements[idxA].z -= pullZ
        
        displacements[idxB].x += pullX
        displacements[idxB].y += pullY
        displacements[idxB].z += pullZ
      }
    }
    
    // Gravity attraction back to own category center
    nodes.forEach((node, idx) => {
      if (hasCoordinates(node.raw)) return
      const galaxy = GALAXIES[node.category]
      const dx = galaxy.center[0] - node.position.x
      const dy = galaxy.center[1] - node.position.y
      const dz = galaxy.center[2] - node.position.z
      
      displacements[idx].x += dx * 0.022
      displacements[idx].y += dy * 0.022
      displacements[idx].z += dz * 0.022
    })
    
    // Apply displacements
    nodes.forEach((node, idx) => {
      if (hasCoordinates(node.raw)) return
      node.position.x += displacements[idx].x
      node.position.y += displacements[idx].y
      node.position.z += displacements[idx].z
    })
  }
}

function buildNodes(entities, relations) {
  const relationCount = Object.create(null)
  for (const rel of relations) {
    relationCount[rel.source] = (relationCount[rel.source] || 0) + 1
    relationCount[rel.target] = (relationCount[rel.target] || 0) + 1
  }

  const sorted = [...entities]
    .sort((a, b) => (relationCount[b.name] || 0) - (relationCount[a.name] || 0))

  const hidden = Math.max(0, sorted.length - props.maxNodes)
  emit('hidden-count', hidden)

  const nodes = sorted.slice(0, props.maxNodes).map((entity, index) => {
    const category = galaxyFor(entity)
    const galaxy = GALAXIES[category]
    const seed = hash(`${entity.id || ''}:${entity.name || ''}:${index}`)
    const weight = normalizeWeight(entity, relationCount[entity.name] || 0)
    const spread = 34 + Math.max(0, 10 - weight) * 4.2
    const preset = hasCoordinates(entity)
      ? [Number(entity.x), Number(entity.y), Number(entity.z)]
      : [
          galaxy.center[0] + signedNoise(seed, 1) * spread,
          galaxy.center[1] + signedNoise(seed, 2) * spread,
          galaxy.center[2] + signedNoise(seed, 3) * spread,
        ]

    return {
      raw: entity,
      id: entity.id,
      name: entity.name || '未命名实体',
      category,
      color: galaxy.color,
      weight,
      relationCount: relationCount[entity.name] || 0,
      position: new THREE.Vector3(preset[0], preset[1], preset[2]),
    }
  })

  // Run our high-fidelity 3D force layout to relax positions and avoid clumping!
  runSimple3DForceLayout(nodes, relations)

  return nodes
}

function getCategoryCount(category) {
  return graphNodes.value.filter(n => n.category === category).length
}

function toggleLeftSidebar() {
  leftSidebarCollapsed.value = !leftSidebarCollapsed.value
}

function galaxyFor(entity) {
  if (entity.category && GALAXIES[entity.category]) return entity.category
  if (TYPE_TO_GALAXY[entity.entity_type]) return TYPE_TO_GALAXY[entity.entity_type]
  return galaxyKeys[hash(entity.name || entity.entity_type || 'semantic') % galaxyKeys.length]
}

function normalizeWeight(entity, count) {
  const direct = Number(entity.weight || entity.importance || entity.score)
  if (Number.isFinite(direct) && direct > 0) return Math.max(1, Math.min(10, direct))
  return Math.max(1, Math.min(10, 3 + Math.sqrt(count) * 2))
}

function visualRadius(node) {
  return 0.92 + node.weight * 0.26 + Math.min(node.relationCount, 8) * 0.035
}

function hasCoordinates(entity) {
  return ['x', 'y', 'z'].every(key => Number.isFinite(Number(entity[key])))
}

function hash(input) {
  let h = 2166136261
  const text = String(input)
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h >>> 0)
}

function signedNoise(seed, salt) {
  return (((seed * (salt * 9301 + 49297)) % 233280) / 116640) - 1
}

function syncRightPanelData(node) {
  const name = node.name
  const categoryLabel = GALAXIES[node.category]?.name || node.category
  const color = node.color
  const raw = node.raw || {}
  const typeLabel = raw.entity_type || raw.type || node.category || 'Unknown'
  const description = raw.description || raw.desc || raw.summary || raw.content || '该实体暂无描述。'
  const relationItems = props.relations
    .filter(rel => rel.source === name || rel.target === name || rel.source_id === node.id || rel.target_id === node.id)
    .slice(0, 8)
    .map(rel => {
      const relationType = rel.relation_type || rel.rel || rel.type || '关联'
      if (rel.source === name || rel.source_id === node.id) return `${name} → ${relationType} → ${rel.target}`
      return `${rel.source} → ${relationType} → ${name}`
    })
  
  hudData.value = {
    name,
    category: node.category,
    categoryLabel,
    typeLabel,
    entityId: raw.id || node.id || '-',
    relationCount: node.relationCount,
    weight: node.weight.toFixed(1),
    color,
    description,
    relationItems
  }
}

function closeDetailPanel() {
  isNodeHovered.value = false
}

// GSAP Switch Mode Transition Function
function switchMode(newMode) {
  if (viewMode.value === newMode) return
  viewMode.value = newMode
  
  if (newMode === 'topology') {
    // 1. Zoom Camera Out & Pan to Center of Macro Net
    gsap.to(camera.position, {
      x: 0,
      y: 35,
      z: 260,
      duration: 1.8,
      ease: 'power2.inOut',
    })
    gsap.to(controls.target, {
      x: 0,
      y: 0,
      z: 0,
      duration: 1.8,
      ease: 'power2.inOut',
    })

    // 2. Additive Translucent Spheres Fade Out
    if (nodeGroup && nodeGroup.children) {
      nodeGroup.children.forEach(group => {
        group.children.forEach(child => {
          if (child.material) {
            gsap.to(child.material, {
              opacity: child.userData.isRing ? 0.08 : (child.userData.isMoonGroup ? 0.0 : 0.15),
              duration: 1.4,
            })
          }
        })
      })
    }

    // 3. Topology Links and Flowing Energy Particles Fade In
    if (linkGroup && linkGroup.children) {
      linkGroup.children.forEach(line => {
        if (line.material) {
          gsap.to(line.material, {
            opacity: 0.75,
            duration: 1.4,
          })
        }
      })
    }
    if (flowGroup && flowGroup.children) {
      flowGroup.children.forEach(pulse => {
        if (pulse.material) {
          gsap.to(pulse.material, {
            opacity: 1.0,
            duration: 1.4,
          })
        }
      })
    }

    // 4. Intensify Bloom Strength for Network Glow
    gsap.to(composer.passes[1], {
      strength: 1.1,
      duration: 1.4,
    })

    // 5. Hide Digital Grid slightly
    if (gridHelper) {
      gsap.to(gridHelper.material, {
        opacity: 0.05,
        duration: 1.2
      })
    }
  } else {
    // 1. Zoom Camera In to Cosmic Scale
    gsap.to(camera.position, {
      x: 0,
      y: 0,
      z: 185,
      duration: 1.8,
      ease: 'power2.inOut',
    })
    gsap.to(controls.target, {
      x: 0,
      y: 0,
      z: 0,
      duration: 1.8,
      ease: 'power2.inOut',
    })

    // 2. Restore Additive Translucent Spheres Opacities
    if (nodeGroup && nodeGroup.children) {
      nodeGroup.children.forEach(group => {
        group.children.forEach(child => {
          if (child.material) {
            const targetOpacity = child.userData.isRing ? 0.22 : (child.userData.isMoonGroup ? 0.62 : 0.42)
            gsap.to(child.material, {
              opacity: targetOpacity,
              duration: 1.4,
            })
          }
        })
      })
    }

    // 3. Reset Topology Links and Particles Opacities
    if (linkGroup && linkGroup.children) {
      linkGroup.children.forEach(line => {
        if (line.material) {
          gsap.to(line.material, {
            opacity: 0.11,
            duration: 1.4,
          })
        }
      })
    }
    if (flowGroup && flowGroup.children) {
      flowGroup.children.forEach(pulse => {
        if (pulse.material) {
          gsap.to(pulse.material, {
            opacity: 0.36,
            duration: 1.4,
          })
        }
      })
    }

    // 4. Reset Bloom Strength to Normal
    gsap.to(composer.passes[1], {
      strength: 0.62,
      duration: 1.4,
    })

    // 5. Restore Digital Grid
    if (gridHelper) {
      gsap.to(gridHelper.material, {
        opacity: 0.08,
        duration: 1.2
      })
    }
  }
}

function initScene() {
  if (!mountRef.value) return

  scene = new THREE.Scene()
  scene.background = new THREE.Color('#000000') // pure black background for sci-fi look
  scene.fog = new THREE.FogExp2('#000000', 0.0035)

  camera = new THREE.PerspectiveCamera(58, 1, 0.1, 1200)
  camera.position.set(0, 0, 185)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 0.92
  mountRef.value.appendChild(renderer.domElement)

  labelRenderer = new CSS2DRenderer()
  labelRenderer.domElement.className = 'cosmos-label-layer'
  labelRenderer.domElement.style.position = 'absolute'
  labelRenderer.domElement.style.top = '0'
  labelRenderer.domElement.style.left = '0'
  labelRenderer.domElement.style.pointerEvents = 'none' // CRITICAL: Inline style to bypass any scoped CSS pointer interception!
  mountRef.value.appendChild(labelRenderer.domElement)

  labelLayer = document.createElement('div')
  labelLayer.className = 'cosmos-manual-label-layer'
  labelLayer.style.position = 'absolute'
  labelLayer.style.inset = '0'
  labelLayer.style.pointerEvents = 'none'
  mountRef.value.appendChild(labelLayer)

  // FIX: Attach OrbitControls directly to renderer.domElement (the WebGL canvas) so drags and scrolls are captured perfectly,
  // bypassing the overlays of CSS2DRenderer which intercept and block pointer events!
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 42
  controls.maxDistance = 360
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.12
  controls.addEventListener('start', handleControlStart)

  // 1. Digital Grid Helper (HUD aesthetic net)
  gridHelper = new THREE.GridHelper(520, 52, '#06b6d4', '#1e1b4b')
  gridHelper.position.y = -80
  gridHelper.material.transparent = true
  gridHelper.material.opacity = 0.08
  scene.add(gridHelper)

  // 2. High-power Directional & Ambient Lights (Essential for transparent Physical Glass refraction)
  scene.add(new THREE.AmbientLight('#dbeafe', 0.24))
  
  const dirLight1 = new THREE.DirectionalLight('#7dd3fc', 1.05)
  dirLight1.position.set(100, 150, 50)
  scene.add(dirLight1)
  
  const dirLight2 = new THREE.DirectionalLight('#f0abfc', 0.64)
  dirLight2.position.set(-100, -100, -50)
  scene.add(dirLight2)

  // 3. Setup effects
  const renderPass = new RenderPass(scene, camera)
  const bloomPass = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.62, 0.42, 0.18)
  composer = new EffectComposer(renderer)
  composer.addPass(renderPass)
  composer.addPass(bloomPass)

  raycaster = new THREE.Raycaster()
  pointer = new THREE.Vector2()

  // 4. Slow Flowing Nebulae Stars
  createDust()
  renderCosmos()
  resize()

  // Real-time HUD system clock tick
  clockTimer = setInterval(() => {
    const d = new Date()
    systemTime.value = d.toTimeString().split(' ')[0]
  }, 1000)

  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(mountRef.value)
  
  // Separation hooks
  renderer.domElement.addEventListener('pointerdown', handlePointerDown)
  renderer.domElement.addEventListener('pointerup', handlePointerUp)
  window.addEventListener('pointermove', onPointerMove)
  animate()
}

function onPointerMove(event) {
  if (!renderer || !camera || !mountRef.value) return
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
}

function handleControlStart() {
  isCameraAnimating = false
  controls.autoRotate = false
  gsap.killTweensOf(camera.position)
  gsap.killTweensOf(controls.target)
  gsap.killTweensOf(cameraTarget)
  gsap.killTweensOf(focusTarget)
}

function animateCameraTo(targetPosition, targetLookAt, duration = 1.15) {
  if (!camera || !controls) return
  isCameraAnimating = true
  gsap.killTweensOf(camera.position)
  gsap.killTweensOf(controls.target)
  gsap.to(camera.position, {
    x: targetPosition.x,
    y: targetPosition.y,
    z: targetPosition.z,
    duration,
    ease: 'power2.out',
    onUpdate: () => controls.update(),
    onComplete: () => {
      camera.position.copy(targetPosition)
      controls.target.copy(targetLookAt)
      controls.update()
      isCameraAnimating = false
    }
  })
  gsap.to(controls.target, {
    x: targetLookAt.x,
    y: targetLookAt.y,
    z: targetLookAt.z,
    duration,
    ease: 'power2.out',
    onUpdate: () => controls.update()
  })
}

function createDust() {
  const positions = []
  const colors = []

  // Global subtle stars
  const globalCount = 1800
  for (let i = 0; i < globalCount; i++) {
    const radius = 180 + Math.random() * 450
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    const px = radius * Math.sin(phi) * Math.cos(theta)
    const py = radius * Math.sin(phi) * Math.sin(theta)
    const pz = radius * Math.cos(phi)
    
    positions.push(px, py, pz)
    const val = 0.35 + Math.random() * 0.45
    colors.push(val * 0.5, val * 0.72, val)
  }

  // Clusters dense particle clouds
  Object.keys(GALAXIES).forEach((key) => {
    const galaxy = GALAXIES[key]
    const color = new THREE.Color(galaxy.color)
    const pCount = 300
    for (let j = 0; j < pCount; j++) {
      const u = Math.random()
      const r = (u * u) * 25 + 2.5
      const angle = Math.random() * Math.PI * 2 + (r * 0.15)
      const spreadY = (Math.random() - 0.5) * 5.5 * (1 - r / 28)

      const lx = r * Math.cos(angle)
      const lz = r * Math.sin(angle)
      const ly = spreadY

      const px = galaxy.center[0] + lx
      const py = galaxy.center[1] + ly
      const pz = galaxy.center[2] + lz

      positions.push(px, py, pz)
      const colorVar = 0.8 + Math.random() * 0.25
      colors.push(color.r * colorVar, color.g * colorVar, color.b * colorVar)
    }
  })

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  const material = new THREE.PointsMaterial({
    map: getNebulaTexture(),
    size: 1.9,
    vertexColors: true,
    transparent: true,
    opacity: 0.18,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    alphaTest: 0.01,
  })
  dust = new THREE.Points(geometry, material)
  scene.add(dust)
  createNebulaClouds()
}

function createNebulaClouds() {
  if (nebulaGroup) {
    scene.remove(nebulaGroup)
    nebulaGroup.traverse(obj => {
      if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose?.())
      else obj.material?.dispose?.()
    })
  }
  nebulaGroup = new THREE.Group()
  Object.entries(GALAXIES).forEach(([key, galaxy], galaxyIndex) => {
    const color = new THREE.Color(galaxy.color)
    for (let i = 0; i < 4; i++) {
      const seed = hash(`nebula:${key}:${i}`)
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
        map: getNebulaTexture(),
        color,
        transparent: true,
        opacity: 0.055 + i * 0.01,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      }))
      sprite.position.set(
        galaxy.center[0] + signedNoise(seed, 1) * 34,
        galaxy.center[1] + signedNoise(seed, 2) * 18,
        galaxy.center[2] + signedNoise(seed, 3) * 28
      )
      sprite.scale.set(
        46 + (galaxyIndex % 3) * 12 + i * 9,
        22 + (i % 2) * 14,
        1
      )
      sprite.rotation.z = signedNoise(seed, 4) * Math.PI
      nebulaGroup.add(sprite)
    }
  })
  scene.add(nebulaGroup)
}

function renderCosmos() {
  if (!scene) return
  clearGraphObjects()
  nodeObjects.clear()

  nodeGroup = new THREE.Group()
  linkGroup = new THREE.Group()
  labelGroup = new THREE.Group()
  flowGroup = new THREE.Group()
  scene.add(linkGroup, flowGroup, nodeGroup, labelGroup)

  const visibleNames = new Set(graphNodes.value.map(node => node.name))
  const nodeByName = new Map(graphNodes.value.map(node => [node.name, node]))
  createLinks(visibleNames, nodeByName)

  for (const node of graphNodes.value) {
    createPlanet(node)
  }

  focusSelected(props.selectedEntity)
}

function createLinks(visibleNames, nodeByName) {
  const seen = new Set()
  flowParticles.length = 0

  for (const rel of props.relations) {
    if (!visibleNames.has(rel.source) || !visibleNames.has(rel.target)) continue
    const key = `${rel.source}->${rel.target}:${rel.relation_type || rel.rel || ''}`
    if (seen.has(key)) continue
    seen.add(key)

    const source = nodeByName.get(rel.source)
    const target = nodeByName.get(rel.target)
    
    // 1. Connection lines
    const geometry = new THREE.BufferGeometry().setFromPoints([source.position, target.position])
    const material = new THREE.LineBasicMaterial({
      color: target.color,
      transparent: true,
      opacity: 0.11,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    linkGroup.add(new THREE.Line(geometry, material))

    // 2. Glowing photon flow particle
    const pulseGeom = new THREE.SphereGeometry(0.24, 8, 8)
    const pulseMat = new THREE.MeshBasicMaterial({
      color: target.color,
      transparent: true,
      opacity: 0.36,
      blending: THREE.AdditiveBlending,
    })
    const pulse = new THREE.Mesh(pulseGeom, pulseMat)
    flowGroup.add(pulse)

    flowParticles.push({
      mesh: pulse,
      source: source.position,
      target: target.position,
      speed: 0.28 + Math.random() * 0.32,
      offset: Math.random()
    })
  }
}

function createPlanet(node) {
  const radius = visualRadius(node)
  const color = new THREE.Color(node.color)
  const darkColor = color.clone().multiplyScalar(0.34)
  const group = new THREE.Group()
  group.position.copy(node.position)
  group.userData.node = node

  // 1. Layered planet body: dark glass shell + controlled emissive edge, not a blown-out light blob.
  const sphereGeom = new THREE.SphereGeometry(radius, 48, 24)
  const sphereMat = new THREE.MeshPhysicalMaterial({
    color: darkColor,
    emissive: color,
    emissiveIntensity: node.weight >= 8 ? 0.24 : 0.12,
    roughness: 0.34,
    metalness: 0.08,
    transmission: 0.2,
    thickness: 0.65,
    clearcoat: 0.9,
    clearcoatRoughness: 0.18,
    transparent: true,
    opacity: 0.88,
    depthWrite: false
  })
  const sphere = new THREE.Mesh(sphereGeom, sphereMat)
  sphere.userData.node = node
  sphere.userData.pickNode = node
  group.add(sphere)

  // 2. Small inner core, intentionally dim so the 3D form remains readable.
  const coreGeom = new THREE.SphereGeometry(radius * 0.26, 32, 16)
  const coreMat = new THREE.MeshBasicMaterial({
    color: color.clone().lerp(new THREE.Color('#ffffff'), 0.18),
    transparent: true,
    opacity: node.weight >= 8 ? 0.24 : 0.16,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  })
  const core = new THREE.Mesh(coreGeom, coreMat)
  core.userData.pickNode = node
  group.add(core)

  // 3. Controlled atmospheric halo.
  const haloGeom = new THREE.SphereGeometry(radius * 1.65, 32, 16)
  const haloMat = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: node.weight >= 8 ? 0.07 : 0.04,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  })
  const halo = new THREE.Mesh(haloGeom, haloMat)
  group.add(halo)

  addPlanetSurfaceBands(group, node, radius, color)
  addPlanetDetailShell(group, node, radius, color)

  const glowSprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: getGlowTexture(node.color),
    color,
    transparent: true,
    opacity: node.weight >= 8 ? 0.11 : 0.07,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  }))
  glowSprite.scale.setScalar(radius * (node.weight >= 8 ? 3.7 : 2.8))
  glowSprite.userData.isGlowSprite = true
  group.add(glowSprite)

  // 4. Broad glowing Saturnal rings, close to the reference "knowledge planet" look.
  if (node.weight >= 6.4 || node.relationCount >= 1) {
    const flatRing = new THREE.Mesh(
      new THREE.RingGeometry(radius * 1.62, radius * 2.35, 160),
      new THREE.MeshBasicMaterial({
        color: color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.08,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    )
    flatRing.rotation.x = Math.PI * 0.58
    flatRing.rotation.z = (hash(node.name) % 60) / 100
    flatRing.userData.isRing = true
    group.add(flatRing)

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(radius * 2.05, radius * 0.028, 10, 160),
      new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.22,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    )
    ring.rotation.x = Math.PI * 0.58
    ring.rotation.z = (hash(node.name) % 40) / 100
    ring.userData.isRing = true
    group.add(ring)

    if (node.weight >= 8.6 || node.relationCount >= 5) {
      const secondRing = ring.clone()
      secondRing.material = ring.material.clone()
      secondRing.material.opacity = 0.14
      secondRing.scale.setScalar(1.18)
      secondRing.rotation.x = Math.PI * 0.43
      secondRing.rotation.z = -0.42
      secondRing.userData.isRing = true
      group.add(secondRing)
    }
  }

  // 5. Wireframe concept shells add the gem/polyhedron variation visible in the reference.
  if ((node.weight >= 6.8 || node.relationCount >= 2) && ['Abstract', 'Art', 'Creation'].includes(node.category)) {
    const wire = new THREE.Mesh(
      new THREE.IcosahedronGeometry(radius * 1.34, 1),
      new THREE.MeshBasicMaterial({
        color,
        wireframe: true,
        transparent: true,
        opacity: 0.2,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    )
    wire.rotation.x = 0.38
    wire.rotation.z = 0.72
    wire.userData.isWireShell = true
    wire.userData.pickNode = node
    group.add(wire)
  }

  // 6. Orbiting little satellite moons
  if (node.weight >= 8.8 || node.relationCount >= 5) {
    const moonGroup = new THREE.Group()
    const moonRadius = radius * 0.14
    const moonCount = node.weight >= 9.5 ? 3 : 2
    for (let i = 0; i < moonCount; i++) {
      const moon = new THREE.Mesh(
        new THREE.SphereGeometry(moonRadius * (i === 0 ? 1 : 0.72), 16, 16),
        new THREE.MeshBasicMaterial({
          color: new THREE.Color(i === 0 ? '#ffffff' : node.color),
          transparent: true,
          opacity: 0.86,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        })
      )
      const angle = (Math.PI * 2 * i) / moonCount
      moon.position.set(Math.cos(angle) * radius * (2.15 + i * 0.34), Math.sin(angle) * radius * 0.24, Math.sin(angle) * radius * 1.4)
      moonGroup.add(moon)
    }
    
    moonGroup.rotation.x = Math.random() * Math.PI
    moonGroup.rotation.y = Math.random() * Math.PI
    moonGroup.userData.isMoonGroup = true
    moonGroup.userData.orbitSpeed = 0.012 + (hash(node.name) % 10) * 0.003
    group.add(moonGroup)
  }

  // 7. Local star dust and semantic debris around important/highly connected nodes.
  if (node.weight >= 7 || node.relationCount >= 3) {
    group.add(createLocalDustCluster(node, radius, color))
  }

  // 8. Labels stay anchored to planets, but visibility is distance/importance gated.
  const label = document.createElement('div')
  label.className = 'cosmos-label'
  label.textContent = node.name
  label.style.pointerEvents = 'none'
  label.style.setProperty('--glow-color', node.color)
  label.style.setProperty('--label-opacity', '0')
  labelLayer?.appendChild(label)
  labelObjects.push({
    element: label,
    node,
    radius,
    baseOpacity: Math.min(0.95, 0.56 + node.weight * 0.035),
  })

  // 9. Add group to scene nodeGroup and save in nodeObjects map for hover/focus interactions
  if (nodeGroup) {
    nodeGroup.add(group)
  }
  nodeObjects.set(node.id, group)
  nodeObjects.set(node.name, group)
}

function getGlowTexture(color) {
  if (spriteTextureCache.has(color)) return spriteTextureCache.get(color)
  const canvas = document.createElement('canvas')
  canvas.width = 128
  canvas.height = 128
  const ctx = canvas.getContext('2d')
  const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64)
  gradient.addColorStop(0, 'rgba(255,255,255,0.95)')
  gradient.addColorStop(0.18, `${color}dd`)
  gradient.addColorStop(0.52, `${color}55`)
  gradient.addColorStop(1, `${color}00`)
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 128, 128)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  spriteTextureCache.set(color, texture)
  return texture
}

function getNebulaTexture() {
  const key = '__nebula_soft_sprite__'
  if (spriteTextureCache.has(key)) return spriteTextureCache.get(key)
  const canvas = document.createElement('canvas')
  canvas.width = 128
  canvas.height = 128
  const ctx = canvas.getContext('2d')
  const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64)
  gradient.addColorStop(0, 'rgba(255,255,255,0.78)')
  gradient.addColorStop(0.22, 'rgba(255,255,255,0.46)')
  gradient.addColorStop(0.56, 'rgba(255,255,255,0.12)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 128, 128)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  spriteTextureCache.set(key, texture)
  return texture
}

function addPlanetSurfaceBands(group, node, radius, color) {
  const seed = hash(`surface:${node.name}`)
  const bandCount = node.weight >= 8 ? 5 : 4
  for (let i = 0; i < bandCount; i++) {
    const bandRadius = radius * (0.74 + i * 0.055)
    const tube = Math.max(0.006, radius * 0.007)
    const band = new THREE.Mesh(
      new THREE.TorusGeometry(bandRadius, tube, 6, 112),
      new THREE.MeshBasicMaterial({
        color: color.clone().lerp(new THREE.Color('#ffffff'), 0.2),
        transparent: true,
        opacity: 0.1 - i * 0.01,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    )
    band.rotation.x = Math.PI * (0.5 + signedNoise(seed, i + 5) * 0.055)
    band.rotation.y = signedNoise(seed, i + 11) * 0.45
    band.rotation.z = signedNoise(seed, i + 17) * 0.22
    band.userData.isSurfaceBand = true
    group.add(band)
  }

  const meridianCount = node.weight >= 8 ? 3 : 2
  for (let i = 0; i < meridianCount; i++) {
    const meridian = new THREE.Mesh(
      new THREE.TorusGeometry(radius * 1.015, Math.max(0.006, radius * 0.006), 6, 112),
      new THREE.MeshBasicMaterial({
        color: color.clone().lerp(new THREE.Color('#ffffff'), 0.1),
        transparent: true,
        opacity: 0.065,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    )
    meridian.rotation.y = Math.PI * 0.5
    meridian.rotation.x = signedNoise(seed, i + 29) * 0.46
    meridian.rotation.z = (Math.PI / meridianCount) * i + signedNoise(seed, i + 31) * 0.18
    meridian.userData.isSurfaceBand = true
    group.add(meridian)
  }

  const equator = new THREE.Mesh(
    new THREE.TorusGeometry(radius * 1.08, Math.max(0.008, radius * 0.009), 8, 144),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.11,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  )
  equator.rotation.x = Math.PI * 0.5
  equator.rotation.z = signedNoise(seed, 41) * 0.35
  equator.userData.isSurfaceBand = true
  group.add(equator)

  group.add(createPlanetSurfaceSpeckles(node, radius, color))

  const terminator = new THREE.Mesh(
    new THREE.SphereGeometry(radius * 1.006, 48, 24),
    new THREE.MeshBasicMaterial({
      color: '#020617',
      transparent: true,
      opacity: 0.18,
      depthWrite: false
    })
  )
  terminator.scale.set(1.02, 1.02, 0.82)
  terminator.position.set(radius * 0.2, -radius * 0.12, -radius * 0.18)
  terminator.userData.isTerminator = true
  group.add(terminator)
}

function addPlanetDetailShell(group, node, radius, color) {
  const seed = hash(`shell:${node.name}`)
  const shellOpacity = node.weight >= 7 ? 0.12 : 0.075
  const shell = new THREE.Mesh(
    new THREE.OctahedronGeometry(radius * 1.32, 1),
    new THREE.MeshBasicMaterial({
      color: color.clone().lerp(new THREE.Color('#ffffff'), 0.12),
      wireframe: true,
      transparent: true,
      opacity: shellOpacity,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  )
  shell.rotation.x = signedNoise(seed, 5) * 0.8
  shell.rotation.y = signedNoise(seed, 7) * 0.8
  shell.rotation.z = signedNoise(seed, 9) * 0.8
  shell.userData.isWireShell = true
  group.add(shell)

  const arcCount = node.weight >= 8 || node.relationCount >= 3 ? 3 : 2
  for (let i = 0; i < arcCount; i++) {
    const arc = new THREE.Mesh(
      new THREE.TorusGeometry(radius * (1.28 + i * 0.15), Math.max(0.006, radius * 0.006), 6, 128),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.065 - i * 0.012,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    )
    arc.rotation.x = Math.PI * (0.36 + Math.abs(signedNoise(seed, i + 13)) * 0.26)
    arc.rotation.y = signedNoise(seed, i + 17) * 0.5
    arc.rotation.z = signedNoise(seed, i + 19) * 0.7
    arc.userData.isDetailArc = true
    group.add(arc)
  }
}

function createPlanetSurfaceSpeckles(node, radius, color) {
  const positions = []
  const colors = []
  const seed = hash(`speckles:${node.name}`)
  const count = node.weight >= 8 ? 42 : 24
  for (let i = 0; i < count; i++) {
    const theta = Math.PI * 2 * Math.abs(signedNoise(seed, i + 3))
    const phi = Math.PI * (0.24 + Math.abs(signedNoise(seed, i + 9)) * 0.52)
    const shell = radius * 1.018
    const px = Math.sin(phi) * Math.cos(theta) * shell
    const py = Math.cos(phi) * shell
    const pz = Math.sin(phi) * Math.sin(theta) * shell
    positions.push(px, py, pz)
    const intensity = 0.55 + Math.abs(signedNoise(seed, i + 15)) * 0.24
    const c = color.clone().lerp(new THREE.Color('#ffffff'), 0.22).multiplyScalar(intensity)
    colors.push(c.r, c.g, c.b)
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  const material = new THREE.PointsMaterial({
    map: getNebulaTexture(),
    size: Math.max(0.08, radius * 0.09),
    vertexColors: true,
    transparent: true,
    opacity: 0.18,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    alphaTest: 0.01,
  })
  const points = new THREE.Points(geometry, material)
  points.userData.isSurfaceSpeckles = true
  return points
}

function createLocalDustCluster(node, radius, color) {
  const positions = []
  const colors = []
  const particleCount = Math.min(110, 26 + Math.round(node.weight * 4) + node.relationCount * 8)
  const seed = hash(`dust:${node.name}`)
  for (let i = 0; i < particleCount; i++) {
    const ringBias = i / particleCount
    const angle = ringBias * Math.PI * 16 + signedNoise(seed, i + 7) * 0.55
    const spread = radius * (2.25 + Math.abs(signedNoise(seed, i + 13)) * 2.6)
    const flatness = 0.18 + (hash(`${node.name}:${i}`) % 40) / 160
    positions.push(
      Math.cos(angle) * spread,
      signedNoise(seed, i + 19) * radius * 1.1,
      Math.sin(angle) * spread * flatness
    )
    const intensity = 0.72 + Math.abs(signedNoise(seed, i + 23)) * 0.36
    colors.push(color.r * intensity, color.g * intensity, color.b * intensity)
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  const material = new THREE.PointsMaterial({
    map: getNebulaTexture(),
    size: Math.max(0.8, radius * 0.34),
    vertexColors: true,
    transparent: true,
    opacity: 0.13,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    alphaTest: 0.01,
  })
  const points = new THREE.Points(geometry, material)
  points.rotation.x = Math.PI * 0.58
  points.rotation.z = (hash(node.name) % 120) / 100
  points.userData.isLocalDust = true
  return points
}

function clearGraphObjects() {
  labelObjects.forEach(labelObj => labelObj.element?.remove?.())
  labelObjects = []

  for (const group of [nodeGroup, linkGroup, labelGroup, flowGroup]) {
    if (!group) continue
    scene.remove(group)
    group.traverse(obj => {
      obj.geometry?.dispose?.()
      if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose?.())
      else obj.material?.dispose?.()
      if (obj.element?.remove) obj.element.remove()
    })
  }
  nodeGroup = null
  linkGroup = null
  labelGroup = null
  flowGroup = null
  flowParticles.length = 0
}

function handlePointerDown(event) {
  pointerDownTime = performance.now()
  pointerDownPos.set(event.clientX, event.clientY)
}

function handlePointerUp(event) {
  const duration = performance.now() - pointerDownTime
  const distance = Math.hypot(event.clientX - pointerDownPos.x, event.clientY - pointerDownPos.y)
  
  if (duration < 300 && distance < 6) {
    onCanvasClick(event)
  }
}

function onCanvasClick(event) {
  if (!renderer || !camera || !nodeGroup) return
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  let node = findNodeFromScreenPoint(event, rect)
  if (!node) {
    raycaster.setFromCamera(pointer, camera)
    const hits = raycaster.intersectObjects(nodeGroup.children, true)
    node = findNodeFromHit(hits)
  }
  
  if (node) {
    emit('select', node.raw)
    focusNode(node)
    syncRightPanelData(node)
    isNodeHovered.value = true
  } else {
    // Clicked empty space
    closePopup()
  }
}

function findNodeFromScreenPoint(event, rect) {
  if (!camera) return null

  cameraRight.setFromMatrixColumn(camera.matrixWorld, 0).normalize()
  let best = null
  let bestScore = Infinity

  for (const node of graphNodes.value) {
    const group = nodeObjects.get(node.id) || nodeObjects.get(node.name)
    if (!group) continue

    group.getWorldPosition(pickWorldPos)
    pickScreenPos.copy(pickWorldPos).project(camera)
    if (
      pickScreenPos.z < -1 ||
      pickScreenPos.z > 1 ||
      pickScreenPos.x < -1.16 ||
      pickScreenPos.x > 1.16 ||
      pickScreenPos.y < -1.16 ||
      pickScreenPos.y > 1.16
    ) {
      continue
    }

    const cx = (pickScreenPos.x * 0.5 + 0.5) * rect.width + rect.left
    const cy = (-pickScreenPos.y * 0.5 + 0.5) * rect.height + rect.top
    pickRadiusPos.copy(pickWorldPos).addScaledVector(cameraRight, visualRadius(node) * 2.15)
    pickRadiusPos.project(camera)
    const rx = (pickRadiusPos.x * 0.5 + 0.5) * rect.width + rect.left
    const screenRadius = Math.abs(rx - cx)
    const threshold = THREE.MathUtils.clamp(screenRadius + 18, 24, 92)
    const dist = Math.hypot(event.clientX - cx, event.clientY - cy)

    if (dist <= threshold) {
      const score = dist - screenRadius * 0.18
      if (score < bestScore) {
        bestScore = score
        best = node
      }
    }
  }

  return best
}

function findNodeFromHit(hits) {
  for (const hit of hits) {
    let current = hit.object
    while (current) {
      if (current.userData?.pickNode) return current.userData.pickNode
      current = current.parent
    }
  }
  return null
}

function closePopup() {
  isNodeHovered.value = false
  emit('select', null)
  resetView()
}

function focusSelected(entity) {
  if (!entity) {
    closePopup()
    return
  }
  const target = nodeObjects.get(entity.id) || nodeObjects.get(entity.name)
  if (target?.userData.node) {
    focusNode(target.userData.node)
    syncRightPanelData(target.userData.node)
    isNodeHovered.value = true
  }
}

function focusNode(node) {
  const targetObject = nodeObjects.get(node.id) || nodeObjects.get(node.name)
  if (targetObject) {
    targetObject.getWorldPosition(focusTarget)
  } else {
    focusTarget.copy(node.position)
  }

  cameraFocusDir.copy(camera.position).sub(controls.target)
  if (cameraFocusDir.lengthSq() < 0.0001) cameraFocusDir.set(0, 0, 1)
  cameraFocusDir.normalize()

  const distance = THREE.MathUtils.clamp(58 + node.weight * 4.2, 62, 108)
  const targetCam = focusTarget.clone().add(cameraFocusDir.multiplyScalar(distance))
  cameraTarget.copy(targetCam)
  animateCameraTo(targetCam, focusTarget.clone(), 0.95)
  controls.autoRotate = false
}

function isSelectedNode(node) {
  const selected = props.selectedEntity
  return !!selected && (selected.id === node.id || selected.name === node.name)
}

function isHoveredNode(node) {
  return !!hoveredNode && (hoveredNode.id === node.id || hoveredNode.name === node.name)
}

function updateLabelVisibility() {
  if (!camera || !renderer || !labelObjects.length) return

  const maxVisible = viewMode.value === 'topology' ? 16 : 24
  const candidates = []
  const width = renderer.domElement.clientWidth || 1
  const height = renderer.domElement.clientHeight || 1
  cameraRight.setFromMatrixColumn(camera.matrixWorld, 0).normalize()

  for (const labelObj of labelObjects) {
    const el = labelObj.element
    const node = labelObj.node
    if (!el || !node) continue

    const group = nodeObjects.get(node.id) || nodeObjects.get(node.name)
    if (group) {
      group.getWorldPosition(labelWorldPos)
    } else {
      labelWorldPos.copy(node.position)
    }

    const distance = camera.position.distanceTo(labelWorldPos)
    labelScreenPos.copy(labelWorldPos).project(camera)

    const selected = isSelectedNode(node)
    const hovered = isHoveredNode(node)
    const sphereOnScreen =
      labelScreenPos.z > -1 &&
      labelScreenPos.z < 1 &&
      labelScreenPos.x > -0.98 &&
      labelScreenPos.x < 0.98 &&
      labelScreenPos.y > -0.98 &&
      labelScreenPos.y < 0.98

    const priority = node.weight + node.relationCount * 0.42
    const distanceLimit = selected || hovered
      ? 180
      : node.weight >= 9
        ? 116
        : node.relationCount >= 5
          ? 96
          : 78
    const readable = sphereOnScreen && (selected || hovered || (distance < distanceLimit && priority >= 5.8))

    if (readable) {
      const sphereX = (labelScreenPos.x * 0.5 + 0.5) * width
      const sphereY = (-labelScreenPos.y * 0.5 + 0.5) * height
      labelAnchorPos.copy(labelWorldPos).addScaledVector(cameraRight, (labelObj.radius || visualRadius(node)) * 1.02)
      pickRadiusPos.copy(labelAnchorPos).project(camera)
      const radiusX = (pickRadiusPos.x * 0.5 + 0.5) * width
      const screenRadius = Math.max(10, Math.abs(radiusX - sphereX))
      candidates.push({
        labelObj,
        distance,
        selected,
        hovered,
        priority,
        x: sphereX,
        y: sphereY - screenRadius - 4,
        score: (selected ? 1200 : 0) + (hovered ? 800 : 0) + priority * 34 - distance,
      })
    } else {
      el.style.display = 'none'
      el.classList.remove('is-focus', 'is-hovered')
    }
  }

  candidates.sort((a, b) => b.score - a.score)
  const visibleSet = new Set(candidates.slice(0, maxVisible).map(item => item.labelObj))

  for (const item of candidates) {
    const el = item.labelObj.element
    if (!visibleSet.has(item.labelObj)) {
      el.style.display = 'none'
      el.classList.remove('is-focus', 'is-hovered')
      continue
    }

    const distanceFade = THREE.MathUtils.clamp(1 - (item.distance - 78) / 138, 0.24, 1)
    const opacity = item.selected || item.hovered
      ? 1
      : Math.min(item.labelObj.baseOpacity, distanceFade)
    el.style.display = 'block'
    el.style.left = `${item.x.toFixed(1)}px`
    el.style.top = `${item.y.toFixed(1)}px`
    el.style.setProperty('--label-opacity', opacity.toFixed(2))
    el.classList.toggle('is-focus', item.selected)
    el.classList.toggle('is-hovered', item.hovered)
  }
}

// Hover Raycaster Detection inside Animation Frame
function updateHoverRaycaster() {
  if (!renderer || !camera || !nodeGroup) return
  raycaster.setFromCamera(pointer, camera)
  const hits = raycaster.intersectObjects(nodeGroup.children, true)
  const node = findNodeFromHit(hits)
  
  if (node) {
    if (hoveredNode !== node) {
      // Unscale previous hovered node smoothly
      if (hoveredNode) {
        const prevGroup = nodeObjects.get(hoveredNode.id)
        if (prevGroup) {
          gsap.to(prevGroup.scale, { x: 1.0, y: 1.0, z: 1.0, duration: 0.35, overwrite: 'auto' })
        }
      }
      
      hoveredNode = node
      // Hover only changes the planet affordance; the data panel opens on click/selection.
      
      // Scale up current hovered node smoothly using GSAP
      const currentGroup = nodeObjects.get(node.id)
      if (currentGroup) {
        gsap.to(currentGroup.scale, { x: 1.18, y: 1.18, z: 1.18, duration: 0.35, overwrite: 'auto' })
      }
      
    }
  } else {
    // If we were hovering, smoothly scale back to 1.0
    if (hoveredNode) {
      const prevGroup = nodeObjects.get(hoveredNode.id)
      if (prevGroup) {
        gsap.to(prevGroup.scale, { x: 1.0, y: 1.0, z: 1.0, duration: 0.35, overwrite: 'auto' })
      }
      hoveredNode = null
    }
  }
}

// Zoom Bloom Amplification based on Camera Distance
function updateCameraDistanceGlow() {
  if (!camera || !composer || !controls) return
  const dist = camera.position.distanceTo(controls.target)
  
  if (viewMode.value === 'topology') {
    const minD = 42
    const maxD = 220
    const factor = Math.max(0, Math.min(1, (dist - minD) / (maxD - minD)))
    
    // Zoomed in close -> expand bloom glow intensely!
    const targetBloom = 1.28 - factor * 0.52
    composer.passes[1].strength = THREE.MathUtils.lerp(composer.passes[1].strength, targetBloom, 0.05)
  }
}

function zoomIn() {
  const dir = camera.position.clone().sub(controls.target).multiplyScalar(0.78)
  const targetCam = controls.target.clone().add(dir)
  animateCameraTo(targetCam, controls.target.clone(), 0.6)
  controls.autoRotate = false
}

function zoomOut() {
  const dir = camera.position.clone().sub(controls.target).multiplyScalar(1.28)
  const targetCam = controls.target.clone().add(dir)
  animateCameraTo(targetCam, controls.target.clone(), 0.6)
  controls.autoRotate = false
}

function resetView() {
  focusTarget.set(0, 0, 0)
  cameraTarget.set(0, 0, 185)
  animateCameraTo(cameraTarget, focusTarget, 1.2)
  controls.autoRotate = true
}

function fitView() {
  resetView()
}

function resize() {
  if (!mountRef.value || !renderer || !camera) return
  const width = mountRef.value.clientWidth || 1
  const height = mountRef.value.clientHeight || 1
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height, false)
  labelRenderer.setSize(width, height)
  composer.setSize(width, height)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  const elapsed = performance.now() * 0.001

  if (dust) {
    dust.rotation.y += 0.0004
    dust.rotation.x += 0.0001
  }

  // Animate logical flow particles
  if (flowParticles.length) {
    flowParticles.forEach(p => {
      const progress = (elapsed * p.speed + p.offset) % 1.0
      p.mesh.position.lerpVectors(p.source, p.target, progress)
    })
  }

  if (nodeGroup) {
    nodeGroup.children.forEach((group, index) => {
      group.rotation.y += 0.002 + (index % 5) * 0.00018
      const ring = group.children.find(child => child.userData.isRing)
      if (ring) ring.rotation.z += 0.005
      
      const moonGroup = group.children.find(child => child.userData.isMoonGroup)
      if (moonGroup) {
        moonGroup.rotation.y += moonGroup.userData.orbitSpeed
      }
      
      // Pulse outer glow halo (located at index 2 of group children)
      const halo = group.children[2]
      if (halo?.material) halo.material.opacity = 0.14 + Math.sin(elapsed * 1.8 + index) * 0.04
    })
  }

  controls.update()

  // Real-time hover detection
  updateHoverRaycaster()

  // Real-time distance bloom flaring
  updateCameraDistanceGlow()

  // Bind labels to planets while hiding distant and low-priority labels.
  updateLabelVisibility()

  composer.render()
  labelRenderer.render(scene, camera)
}

function disposeScene() {
  cancelAnimationFrame(animationId)
  if (clockTimer) clearInterval(clockTimer)
  resizeObserver?.disconnect()
  renderer?.domElement?.removeEventListener('pointerdown', handlePointerDown)
  renderer?.domElement?.removeEventListener('pointerup', handlePointerUp)
  window.removeEventListener('pointermove', onPointerMove)
  controls?.removeEventListener?.('start', handleControlStart)
  controls?.dispose()
  clearGraphObjects()
  if (dust) {
    scene?.remove(dust)
    dust.geometry.dispose()
    dust.material.dispose()
  }
  if (nebulaGroup) {
    scene?.remove(nebulaGroup)
    nebulaGroup.traverse(obj => {
      if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose?.())
      else obj.material?.dispose?.()
    })
    nebulaGroup = null
  }
  if (gridHelper) {
    scene?.remove(gridHelper)
    gridHelper.geometry.dispose()
    gridHelper.material.dispose()
  }
  renderer?.dispose()
  composer?.dispose?.()
  renderer?.domElement?.remove()
  labelRenderer?.domElement?.remove()
  labelLayer?.remove()
  labelLayer = null
  spriteTextureCache.forEach(texture => texture.dispose?.())
  spriteTextureCache.clear()
}

// Watch props.entities and props.relations directly for instant asynchronous data load triggers!
watch([() => props.entities, () => props.relations], () => {
  nextTick(() => {
    renderCosmos()
  })
}, { deep: true, immediate: true })

watch(() => props.selectedEntity, focusSelected)

onMounted(initScene)
onBeforeUnmount(disposeScene)

defineExpose({ zoomIn, zoomOut, resetView, fitView })
</script>

<style scoped>
/* HUD full viewport style */
.semantic-cosmos {
  position: absolute;
  inset: 0;
  z-index: 3;
  overflow: hidden;
  font-family: 'Outfit', 'Inter', -apple-system, sans-serif;
  background:
    radial-gradient(circle at 54% 42%, rgba(15, 23, 42, 0.34), transparent 34%),
    radial-gradient(circle at 38% 60%, rgba(8, 47, 73, 0.16), transparent 32%),
    #000000;
}

.semantic-cosmos canvas {
  display: block;
  width: 100%;
  height: 100%;
}

:deep(.cosmos-label-layer) {
  position: absolute;
  inset: 0;
  pointer-events: none; /* FIX: Enable clicks to pass right through the label layer! */
  z-index: 4;
}

:deep(.cosmos-manual-label-layer) {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 5;
  overflow: hidden;
}

:deep(.cosmos-label) {
  color: #ffffff;
  font-size: 11px;
  font-weight: 680;
  line-height: 1.18;
  white-space: nowrap;
  position: relative;
  opacity: var(--label-opacity, 0);
  text-shadow: 
    0 1px 2px rgba(0, 0, 0, 0.95),
    0 0 5px color-mix(in srgb, var(--glow-color) 52%, transparent),
    0 0 14px rgba(0, 0, 0, 0.85);
  background: rgba(2, 6, 23, 0.68);
  border: 1px solid color-mix(in srgb, var(--glow-color) 36%, transparent);
  border-radius: 6px;
  padding: 4px 7px 4px;
  max-width: 132px;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none; /* FIX: Make individual labels transparent to mouse pointer clicks! */
  user-select: none;
  position: absolute;
  transform: translate(-50%, -100%);
  backdrop-filter: blur(10px);
  box-shadow:
    0 8px 22px rgba(0, 0, 0, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  transition: opacity 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

:deep(.cosmos-label::after) {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -11px;
  width: 1px;
  height: 10px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--glow-color) 72%, transparent), transparent);
  transform: translateX(-50%);
  opacity: calc(var(--label-opacity, 0) * 0.72);
}

:deep(.cosmos-label.is-focus),
:deep(.cosmos-label.is-hovered) {
  background: rgba(8, 15, 30, 0.86);
  border-color: color-mix(in srgb, var(--glow-color) 70%, rgba(255, 255, 255, 0.2));
  box-shadow:
    0 12px 28px rgba(0, 0, 0, 0.42),
    0 0 16px color-mix(in srgb, var(--glow-color) 28%, transparent);
}

/* ==========================================================================
   HUD Layout Overlays (Tailwind equivalent modern CSS implementation)
   ========================================================================== */

/* 1. Header HUD */
.cosmos-header-hud {
  display: none;
}

.cosmos-logo {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.cosmos-logo .main-title {
  font-size: 18px;
  font-weight: 750;
  color: #ffffff;
  margin: 0;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.35);
}

.cosmos-logo .logo-accent {
  font-size: 9px;
  font-weight: 700;
  font-family: monospace;
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.2);
  padding: 1px 4px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}

/* 2. Cyber Mode Switcher */
.cosmos-mode-switch {
  display: flex;
  gap: 2px;
  background: rgba(0, 0, 0, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 3px;
  border-radius: 30px;
  backdrop-filter: blur(18px);
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.05);
}

.cosmos-mode-switch button {
  background: transparent;
  border: none;
  padding: 7px 14px;
  border-radius: 20px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.24s cubic-bezier(0.4, 0, 0.2, 1);
}

.cosmos-mode-switch button .btn-indicator {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  transition: all 0.24s;
}

.cosmos-mode-switch button.active {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
  text-shadow: 0 0 8px rgba(255, 255, 255, 0.4);
}

.cosmos-mode-switch button.active .btn-indicator {
  background: #06b6d4;
  box-shadow: 0 0 6px #06b6d4, 0 0 12px #06b6d4;
}

.system-time {
  font-family: monospace;
  font-size: 11px;
  display: flex;
  gap: 6px;
  color: rgba(255, 255, 255, 0.4);
}

.system-time .time-value {
  color: #ffffff;
  text-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
}

/* 3. Left Glassmorphic Sidebar HUD */
.cosmos-left-sidebar {
  position: absolute;
  top: auto;
  left: 24px;
  bottom: 32px;
  width: 218px;
  max-height: min(48vh, 430px);
  z-index: 10;
  background: rgba(2, 4, 10, 0.52);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  backdrop-filter: blur(18px);
  box-shadow: 
    0 20px 48px rgba(0, 0, 0, 0.55),
    inset 0 1px 1px rgba(255, 255, 255, 0.05);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: auto;
}

.cosmos-left-sidebar.collapsed {
  transform: translateX(-194px);
  background: rgba(2, 4, 10, 0.4);
}

.sidebar-toggle-btn {
  position: absolute;
  top: 20px;
  right: -16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(10, 15, 30, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 11;
  transition: all 0.2s;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
}

.sidebar-toggle-btn:hover {
  background: #0b0f19;
  color: #ffffff;
  border-color: rgba(6, 182, 212, 0.4);
  box-shadow: 0 0 8px rgba(6, 182, 212, 0.2);
}

.sidebar-content {
  position: absolute;
  inset: 0;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.hud-section-header {
  border-left: 3px solid #06b6d4;
  padding-left: 8px;
  margin-bottom: 12px;
}

.section-title-zh {
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 1px;
}

.section-title-en {
  font-size: 8px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1.2px;
  margin-top: 2px;
}

.hud-category-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.hud-category-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  background: rgba(255, 255, 255, 0.018);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  transition: all 0.2s;
}

.hud-category-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
}

.hud-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--galaxy-color);
  box-shadow: 0 0 6px var(--galaxy-color), 0 0 12px var(--galaxy-color);
  flex-shrink: 0;
}

.category-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.category-info .label-zh {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
}

.category-info .label-en {
  font-size: 8px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.5px;
  margin-top: 1px;
}

.category-stat {
  font-family: monospace;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.category-stat .stat-num {
  font-weight: 700;
}

.category-stat .stat-unit {
  font-size: 7px;
  color: rgba(255, 255, 255, 0.35);
}

.sidebar-footer-stats {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 10px;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.footer-stat-item {
  display: flex;
  justify-content: space-between;
  font-family: monospace;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.35);
}

.footer-stat-val {
  color: rgba(255, 255, 255, 0.7);
}

.text-cyan {
  color: #06b6d4 !important;
  text-shadow: 0 0 6px rgba(6, 182, 212, 0.4);
}

/* 4. Node HUD: Minimalist Glowing Data Panel */
.cosmos-right-panel {
  position: absolute;
  top: 86px;
  left: 24px;
  bottom: auto;
  max-height: min(62vh, 520px);
  width: 300px;
  z-index: 10;
  background: rgba(2, 6, 23, 0.76);
  border: 1px solid rgba(125, 211, 252, 0.16);
  border-radius: 8px;
  backdrop-filter: blur(18px);
  box-shadow: 
    0 20px 48px rgba(0, 0, 0, 0.54),
    inset 0 1px 1px rgba(255, 255, 255, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0;
  transform: translateX(-24px);
  pointer-events: none;
  box-sizing: border-box;
}

/* Faint neon glowing border on active hover status */
.cosmos-right-panel.active {
  opacity: 1.0;
  transform: translateX(0);
  pointer-events: auto;
  border-color: rgba(125, 211, 252, 0.3);
  box-shadow: 
    0 20px 48px rgba(0, 0, 0, 0.62),
    0 0 20px rgba(14, 165, 233, 0.1),
    inset 0 1px 1px rgba(255, 255, 255, 0.1);
}

.panel-content {
  position: relative;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-sizing: border-box;
}

.panel-node-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 24px;
  align-items: start;
  gap: 10px;
  border-bottom: 1px solid rgba(125, 211, 252, 0.12);
  padding-bottom: 12px;
  margin-bottom: 14px;
}

.panel-node-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.panel-node-title {
  font-size: 17px;
  font-weight: 720;
  color: #ffffff;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.panel-node-subtitle {
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  color: rgba(226, 246, 255, 0.54);
}

.panel-node-category {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 7px;
  border-radius: 4px;
  border: 1px solid;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.panel-close-btn {
  width: 24px;
  height: 24px;
  border: 1px solid rgba(125, 211, 252, 0.16);
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: rgba(226, 246, 255, 0.7);
  background: rgba(15, 23, 42, 0.72);
  cursor: pointer;
  transition: background 0.18s, border-color 0.18s, color 0.18s;
}

.panel-close-btn:hover {
  color: #ffffff;
  background: rgba(30, 41, 59, 0.9);
  border-color: rgba(125, 211, 252, 0.34);
}

.panel-close-btn svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

.hud-panel-section {
  margin-bottom: 14px;
}

.hud-panel-section:last-child {
  margin-bottom: 0;
}

.panel-section-title {
  font-family: monospace;
  font-size: 9px;
  font-weight: 700;
  color: rgba(148, 163, 184, 0.78);
  letter-spacing: 1px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.title-bracket {
  color: #38bdf8;
  font-weight: 800;
}

.panel-text-etymology {
  font-size: 12px;
  color: rgba(226, 246, 255, 0.78);
  line-height: 1.6;
  margin: 0;
  overflow-wrap: anywhere;
}

.panel-memory-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-memory-list .memory-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.panel-memory-list .memory-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}

.panel-memory-list .memory-text {
  font-size: 11.5px;
  color: rgba(226, 246, 255, 0.76);
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.panel-empty-text {
  list-style: none;
  padding: 9px 10px;
  color: rgba(148, 163, 184, 0.72);
  background: rgba(15, 23, 42, 0.42);
  border: 1px dashed rgba(125, 211, 252, 0.14);
  border-radius: 6px;
  font-size: 12px;
}

.panel-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.meta-item {
  min-width: 0;
  padding: 8px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.48);
  border: 1px solid rgba(125, 211, 252, 0.12);
}

.meta-item span {
  display: block;
  font-size: 9px;
  color: rgba(148, 163, 184, 0.74);
  margin-bottom: 4px;
}

.meta-item strong {
  display: block;
  font-size: 11px;
  color: rgba(248, 250, 252, 0.9);
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 5. Bottom-Right HUD Overlay */
.cosmos-bottom-right-hud {
  position: absolute;
  bottom: 22px;
  right: 28px;
  z-index: 10;
  pointer-events: none;
  user-select: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.cosmos-bottom-right-hud .fps-hud {
  font-family: monospace;
  font-size: 9px;
  color: rgba(6, 182, 212, 0.6);
  letter-spacing: 0.5px;
  background: rgba(6, 182, 212, 0.05);
  border: 1px solid rgba(6, 182, 212, 0.15);
  padding: 2px 6px;
  border-radius: 3px;
}

.sparkle-svg {
  width: 38px;
  height: 38px;
  filter: drop-shadow(0 0 6px rgba(255, 255, 255, 0.35));
  animation: compassSpin 25s linear infinite;
}

@keyframes compassSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .cosmos-header-hud {
    top: 10px;
    padding: 0 14px;
  }

  .cosmos-mode-switch {
    display: none;
  }

  .system-time {
    display: none;
  }

  .cosmos-left-sidebar {
    left: 12px;
    bottom: 14px;
    width: 190px;
    max-height: 42vh;
  }

  .cosmos-left-sidebar.collapsed {
    transform: translateX(-166px);
  }

  .cosmos-right-panel {
    top: 74px;
    left: 12px;
    width: min(320px, calc(100vw - 24px));
  }

  :deep(.cosmos-label) {
    font-size: 10px;
  }
}
</style>
