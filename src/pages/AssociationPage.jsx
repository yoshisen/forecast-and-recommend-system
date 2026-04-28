import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Slider,
  message,
  Row,
  Col,
  Table,
  Tag,
} from 'antd';
import {
  getAssociationRecommendations,
  getAssociationRules,
  trainAssociationModel,
} from '../services/api';

const AssociationPage = () => {
  const [searchParams] = useSearchParams();
  const initialProductId = searchParams.get('product_id') || undefined;
  const rawTopK = Number(searchParams.get('top_k'));
  const initialTopK = Number.isFinite(rawTopK) && rawTopK > 0 ? rawTopK : 10;

  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState([]);
  const [summary, setSummary] = useState(null);
  const [recs, setRecs] = useState(null);
  const [minConfidence, setMinConfidence] = useState(0);
  const [minLift, setMinLift] = useState(0);
  const [requestedTopK, setRequestedTopK] = useState(initialTopK);

  const [ruleForm] = Form.useForm();

  const handleTrainAndLoad = async () => {
    try {
      setLoading(true);
      const trainResp = await trainAssociationModel();
      if (trainResp.success) {
        setSummary(trainResp.data.summary || null);
      }

      const ruleResp = await getAssociationRules(100);
      if (ruleResp.success) {
        setRules(ruleResp.data.rules || []);
        setSummary(ruleResp.data.summary || trainResp.data.summary || null);
      }
      message.success('アソシエーションルールを更新しました');
    } catch (error) {
      message.error(`アソシエーション処理に失敗しました: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRecommend = async (values) => {
    try {
      setLoading(true);
      const topK = Number(values.top_k) || 10;
      setRequestedTopK(topK);
      const resp = await getAssociationRecommendations(values.product_id, topK);
      if (resp.success) {
        setRecs(resp.data);
        message.success('クロスセル推薦を生成しました');
      }
    } catch (error) {
      message.error(`推薦取得に失敗しました: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '前件',
      dataIndex: 'antecedents',
      key: 'antecedents',
      render: (arr) => (arr || []).join(', '),
    },
    {
      title: '後件',
      dataIndex: 'consequents',
      key: 'consequents',
      render: (arr) => (arr || []).join(', '),
    },
    { title: '支持度', dataIndex: 'support', key: 'support', render: (v) => Number(v).toFixed(4) },
    { title: '確信度', dataIndex: 'confidence', key: 'confidence', render: (v) => Number(v).toFixed(4) },
    { title: 'リフト', dataIndex: 'lift', key: 'lift', render: (v) => Number(v).toFixed(4) },
  ];

  const recColumns = [
    { title: '商品ID', dataIndex: 'product_id', key: 'product_id' },
    { title: '確信度', dataIndex: 'confidence', key: 'confidence', render: (v) => Number(v).toFixed(4) },
    { title: 'リフト', dataIndex: 'lift', key: 'lift', render: (v) => Number(v).toFixed(4) },
    { title: '支持度', dataIndex: 'support', key: 'support', render: (v) => Number(v).toFixed(4) },
  ];

  const normalizeNumericValue = (value, fallback = 0) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  const filteredRecommendations = (recs?.recommendations || []).filter((item) => {
    const confidence = normalizeNumericValue(item.confidence, 0);
    const lift = normalizeNumericValue(item.lift, 0);
    return confidence >= minConfidence && lift >= minLift;
  });

  const shownRecommendations = filteredRecommendations.slice(0, Math.max(1, normalizeNumericValue(requestedTopK, 10)));

  return (
    <div style={{ padding: 24 }}>
      <Card title="🔗 アソシエーション分析（ch05_04）" style={{ marginBottom: 24 }}>
        <Button type="primary" loading={loading} onClick={handleTrainAndLoad}>
          ルールを学習して読み込む
        </Button>
        {summary && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col><Tag color="blue">取引数: {summary.n_transactions}</Tag></Col>
            <Col><Tag color="green">商品数: {summary.n_products}</Tag></Col>
            <Col><Tag color="purple">ルール数: {summary.n_rules}</Tag></Col>
            <Col><Tag color="gold">頻出集合数: {summary.n_itemsets}</Tag></Col>
          </Row>
        )}
      </Card>

      <Card title="商品からクロスセル推薦を取得" style={{ marginBottom: 24 }}>
        <Form form={ruleForm} layout="inline" onFinish={handleRecommend}>
          <Form.Item
            label="商品ID"
            name="product_id"
            initialValue={initialProductId}
            rules={[{ required: true, message: 'product_id を入力してください' }]}
          >
            <Input placeholder="例: P00001" />
          </Form.Item>
          <Form.Item label="上位件数" name="top_k" initialValue={initialTopK}>
            <InputNumber min={1} max={100} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>推薦を取得</Button>
          </Form.Item>
        </Form>

        {recs && (
          <Card
            size="small"
            title="推薦フィルタ"
            style={{ marginTop: 16 }}
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <div style={{ marginBottom: 8 }}>最小信頼度: {minConfidence.toFixed(2)}</div>
                <Row gutter={8} align="middle">
                  <Col flex="auto">
                    <Slider
                      min={0}
                      max={1}
                      step={0.01}
                      value={minConfidence}
                      onChange={(value) => setMinConfidence(normalizeNumericValue(value, 0))}
                    />
                  </Col>
                  <Col>
                    <InputNumber
                      aria-label="min-confidence"
                      min={0}
                      max={1}
                      step={0.01}
                      value={minConfidence}
                      onChange={(value) => setMinConfidence(normalizeNumericValue(value, 0))}
                    />
                  </Col>
                </Row>
              </Col>

              <Col xs={24} md={12}>
                <div style={{ marginBottom: 8 }}>最小 Lift: {minLift.toFixed(2)}</div>
                <Row gutter={8} align="middle">
                  <Col flex="auto">
                    <Slider
                      min={0}
                      max={10}
                      step={0.05}
                      value={minLift}
                      onChange={(value) => setMinLift(normalizeNumericValue(value, 0))}
                    />
                  </Col>
                  <Col>
                    <InputNumber
                      aria-label="min-lift"
                      min={0}
                      max={10}
                      step={0.05}
                      value={minLift}
                      onChange={(value) => setMinLift(normalizeNumericValue(value, 0))}
                    />
                  </Col>
                </Row>
              </Col>
            </Row>

            <Button
              style={{ marginTop: 12 }}
              onClick={() => {
                setMinConfidence(0);
                setMinLift(0);
              }}
            >
              フィルタをリセット
            </Button>
          </Card>
        )}

        {recs && (
          <Alert
            style={{ marginTop: 16 }}
            type="info"
            showIcon
            message={`商品ID: ${recs.product_id}`}
            description={`表示件数: ${shownRecommendations.length} / 取得件数: ${(recs.recommendations || []).length}`}
          />
        )}

        {recs && shownRecommendations.length === 0 && (
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            showIcon
            message="フィルタ条件に一致する推薦がありません"
          />
        )}
      </Card>

      {shownRecommendations.length > 0 && (
        <Card title="クロスセル推薦" style={{ marginBottom: 24 }}>
          <Table
            rowKey={(row) => `${row.product_id}-${row.lift}`}
            dataSource={shownRecommendations}
            columns={recColumns}
            pagination={{ pageSize: 8 }}
            size="small"
          />
        </Card>
      )}

      <Card title="アソシエーションルール一覧">
        <Table
          rowKey={(row) => `${(row.antecedents || []).join('_')}=>${(row.consequents || []).join('_')}`}
          dataSource={rules}
          columns={columns}
          pagination={{ pageSize: 10 }}
          size="small"
          scroll={{ x: 980 }}
        />
      </Card>
    </div>
  );
};

export default AssociationPage;
