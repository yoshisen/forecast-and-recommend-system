import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, Form, Input, InputNumber, Button, message, Spin, Alert, Row, Col, Tag } from 'antd';
import { GiftOutlined, StarOutlined } from '@ant-design/icons';
import { getRecommendations, getPopularRecommendations } from '../services/api';

const RecommendPage = () => {
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState(null);
  const [popularItems, setPopularItems] = useState(null);
  const [autoSubmitted, setAutoSubmitted] = useState(false);
  const [form] = Form.useForm();
  const [searchParams] = useSearchParams();

  const initialCustomerId = searchParams.get('customer_id') || undefined;
  const initialTopK = Number(searchParams.get('top_k') || 10);

  useEffect(() => {
    if (autoSubmitted) return;
    if (initialCustomerId) {
      form.submit();
      setAutoSubmitted(true);
    }
  }, [autoSubmitted, initialCustomerId, form]);

  const handleRecommend = async (values) => {
    try {
      setLoading(true);
      const response = await getRecommendations(
        values.customer_id,
        values.top_k || 10
      );

      if (response.success) {
        setRecommendations(response.data);
        message.success('推薦完了！');
      }
    } catch (error) {
      message.error(`推薦エラー: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePopular = async () => {
    try {
      setLoading(true);
      const response = await getPopularRecommendations(10);

      if (response.success) {
        setPopularItems(response.data);
        message.success('人気商品取得完了！');
      }
    } catch (error) {
      message.error(`取得エラー: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const renderRecommendationCard = (item, index) => {
    const normalizedScore = Math.max(0, Math.min(Number(item.score ?? 0), 1));
    const rawScore = Number(item.raw_score ?? normalizedScore);

    return (
      <Col xs={24} sm={12} lg={8} key={item.product_id}>
      <Card
        hoverable
        style={{ marginBottom: 16 }}
        title={
          <span>
            <Tag color="blue">#{index + 1}</Tag>
            {item.product_id}
          </span>
        }
      >
        <p><strong>商品名:</strong> {item.product_name || 'N/A'}</p>
        <p><strong>カテゴリー:</strong> {item.category || 'N/A'}</p>
        <p><strong>価格:</strong> ¥{item.price ? item.price.toFixed(0) : 'N/A'}</p>
        <p>
          <strong>推薦スコア:</strong>{' '}
          <Tag color="green">{normalizedScore.toFixed(3)}</Tag>
        </p>
        <div style={{ marginTop: 12 }}>
          <StarOutlined style={{ color: '#faad14', marginRight: 4 }} />
          <span>おすすめ度: {(normalizedScore * 100).toFixed(1)}%</span>
        </div>
        <div style={{ marginTop: 4, color: '#888', fontSize: 12 }}>
          生スコア: {rawScore.toFixed(3)}
        </div>
      </Card>
      </Col>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Card title="🎁 個別推薦システム" style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleRecommend}
        >
          <Form.Item
            label="顧客ID"
            name="customer_id"
            initialValue={initialCustomerId}
            rules={[{ required: true, message: '顧客IDを入力してください' }]}
          >
            <Input placeholder="例: C000001" />
          </Form.Item>

          <Form.Item
            label="推薦商品数"
            name="top_k"
            initialValue={initialTopK}
          >
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} size="large" style={{ marginRight: 8 }}>
              <GiftOutlined /> 推薦取得
            </Button>
            <Button onClick={handlePopular} loading={loading} size="large">
              <StarOutlined /> 人気商品表示
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>推薦計算中...</p>
        </div>
      )}

      {recommendations && !loading && (
        <Card 
          title={`📦 ${recommendations.customer_id} 様へのおすすめ商品`}
          extra={<Tag color="volcano">協同フィルタリング + コンテンツベース</Tag>}
          style={{ marginBottom: 24 }}
        >
          <Alert
            message={`推薦方法: ${recommendations.method}`}
            description={`トップ ${recommendations.recommendations.length} 商品を表示`}
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Row gutter={16}>
            {recommendations.recommendations.map((item, index) => 
              renderRecommendationCard(item, index)
            )}
          </Row>
        </Card>
      )}

      {popularItems && !loading && (
        <Card 
          title="🔥 人気商品ランキング"
          extra={<Tag color="red">全店舗データ集計</Tag>}
        >
          <Row gutter={16}>
            {popularItems.recommendations.map((item, index) => (
              <Col xs={24} sm={12} lg={8} key={item.product_id}>
                <Card
                  hoverable
                  style={{ marginBottom: 16 }}
                  title={
                    <span>
                      <Tag color="red">#{index + 1}</Tag>
                      {item.product_id}
                    </span>
                  }
                >
                  <p><strong>商品名:</strong> {item.product_name || 'N/A'}</p>
                  <p><strong>カテゴリー:</strong> {item.category || 'N/A'}</p>
                  <p><strong>価格:</strong> ¥{item.price ? item.price.toFixed(0) : 'N/A'}</p>
                  <p>
                    <strong>人気度:</strong>{' '}
                    <Tag color="magenta">{item.score.toFixed(3)}</Tag>
                  </p>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}
    </div>
  );
};

export default RecommendPage;
