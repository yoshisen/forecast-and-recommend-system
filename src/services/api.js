import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Upload file(s)
export const uploadExcel = async (fileOrFiles, options = {}) => {
  const normalizedFiles = Array.isArray(fileOrFiles)
    ? fileOrFiles.filter(Boolean)
    : [fileOrFiles].filter(Boolean);

  const { onUploadProgress } = options;

  if (normalizedFiles.length === 0) {
    throw new Error('アップロード対象ファイルがありません');
  }

  const formData = new FormData();
  if (normalizedFiles.length === 1) {
    formData.append('file', normalizedFiles[0]);
  } else {
    normalizedFiles.forEach((file) => {
      formData.append('files', file);
    });
  }
  
  const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 120000, // 2 minutes for large files
    onUploadProgress,
  });
  
  return response.data;
};

// Get data summary
export const getDataSummary = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.get('/data/summary', { params });
  return response.data;
};

// Get task readiness matrix
export const getTaskReadiness = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.get('/data/readiness', { params });
  return response.data;
};

// Get quick sample ids for forms
export const getDataSamples = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.get('/data/samples', { params });
  return response.data;
};

// Get upload schema guide
export const getUploadSchemaGuide = async () => {
  const response = await api.get('/data/upload-schema');
  return response.data;
};

// Get field-level readiness for current/uploaded version
export const getDataFieldReadiness = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.get('/data/field-readiness', { params });
  return response.data;
};

// Get total amount forecast for Home page
export const getTotalForecast = async (
  horizon = 14,
  modelType = 'auto',
  version = null,
  topNPairs = 20
) => {
  const params = { horizon, model_type: modelType, top_n_pairs: topNPairs };
  if (version) params.version = version;
  const response = await api.get('/data/forecast-total', { params });
  return response.data;
};

// Get quality report
export const getQualityReport = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.get('/data/quality', { params });
  return response.data;
};

// Get versions list
export const getVersions = async () => {
  const response = await api.get('/versions');
  return response.data;
};

// Train forecast model
export const trainForecastModel = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.post('/forecast/train', null, { params });
  return response.data;
};

// Get forecast
export const getForecast = async (
  productId,
  storeId,
  horizon = 14,
  useBaseline = false,
  version = null,
  algorithm = 'lightgbm'
) => {
  const params = { product_id: productId, store_id: storeId, horizon, use_baseline: useBaseline };
  if (version) params.version = version;
  if (algorithm) params.algorithm = algorithm;
  
  const response = await api.get('/forecast', { params });
  return response.data;
};

// Batch forecast
export const batchForecast = async (pairs, horizon = 14, version = null) => {
  const params = version ? { version } : {};
  const response = await api.post('/forecast/batch', { pairs, horizon }, { params });
  return response.data;
};

// Train recommender
export const trainRecommender = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.post('/recommend/train', null, { params });
  return response.data;
};

// Get recommendations
export const getRecommendations = async (customerId, topK = 10, version = null) => {
  const params = { customer_id: customerId, top_k: topK };
  if (version) params.version = version;
  
  const response = await api.get('/recommend', { params });
  return response.data;
};

// Get popular recommendations
export const getPopularRecommendations = async (topK = 10, storeId = null, version = null) => {
  const params = { top_k: topK };
  if (storeId) params.store_id = storeId;
  if (version) params.version = version;
  
  const response = await api.get('/recommend/popular', { params });
  return response.data;
};

// Train classification model
export const trainClassificationModel = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.post('/classification/train', null, { params });
  return response.data;
};

// Predict customer class by customer id
export const predictCustomerClass = async (customerId, threshold = null, version = null) => {
  const params = { customer_id: customerId };
  if (threshold !== null && threshold !== undefined) params.threshold = threshold;
  if (version) params.version = version;
  const response = await api.get('/classification/predict', { params });
  return response.data;
};

// Threshold scan for classification
export const getClassificationThresholdScan = async (step = 0.05, version = null) => {
  const params = { step };
  if (version) params.version = version;
  const response = await api.get('/classification/threshold-scan', { params });
  return response.data;
};

// Tune default threshold for classification
export const tuneClassificationThreshold = async (threshold, version = null) => {
  const params = { threshold };
  if (version) params.version = version;
  const response = await api.post('/classification/tune-threshold', null, { params });
  return response.data;
};

// Train association model
export const trainAssociationModel = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.post('/association/train', null, { params });
  return response.data;
};

// Get association rules
export const getAssociationRules = async (topK = 50, version = null) => {
  const params = { top_k: topK };
  if (version) params.version = version;
  const response = await api.get('/association/rules', { params });
  return response.data;
};

// Get cross-sell recommendations from association rules
export const getAssociationRecommendations = async (productId, topK = 10, version = null) => {
  const params = { product_id: productId, top_k: topK };
  if (version) params.version = version;
  const response = await api.get('/association/recommendations', { params });
  return response.data;
};

// Train clustering model
export const trainClusteringModel = async (nClusters = 4, version = null) => {
  const params = { n_clusters: nClusters };
  if (version) params.version = version;
  const response = await api.post('/clustering/train', null, { params });
  return response.data;
};

// Get cluster segments
export const getClusterSegments = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.get('/clustering/segments', { params });
  return response.data;
};

// Get cluster points for visualization
export const getClusterPoints = async (limit = 1500, version = null) => {
  const params = { limit };
  if (version) params.version = version;
  const response = await api.get('/clustering/points', { params });
  return response.data;
};

// Get customer cluster assignment
export const getCustomerCluster = async (customerId, version = null) => {
  const params = version ? { version } : {};
  const response = await api.get(`/clustering/customer/${customerId}`, { params });
  return response.data;
};

// Train prophet time series model
export const trainTimeSeriesModel = async (version = null) => {
  const params = version ? { version } : {};
  const response = await api.post('/timeseries/train', null, { params });
  return response.data;
};

// Get prophet forecast
export const getTimeSeriesForecast = async (horizon = 14, version = null) => {
  const params = { horizon };
  if (version) params.version = version;
  const response = await api.get('/timeseries/forecast', { params });
  return response.data;
};

// Health check
export const healthCheck = async () => {
  const response = await axios.get('http://localhost:8000/api/health');
  return response.data;
};

export default api;
