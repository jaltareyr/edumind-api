import { apiRequest, buildQuery, resolveBaseUrl } from './http'
import { getToken } from '@/api/auth'

const basePath = '/questions'

const normaliseQuery = (query) => buildQuery(query)

export const createQuestions = ({ payload, query, headers } = {}) => {
  if (!payload) {
    throw new Error('createQuestions requires a payload parameter')
  }

  return apiRequest(`${basePath}/`, {
    method: 'POST',
    query: normaliseQuery(query),
    headers,
    body: payload,
  })
}

export const listQuestions = ({ query, headers } = {}) =>
  apiRequest(`${basePath}/`, {
    method: 'GET',
    query: normaliseQuery(query),
    headers,
  })

export const bulkPatchQuestions = ({ payload, query, headers } = {}) => {
  if (!payload) {
    throw new Error('bulkPatchQuestions requires a payload parameter')
  }

  return apiRequest(`${basePath}/`, {
    method: 'PATCH',
    query: normaliseQuery(query),
    headers,
    body: payload,
  })
}

export const getQuestion = ({ id, query, headers } = {}) => {
  if (!id) {
    throw new Error('getQuestion requires an id parameter')
  }

  return apiRequest(`${basePath}/${encodeURIComponent(id)}`, {
    method: 'GET',
    query: normaliseQuery(query),
    headers,
  })
}

export const updateQuestion = ({ id, payload, query, headers } = {}) => {
  if (!id) {
    throw new Error('updateQuestion requires an id parameter')
  }
  if (!payload) {
    throw new Error('updateQuestion requires a payload parameter')
  }

  return apiRequest(`${basePath}/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    query: normaliseQuery(query),
    headers,
    body: payload,
  })
}

export const deleteQuestion = ({ id, query, headers } = {}) => {
  if (!id) {
    throw new Error('deleteQuestion requires an id parameter')
  }

  return apiRequest(`${basePath}/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    query: normaliseQuery(query),
    headers,
  })
}

export const exportQuestions = async ({ payload, headers } = {}) => {
  if (!payload) {
    throw new Error('exportQuestions requires a payload parameter')
  }
  const url = resolveBaseUrl();

  const token = getToken()
  
  const h = new Headers(headers);

  h.set('Content-Type', 'application/json')
  if (token) h.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${url}${basePath}/export`, {
    method: 'POST',
    headers: h,
    body: JSON.stringify(payload),
    responseType: 'blob',
  })
  return response
}
