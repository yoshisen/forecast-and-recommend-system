import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Form,
  Grid,
  Input,
  InputNumber,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  message,
} from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getForecast, getTimeSeriesForecast, trainTimeSeriesModel } from '../services/api';

const ALGO_LIGHTGBM = 'lightgbm';
const ALGO_SARIMA = 'sarima';
const ALGO_XGBOOST = 'xgboost';
const ALGO_PROPHET = 'prophet';

const ALGORITHMS = [ALGO_LIGHTGBM, ALGO_SARIMA, ALGO_XGBOOST, ALGO_PROPHET];

const getAlgorithmLabel = (algorithm) => {
  switch ((algorithm || '').toLowerCase()) {
    case ALGO_SARIMA:
      return 'SARIMA';
    case ALGO_XGBOOST:
      return 'XGBoost';
    case ALGO_PROPHET:
      return 'Prophet';
    case ALGO_LIGHTGBM:
    default:
      return 'LightGBM';
  }
};

const normalizeAlgorithm = (value) => {
  const lowered = (value || '').toLowerCase().trim();
  if (ALGORITHMS.includes(lowered)) return lowered;
  if (lowered === 'sales') return ALGO_LIGHTGBM;
  return ALGO_LIGHTGBM;
};

const ForecastPage = ({ defaultAlgorithm = ALGO_LIGHTGBM }) => {
  const [loading, setLoading] = useState(false);
  const [autoSubmitted, setAutoSubmitted] = useState(false);
  const [modelResult, setModelResult] = useState(null);
  const [form] = Form.useForm();
  const [searchParams] = useSearchParams();
  const screens = Grid.useBreakpoint();

  const initialProductId = searchParams.get('product_id') || undefined;
  const initialStoreId = searchParams.get('store_id') || undefined;
  const initialHorizon = Number(searchParams.get('horizon') || 14);
  const queryAlgo = searchParams.get('algo') || searchParams.get('algorithm') || defaultAlgorithm;

  const [selectedAlgorithm, setSelectedAlgorithm] = useState(() => normalizeAlgorithm(queryAlgo));

  useEffect(() => {
    if (autoSubmitted) return;
    if (selectedAlgorithm !== ALGO_PROPHET && initialProductId && initialStoreId) {
      form.submit();
      setAutoSubmitted(true);
    }
  }, [autoSubmitted, selectedAlgorithm, initialProductId, initialStoreId, form]);

  const handleAlgorithmChange = (algorithm) => {
    setSelectedAlgorithm(algorithm);
    setModelResult(null);
  };

  const handleForecast = async (values) => {
    const horizon = values.horizon || 14;
    const algorithmLabel = getAlgorithmLabel(selectedAlgorithm);

    try {
      setLoading(true);

      if (selectedAlgorithm === ALGO_PROPHET) {
        const trainResponse = await trainTimeSeriesModel();
        const forecastResponse = await getTimeSeriesForecast(horizon);

        if (trainResponse.success && forecastResponse.success) {
          setModelResult({
            algorithm: ALGO_PROPHET,
            method: trainResponse.data?.summary?.method || 'prophet',
            productId: values.product_id,
            storeId: values.store_id,
            horizon,
            forecast: forecastResponse.data,
          });
          message.success('Prophet 予測結果を取得しました');
        }
        return;
      }

      const response = await getForecast(
        values.product_id,
        values.store_id,
        horizon,
        values.use_baseline || false,
        null,
        selectedAlgorithm
      );

      if (response.success) {
        setModelResult({
          algorithm: selectedAlgorithm,
          method: response.data?.method,
          productId: response.data?.product_id,
          storeId: response.data?.store_id,
          horizon: response.data?.horizon || horizon,
          forecast: response.data,
        });
        message.success(`${algorithmLabel} 予測結果を取得しました`);
      }
    } catch (error) {
      message.error(`${algorithmLabel} 予測に失敗しました: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const chartData = useMemo(() => {
    if (!modelResult?.forecast) return [];

    if (modelResult.algorithm === ALGO_PROPHET) {
      const forecast = modelResult.forecast;
      if (!forecast?.dates || !forecast?.yhat) return [];
      return forecast.dates.map((date, index) => ({
        date,
        value: Number(forecast.yhat[index] || 0),
        trend: Number(forecast.trend?.[index] || 0),
        upper: Number(forecast.yhat_upper?.[index] || 0),
        lower: Number(forecast.yhat_lower?.[index] || 0),
      }));
    }

    const forecast = modelResult.forecast;
    if (!forecast?.dates || !forecast?.predictions) return [];
    return forecast.dates.map((date, index) => ({
      date,
      value: Number(forecast.predictions[index] || 0),
    }));
  }, [modelResult]);

  const activeResult = useMemo(() => {
    if (!modelResult || chartData.length === 0) return null;

    const totalForecast = chartData.reduce((sum, row) => sum + Number(row.value || 0), 0);
    const algorithmLabel = getAlgorithmLabel(modelResult.algorithm);

    return {
      title: `予測結果（${algorithmLabel}）`,
      method: modelResult.method || '-',
      productId: modelResult.productId,
      storeId: modelResult.storeId,
      horizon: Number(modelResult.horizon || chartData.length),
      totalForecast,
      avgDailyForecast: chartData.length > 0 ? totalForecast / chartData.length : 0,
      chartData,
      showProphetLines: modelResult.algorithm === ALGO_PROPHET,
    };
  }, [modelResult, chartData]);

  const cumulativeChartData = useMemo(() => {
    const rows = activeResult?.chartData || [];
    let cumulative = 0;

    return rows.map((row, index) => {
      const value = Number(row.value || 0);
      cumulative += value;

      return {
        date: row.date,
        cumulative: Number(cumulative.toFixed(2)),
        runningAverage: Number((cumulative / (index + 1)).toFixed(2)),
      };
    });
  }, [activeResult]);

  const tableData = (activeResult?.chartData || []).map((row, index) => ({
    key: `${row.date}-${index}`,
    date: row.date,
    value: Number(row.value || 0).toFixed(2),
    trend: Number(row.trend || 0).toFixed(2),
    upper: Number(row.upper || 0).toFixed(2),
    lower: Number(row.lower || 0).toFixed(2),
  }));

  const columns = [
    { title: '日付', dataIndex: 'date', key: 'date' },
    { title: '予測値', dataIndex: 'value', key: 'value', align: 'right' },
    ...(selectedAlgorithm === ALGO_PROPHET
      ? [
          { title: 'トレンド', dataIndex: 'trend', key: 'trend', align: 'right' },
          { title: '上限', dataIndex: 'upper', key: 'upper', align: 'right' },
          { title: '下限', dataIndex: 'lower', key: 'lower', align: 'right' },
        ]
      : []),
  ];

  const chartHeight = screens.xs ? 300 : 400;
  const pageSize = screens.xs ? 6 : 10;
  const runButtonLabel = `${getAlgorithmLabel(selectedAlgorithm)} で予測`;

  return (
    <div style={{ padding: 24 }}>
      <Card title="📈 予測アルゴリズム比較" style={{ marginBottom: 24 }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Button
            type={selectedAlgorithm === ALGO_LIGHTGBM ? 'primary' : 'default'}
            onClick={() => handleAlgorithmChange(ALGO_LIGHTGBM)}
          >
            LightGBM
          </Button>
          <Button
            type={selectedAlgorithm === ALGO_SARIMA ? 'primary' : 'default'}
            onClick={() => handleAlgorithmChange(ALGO_SARIMA)}
          >
            SARIMA
          </Button>
          <Button
            type={selectedAlgorithm === ALGO_XGBOOST ? 'primary' : 'default'}
            onClick={() => handleAlgorithmChange(ALGO_XGBOOST)}
          >
            XGBoost
          </Button>
          <Button
            type={selectedAlgorithm === ALGO_PROPHET ? 'primary' : 'default'}
            onClick={() => handleAlgorithmChange(ALGO_PROPHET)}
          >
            Prophet
          </Button>
          <Tag color="blue">選択中: {getAlgorithmLabel(selectedAlgorithm)}</Tag>
        </Space>

        <div style={{ marginBottom: 16, padding: 12, border: '1px solid #e5e7eb', borderRadius: 8, background: '#fafafa' }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>アルゴリズム説明</div>
          <div>LightGBM: 多数の特徴量から非線形パターンを学習し、短中期の需要変動を高速に予測します。</div>
          <div>SARIMA: トレンドと季節性を明示的に分解し、時系列の周期変化を重視して予測します。</div>
          <div>XGBoost: 勾配ブースティングで誤差を段階的に補正し、複雑な関係を高精度に予測します。</div>
          <div>Prophet: トレンド・季節性・休日効果を加法モデルで扱い、将来推移を安定して推定します。</div>
        </div>

        {selectedAlgorithm === ALGO_PROPHET && (
          <Alert
            style={{ marginBottom: 16 }}
            type="info"
            showIcon
            message="Prophet は総量時系列モデルです"
            description="商品ID・店舗IDは必須ではありません。予測期間を指定して実行してください。"
          />
        )}

        <Form form={form} layout="vertical" onFinish={handleForecast}>
          <Form.Item
            label="商品ID"
            name="product_id"
            initialValue={initialProductId}
            rules={[{ required: selectedAlgorithm !== ALGO_PROPHET, message: '商品IDを入力してください' }]}
          >
            <Input placeholder="例: P000001" disabled={selectedAlgorithm === ALGO_PROPHET} />
          </Form.Item>

          <Form.Item
            label="店舗ID"
            name="store_id"
            initialValue={initialStoreId}
            rules={[{ required: selectedAlgorithm !== ALGO_PROPHET, message: '店舗IDを入力してください' }]}
          >
            <Input placeholder="例: LUMI0001" disabled={selectedAlgorithm === ALGO_PROPHET} />
          </Form.Item>

          <Form.Item label="予測期間（日数）" name="horizon" initialValue={initialHorizon}>
            <InputNumber min={1} max={90} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} size="large">
              {runButtonLabel}
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>{getAlgorithmLabel(selectedAlgorithm)} で予測計算中...</p>
        </div>
      )}

      {!loading && activeResult && (
        <>
          <Card title={`📊 ${activeResult.title}`} style={{ marginBottom: 24 }}>
            <Alert
              message={`予測方法: ${activeResult.method}`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            {activeResult.productId && <p><strong>商品ID:</strong> {activeResult.productId}</p>}
            {activeResult.storeId && <p><strong>店舗ID:</strong> {activeResult.storeId}</p>}
            <Space size="large" wrap>
              <Statistic title="予測期間" value={activeResult.horizon} suffix="日" />
              <Statistic title="総予測販売数" value={Number(activeResult.totalForecast || 0).toFixed(2)} />
              <Statistic title="1日平均予測" value={Number(activeResult.avgDailyForecast || 0).toFixed(2)} />
            </Space>
          </Card>

          <Card title="📉 予測トレンド" style={{ marginBottom: 24 }}>
            <ResponsiveContainer width="100%" height={chartHeight}>
              <LineChart data={activeResult.chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" name="予測値" stroke="#1890ff" strokeWidth={2} dot={false} />
                {activeResult.showProphetLines && (
                  <Line type="monotone" dataKey="trend" name="トレンド" stroke="#16a34a" strokeWidth={1.8} dot={false} />
                )}
                {activeResult.showProphetLines && (
                  <Line type="monotone" dataKey="upper" name="上限" stroke="#94a3b8" strokeDasharray="5 4" dot={false} />
                )}
                {activeResult.showProphetLines && (
                  <Line type="monotone" dataKey="lower" name="下限" stroke="#94a3b8" strokeDasharray="5 4" dot={false} />
                )}
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card title="📋 詳細データ">
            <Table dataSource={tableData} columns={columns} pagination={{ pageSize }} size="small" />
          </Card>

          <Card title="📈 累積予測推移（配套グラフ）" style={{ marginTop: 24 }}>
            <ResponsiveContainer width="100%" height={chartHeight}>
              <LineChart data={cumulativeChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="cumulative" name="累積予測" stroke="#ef4444" strokeWidth={2.2} dot={false} />
                <Line type="monotone" dataKey="runningAverage" name="累積平均" stroke="#f59e0b" strokeWidth={1.8} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </>
      )}

      {!loading && !activeResult && (
        <Alert
          type="info"
          showIcon
          message="表示できる予測結果がありません"
          description={
            selectedAlgorithm === ALGO_PROPHET
              ? '予測期間を設定して Prophet 予測を実行してください。'
              : '商品ID・店舗IDを入力して選択中アルゴリズムを実行してください。'
          }
        />
      )}
    </div>
  );
};

export default ForecastPage;
