import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  message,
  Row,
  Statistic,
  Table,
  Tag,
} from 'antd';
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  getClusterPoints,
  getClusterSegments,
  getCustomerCluster,
  trainClusteringModel,
} from '../services/api';

const COLORS = ['#4f46e5', '#16a34a', '#dc2626', '#d97706', '#0891b2', '#7c3aed'];

const ClusteringPage = () => {
  const [searchParams] = useSearchParams();

  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [segments, setSegments] = useState([]);
  const [points, setPoints] = useState([]);
  const [customerCluster, setCustomerCluster] = useState(null);

  const [trainForm] = Form.useForm();
  const [customerForm] = Form.useForm();

  const initialCustomerId = searchParams.get('customer_id') || undefined;

  const loadClusterAssets = async () => {
    const [segResp, pointResp] = await Promise.all([
      getClusterSegments(),
      getClusterPoints(2000),
    ]);

    if (segResp.success) {
      setSegments(segResp.data.segments || []);
      setSummary(segResp.data.summary || null);
    }
    if (pointResp.success) {
      setPoints(pointResp.data.points || []);
    }
  };

  const handleTrain = async (values) => {
    try {
      setLoading(true);
      const resp = await trainClusteringModel(values.n_clusters || 4);
      if (resp.success) {
        setSummary(resp.data.summary || null);
        await loadClusterAssets();
        message.success('クラスタリングモデルの学習が完了しました');
      }
    } catch (error) {
      message.error(`クラスタリング学習に失敗しました: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomerQuery = async (values) => {
    try {
      setLoading(true);
      const resp = await getCustomerCluster(values.customer_id);
      if (resp.success) {
        setCustomerCluster(resp.data);
        message.success('顧客クラスタ照会が完了しました');
      }
    } catch (error) {
      message.error(`照会に失敗しました: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const segmentColumns = [
    { title: 'クラスタ', dataIndex: 'cluster', key: 'cluster' },
    { title: '件数', dataIndex: 'count', key: 'count' },
    {
      title: 'プロファイル（主要指標）',
      dataIndex: 'profile',
      key: 'profile',
      render: (profile) => {
        if (!profile) return '-';
        const tx = profile.transaction_count ? Number(profile.transaction_count).toFixed(2) : '0';
        const amount = profile.total_amount ? Number(profile.total_amount).toFixed(2) : '0';
        const recency = profile.recency_days ? Number(profile.recency_days).toFixed(2) : '0';
        return `tx=${tx}, total=${amount}, recency=${recency}`;
      },
    },
  ];

  const chartGroups = segments.map((seg) => {
    const cluster = seg.cluster;
    return {
      name: `Cluster ${cluster}`,
      color: COLORS[cluster % COLORS.length],
      data: points.filter((p) => Number(p.cluster) === Number(cluster)),
    };
  });

  return (
    <div style={{ padding: 24 }}>
      <Card title="🧩 顧客クラスタリング分析（ch05_05）" style={{ marginBottom: 24 }}>
        <Form form={trainForm} layout="inline" onFinish={handleTrain}>
          <Form.Item label="クラスタ数" name="n_clusters" initialValue={4}>
            <InputNumber min={2} max={12} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>クラスタリングを学習</Button>
          </Form.Item>
        </Form>

        {summary && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col xs={12} md={6}><Statistic title="顧客数" value={summary.n_customers || 0} /></Col>
            <Col xs={12} md={6}><Statistic title="クラスタ数" value={summary.n_clusters || 0} /></Col>
            <Col xs={12} md={6}><Statistic title="シルエット係数" value={summary.silhouette || 0} precision={4} /></Col>
            <Col xs={12} md={6}><Statistic title="イナーシャ" value={summary.inertia || 0} precision={2} /></Col>
          </Row>
        )}
      </Card>

      <Card title="クラスタ2次元投影（PCA）" style={{ marginBottom: 24 }}>
        {points.length > 0 ? (
          <ResponsiveContainer width="100%" height={420}>
            <ScatterChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
              <CartesianGrid />
              <XAxis type="number" dataKey="pca_x" name="PCA-X" />
              <YAxis type="number" dataKey="pca_y" name="PCA-Y" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Legend />
              {chartGroups.map((group) => (
                <Scatter
                  key={group.name}
                  name={group.name}
                  data={group.data}
                  fill={group.color}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        ) : (
          <Alert type="info" showIcon message="クラスタ点データがありません。先にモデルを学習してください。" />
        )}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Card title="クラスタ概要">
            <Table
              rowKey={(row) => `${row.cluster}`}
              dataSource={segments}
              columns={segmentColumns}
              pagination={{ pageSize: 6 }}
              size="small"
            />
          </Card>
        </Col>

        <Col xs={24} xl={10}>
          <Card title="顧客クラスタ照会" style={{ height: '100%' }}>
            <Form form={customerForm} layout="vertical" onFinish={handleCustomerQuery}>
              <Form.Item
                label="顧客ID"
                name="customer_id"
                initialValue={initialCustomerId}
                rules={[{ required: true, message: '顧客IDを入力してください' }]}
              >
                <Input placeholder="例: C000001" />
              </Form.Item>
              <Form.Item>
                <Button htmlType="submit" type="primary" loading={loading}>顧客クラスタを照会</Button>
              </Form.Item>
            </Form>

            {customerCluster && (
              <Alert
                type="success"
                showIcon
                message={`クラスタ: ${customerCluster.cluster}`}
                description={
                  <div>
                    <div>顧客ID: {customerCluster.customer_id}</div>
                    <div>PCA: ({Number(customerCluster.pca_x).toFixed(3)}, {Number(customerCluster.pca_y).toFixed(3)})</div>
                    {customerCluster.profile && (
                      <div style={{ marginTop: 8 }}>
                        <Tag color="blue">平均客単価: {Number(customerCluster.profile.avg_ticket || 0).toFixed(2)}</Tag>
                        <Tag color="green">取引数: {Number(customerCluster.profile.transaction_count || 0).toFixed(2)}</Tag>
                      </div>
                    )}
                  </div>
                }
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ClusteringPage;
