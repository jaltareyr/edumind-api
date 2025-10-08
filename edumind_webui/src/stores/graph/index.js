import { defineStore } from 'pinia'
import { graphApi } from '@/api'
import { DirectedGraph, MultiDirectedGraph, Graph } from 'graphology'
import { useWorkspaceContextStore } from '../workspaceContext'

function makeGraphFrom(serialized) {
  // Prefer attributes.*; fall back to options.* if that’s what your backend uses
  const attrs = serialized?.attributes ?? {}
  const opts  = serialized?.options ?? {}
  const isMulti    = Boolean(attrs.multi ?? opts.multi)
  const isDirected = (attrs.type ?? opts.type ?? 'directed') !== 'undirected'

  // Choose a concrete class to avoid inconsistency errors
  if (isDirected && isMulti)   return MultiDirectedGraph.from(serialized)
  if (isDirected && !isMulti)  return DirectedGraph.from(serialized)
  // If you ever serve undirected graphs, handle them similarly with the Undirected variants.
  return Graph.from(serialized)  // safe fallback if you use mixed types elsewhere
}

class RawGraph {
  constructor() {
    this.nodes = []                  // Array<RawNodeType>
    this.edges = []                  // Array<RawEdgeType>
    this.nodeIdMap = {}              // nodeId -> index
    this.edgeIdMap = {}              // edgeId -> index
    this.edgeDynamicIdMap = {}       // dynamicId -> index
  }

  getNode(nodeId) {
    const idx = this.nodeIdMap[nodeId]
    return idx !== undefined ? this.nodes[idx] : undefined
  }

  getEdge(edgeId, dynamicId = true) {
    const idx = dynamicId ? this.edgeDynamicIdMap[edgeId] : this.edgeIdMap[edgeId]
    return idx !== undefined ? this.edges[idx] : undefined
  }

  buildDynamicMap() {
    this.edgeDynamicIdMap = {}
    for (let i = 0; i < this.edges.length; i++) {
      const e = this.edges[i]
      this.edgeDynamicIdMap[e.dynamicId] = i
    }
  }
}

export const useGraphStore = defineStore('graph', {
  state: () => ({
    // selection/focus
    selectedNode: null,
    focusedNode: null,
    selectedEdge: null,
    focusedEdge: null,

    // instances
    rawGraph: null,                 // RawGraph
    sigmaGraph: null,               // graphology DirectedGraph
    sigmaInstance: null,            // Sigma instance (set from your component)
    allDatabaseLabels: ['*'],

    // search (MiniSearch or whatever you plug later)
    searchEngine: null,

    // ui/control flags
    moveToSelectedNode: false,
    isFetching: false,
    graphIsEmpty: false,
    lastSuccessfulQueryLabel: '',

    // color map per type (optional)
    typeColorMap: new Map(),

    // fetch-attempt flags (for one-time fetch logic)
    graphDataFetchAttempted: false,
    labelsFetchAttempted: false,

    // node operation triggers
    nodeToExpand: null,
    nodeToPrune: null,

    // version to force reactivity in dependents
    graphDataVersion: 0,
  }),

  getters: {
    hasGraph: (s) => !!s.sigmaGraph && s.sigmaGraph.order > 0,
  },

  actions: {
    // -------- simple setters --------
    setSigmaInstance(instance) { this.sigmaInstance = instance },
    setSelectedNode(nodeId, moveToSelectedNode = false) {
      this.selectedNode = nodeId
      // this.moveToSelectedNode = !!moveToSelectedNode
    },
    setFocusedNode(nodeId) { this.focusedNode = nodeId },
    setSelectedEdge(edgeId) { this.selectedEdge = edgeId },
    setFocusedEdge(edgeId) { this.focusedEdge = edgeId },
    setIsFetching(v) { this.isFetching = !!v },
    setGraphIsEmpty(v) { this.graphIsEmpty = !!v },
    setLastSuccessfulQueryLabel(label) { this.lastSuccessfulQueryLabel = label || '' },
    setRawGraph(rg) { this.rawGraph = rg },
    setSigmaGraph(g) { this.sigmaGraph = g || null },
    setAllDatabaseLabels(labels) { this.allDatabaseLabels = Array.isArray(labels) ? labels : ['*'] },
    setSearchEngine(engine) { this.searchEngine = engine || null },
    resetSearchEngine() { this.searchEngine = null },
    setGraphDataFetchAttempted(b) { this.graphDataFetchAttempted = !!b },
    setLabelsFetchAttempted(b) { this.labelsFetchAttempted = !!b },
    setMoveToSelectedNode(b) { this.moveToSelectedNode = !!b },
    setTypeColorMap(map) { this.typeColorMap = map instanceof Map ? map : new Map() },

    clearSelection() {
      this.selectedNode = null
      this.focusedNode = null
      this.selectedEdge = null
      this.focusedEdge = null
    },

    reset() {
      this.selectedNode = null
      this.focusedNode = null
      this.selectedEdge = null
      this.focusedEdge = null
      this.rawGraph = null
      this.sigmaGraph = null
      this.searchEngine = null
      this.moveToSelectedNode = false
      this.graphIsEmpty = false
    },

    incrementGraphDataVersion() {
      this.graphDataVersion = this.graphDataVersion + 1
    },

    triggerNodeExpand(nodeId) { this.nodeToExpand = nodeId },
    triggerNodePrune(nodeId) { this.nodeToPrune = nodeId },

    async fetchAllDatabaseLabels() {
      try {
        const query = {}
        const workspaceStore = useWorkspaceContextStore()
        const headers = {
            'X-Workspace': workspaceStore.workspaceId,
        }
        const labels = await graphApi.getGraphLabels({ query, headers })
        this.setAllDatabaseLabels(['*', ...(labels || [])])
        this.setLabelsFetchAttempted(true)
      } catch (err) {
        console.error('fetchAllDatabaseLabels failed:', err)
        this.setAllDatabaseLabels(['*'])
        this.setLabelsFetchAttempted(true)
      }
    },

    async fetchGraph() {
      this.setIsFetching(true)
      this.setGraphDataFetchAttempted(true)
      try {
        const query = { 
            label: '*',
            max_depth: 6,
            max_nodes: 1000
        }

        const workspaceStore = useWorkspaceContextStore()
        const headers = { 'X-Workspace': workspaceStore.workspaceId }

        const resp = await graphApi.queryGraph({ query, headers })
        const { nodes, edges } = this._normalizeGraphResponse(resp)

        console.log('nodes:', nodes, 'edges:', edges);

        const rg = new RawGraph()
        rg.nodes = nodes || []
        rg.edges = edges || []

        rg.nodeIdMap = {}
        for (let i = 0; i < rg.nodes.length; i++) {
          rg.nodeIdMap[String(rg.nodes[i].id)] = i
        }
        rg.edgeIdMap = {}
        for (let i = 0; i < rg.edges.length; i++) {
          rg.edgeIdMap[String(rg.edges[i].id)] = i
        }
        rg.buildDynamicMap()

        const g = new MultiDirectedGraph({ allowSelfLoops: true })

        rg.nodes.forEach((n) => {
          const attrs = {
            x: n.x ?? Math.random() * 10 - 5,
            y: n.y ?? Math.random() * 10 - 5,
            size: n.size ?? 4,   // was 4
            color: n.color ?? '#7aa2ff',
            label: n.properties?.entity_id || n.id,
            labels: n.labels || [],
            properties: n.properties || {},
          }
          g.addNode(String(n.id), attrs)
        })

        rg.edges.forEach((e) => {
          const w = Number(e.properties?.weight ?? 1)
          const edgeSize = Math.min(6, 1 + w * 1.5)
          const attrs = {
            label: e.id,
            properties: e.properties || {},
            source: String(e.source),
            target: String(e.target),
            type: e.type || undefined,
            size: edgeSize,
          }

          const edgeType = e.type === 'DIRECTED' ? 'curvedArrow' : 'curvedNoArrow'
          const key = e.id ?? `${e.source}->${e.target}`
          
          // Graphology will create an internal edge key; we don’t force IDs here
          g.addEdgeWithKey(
            String(key),
            String(e.source),
            String(e.target),
            { ...attrs, type: edgeType }
          )
        })

        this.setRawGraph(rg)
        this.setSigmaGraph(g)
        this.setGraphIsEmpty(g.order === 0)
        this.incrementGraphDataVersion()
        // update last successful label if query contains it
        if (query && query.label) this.setLastSuccessfulQueryLabel(String(query.label))
      } catch (err) {
        console.error('fetchGraph failed:', err)
        this.setSigmaGraph(null)
        this.setRawGraph(null)
        this.setGraphIsEmpty(true)
        throw err
      } finally {
        this.setIsFetching(false)
      }
    },

    /**
     * Normalize backend response to {nodes, edges}.
     * Change this if your API returns another shape.
     */
    _normalizeGraphResponse(resp) {
      // common patterns:
      // { nodes, edges } or { data: { nodes, edges } }
      if (!resp) return { nodes: [], edges: [] }
      if (Array.isArray(resp.nodes) && Array.isArray(resp.edges)) return resp
      if (resp.data && Array.isArray(resp.data.nodes) && Array.isArray(resp.data.edges)) return resp.data
      return { nodes: [], edges: [] }
    },

    async updateNodeAndSelect(nodeId, entityId, propertyName, newValue) {
      const sigmaGraph = this.sigmaGraph
      const rawGraph = this.rawGraph
      if (!sigmaGraph || !rawGraph || !sigmaGraph.hasNode(String(nodeId))) return

      try {
        const attrs = sigmaGraph.getNodeAttributes(String(nodeId))

        // entity_id rename case (NetworkX: nodeId === entityId)
        if ((nodeId === entityId) && propertyName === 'entity_id') {
          const newId = String(newValue)

          // 1) add new node with same attrs but new label/id
          sigmaGraph.addNode(newId, { ...attrs, label: newId })

          const edgesToUpdate = []  // { originalDynamicId, newEdgeId, edgeIndex }

          // 2) rewire edges
          sigmaGraph.forEachEdge(nodeId, (edgeKey, eAttrs, source, target) => {
            const other = source === nodeId ? target : source
            const isOut = source === nodeId
            const originalDyn = eAttrs.dynamicId || edgeKey
            const rawIndex = rawGraph.edgeDynamicIdMap[originalDyn]

            const newEdgeKey = sigmaGraph.addEdge(
              isOut ? newId : other,
              isOut ? other : newId,
              eAttrs
            )

            if (rawIndex !== undefined) {
              edgesToUpdate.push({
                originalDynamicId: originalDyn,
                newEdgeId: newEdgeKey,
                edgeIndex: rawIndex,
              })
            }
            sigmaGraph.dropEdge(edgeKey)
          })

          // 3) drop old node
          sigmaGraph.dropNode(String(nodeId))

          // 4) update raw graph node + maps
          const nodeIndex = rawGraph.nodeIdMap[String(nodeId)]
          if (nodeIndex !== undefined) {
            rawGraph.nodes[nodeIndex].id = newId
            rawGraph.nodes[nodeIndex].labels = [newId]
            rawGraph.nodes[nodeIndex].properties.entity_id = newId
            delete rawGraph.nodeIdMap[String(nodeId)]
            rawGraph.nodeIdMap[newId] = nodeIndex
          }

          // 5) update raw edges + dynamicId map
          edgesToUpdate.forEach(({ originalDynamicId, newEdgeId, edgeIndex }) => {
            const edge = rawGraph.edges[edgeIndex]
            if (!edge) return
            if (edge.source === nodeId) edge.source = newId
            if (edge.target === nodeId) edge.target = newId
            edge.dynamicId = newEdgeId
            delete rawGraph.edgeDynamicIdMap[originalDynamicId]
            rawGraph.edgeDynamicIdMap[newEdgeId] = edgeIndex
          })

          // 6) update selection
          this.setSelectedNode(newId, true)
        } else {
          // normal property update
          const nodeIndex = rawGraph.nodeIdMap[String(nodeId)]
          if (nodeIndex !== undefined) {
            rawGraph.nodes[nodeIndex].properties[propertyName] = newValue
            if (propertyName === 'entity_id') {
              rawGraph.nodes[nodeIndex].labels = [newValue]
              sigmaGraph.setNodeAttribute(String(nodeId), 'label', String(newValue))
            }
          }
          this.incrementGraphDataVersion()
        }
      } catch (err) {
        console.error('updateNodeAndSelect error:', err)
        throw new Error('Failed to update node in graph')
      }
    },

    async updateEdgeAndSelect(edgeId, dynamicId, sourceId, targetId, propertyName, newValue) {
      const sigmaGraph = this.sigmaGraph
      const rawGraph = this.rawGraph
      if (!sigmaGraph || !rawGraph) return

      try {
        const edgeIndex = rawGraph.edgeIdMap[String(edgeId)]
        if (edgeIndex !== undefined && rawGraph.edges[edgeIndex]) {
          rawGraph.edges[edgeIndex].properties[propertyName] = newValue
          if (dynamicId !== undefined && propertyName === 'keywords') {
            sigmaGraph.setEdgeAttribute(dynamicId, 'label', String(newValue))
          }
        }

        this.incrementGraphDataVersion()
        this.setSelectedEdge(dynamicId)
      } catch (err) {
        console.error(`updateEdgeAndSelect error for ${sourceId}->${targetId}:`, err)
        throw new Error('Failed to update edge in graph')
      }
    },
    async loadGraph() {
        const queryLabel = '*'
          if (!graphStore.sigmaGraph) createRenderer(new DirectedGraph())
        await graphStore.fetchAllDatabaseLabels()
        try {
            const headers = { 'X-Workspace': useWorkspaceContextStore().workspaceId }
            await graphStore.fetchGraph({ query: { limit: 1000 }, headers })
            console.log('order', graphStore.sigmaGraph?.order, 'edges', graphStore.sigmaGraph?.size)
        } catch (e) { console.error(e) }

    },
  },
})

