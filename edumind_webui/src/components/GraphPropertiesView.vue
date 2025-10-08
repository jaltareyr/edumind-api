<script setup>
import { ref, computed, watch } from 'vue'
import { useGraphStore } from '@/stores/graph'
import { VListItem } from 'vuetify/components' // type assist only

const graphStore = useGraphStore()

const selectedNode   = computed(() => graphStore.selectedNode)
const focusedNode    = computed(() => graphStore.focusedNode)
const selectedEdge   = computed(() => graphStore.selectedEdge)
const focusedEdge    = computed(() => graphStore.focusedEdge)
const sigmaGraph     = computed(() => graphStore.sigmaGraph)
const rawGraph       = computed(() => graphStore.rawGraph)
const dataVersion    = computed(() => graphStore.graphDataVersion)
const currentType    = ref/** @type {'node' | 'edge' | null} */(null)
const currentElement = ref/** @type {any} */(null)

function toNodeLabel(n) {
  if (!n) return ''
  return n.properties?.entity_id ?? String(n.id ?? '')
}

function refineNodeProperties(nodeId) {
  const g = sigmaGraph.value
  const rg = rawGraph.value
  if (!g || !rg || !g.hasNode(String(nodeId))) return null

  // base
  const n = rg.getNode(String(nodeId))
  if (!n) return null

  // degree
  const degree = g.degree(String(nodeId)) ?? 0

  // neighbors via edges touching this node
  const relationships = []
  try {
    const edgeKeys = g.edges(String(nodeId))
    for (const ek of edgeKeys) {
      if (!g.hasEdge(ek)) continue
      const eAttrs = g.getEdgeAttributes(ek) || {}
      const source = eAttrs.source ?? g.source(ek)
      const target = eAttrs.target ?? g.target(ek)

      // who is the neighbor?
      const isOut = String(source) === String(nodeId)
      const neighborId = isOut ? target : source

      if (!g.hasNode(String(neighborId))) continue
      const neighbor = rg.getNode(String(neighborId))
      if (!neighbor) continue

      relationships.push({
        type: isOut ? 'Out' : 'In',
        id: String(neighborId),
        label: toNodeLabel(neighbor),
      })
    }
  } catch (err) {
    // noop
  }

  return {
    ...n,
    degree,
    relationships,
  }
}

function refineEdgeProperties(edgeKeyOrDyn) {
  const g = sigmaGraph.value
  const rg = rawGraph.value
  if (!g || !rg) return null
  if (!g.hasEdge(String(edgeKeyOrDyn))) return null

  // find raw edge by dynamicId (graphology edge key)
  const idx = rg.edgeDynamicIdMap[String(edgeKeyOrDyn)]
  const base = idx !== undefined ? rg.edges[idx] : null
  if (!base) return null

  let sourceNode, targetNode
  if (g.hasNode(String(base.source))) {
    sourceNode = rg.getNode(String(base.source))
  }
  if (g.hasNode(String(base.target))) {
    targetNode = rg.getNode(String(base.target))
  }

  return {
    ...base,
    dynamicId: String(edgeKeyOrDyn),
    sourceNode,
    targetNode,
  }
}

function resolveCurrent() {
  // priority: focused node > selected node > focused edge > selected edge
  if (focusedNode.value) {
    currentType.value = 'node'
    currentElement.value = refineNodeProperties(focusedNode.value)
    return
  }
  if (selectedNode.value) {
    currentType.value = 'node'
    currentElement.value = refineNodeProperties(selectedNode.value)
    return
  }
  if (focusedEdge.value) {
    currentType.value = 'edge'
    currentElement.value = refineEdgeProperties(focusedEdge.value)
    return
  }
  if (selectedEdge.value) {
    currentType.value = 'edge'
    currentElement.value = refineEdgeProperties(selectedEdge.value)
    return
  }
  currentType.value = null
  currentElement.value = null
}

watch(
  [focusedNode, selectedNode, focusedEdge, selectedEdge, sigmaGraph, rawGraph, dataVersion],
  resolveCurrent,
  { immediate: true }
)

async function saveNodeProperty(nodeId, entityId, name, val) {
  await graphStore.updateNodeAndSelect(nodeId, entityId, name, val)
}

async function saveEdgeProperty(edgeId, dynamicId, sourceId, targetId, name, val) {
  await graphStore.updateEdgeAndSelect(edgeId, dynamicId, sourceId, targetId, name, val)
}

function gotoNode(nodeId) {
  graphStore.setSelectedNode(String(nodeId), true)
}

const editingKey = ref('')
const editingVal = ref('')

function cancelEdit() {
  editingKey.value = ''
  editingVal.value = ''
}
async function confirmEdit(entry) {
  if (!currentElement.value) return
  const key = editingKey.value
  const val = editingVal.value
  const el = currentElement.value

  try {
    if (currentType.value === 'node') {
      await saveNodeProperty(el.id, el.properties?.entity_id ?? el.id, key, val)
    } else if (currentType.value === 'edge') {
      await saveEdgeProperty(el.id, el.dynamicId, el.sourceNode?.properties?.entity_id ?? el.source, el.targetNode?.properties?.entity_id ?? el.target, key, val)
    }
  } finally {
    cancelEdit()
    resolveCurrent()
  }
}

function isEditableProp(entityType, key) {
  if (entityType === 'node') {
    return key === 'description' || key === 'entity_id'
  }
  if (entityType === 'edge') {
    return key === 'description' || key === 'keywords'
  }
  return false
}
</script>

<template>
  <div v-if="currentElement" class="pa-2" style="max-width: 320px;">
    <!-- Container -->
    <v-card class="bg-surface opacity-95" elevation="8" rounded="lg" border>
      <!-- Header -->
      <v-card-title class="d-flex align-center justify-space-between py-2">
        <div class="text-subtitle-1 font-weight-bold">
          {{ currentType === 'node' ? 'Node' : 'Edge' }} Properties
        </div>
      </v-card-title>

      <v-divider />

      <!-- Top summary (id/labels/degree or edge endpoints) -->
      <v-card-text class="py-2">
        <template v-if="currentType === 'node'">
          <v-list density="compact" class="py-0">
            <v-list-item title="ID" :subtitle="String(currentElement.id)" />
            <v-list-item
              title="Labels"
              :subtitle="Array.isArray(currentElement.labels) ? currentElement.labels.join(', ') : ''"
              @click="gotoNode(currentElement.id)"
              class="cursor-pointer"
            />
            <v-list-item title="Degree" :subtitle="String(currentElement.degree ?? 0)" />
          </v-list>
        </template>

        <template v-else>
          <v-list density="compact" class="py-0">
            <v-list-item title="ID" :subtitle="String(currentElement.id)" />
            <v-list-item
              title="Type"
              v-if="currentElement.type"
              :subtitle="String(currentElement.type)"
            />
            <v-list-item
              title="Source"
              :subtitle="currentElement.sourceNode ? currentElement.sourceNode.labels.join(', ') : String(currentElement.source)"
              class="cursor-pointer"
              @click="gotoNode(currentElement.source)"
            />
            <v-list-item
              title="Target"
              :subtitle="currentElement.targetNode ? currentElement.targetNode.labels.join(', ') : String(currentElement.target)"
              class="cursor-pointer"
              @click="gotoNode(currentElement.target)"
            />
          </v-list>
        </template>
      </v-card-text>

      <v-divider />

      <!-- Properties -->
      <v-card-text class="py-2">
        <div class="text-body-2 text-primary font-weight-medium mb-1">Properties</div>

        <v-list density="compact" class="py-0" style="max-height: 280px; overflow: auto;">
          <template v-for="(val, key) in (currentElement.properties || {})" :key="key">
            <template v-if="key !== 'created_at'">
              <!-- Editable -->
              <div v-if="isEditableProp(currentType, key)">
                <v-list-item>
                  <div class="d-flex align-center w-100">
                    <div class="text-medium-emphasis mr-2" style="min-width: 96px">{{ key }}</div>

                    <!-- Edit mode -->
                    <template v-if="editingKey === key">
                      <v-text-field
                        v-model="editingVal"
                        hide-details
                        density="compact"
                        variant="outlined"
                        class="flex-1 mr-2"
                      />
                      <v-btn size="small" color="primary" variant="flat" class="mr-1" @click="confirmEdit()">
                        Save
                      </v-btn>
                      <v-btn size="small" variant="text" @click="cancelEdit">Cancel</v-btn>
                    </template>

                    <!-- Read mode -->
                    <template v-else>
                      <div
                        class="flex-1 px-2 py-1 rounded bg-primary-container text-primary-on-container overflow-hidden text-truncate"
                        :title="typeof val === 'string' ? val : JSON.stringify(val, null, 2)"
                      >
                        {{ typeof val === 'string' ? val : JSON.stringify(val) }}
                      </div>
                    </template>
                  </div>
                </v-list-item>
                <v-divider />
              </div>

              <!-- Non-editable -->
              <div v-else>
                <v-list-item>
                  <div class="d-flex align-center w-100">
                    <div class="text-medium-emphasis mr-2" style="min-width: 96px">{{ key }}</div>
                    <div
                      class="flex-1 px-2 py-1 rounded bg-surface-variant text-on-surface-variant overflow-hidden text-truncate"
                      :title="typeof val === 'string' ? val : JSON.stringify(val, null, 2)"
                    >
                      {{ typeof val === 'string' ? val : JSON.stringify(val) }}
                    </div>
                  </div>
                </v-list-item>
                <v-divider />
              </div>
            </template>
          </template>
        </v-list>
      </v-card-text>

      <!-- Relationships (for nodes) -->
      <template v-if="currentType === 'node' && currentElement.relationships && currentElement.relationships.length">
        <v-divider />
        <v-card-text class="py-2">
          <div class="text-body-2 text-success font-weight-medium mb-1">Relationships</div>
          <v-list density="compact" class="py-0" style="max-height: 200px; overflow: auto;">
            <v-list-item
              v-for="rel in currentElement.relationships"
              :key="rel.id + ':' + rel.type"
              class="cursor-pointer"
              @click="gotoNode(rel.id)"
            >
              <div class="d-flex align-center ga-2">
                <v-chip size="x-small" label variant="flat">{{ rel.type }}</v-chip>
                <div class="text-truncate" :title="rel.label">{{ rel.label }}</div>
              </div>
            </v-list-item>
          </v-list>
        </v-card-text>
      </template>
    </v-card>
  </div>
</template>

<style scoped>

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
