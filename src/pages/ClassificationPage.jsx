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
  Spin,
  Statistic,
  Table,
  Tag,
} from 'antd';
import {
  getClassificationThresholdScan,
  predictCustomerClass,
  trainClassificationModel,
  tuneClassificationThreshold,
} from '../services/api';

const ClassificationPage = () => {
  const [searchParams] = useSearchParams();

  const [trainLoading, setTrainLoading] = useState(false);
  const [predictLoading, setPredictLoading] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);

  const [trainResult, setTrainResult] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [scanResult, setScanResult] = useState(null);

  const [predictForm] = Form.useForm();
  const [thresholdForm] = Form.useForm();

  const initialCustomerId = searchParams.get('customer_id') || undefined;
  const initialThreshold = Number(searchParams.get('threshold') || 0.5);

  const handleTrain = async () => {
    try {
      setTrainLoading(true);
      const response = await trainClassificationModel();
      if (response.success) {
        setTrainResult(response.data);
        message.success('分類モデルの学習が完了しました');
      }
    } catch (error) {
      message.error(`分類学習に失敗しました: ${error.message}`);
    } finally {
      setTrainLoading(false);
    }
  };

  const handlePredict = async (values) => {
    try {
      setPredictLoading(true);
      const response = await predictCustomerClass(values.customer_id, values.threshold);
      if (response.success) {
        setPrediction(response.data);
        message.success('分類予測が完了しました');
      }
    } catch (error) {
      message.error(`予測に失敗しました: ${error.message}`);
    } finally {
      setPredictLoading(false);
    }
  };

  const handleScan = async () => {
    try {
      setScanLoading(true);
      const response = await getClassificationThresholdScan(0.05);
      if (response.success) {
        setScanResult(response.data);
        message.success('しきい値スキャンが完了しました');
      }
    } catch (error) {
      message.error(`しきい値スキャンに失敗しました: ${error.message}`);
    } finally {
      setScanLoading(false);
    }
  };

  const handleTuneThreshold = async (values) => {
    try {
      setScanLoading(true);
      const response = await tuneClassificationThreshold(values.threshold);
      if (response.success) {
        message.success(`既定しきい値を設定しました: ${values.threshold}`);
        await handleScan();
      }
    } catch (error) {
      message.error(`しきい値更新に失敗しました: ${error.message}`);
    } finally {
      setScanLoading(false);
    }
  };

  const thresholdColumns = [
    { title: 'しきい値', dataIndex: 'threshold', key: 'threshold' },
    { title: '適合率', dataIndex: 'precision', key: 'precision', render: (v) => Number(v).toFixed(4) },
    { title: '再現率', dataIndex: 'recall', key: 'recall', render: (v) => Number(v).toFixed(4) },
    { title: 'F1', dataIndex: 'f1', key: 'f1', render: (v) => Number(v).toFixed(4) },
    { title: '陽性予測数', dataIndex: 'positive_predictions', key: 'positive_predictions' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title="🧠 分類分析（ch05_01）" style={{ marginBottom: 24 }}>
        <Button type="primary" loading={trainLoading} onClick={handleTrain}>
          分類モデルを学習
        </Button>
        {trainLoading && <Spin style={{ marginLeft: 12 }} />}

        {trainResult?.metrics && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col xs={12} md={6}><Statistic title="適合率" value={trainResult.metrics.precision} precision={4} /></Col>
            <Col xs={12} md={6}><Statistic title="再現率" value={trainResult.metrics.recall} precision={4} /></Col>
            <Col xs={12} md={6}><Statistic title="F1" value={trainResult.metrics.f1} precision={4} /></Col>
            <Col xs={12} md={6}><Statistic title="ROC-AUC" value={trainResult.metrics.roc_auc} precision={4} /></Col>
          </Row>
        )}

        {trainResult?.dataset_info?.label_is_derived && (
          <Alert
            style={{ marginTop: 12 }}
            type="warning"
            showIcon
            message="指標の解釈に関する注意"
            description={
              <div>
                <div>この学習は派生ラベルを使用しています。データ特性により指標が高めに出る場合があります。</div>
                <div>label_source: {trainResult?.dataset_info?.label_source || '-'}</div>
                {(trainResult?.dataset_info?.dropped_feature_columns || []).length > 0 && (
                  <div>
                    リーク対策で除外した列: {(trainResult.dataset_info.dropped_feature_columns || []).join(', ')}
                  </div>
                )}
              </div>
            }
          />
        )}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="顧客分類予測" style={{ height: '100%' }}>
            <Form form={predictForm} layout="vertical" onFinish={handlePredict}>
              <Form.Item
                label="顧客ID"
                name="customer_id"
                initialValue={initialCustomerId}
                rules={[{ required: true, message: '顧客IDを入力してください' }]}
              >
                <Input placeholder="例: C000001" />
              </Form.Item>
              <Form.Item label="しきい値（任意）" name="threshold" initialValue={initialThreshold}>
                <InputNumber min={0.01} max={0.99} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item>
                <Button htmlType="submit" type="primary" loading={predictLoading}>予測</Button>
              </Form.Item>
            </Form>

            {prediction && (
              <Alert
                type={prediction.prediction === 1 ? 'success' : 'info'}
                showIcon
                message={`予測結果: ${prediction.prediction === 1 ? '陽性' : '陰性'}`}
                description={
                  <div>
                    <div>確率: {Number(prediction.probability).toFixed(4)}</div>
                    <div>しきい値: {Number(prediction.threshold).toFixed(2)}</div>
                  </div>
                }
              />
            )}
          </Card>
        </Col>

        <Col xs={24} xl={12}>
          <Card title="しきい値調整" style={{ height: '100%' }}>
            <div style={{ marginBottom: 12 }}>
              <Button onClick={handleScan} loading={scanLoading}>しきい値をスキャン</Button>
            </div>

            <Form form={thresholdForm} layout="inline" onFinish={handleTuneThreshold}>
              <Form.Item
                label="新しい既定しきい値"
                name="threshold"
                rules={[{ required: true, message: 'しきい値を入力してください' }]}
              >
                <InputNumber min={0.01} max={0.99} step={0.01} />
              </Form.Item>
              <Form.Item>
                <Button htmlType="submit" type="primary" loading={scanLoading}>しきい値を更新</Button>
              </Form.Item>
            </Form>

            {scanResult?.best_by_f1 && (
              <div style={{ marginTop: 12 }}>
                <Tag color="green">Best F1 Threshold: {scanResult.best_by_f1.threshold}</Tag>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="しきい値スキャン詳細" style={{ marginTop: 24 }}>
        <Table
          rowKey={(row) => `${row.threshold}`}
          dataSource={scanResult?.rows || []}
          columns={thresholdColumns}
          pagination={{ pageSize: 8 }}
          size="small"
        />
      </Card>
    </div>
  );
};

export default ClassificationPage;
