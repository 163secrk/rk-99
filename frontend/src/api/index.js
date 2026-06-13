import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const datasourceApi = {
  list: () => api.get('/datasources'),
  get: (id) => api.get(`/datasources/${id}`),
  create: (data) => api.post('/datasources', data),
  update: (id, data) => api.put(`/datasources/${id}`, data),
  delete: (id) => api.delete(`/datasources/${id}`),
  test: (data) => api.post('/datasources/test', data)
}

export const queryApi = {
  execute: (data) => api.post('/execute', data)
}

export const auditApi = {
  list: (params) => api.get('/audit-logs', { params }),
  delete: (id) => api.delete(`/audit-logs/${id}`)
}

export const riskRuleApi = {
  list: (params) => api.get('/risk-rules', { params }),
  get: (id) => api.get(`/risk-rules/${id}`),
  create: (data) => api.post('/risk-rules', data),
  update: (id, data) => api.put(`/risk-rules/${id}`, data),
  delete: (id) => api.delete(`/risk-rules/${id}`),
  check: (data) => api.post('/risk-check', data)
}

export default api
