import { defineStore } from 'pinia'
import { agentApi } from '@/api'
import { useWorkspaceContextStore } from '../workspaceContext'
import { useUserStore } from '../user'

const initialState = () => ({
  requirements: '',
  includePdf: true,
  includePpt: true,
  outputDir: './output',
  loading: false,
  error: null,
  lastMessage: '',
  generatedFiles: [],
  downloadUrls: [],
  topicsCovered: [],
  agentTraceId: null,
})

export const useNotesMakerStore = defineStore('notesMaker', {
  state: initialState,
  getters: {
    canGenerate(state) {
      return state.requirements.trim().length > 0 && !state.loading && (state.includePdf || state.includePpt)
    },
    hasGeneratedFiles(state) {
      return state.generatedFiles.length > 0
    },
  },
  actions: {
    setRequirements(value) {
      this.requirements = value
      this.resetStatus()
    },
    setIncludePdf(value) {
      this.includePdf = value
      this.resetStatus()
    },
    setIncludePpt(value) {
      this.includePpt = value
      this.resetStatus()
    },
    setOutputDir(value) {
      this.outputDir = value
      this.resetStatus()
    },
    resetStatus() {
      this.error = null
      this.lastMessage = ''
    },
    reset() {
      Object.assign(this, initialState())
    },
    async generate() {
      if (!this.canGenerate) {
        return
      }

      const workspaceStore = useWorkspaceContextStore()
      if (!workspaceStore.hasWorkspace) {
        this.error = new Error('Please select a workspace before generating notes.')
        return
      }

      const userStore = useUserStore()

      this.loading = true
      this.error = null
      this.lastMessage = ''
      this.generatedFiles = []
      this.downloadUrls = []
      this.topicsCovered = []
      this.agentTraceId = null

      try {
        const payload = {
          requirements: this.requirements,
          include_pdf: this.includePdf,
          include_ppt: this.includePpt,
          output_dir: this.outputDir,
        }

        const headers = {
          'X-Workspace': workspaceStore.workspaceId,
          'X-User-ID': userStore.userId,
        }

        const response = await agentApi.generateContent({ payload, headers })

        if (response.status === 'success' || response.status === 'completed') {
          this.generatedFiles = response.generated_files || []
          this.downloadUrls = response.download_urls || []
          this.topicsCovered = response.topics_covered || []
          this.agentTraceId = response.agent_trace_id
          this.lastMessage = response.message || 'Content generated successfully!'
          
          // Automatically download generated files
          if (this.downloadUrls.length > 0) {
            await this.downloadGeneratedFiles()
          }
        } else if (response.status === 'partial') {
          this.generatedFiles = response.generated_files || []
          this.downloadUrls = response.download_urls || []
          this.topicsCovered = response.topics_covered || []
          this.agentTraceId = response.agent_trace_id
          this.lastMessage = response.message || 'Content partially generated.'
          this.error = new Error('Some files may not have been generated correctly')
          
          // Still try to download any available files
          if (this.downloadUrls.length > 0) {
            await this.downloadGeneratedFiles()
          }
        } else {
          throw new Error(response.error || response.message || 'Failed to generate content')
        }
      } catch (err) {
        console.error('Error generating notes:', err)
        this.error = err
        this.lastMessage = err.message || 'Failed to generate content'
      } finally {
        this.loading = false
      }
    },
    async downloadGeneratedFiles() {
      if (!this.downloadUrls || this.downloadUrls.length === 0) {
        return
      }

      const workspaceStore = useWorkspaceContextStore()
      const userStore = useUserStore()

      try {
        for (const downloadUrl of this.downloadUrls) {
          // Extract filename from URL
          const filename = downloadUrl.split('/').pop()
          
          // Create a temporary link and trigger download
          // The backend will serve the file with proper headers
          const link = document.createElement('a')
          link.href = `${window.location.origin}${downloadUrl}`
          link.download = filename
          link.style.display = 'none'
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          
          // Small delay between downloads to avoid browser blocking
          await new Promise(resolve => setTimeout(resolve, 500))
        }
        
        this.lastMessage = `Downloaded ${this.downloadUrls.length} file(s) successfully!`
      } catch (err) {
        console.error('Error downloading files:', err)
        // Don't overwrite the main error if generation succeeded
        if (!this.error) {
          this.error = err
        }
        this.lastMessage = 'Files generated but download failed. Please try downloading from the output directory.'
      }
    },
    async checkAgentStatus() {
      try {
        const response = await agentApi.getAgentStatus()
        return response
      } catch (err) {
        console.error('Error checking agent status:', err)
        return { status: 'error', message: err.message }
      }
    },
  },
})
