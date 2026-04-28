import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Card, Col, Divider, List, Row, Select, Space, Spin, Table, Tag, Typography } from 'antd';
import { useLocation } from 'react-router-dom';
import { getDataFieldReadiness, getUploadSchemaGuide } from '../services/api';
import { formatReadinessReason } from '../utils/readinessReason';

const { Paragraph, Text, Title } = Typography;

const utilityColor = {
  critical: 'red',
  high: 'orange',
  medium: 'blue',
  nice_to_have: 'default',
};

const FIELD_GUIDE_OVERRIDES = {
  transaction_id: { meaningJa: '取引ID', sampleValue: 'T202501010001' },
  transaction_item_id: { meaningJa: '取引明細ID', sampleValue: 'TI202501010001' },
  customer_id: { meaningJa: '顧客ID', sampleValue: 'C000123' },
  product_id: { meaningJa: '商品ID', sampleValue: 'P000321' },
  store_id: { meaningJa: '店舗ID', sampleValue: 'S000015' },
  promotion_id: { meaningJa: '販促ID', sampleValue: 'PR202507' },
  review_id: { meaningJa: 'レビューID', sampleValue: 'R000987' },
  transaction_date: { meaningJa: '取引日', sampleValue: '2025-07-01' },
  date: { meaningJa: '日付', sampleValue: '2025-07-01' },
  transaction_time: { meaningJa: '取引時刻', sampleValue: '14:35:00' },
  event_timestamp: { meaningJa: 'イベント日時', sampleValue: '2025-07-01T14:35:00+09:00' },
  quantity: { meaningJa: '購入数量', sampleValue: '2' },
  unit_price_jpy: { meaningJa: '単価（税込）', sampleValue: '640' },
  line_total_jpy: { meaningJa: '明細金額（税込）', sampleValue: '1280' },
  total_amount_jpy: { meaningJa: '合計金額（税込）', sampleValue: '4280' },
  total_amount: { meaningJa: '合計金額', sampleValue: '4280' },
  avg_ticket: { meaningJa: '平均客単価', sampleValue: '2140' },
  age: { meaningJa: '年齢', sampleValue: '34' },
  gender: { meaningJa: '性別', sampleValue: 'F' },
  registration_date: { meaningJa: '会員登録日', sampleValue: '2023-04-15' },
  category_level1: { meaningJa: 'カテゴリ（大分類）', sampleValue: 'OTC薬' },
  category_level2: { meaningJa: 'カテゴリ（中分類）', sampleValue: '鎮痛薬' },
  category_level3: { meaningJa: 'カテゴリ（小分類）', sampleValue: '解熱鎮痛薬' },
  support: { meaningJa: '支持度', sampleValue: '0.072' },
  confidence: { meaningJa: '確信度', sampleValue: '0.41' },
  lift: { meaningJa: 'リフト値', sampleValue: '1.86' },
  rating_score: { meaningJa: '評価スコア', sampleValue: '4.2' },
  sentiment_score: { meaningJa: '感情スコア', sampleValue: '0.68' },
};

const TOKEN_TO_JA = {
  transaction: '取引',
  item: '明細',
  customer: '顧客',
  product: '商品',
  store: '店舗',
  promotion: '販促',
  review: 'レビュー',
  date: '日付',
  time: '時刻',
  timestamp: '日時',
  quantity: '数量',
  amount: '金額',
  price: '価格',
  total: '合計',
  avg: '平均',
  age: '年齢',
  gender: '性別',
  category: 'カテゴリ',
  level: '階層',
  score: 'スコア',
  rate: '比率',
  pct: '割合',
  count: '件数',
  days: '日数',
  weather: '天候',
  holiday: '祝日',
  inventory: '在庫',
  stock: '在庫',
};

const buildFallbackMeaningJa = (fieldName) => {
  const tokens = String(fieldName || '').split('_').filter(Boolean);
  if (tokens.length === 0) {
    return '項目';
  }

  return tokens
    .map((token) => TOKEN_TO_JA[token] || token)
    .join(' ');
};

const buildFallbackSampleValue = (fieldName) => {
  const name = String(fieldName || '').toLowerCase();

  if (name.endsWith('_id')) {
    if (name.includes('transaction_item')) return 'TI202501010001';
    if (name.includes('transaction')) return 'T202501010001';
    if (name.includes('customer')) return 'C000123';
    if (name.includes('product')) return 'P000321';
    if (name.includes('store')) return 'S000015';
    if (name.includes('promotion')) return 'PR202507';
    if (name.includes('review')) return 'R000987';
    return 'ID000001';
  }

  if (name.endsWith('_timestamp')) return '2025-07-01T14:35:00+09:00';
  if (name.endsWith('_date') || name === 'date') return '2025-07-01';
  if (name.endsWith('_time') || name === 'time') return '14:35:00';
  if (name.startsWith('is_') || name.endsWith('_flag')) return 'true';
  if (name.endsWith('_rate')) return '0.18';
  if (name.endsWith('_pct')) return '18.0';

  if (name.includes('amount') || name.includes('price') || name.includes('cost') || name.includes('jpy')) {
    return '1280';
  }
  if (name.includes('quantity')) return '2';
  if (name.includes('count')) return '12';
  if (name.includes('days')) return '7';
  if (name.includes('age')) return '34';
  if (name.includes('gender')) return 'F';
  if (name.includes('category')) return 'OTC薬';
  if (name.includes('score')) return '0.72';
  if (name.includes('confidence')) return '0.41';
  if (name.includes('support')) return '0.072';
  if (name.includes('lift')) return '1.86';

  return 'sample_value';
};

const getFieldGuide = (fieldName) => {
  const override = FIELD_GUIDE_OVERRIDES[fieldName] || null;
  const meaningJa = override?.meaningJa || buildFallbackMeaningJa(fieldName);
  const sampleValue = override?.sampleValue || buildFallbackSampleValue(fieldName);
  return {
    meaningJa,
    sampleValue,
    sampleRow: `${fieldName}: ${sampleValue}`,
  };
};

const buildSheetFieldRows = (sheetName, sheet) => {
  const sections = [
    { key: 'minimum_fields', label: '最低限', color: 'red' },
    { key: 'recommended_fields', label: '推奨', color: 'orange' },
    { key: 'optional_fields', label: '任意拡張', color: 'blue' },
  ];

  const rows = [];
  sections.forEach((section) => {
    const fields = sheet?.[section.key] || [];
    fields.forEach((fieldName) => {
      const guide = getFieldGuide(fieldName);
      rows.push({
        key: `${sheetName}-${section.key}-${fieldName}`,
        category: section.label,
        color: section.color,
        field: fieldName,
        meaning_ja: guide.meaningJa,
        sample_row: guide.sampleRow,
      });
    });
  });
  return rows;
};

const UploadSchemaGuidePage = () => {
  const location = useLocation();
  const taskFromQuery = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('task') || 'all';
  }, [location.search]);
  const utilityFromQuery = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const value = params.get('utility') || 'all';
    const allowed = ['all', 'critical', 'high_or_critical', 'high'];
    return allowed.includes(value) ? value : 'all';
  }, [location.search]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [schema, setSchema] = useState(null);
  const [currentReadiness, setCurrentReadiness] = useState(null);
  const [currentReadinessError, setCurrentReadinessError] = useState(null);
  const [selectedTask, setSelectedTask] = useState(taskFromQuery);
  const [selectedUtility, setSelectedUtility] = useState(utilityFromQuery);

  useEffect(() => {
    setSelectedTask(taskFromQuery);
  }, [taskFromQuery]);

  useEffect(() => {
    setSelectedUtility(utilityFromQuery);
  }, [utilityFromQuery]);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        setLoading(true);
        const response = await getUploadSchemaGuide();
        if (!active) return;
        if (response.success) {
          setSchema(response.data);
          setError(null);
        } else {
          setSchema(null);
          setError('フィールド規約の読み込みに失敗しました');
        }

        try {
          const readinessResponse = await getDataFieldReadiness();
          if (!active) return;
          if (readinessResponse.success) {
            setCurrentReadiness(readinessResponse.data.field_readiness || null);
            setCurrentReadinessError(null);
          }
        } catch (readinessErr) {
          if (!active) return;
          setCurrentReadiness(null);
          setCurrentReadinessError(readinessErr.message || '診断可能なデータがまだアップロードされていません');
        }
      } catch (err) {
        if (!active) return;
        setSchema(null);
        setError(err.message || 'フィールド規約の読み込みに失敗しました');
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    return () => {
      active = false;
    };
  }, []);

  const taskRows = useMemo(() => {
    if (!schema?.task_requirements) return [];
    return Object.entries(schema.task_requirements).map(([task, info]) => ({
      key: task,
      task,
      sheets: (info.required_sheets || []).join(', '),
      utility: info.usefulness || 'medium',
    }));
  }, [schema]);

  const fieldRows = useMemo(() => {
    return (schema?.field_catalog || []).map((item) => {
      const guide = getFieldGuide(item.field);
      return {
        key: item.field,
        ...item,
        meaning_ja: guide.meaningJa,
        sample_row: guide.sampleRow,
      };
    });
  }, [schema]);

  const taskOptions = useMemo(() => {
    return [
      { label: '全タスク', value: 'all' },
      ...taskRows.map((row) => ({
        label: row.task,
        value: row.task,
      })),
    ];
  }, [taskRows]);

  const utilityOptions = [
    { label: 'すべて', value: 'all' },
    { label: 'critical のみ', value: 'critical' },
    { label: 'high 以上', value: 'high_or_critical' },
    { label: 'high のみ', value: 'high' },
  ];

  useEffect(() => {
    if (selectedTask === 'all') return;
    if (taskRows.length === 0) return;
    if (!taskRows.some((row) => row.task === selectedTask)) {
      setSelectedTask('all');
    }
  }, [selectedTask, taskRows]);

  const filteredFieldRows = useMemo(() => {
    const byTask = selectedTask === 'all'
      ? fieldRows
      : fieldRows.filter((row) => (row.used_by || []).includes(selectedTask));

    return byTask.filter((row) => {
      const utility = row.utility || 'nice_to_have';
      if (selectedUtility === 'all') return true;
      if (selectedUtility === 'critical') return utility === 'critical';
      if (selectedUtility === 'high') return utility === 'high';
      if (selectedUtility === 'high_or_critical') return ['critical', 'high'].includes(utility);
      return true;
    });
  }, [fieldRows, selectedTask, selectedUtility]);

  const currentTaskRows = useMemo(() => {
    const tasks = currentReadiness?.tasks || {};
    return Object.entries(tasks).map(([taskName, info]) => ({
      key: taskName,
      task: taskName,
      canTrain: !!info.can_train_with_fields,
      reason: formatReadinessReason(info.reason, info.reason_ja, info.reason_code),
      missingSheets: (info.missing_required_sheets || []).join(', ') || '-',
      missingFields: Object.entries(info.missing_required_fields_by_sheet || {})
        .map(([sheet, fields]) => `${sheet}[${fields.join(', ')}]`)
        .join('; ') || '-',
    }));
  }, [currentReadiness]);

  const taskColumns = [
    {
      title: 'タスク',
      dataIndex: 'task',
      key: 'task',
    },
    {
      title: '必須シート',
      dataIndex: 'sheets',
      key: 'sheets',
    },
    {
      title: 'フィールド有用度',
      dataIndex: 'utility',
      key: 'utility',
      render: (value) => <Tag color={utilityColor[value] || 'default'}>{value}</Tag>,
    },
  ];

  const fieldColumns = [
    {
      title: 'フィールド名（Excel推奨列名）',
      dataIndex: 'field',
      key: 'field',
      width: 220,
    },
    {
      title: '日本語の意味',
      dataIndex: 'meaning_ja',
      key: 'meaning_ja',
      width: 220,
    },
    {
      title: 'サンプル（列名: 値）',
      dataIndex: 'sample_row',
      key: 'sample_row',
      width: 260,
    },
    {
      title: '別名（自動認識）',
      dataIndex: 'aliases',
      key: 'aliases',
      render: (aliases = []) => (
        <Space size={[4, 4]} wrap>
          {aliases.slice(0, 8).map((alias) => (
            <Tag key={`${aliases}-${alias}`}>{alias}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '有用度',
      dataIndex: 'utility',
      key: 'utility',
      width: 120,
      render: (value) => <Tag color={utilityColor[value] || 'default'}>{value}</Tag>,
    },
    {
      title: '利用タスク',
      dataIndex: 'used_by',
      key: 'used_by',
      render: (values = []) => (
        <Space size={[4, 4]} wrap>
          {values.map((item) => (
            <Tag color="blue" key={`${values}-${item}`}>{item}</Tag>
          ))}
        </Space>
      ),
    },
  ];

  const currentTaskColumns = [
    {
      title: 'タスク',
      dataIndex: 'task',
      key: 'task',
      width: 130,
    },
    {
      title: '学習可否',
      dataIndex: 'canTrain',
      key: 'canTrain',
      width: 100,
      render: (value) => (value ? <Tag color="green">可</Tag> : <Tag color="red">不可</Tag>),
    },
    {
      title: '不足シート',
      dataIndex: 'missingSheets',
      key: 'missingSheets',
    },
    {
      title: '不足必須フィールド',
      dataIndex: 'missingFields',
      key: 'missingFields',
    },
    {
      title: '理由',
      dataIndex: 'reason',
      key: 'reason',
    },
  ];

  const sheetFieldColumns = [
    {
      title: '区分',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (value, row) => <Tag color={row.color}>{value}</Tag>,
    },
    {
      title: 'フィールド名',
      dataIndex: 'field',
      key: 'field',
      width: 220,
    },
    {
      title: '日本語の意味',
      dataIndex: 'meaning_ja',
      key: 'meaning_ja',
      width: 240,
    },
    {
      title: 'サンプル（列名: 値）',
      dataIndex: 'sample_row',
      key: 'sample_row',
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="error" showIcon message="フィールド規約の読み込みに失敗しました" description={error} />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={3} style={{ marginTop: 0 }}>Excelアップロード項目規約ガイド</Title>
        <Paragraph>
          このページでは、Excel アップロード時に必要なシートとフィールド、推奨される列名を確認できます。
        </Paragraph>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="アップロード形式"
          description="現在のアップロードAPIは .xlsx / .xls / .csv / .zip に対応しています。CSV は 1ファイル=1シートとして扱われ、複数シートをまとめる場合は ZIP を利用できます。CSV ファイル名には標準シート名（例: transaction_items）を含めてください。"
        />
        <Paragraph>
          <Text strong>方針：</Text>フィールドが多いほど精度は上がりますが、不足があってもフォールバックで可能な分析を継続します。
        </Paragraph>

        <Divider orientation="left">命名ルール</Divider>
        <List
          size="small"
          dataSource={Object.entries(schema?.naming_rules || {})}
          renderItem={([name, value]) => (
            <List.Item>
              <Text code>{name}</Text>
              <Text style={{ marginLeft: 12 }}>{Array.isArray(value) ? value.join(', ') : String(value)}</Text>
            </List.Item>
          )}
        />
      </Card>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        {(schema?.sheets || []).map((sheet) => (
          <Col span={24} key={sheet.sheet}>
            <Card title={`Sheet: ${sheet.sheet}`}>
              <Paragraph type="secondary" style={{ marginBottom: 8 }}>{sheet.description}</Paragraph>

              <div style={{ marginBottom: 12 }}>
                <Text strong>別名：</Text>
                <div style={{ marginTop: 6 }}>
                  {(sheet.aliases || []).map((alias) => (
                    <Tag key={`${sheet.sheet}-${alias}`}>{alias}</Tag>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: 12 }}>
                <Text strong>最低限フィールド（推奨必須）：</Text>
                <div style={{ marginTop: 6 }}>
                  {(sheet.minimum_fields || []).map((field) => (
                    <Tag color="red" key={`${sheet.sheet}-min-${field}`}>{field}</Tag>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: 12 }}>
                <Text strong>推奨フィールド：</Text>
                <div style={{ marginTop: 6 }}>
                  {(sheet.recommended_fields || []).map((field) => (
                    <Tag color="orange" key={`${sheet.sheet}-rec-${field}`}>{field}</Tag>
                  ))}
                </div>
              </div>

              <div>
                <Text strong>任意拡張フィールド：</Text>
                <div style={{ marginTop: 6 }}>
                  {(sheet.optional_fields || []).map((field) => (
                    <Tag color="blue" key={`${sheet.sheet}-opt-${field}`}>{field}</Tag>
                  ))}
                </div>
              </div>

              <Divider orientation="left" style={{ margin: '16px 0 12px' }}>
                フィールド説明（日本語・サンプル）
              </Divider>
              <Table
                columns={sheetFieldColumns}
                dataSource={buildSheetFieldRows(sheet.sheet, sheet)}
                pagination={false}
                size="small"
                scroll={{ x: 960 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="タスク最小要件" style={{ marginTop: 16 }}>
        <Table columns={taskColumns} dataSource={taskRows} pagination={false} size="small" />
      </Card>

      <Card title="現在アップロード済みデータのフィールド診断" style={{ marginTop: 16 }}>
        {currentReadiness ? (
          <Table
            columns={currentTaskColumns}
            dataSource={currentTaskRows}
            pagination={false}
            size="small"
            scroll={{ x: 980 }}
          />
        ) : (
          <Alert
            type="info"
            showIcon
            message="診断可能なアップロードデータがありません"
            description={currentReadinessError || '先に Excel ファイルをアップロードしてください。'}
          />
        )}
      </Card>

      <Card
        title="フィールド有用度と自動認識別名"
        style={{ marginTop: 16 }}
        extra={(
          <Space>
            <Text type="secondary">タスク</Text>
            <Select
              value={selectedTask}
              onChange={setSelectedTask}
              options={taskOptions}
              style={{ minWidth: 150 }}
            />
            <Text type="secondary">重要度</Text>
            <Select
              value={selectedUtility}
              onChange={setSelectedUtility}
              options={utilityOptions}
              style={{ minWidth: 170 }}
            />
          </Space>
        )}
      >
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          現在表示中: {filteredFieldRows.length} 件
        </Paragraph>
        <Table
          columns={fieldColumns}
          dataSource={filteredFieldRows}
          pagination={{ pageSize: 12 }}
          size="small"
          scroll={{ x: 1450 }}
        />
      </Card>

      <Card title="フィールド不足時のフォールバック方針" style={{ marginTop: 16 }}>
        <List
          dataSource={schema?.degrade_policy || []}
          renderItem={(item) => (
            <List.Item>
              <Text strong>{item.condition}</Text>
              <Text style={{ marginLeft: 12 }}>{item.behavior}</Text>
            </List.Item>
          )}
        />

        {(schema?.notes || []).length > 0 && (
          <Alert
            type="info"
            showIcon
            style={{ marginTop: 12 }}
            message="補足"
            description={
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {schema.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            }
          />
        )}
      </Card>
    </div>
  );
};

export default UploadSchemaGuidePage;
