import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (username, password) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/login', formData)
  },
  register: (data) => api.post('/register', data),
  getCurrentUser: () => api.get('/me')
}

export const userApi = {
  list: () => api.get('/users'),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`)
}

export const myLogApi = {
  list: (params) => api.get('/my-logs', { params })
}

export const datasourceApi = {
  list: () => api.get('/datasources'),
  get: (id) => api.get(`/datasources/${id}`),
  create: (data) => api.post('/datasources', data),
  update: (id, data) => api.put(`/datasources/${id}`, data),
  delete: (id) => api.delete(`/datasources/${id}`),
  test: (data) => api.post('/datasources/test', data)
}

export const queryApi = {
  execute: (data) => api.post('/execute', data),
  executeBatch: (data) => api.post('/execute-batch', data)
}

export const auditApi = {
  list: (params) => api.get('/audit-logs', { params }),
  delete: (id) => api.delete(`/audit-logs/${id}`),
  getStatistics: (params) => api.get('/audit-statistics', { params })
}

export const riskRuleApi = {
  list: (params) => api.get('/risk-rules', { params }),
  get: (id) => api.get(`/risk-rules/${id}`),
  create: (data) => api.post('/risk-rules', data),
  update: (id, data) => api.put(`/risk-rules/${id}`, data),
  delete: (id) => api.delete(`/risk-rules/${id}`),
  check: (data) => api.post('/risk-check', data)
}

export const maskingRuleApi = {
  list: (params) => api.get('/masking-rules', { params }),
  get: (id) => api.get(`/masking-rules/${id}`),
  create: (data) => api.post('/masking-rules', data),
  update: (id, data) => api.put(`/masking-rules/${id}`, data),
  delete: (id) => api.delete(`/masking-rules/${id}`)
}

export const workOrderApi = {
  list: (params) => api.get('/work-orders', { params }),
  get: (id) => api.get(`/work-orders/${id}`),
  create: (data) => api.post('/work-orders', data),
  update: (id, data) => api.put(`/work-orders/${id}`, data),
  delete: (id) => api.delete(`/work-orders/${id}`),
  approve: (id) => api.post(`/work-orders/${id}/approve`),
  reject: (id, data) => api.post(`/work-orders/${id}/reject`, data),
  execute: (id) => api.post(`/work-orders/${id}/execute`),
  rollback: (id) => api.post(`/work-orders/${id}/rollback`)
}

export default api
