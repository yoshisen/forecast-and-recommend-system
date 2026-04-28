import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  InputNumber,
  message,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  AppstoreOutlined,
  DashboardOutlined,
  GiftOutlined,
  LineChartOutlined,
  RocketOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { getDataSamples, getDataSummary, getTotalForecast, uploadExcel } from '../services/api';

const { Dragger } = Upload;
const { Title, Text } = Typography;

const TASK_LABELS = {
  forecast: 'Forecast',
  recommend: 'Recommend',
  classification: 'Classification',
  association: 'Association',
  clustering: 'Clustering',
  prophet: 'Prophet',
};

const statusColor = (status) => {
  switch (status) {
    case 'completed':
      return 'green';
    case 'running':
      return 'processing';
    case 'pending':
      return 'gold';
    case 'failed':
      return 'red';
    case 'skipped':
      return 'default';
    default:
      return 'default';
  }
};

const HomePage = ({ onUploadSuccess }) => {
  const navigate = useNavigate();

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [samples, setSamples] = useState(null);

  const [forecastLoading, setForecastLoading] = useState(false);
  const [totalForecast, setTotalForecast] = useState(null);

  const [horizon, setHorizon] = useState(14);
  const [modelType, setModelType] = useState('auto');

  const normalizeUploadFiles = (fileOrFiles) => {
    if (Array.isArray(fileOrFiles)) {
      return fileOrFiles.filter(Boolean);
    }
    return [fileOrFiles].filter(Boolean);
  };

  const currentVersion = summary?.version || uploadResult?.version || null;

  const loadSummary = async (version = null) => {
    try {
      setSummaryLoading(true);
      const response = await getDataSummary(version);
      if (response.success) {
        setSummary(response.data);
        return response.data;
      }
      return null;
    } catch (error) {
      setSummary(null);
      return null;
    } finally {
      setSummaryLoading(false);
    }
  };

  const loadSamples = async (version = null) => {
    try {
      const response = await getDataSamples(version);
      if (response.success) {
        setSamples(response.data.samples || null);
      }
    } catch (error) {
      setSamples(null);
    }
  };

  const loadTotalForecast = async (version = null, nextHorizon = horizon, nextModelType = modelType) => {
    try {
      setForecastLoading(true);
      const response = await getTotalForecast(nextHorizon, nextModelType, version);
      if (response.success) {
        setTotalForecast(response.data);
      }
    } catch (error) {
      setTotalForecast(null);
      message.error(`総額予測の取得に失敗しました: ${error.message}`);
    } finally {
      setForecastLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    const boot = async () => {
      const data = await loadSummary();
      if (!mounted) return;
      if (data?.version) {
        await loadSamples(data.version);
        await loadTotalForecast(data.version);
      }
    };
    boot();
    return () => {
      mounted = false;
    };
  }, []);

  const refreshForecast = async () => {
    if (!currentVersion) {
      message.warning('先にデータをアップロードしてから予測を更新してください');
      return;
    }
    await loadTotalForecast(currentVersion, horizon, modelType);
  };

  const handleUpload = async (fileOrFiles) => {
    const uploadFiles = normalizeUploadFiles(fileOrFiles);
    if (uploadFiles.length === 0) {
      return false;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);

    const progressTimer = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 180);

    try {
      const result = await uploadExcel(uploadFiles);
      clearInterval(progressTimer);
      setUploadProgress(100);

      if (!result.success) {
        throw new Error('Upload API returned success=false');
      }

      setUploadResult(result);
      if (onUploadSuccess) {
        onUploadSuccess(result.version);
      }

      message.success(`アップロード成功（${uploadFiles.length} ファイル）。ワークベンチを更新しています`);

      const newSummary = await loadSummary(result.version);
      await loadSamples(newSummary?.version || result.version);
      await loadTotalForecast(newSummary?.version || result.version);
    } catch (error) {
      clearInterval(progressTimer);
      setUploadError(error.message);
      message.error(`アップロードに失敗しました: ${error.message}`);
    } finally {
      setUploading(false);
    }

    return false;
  };

  const chartData = useMemo(() => {
    if (!totalForecast?.dates || !totalForecast?.totals) {
      return [];
    }
    return totalForecast.dates.map((date, idx) => ({
      date,
      total: Number(totalForecast.totals[idx] || 0),
    }));
  }, [totalForecast]);

  const uploadProps = {
    name: 'file',
    multiple: true,
    accept: '.xlsx,.xls,.csv,.zip',
    beforeUpload: (currentFile, selectedFileList) => {
      const isLast = selectedFileList[selectedFileList.length - 1] === currentFile;
      if (isLast) {
        void handleUpload(selectedFileList);
      }
      return false;
    },
    showUploadList: false,
    disabled: uploading,
  };

  const overallSummary = summary?.overall_summary || {};
  const training = summary?.training || {};
  const topPair = samples?.top_pairs?.[0] || null;
  const defaultProduct = topPair?.product_id || samples?.product_ids?.[0] || '';
  const defaultStore = topPair?.store_id || samples?.store_ids?.[0] || '';
  const defaultCustomer = samples?.customer_ids?.[0] || '';

  return (
    <div className="home-workbench fade-in">
      <div className="home-hero">
        <Title level={2} style={{ marginBottom: 8 }}>AI Excel Analytics Workbench</Title>
        <Text type="secondary">
          アップロード後に総額予測を確認し、予測・レコメンド・学習監視へすぐ移動できます。
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card className="home-upload-card" title="1) データをアップロード">
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <UploadOutlined style={{ fontSize: 28 }} />
              </p>
              <p className="ant-upload-text">ドラッグまたはクリックしてデータファイルをアップロード</p>
              <p className="ant-upload-hint">.xlsx / .xls / .csv / .zip に対応。複数CSVを同時アップロード可能です。</p>
            </Dragger>

            {uploading && (
              <div style={{ marginTop: 16 }}>
                <Progress percent={uploadProgress} status="active" />
              </div>
            )}

            {uploadError && (
              <Alert
                style={{ marginTop: 16 }}
                type="error"
                showIcon
                message="アップロード失敗"
                description={uploadError}
              />
            )}

            {uploadResult?.version && (
              <Alert
                style={{ marginTop: 16 }}
                type="success"
                showIcon
                message={`アップロードバージョン: ${uploadResult.version}`}
                description="ワークベンチを更新しました。総額予測とクイック導線をそのまま利用できます。"
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card className="home-status-card" title="2) データ概要">
            {summaryLoading ? (
              <div style={{ textAlign: 'center', padding: '36px 0' }}>
                <Spin />
              </div>
            ) : summary ? (
              <>
                <Row gutter={[12, 12]}>
                  <Col span={12}>
                    <Statistic title="Sheets" value={overallSummary.total_sheets || 0} />
                  </Col>
                  <Col span={12}>
                    <Statistic title="Rows" value={overallSummary.total_rows || 0} />
                  </Col>
                  <Col span={12}>
                    <Statistic title="Fields" value={overallSummary.total_fields || 0} />
                  </Col>
                  <Col span={12}>
                    <Statistic title="Version" value={summary.version || '-'} valueStyle={{ fontSize: 15 }} />
                  </Col>
                </Row>

                <div style={{ marginTop: 14 }}>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>学習ステータス</Text>
                  {Object.keys(TASK_LABELS).map((task) => (
                    <Tag key={task} color={statusColor(training[task])} style={{ marginBottom: 6 }}>
                      {TASK_LABELS[task]}: {training[task] || 'n/a'}
                    </Tag>
                  ))}
                </div>
              </>
            ) : (
              <Alert type="info" showIcon message="まだ利用可能なデータがありません" description="先にデータファイルをアップロードして分析ワークベンチを有効化してください。" />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 4 }}>
        <Col span={24}>
          <Card
            title="3) 総額予測（即時）"
            extra={
              <Space>
                <Select
                  value={modelType}
                  style={{ width: 130 }}
                  options={[
                    { label: '自動', value: 'auto' },
                    { label: 'モデル', value: 'model' },
                    { label: 'ナイーブ', value: 'naive' },
                  ]}
                  onChange={(value) => setModelType(value)}
                />
                <InputNumber
                  min={1}
                  max={90}
                  value={horizon}
                  onChange={(value) => setHorizon(value || 14)}
                />
                <Button type="primary" onClick={refreshForecast} loading={forecastLoading}>
                  更新
                </Button>
              </Space>
            }
          >
            {forecastLoading ? (
              <div style={{ textAlign: 'center', padding: '56px 0' }}>
                <Spin />
              </div>
            ) : chartData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={350}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="totalColor" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1f8a70" stopOpacity={0.45} />
                        <stop offset="95%" stopColor="#1f8a70" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" angle={-25} textAnchor="end" height={70} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="total" name="総額予測" stroke="#1f8a70" fill="url(#totalColor)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>

                <Row gutter={16} style={{ marginTop: 8 }}>
                  <Col xs={24} md={8}>
                    <Statistic title="累計予測総額" value={Number(totalForecast.cumulative_total || 0).toFixed(2)} />
                  </Col>
                  <Col xs={24} md={8}>
                    <Statistic title="日次平均予測額" value={Number(totalForecast.avg_daily_total || 0).toFixed(2)} />
                  </Col>
                  <Col xs={24} md={8}>
                    <Statistic title="手法" value={totalForecast.method || '-'} valueStyle={{ fontSize: 16 }} />
                  </Col>
                </Row>

                {totalForecast.note && (
                  <Alert style={{ marginTop: 12 }} type="info" showIcon message={totalForecast.note} />
                )}
              </>
            ) : (
              <Alert type="warning" showIcon message="予測データがありません" description="データをアップロードして「更新」を押すと総額予測を表示できます。" />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 4 }}>
        <Col span={24}>
          <Card title="4) クイックアクション">
            <Space wrap size="middle">
              <Button icon={<DashboardOutlined />} onClick={() => navigate('/dashboard')}>トレーニング監視</Button>
              <Button
                icon={<LineChartOutlined />}
                type="primary"
                onClick={() => navigate(`/forecast?product_id=${encodeURIComponent(defaultProduct)}&store_id=${encodeURIComponent(defaultStore)}&horizon=14`)}
              >
                予測ページへ
              </Button>
              <Button
                icon={<GiftOutlined />}
                onClick={() => navigate(`/recommend?customer_id=${encodeURIComponent(defaultCustomer)}&top_k=10`)}
              >
                レコメンド
              </Button>
              <Button icon={<UploadOutlined />} onClick={() => navigate('/upload')}>アップロード詳細</Button>
              <Button
                icon={<AppstoreOutlined />}
                onClick={() => navigate(`/association?product_id=${encodeURIComponent(defaultProduct)}&top_k=10`)}
              >
                アソシエーション
              </Button>
              <Button
                icon={<RocketOutlined />}
                onClick={() => navigate(`/clustering?customer_id=${encodeURIComponent(defaultCustomer)}`)}
              >
                クラスタリング
              </Button>
              <Button
                icon={<RocketOutlined />}
                onClick={() => navigate(`/classification?customer_id=${encodeURIComponent(defaultCustomer)}&threshold=0.5`)}
              >
                分類分析
              </Button>
              <Button icon={<LineChartOutlined />} onClick={() => navigate('/forecast?algo=prophet')}>予測（Prophet）</Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HomePage;
