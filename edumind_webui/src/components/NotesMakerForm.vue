<template>
  <div class="notes-maker">
    <div class="notes-maker__body">
      <header class="notes-maker__header">
        <div class="notes-maker__header-copy">
          <div class="notes-maker__eyebrow-line">
            <v-icon icon="mdi-information-outline" size="small" color="primary" />
            <span class="text-caption text-medium-emphasis">
              Describe what you want to generate
            </span>
          </div>
        </div>
      </header>

      <v-textarea
        v-model="requirementsModel"
        label="Content Requirements"
        variant="outlined"
        auto-grow
        rows="3"
        max-rows="6"
        density="comfortable"
        placeholder="e.g. Create a summary PDF file on coding practices and methods, provide proper references"
        :disabled="loading"
        required
      />

      <div class="notes-maker__options">
        <v-switch
          v-model="includePdfModel"
          inset
          label="Generate PDF"
          color="primary"
          :disabled="loading"
        />
        
        <v-switch
          v-model="includePptModel"
          inset
          label="Generate PowerPoint"
          color="primary"
          :disabled="loading"
        />
      </div>

      <v-text-field
        v-model="outputDirModel"
        label="Output Directory (optional)"
        variant="outlined"
        density="comfortable"
        placeholder="./output"
        :disabled="loading"
        hint="Files will be automatically downloaded to your Downloads folder"
        persistent-hint
      />

      <div v-if="errorMessage" class="notes-maker__alert">
        <v-alert type="error" variant="tonal" density="compact">
          {{ errorMessage }}
        </v-alert>
      </div>

      <div v-if="successMessage" class="notes-maker__alert">
        <v-alert type="success" variant="tonal" density="compact">
          {{ successMessage }}
          <div v-if="generatedFiles.length > 0" class="mt-2">
            <p class="text-caption mb-1">Generated files:</p>
            <ul class="text-caption">
              <li v-for="file in generatedFiles" :key="file">{{ file }}</li>
            </ul>
          </div>
        </v-alert>
      </div>

      <div v-if="loading" class="notes-maker__progress">
        <v-progress-linear
          indeterminate
          color="primary"
          height="4"
        />
        <p class="text-caption text-medium-emphasis mt-2 mb-0">
          Generating your content... This may take a few moments.
        </p>
      </div>
    </div>

    <div class="notes-maker__actions">
      <div class="notes-maker__action-copy">
        <p class="text-caption text-medium-emphasis mb-0">
          Note: Generated files will be automatically downloaded to your Downloads folder.
        </p>
      </div>
      <div class="notes-maker__action-buttons">
        <v-btn
          variant="text"
          color="primary"
          @click="reset"
          :disabled="loading"
        >
          Reset
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!canGenerate"
          :loading="loading"
          prepend-icon="mdi-file-document-plus-outline"
          @click="generate"
        >
          Generate Notes
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useNotesMakerStore } from '@/stores'

const notesMakerStore = useNotesMakerStore()
const {
  requirements,
  includePdf,
  includePpt,
  outputDir,
  loading,
  error,
  lastMessage,
  generatedFiles,
  downloadUrls,
} = storeToRefs(notesMakerStore)

const requirementsModel = computed({
  get: () => requirements.value,
  set: (value: string) => notesMakerStore.setRequirements(value),
})

const includePdfModel = computed({
  get: () => includePdf.value,
  set: (value: boolean) => notesMakerStore.setIncludePdf(value),
})

const includePptModel = computed({
  get: () => includePpt.value,
  set: (value: boolean) => notesMakerStore.setIncludePpt(value),
})

const outputDirModel = computed({
  get: () => outputDir.value,
  set: (value: string) => notesMakerStore.setOutputDir(value),
})

const canGenerate = computed(() => notesMakerStore.canGenerate)

const errorMessage = computed(() => 
  error.value ? error.value.message || 'Failed to generate notes.' : ''
)

const successMessage = computed(() => lastMessage.value)

const generate = () => {
  notesMakerStore.generate()
}

const reset = () => {
  notesMakerStore.reset()
}

onMounted(() => {
  // Optional: Check agent status on mount
  // notesMakerStore.checkAgentStatus()
})
</script>

<style scoped>
.notes-maker {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  min-height: 0;
}

.notes-maker__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.notes-maker__header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.notes-maker__header-copy {
  flex: 1;
}

.notes-maker__eyebrow-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.notes-maker__options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 0;
}

.notes-maker__alert {
  margin-top: 8px;
}

.notes-maker__progress {
  margin-top: 16px;
}

.notes-maker__actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

.notes-maker__action-copy {
  flex: 1;
}

.notes-maker__action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 960px) {
  .notes-maker__action-buttons {
    flex-direction: column;
  }
}
</style>
