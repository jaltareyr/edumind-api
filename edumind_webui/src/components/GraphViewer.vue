<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import Sigma from 'sigma'
import { DirectedGraph } from 'graphology'
import FA2 from 'graphology-layout-forceatlas2'
import louvain from 'graphology-communities-louvain'
import { NodeBorderProgram } from '@sigma/node-border'
import { EdgeCurvedArrowProgram, createEdgeCurveProgram } from '@sigma/edge-curve'
import { EdgeArrowProgram, NodePointProgram, NodeCircleProgram } from 'sigma/rendering'

// Pinia graph store (the JS version we created earlier)
import { useGraphStore } from '@/stores/graph'
import { useHomeStore } from '@/stores/home'

// Refs & store
const containerRef = ref(null)
const graphStore = useGraphStore()
const homeStore = useHomeStore()

// Store-backed state
const isFetching = computed(() => graphStore.isFetching)

// Local UI state (Vuetify controls only)
const enableNodeDrag = ref(true)

// Sigma & current graph
let sigma = null
let currentGraph = null

// --- Default Sigma settings (JS only) ---
const defaultSettings = {
  allowInvalidContainer: true,
  defaultNodeType: 'default',
  defaultEdgeType: 'curvedNoArrow',
  renderEdgeLabels: false,
  labelGridCellSize: 100,
  labelRenderedSizeThreshold: 10,
  enableEdgeEvents: true,
  labelColor: { color: '#000', attribute: 'labelColor' },
  edgeLabelColor: { color: '#000', attribute: 'labelColor' },
  edgeLabelSize: 15,
  labelSize: 20,
  defaultNodeSize: 8,
  minNodeSize: 1,
  maxNodeSize: 12,

  defaultEdgeSize: 8,
  minEdgeSize: 8,
  maxEdgeSize: 20,

  edgeProgramClasses: {
    arrow: EdgeArrowProgram,
    curvedArrow: EdgeCurvedArrowProgram,
    curvedNoArrow: createEdgeCurveProgram(),
  },
  nodeProgramClasses: {
    default: NodeBorderProgram,
    circel: NodeCircleProgram, // keeps parity with your config
    point: NodePointProgram,
  },
}

function goldenHueColor(i) {
  const hue = (i * 0.618033988749895) % 1.0
  const s = 0.8, v = 0.95
  const c = v * s
  const h6 = hue * 6
  const x = c * (1 - Math.abs((h6 % 2) - 1))
  let r=0, g=0, b=0
  if (h6 < 1) [r,g,b] = [c,x,0]
  else if (h6 < 2) [r,g,b] = [x,c,0]
  else if (h6 < 3) [r,g,b] = [0,c,x]
  else if (h6 < 4) [r,g,b] = [0,x,c]
  else if (h6 < 5) [r,g,b] = [x,0,c]
  else [r,g,b] = [0,0,c]
  const m = v - c
  const to255 = (u) => Math.round((u + m) * 255)
  return `rgb(${to255(r)},${to255(g)},${to255(b)})`
}

function computeCommunities(g) {
  if (!g || g.order === 0) return
  louvain.assign(g, { nodeCommunityAttribute: 'community' })
  const comms = new Set()
  g.forEachNode((n, attrs) => comms.add(attrs.community))
  const palette = {}
  Array.from(comms).forEach((c, i) => { palette[String(c)] = goldenHueColor(i) })
  g.forEachNode((n, attrs) => g.setNodeAttribute(n, 'color', palette[String(attrs.community)]))
}

function sizeByDegree(g) {
  if (!g || g.order === 0) return

  g.forEachNode((n) => {
    const d = g.degree(n)
    const MIN = 1, MAX = 40, BASE = 5, GAIN = 4;
    const s = Math.max(MIN, Math.min(MAX, BASE + Math.log2(1 + d) * GAIN));
    g.setNodeAttribute(n, 'size', s)
  })
}

function runSpringLayout(g) {
  if (!g || g.order === 0) return
  FA2.assign(g, {
  iterations: 100,
  settings: {
    scalingRatio: 4,
    gravity: 15,
    strongGravityMode: false,
  }
})
}

function resetCamera() {
  if (!sigma) return 
  const cam = sigma.getCamera()
  // Clear any custom bbox so autoscale fits graph bounds again
  if (sigma.getCustomBBox()) sigma.setCustomBBox(null)
  cam.animatedReset({ duration: 400 })
}

// ---------- Sigma renderer lifecycle ----------
function killRenderer() {
  if (sigma) {
    try { sigma.kill() } catch {}
    sigma = null
  }
  graphStore.setSigmaInstance(null)
}

function createRenderer(g) {
  if (!containerRef.value) return
  killRenderer()
  currentGraph = g || new DirectedGraph()
  sigma = new Sigma(currentGraph, containerRef.value, defaultSettings)
  graphStore.setSigmaInstance(sigma)

  // Cursor
  sigma.on('upNode', onMouseUp)
  sigma.on('mouseupbody', onMouseUp)

  sigma.on('enterNode', () => { containerRef.value.style.cursor = 'pointer' })
  sigma.on('leaveNode', () => { containerRef.value.style.cursor = 'default' })

  // Click select
  sigma.on('clickNode', ({ node }) => {
    if (isDragging || dragMoved) return
    graphStore.setSelectedNode(node, true)
  })

  // Drag support
  sigma.on('downNode', onDownNode)
  sigma.on('mousemovebody', onMouseMove)
  sigma.on('mouseup', onMouseUp)

  // Hover → focused node in store
  sigma.on('enterNode', ({ node }) => graphStore.setFocusedNode(node))
  sigma.on('leaveNode', () => graphStore.setFocusedNode(null))
}

// Drag state/handlers (use currentGraph)
let draggedNode = null
let isDragging = false
let dragMoved = false
let dragStart = { x: 0, y: 0 }
const DRAG_CLICK_EPS = 4
function onDownNode(e) {
  if (!enableNodeDrag.value || !currentGraph) return
  draggedNode = e.node
  isDragging = true
  dragMoved = false
  dragStart = { x: e.x, y: e.y }
  currentGraph.setNodeAttribute(draggedNode, 'highlighted', true)
  e.preventSigmaDefault()
  e.original?.preventDefault?.()
  e.original?.stopPropagation?.()
}
function onMouseMove(e) {
  if (!enableNodeDrag.value || !isDragging || !draggedNode || !sigma || !currentGraph) return

  if (!dragMoved) {
   const dx = e.x - dragStart.x
   const dy = e.y - dragStart.y
   if (dx*dx + dy*dy > DRAG_CLICK_EPS*DRAG_CLICK_EPS) dragMoved = true
  }


  // IMPORTANT: pass explicit x/y to viewportToGraph
  const pos = sigma.viewportToGraph({ x: e.x, y: e.y })
  currentGraph.setNodeAttribute(draggedNode, 'x', pos.x)
  currentGraph.setNodeAttribute(draggedNode, 'y', pos.y)

  e.preventSigmaDefault()
  e.original?.preventDefault?.()
  e.original?.stopPropagation?.()
}

function onMouseUp(e) {
  if (!enableNodeDrag.value) return
  if (draggedNode && currentGraph) {
    currentGraph.removeNodeAttribute(draggedNode, 'highlighted')
    draggedNode = null
  }
  isDragging = false

  e?.preventSigmaDefault?.()
  e?.original?.preventDefault?.()
  e?.original?.stopPropagation?.()
}

watch(
  () => graphStore.sigmaGraph,
  async (newGraph) => {
    createRenderer(newGraph || new DirectedGraph())
    await nextTick()

    if (sigma && newGraph && newGraph.order > 0) {
      try { computeCommunities(newGraph) } catch {}
      sizeByDegree(newGraph)
      runSpringLayout(newGraph)
      sigma.refresh()
      resetCamera()
    }
  },
  { immediate: true }
)

onMounted(() => {
  createRenderer(new DirectedGraph())
})

watch(
  () => graphStore.sigmaGraph,
  (newGraph) => {
    if (!sigma || !newGraph) return
    computeCommunities(newGraph)
    sizeByDegree(newGraph)
    runSpringLayout(newGraph)
    sigma.refresh()
    resetCamera()
  }
)

onBeforeUnmount(() => {
  killRenderer()
})
</script>

<template>
  <div class="graph-viewer" style="position: relative; height: 100%; width: 100%; overflow: hidden;">
    <!-- Controls (Vuetify only) -->
    <v-card
      class="pa-3"
      elevation="8"
      density="comfortable"
      style="position: absolute; top: 12px; left: 12px; z-index: 10; min-width: 220px;"
    >
      <div class="d-flex align-center ga-2">
        <v-btn 
          variant="flat"
          @click="homeStore.loadGraph()"
          prepend-icon="mdi-refresh"
        >
          Refresh
        </v-btn>
        <v-btn color="primary" variant="flat" @click="resetCamera">
          Reset camera
        </v-btn>
        <v-switch
          v-model="enableNodeDrag"
          color="primary"
          hide-details
          inset
          label="Drag nodes"
        />
      </div>
    </v-card>

    <!-- Sigma viewport -->
    <div ref="containerRef" class="sigma-viewport" style="height:100%; width:100%; background:var(--v-theme-background); user-select:none;"></div>

    <!-- Loading overlay (Vuetify only) -->
    <v-overlay
      :model-value="isFetching"
      class="align-center justify-center"
      scrim="rgba(0,0,0,0.65)"
      persistent
    >
      <v-card class="pa-4" elevation="12">
        <div class="d-flex flex-column align-center ga-3">
          <v-progress-circular indeterminate size="32" width="4" color="primary" />
          <div class="text-body-2">Loading Graph Data…</div>
        </div>
      </v-card>
    </v-overlay>
  </div>
</template>
