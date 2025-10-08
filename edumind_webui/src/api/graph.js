import { apiRequest, buildQuery } from './http'

const basePath = '/graph'

const normaliseQuery = (query) => buildQuery(query)

export const queryGraph = ({ query, headers } = {}) => {
    return apiRequest('/graphs', {
        method: 'GET',
        query: normaliseQuery(query),
        headers,
    })
}

export const getGraphLabels = ({ query, headers } = {}) => {
    return apiRequest(`${basePath}/label/list`, {
        method: 'GET',
        query: normaliseQuery(query),
        headers,
    })
}