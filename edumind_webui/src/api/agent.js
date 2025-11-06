import { apiRequest, buildQuery } from './http'

const basePath = '/agent'

const normaliseQuery = (query) => buildQuery(query)

/**
 * Generate educational content (PDF/PPT) using AI agents and knowledge graph
 * @param {Object} options - Generation options
 * @param {Object} options.payload - Request payload
 * @param {string} options.payload.requirements - Natural language description of content requirements
 * @param {boolean} [options.payload.include_pdf=true] - Whether to generate PDF output
 * @param {boolean} [options.payload.include_ppt=true] - Whether to generate PowerPoint presentation
 * @param {string} [options.payload.output_dir='./output'] - Custom output directory for generated files
 * @param {Object} [options.query] - Query parameters
 * @param {Object} [options.headers] - Additional headers
 * @returns {Promise<Object>} Response with generated files information
 */
export const generateContent = ({ payload, query, headers } = {}) => {
  if (!payload) {
    throw new Error('generateContent requires a payload parameter')
  }

  if (!payload.requirements) {
    throw new Error('generateContent requires requirements in payload')
  }

  return apiRequest(`${basePath}/generate`, {
    method: 'POST',
    query: normaliseQuery(query),
    headers,
    body: payload,
  })
}

/**
 * Get agent system status
 * @param {Object} options - Request options
 * @param {Object} [options.query] - Query parameters
 * @param {Object} [options.headers] - Additional headers
 * @returns {Promise<Object>} Agent system status
 */
export const getAgentStatus = ({ query, headers } = {}) => {
  return apiRequest(`${basePath}/status`, {
    method: 'GET',
    query: normaliseQuery(query),
    headers,
  })
}
