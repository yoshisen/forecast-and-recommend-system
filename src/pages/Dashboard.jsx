import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, message, Spin, Alert, Tag, Progress, Space, Collapse } from 'antd';
import { useNavigate } from 'react-router-dom';
import { 
  ApartmentOutlined,
  ClusterOutlined,
  DotChartOutlined,
  LineChartOutlined,
  ClockCircleOutlined,
  ShoppingCartOutlined,
  DatabaseOutlined,
  GiftOutlined,
} from '@ant-design/icons';
import {
  getDataSummary,
  getDataFieldReadiness,
  trainForecastModel,
  trainRecommender,
  trainClassificationModel,
  trainAssociationModel,
  trainClusteringModel,
  trainTimeSeriesModel,
} from '../services/api';
import ForecastMetricsViz from '../components/ForecastMetricsViz';
import RecommenderMatrixViz from '../components/RecommenderMatrixViz';
import { formatReadinessReason } from '../utils/readinessReason';

const TASK_META = {
  forecast: {
    title: '売上予測',
    description: 'LightGBM / ベースライン',
    icon: <LineChartOutlined style={{ fontSize: 40, color: '#1677ff' }} />,
    trainFn: trainForecastModel,
  },
  recommend: {
    title: '商品レコメンド',
    description: 'ハイブリッド推薦',
    icon: <GiftOutlined style={{ fontSize: 40, color: '#16a34a' }} />,
    trainFn: trainRecommender,
  },
  classification: {
    title: '顧客分類',
    description: 'XGBoost / RF フォールバック',
    icon: <DotChartOutlined style={{ fontSize: 40, color: '#7c3aed' }} />,
    trainFn: trainClassificationModel,
  },
  association: {
    title: 'アソシエーション分析',
    description: 'Apriori + Lift',
    icon: <ApartmentOutlined style={{ fontSize: 40, color: '#d97706' }} />,
    trainFn: trainAssociationModel,
  },
  clustering: {
    title: 'クラスタリング分析',
    description: 'KMeans + PCA',
    icon: <ClusterOutlined style={{ fontSize: 40, color: '#0891b2' }} />,
    trainFn: trainClusteringModel,
  },
  prophet: {
    title: '時系列予測',
    description: 'Prophet 季節性',
    icon: <ClockCircleOutlined style={{ fontSize: 40, color: '#16a34a' }} />,
    trainFn: trainTimeSeriesModel,
  },
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [fieldReadiness, setFieldReadiness] = useState(null);
  const [expandedErrorTask, setExpandedErrorTask] = useState(null);
  const [training, setTraining] = useState({});
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    loadSummary();
  }, []);

  // WebSocket で学習状態を反映する
  useEffect(() => {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    const wsUrl = base.replace(/^http/, 'ws') + '/ws/training';
    let ws;
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'training_update') {
            setSummary(prev => {
              if (!prev) return prev; // 初期ロード前は更新しない
              const training = { ...(prev.training || {}) };
              training[msg.model] = msg.status;
              training[`${msg.model}_progress`] = msg.progress;
              if (msg.metrics) training[`${msg.model}_metrics`] = msg.metrics;
              if (msg.error) training[`${msg.model}_error`] = msg.error;
              return { ...prev, training };
            });
          }
        } catch (e) {
          console.error('WebSocket メッセージ解析エラー', e);
        }
      };
      ws.onclose = () => {
        // 切断時はポーリングに切り替える
        setPolling(true);
      };
    } catch (e) {
      console.error('WebSocket 初期化失敗', e);
      setPolling(true);
    }
    return () => ws && ws.close();
  }, []);

  // WebSocket 切断中のフォールバックポーリング
  useEffect(() => {
    if (!polling || !summary) return;
    let interval = setInterval(() => loadSummary(true), 6000);
    return () => clearInterval(interval);
  }, [polling, summary]);

  // 実行中タスクがなくなったらポーリングを停止
  useEffect(() => {
    if (!summary) return;
    const ti = summary.training || {};
    const activeStatuses = ['pending', 'running'];
    const anyActive = Object.keys(TASK_META).some((task) => activeStatuses.includes(ti[task]));
    if (polling && !anyActive) {
      setPolling(false);
    }
  }, [summary, polling]);

  const loadSummary = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const response = await getDataSummary();
      if (response.success) {
        setSummary(response.data);
        try {
          const readinessResponse = await getDataFieldReadiness(response.data?.version || null);
          if (readinessResponse.success) {
            setFieldReadiness(readinessResponse.data?.field_readiness || null);
          } else {
            setFieldReadiness(null);
          }
        } catch (readinessError) {
          console.warn('フィールド診断情報の取得に失敗:', readinessError?.message || readinessError);
          setFieldReadiness(null);
        }
      }
    } catch (error) {
      const statusCode = error?.response?.status;
      if (statusCode === 404) {
        // 404 は未アップロード状態なので通常の空状態 UI へ遷移する。
        setSummary(null);
        setFieldReadiness(null);
        setPolling(false);
      } else if (!silent) {
        message.error(`データ読み込みエラー: ${error.message}`);
      }
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const handleTrainTask = async (taskName) => {
    const meta = TASK_META[taskName];
    if (!meta) return;

    try {
      setTraining((prev) => ({ ...prev, [taskName]: true }));
      message.info(`${meta.title} を学習中...`);

      const response = await meta.trainFn();
      if (response.success) {
        message.success(`${meta.title} の学習が完了しました`);
        loadSummary(true);
      }
    } catch (error) {
      message.error(`${meta.title} の学習に失敗: ${error.message}`);
    } finally {
      setTraining((prev) => ({ ...prev, [taskName]: false }));
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          message="データがありません"
          description="先にExcelファイルをアップロードしてください"
          type="warning"
          showIcon
        />
      </div>
    );
  }

  const overallSummary = summary.overall_summary || {};
  const trainingInfo = summary.training || {};
  const readinessInfo = summary.task_readiness || {};
  const fieldTaskEntries = Object.entries(fieldReadiness?.tasks || {});
  const fieldReadyCount = fieldTaskEntries.filter(([, info]) => !!info.can_train_with_fields).length;
  const fieldBlockedEntries = fieldTaskEntries.filter(([, info]) => !info.can_train_with_fields);

  const buildMissingRequirementText = (taskName, info) => {
    const missingSheetsText = (info.missing_required_sheets || []).join(', ') || '-';
    const missingFieldsText = Object.entries(info.missing_required_fields_by_sheet || {})
      .map(([sheet, fields]) => `${sheet}[${fields.join(', ')}]`)
      .join('; ') || '-';
    const aliasHintText = Object.entries(info.missing_required_field_hints || {})
      .map(([sheet, hints]) => {
        const renderedHints = (hints || [])
          .map((hint) => `${hint.field}: ${(hint.aliases || []).slice(0, 6).join(', ')}`)
          .join(' | ');
        return `${sheet} -> ${renderedHints}`;
      })
      .join('; ');

    return [
      `タスク: ${taskName}`,
      `理由: ${formatReadinessReason(info.reason, info.reason_ja, info.reason_code)}`,
      `不足シート: ${missingSheetsText}`,
      `不足必須フィールド: ${missingFieldsText}`,
      aliasHintText ? `認識可能な別名: ${aliasHintText}` : null,
    ].filter(Boolean).join('\n');
  };

  const copyMissingRequirement = async (taskName, info) => {
    const text = buildMissingRequirementText(taskName, info);
    try {
      if (!navigator?.clipboard?.writeText) {
        message.warning('クリップボードを利用できません');
        return;
      }
      await navigator.clipboard.writeText(text);
      message.success('不足項目をコピーしました');
    } catch (copyError) {
      message.error('コピーに失敗しました');
      console.error('コピー処理失敗:', copyError);
    }
  };

  const blockedDetailItems = fieldBlockedEntries.map(([taskName, info]) => {
    const missingSheetsText = (info.missing_required_sheets || []).join(', ') || '-';
    const missingFieldsText = Object.entries(info.missing_required_fields_by_sheet || {})
      .map(([sheet, fields]) => `${sheet}[${fields.join(', ')}]`)
      .join('; ') || '-';
    const aliasHintText = Object.entries(info.missing_required_field_hints || {})
      .map(([sheet, hints]) => {
        const renderedHints = (hints || [])
          .map((hint) => `${hint.field}: ${(hint.aliases || []).slice(0, 6).join(', ')}`)
          .join(' | ');
        return `${sheet} -> ${renderedHints}`;
      })
      .join('; ');

    return {
      key: taskName,
      label: (
        <Space>
          <Tag color="red">{taskName}</Tag>
          <span>{formatReadinessReason(info.reason, info.reason_ja, info.reason_code)}</span>
          <Button
            type="link"
            size="small"
            onClick={(event) => {
              event.stopPropagation();
              navigate(`/upload-schema?task=${encodeURIComponent(taskName)}`);
            }}
          >
            このタスクの規約を見る
          </Button>
        </Space>
      ),
      children: (
        <div>
          <div><strong>不足シート:</strong> {missingSheetsText}</div>
          <div style={{ marginTop: 6 }}><strong>不足必須フィールド:</strong> {missingFieldsText}</div>
          {aliasHintText ? (
            <div style={{ marginTop: 6 }}><strong>認識可能な別名ヒント:</strong> {aliasHintText}</div>
          ) : null}
          <div style={{ marginTop: 10 }}>
            <Button size="small" onClick={() => copyMissingRequirement(taskName, info)}>
              不足項目をコピー
            </Button>
          </div>
        </div>
      ),
    };
  });

  const statusColor = (s) => {
    switch (s) {
      case 'completed': return 'green';
      case 'failed': return 'red';
      case 'pending': return 'gold';
      case 'running': return 'processing';
      case 'skipped': return 'default';
      default: return 'blue';
    }
  };

  // 表示用ステータス翻訳
  const translateStatus = (s) => {
    switch (s) {
      case 'pending': return '待機中';
      case 'running': return '実行中';
      case 'failed': return '失敗';
      case 'skipped': return 'スキップ';
      case 'completed': return '完了';
      default: return s || 'N/A';
    }
  };

  const renderTaskCard = (taskName) => {
    const meta = TASK_META[taskName];
    const status = trainingInfo[taskName] || 'unknown';
    const progress = trainingInfo[`${taskName}_progress`] || 0;
    const reason = trainingInfo[`${taskName}_reason`];
    const metrics = trainingInfo[`${taskName}_metrics`];
    const matrixInfo = trainingInfo[`${taskName}_matrix_info`];
    const summaryData = trainingInfo[`${taskName}_summary`];
    const error = trainingInfo[`${taskName}_error`];
    const errorTrace = trainingInfo[`${taskName}_error_trace`];
    const readyState = readinessInfo[taskName] || {};

    return (
      <Col xs={24} md={12} xl={8} key={taskName} style={{ marginBottom: 16 }}>
        <Card>
          <div style={{ textAlign: 'center' }}>
            {meta.icon}
            <h3 style={{ marginTop: 10 }}>{meta.title}</h3>
            <p style={{ margin: '4px 0', color: '#666' }}>{meta.description}</p>
            <Tag color={statusColor(status)}>{translateStatus(status)}</Tag>
            {!readyState.can_train && (
              <Alert
                type="warning"
                showIcon
                style={{ marginTop: 12, textAlign: 'left' }}
                message="現在このタスクは学習できません"
                description={formatReadinessReason(readyState.reason || reason, readyState.reason_ja, readyState.reason_code) || '必須入力が不足しています'}
              />
            )}

            {['pending', 'running'].includes(status) && (
              <div style={{ marginTop: 12 }}>
                <Progress percent={progress} status="active" />
              </div>
            )}

            {taskName === 'forecast' && status === 'completed' && metrics && (
              <div style={{ marginTop: 10 }}>
                <ForecastMetricsViz metrics={metrics} />
              </div>
            )}

            {taskName === 'recommend' && status === 'completed' && matrixInfo && (
              <div style={{ marginTop: 10 }}>
                <RecommenderMatrixViz matrix={matrixInfo} />
              </div>
            )}

            {taskName !== 'forecast' && taskName !== 'recommend' && status === 'completed' && (
              <div style={{ marginTop: 10 }}>
                <Space wrap>
                  {metrics && Object.entries(metrics).slice(0, 3).map(([k, v]) => (
                    <Tag key={`${taskName}-${k}`} color="blue">{k}: {typeof v === 'number' ? Number(v).toFixed(4) : String(v)}</Tag>
                  ))}
                  {summaryData && Object.entries(summaryData).slice(0, 3).map(([k, v]) => (
                    <Tag key={`${taskName}-s-${k}`} color="cyan">{k}: {typeof v === 'number' ? Number(v).toFixed(3) : String(v)}</Tag>
                  ))}
                </Space>
              </div>
            )}

            {error && (
              <div style={{ marginTop: 12, textAlign: 'left' }}>
                <Alert type="error" showIcon message={`${meta.title} の学習失敗`} description={error} />
                {errorTrace && (
                  <Button
                    size="small"
                    style={{ marginTop: 8 }}
                    onClick={() => setExpandedErrorTask((prev) => (prev === taskName ? null : taskName))}
                  >
                    {expandedErrorTask === taskName ? 'ログを隠す' : 'ログを見る'}
                  </Button>
                )}
                {expandedErrorTask === taskName && errorTrace && (
                  <pre style={{
                    marginTop: 8,
                    maxHeight: 220,
                    overflow: 'auto',
                    background: '#1e1e1e',
                    color: '#dcdcdc',
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 12,
                  }}>{errorTrace}</pre>
                )}
              </div>
            )}

            <div style={{ marginTop: 12 }}>
              <Button
                type="primary"
                size="large"
                loading={!!training[taskName]}
                onClick={() => handleTrainTask(taskName)}
                disabled={['pending', 'running'].includes(status) || !readyState.can_train}
              >
                {status === 'completed' ? '再学習' : '学習開始'}
              </Button>
            </div>
          </div>
        </Card>
      </Col>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Card title="📊 データサマリー" style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="総シート数"
                value={overallSummary.total_sheets || 0}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="総レコード数"
                value={overallSummary.total_rows || 0}
                prefix={<ShoppingCartOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="総フィールド数"
                value={overallSummary.total_fields || 0}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="バージョン"
                value={summary.version}
                valueStyle={{ fontSize: 16 }}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      <Card title="📈 シート別データ" style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          {Object.entries(summary.sheet_summaries || {}).map(([sheetName, sheetData]) => (
            <Col span={8} key={sheetName} style={{ marginBottom: 16 }}>
              <Card size="small" title={sheetName}>
                <Statistic title="行数" value={sheetData.rows} />
                <Statistic title="列数" value={sheetData.columns} />
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {fieldTaskEntries.length > 0 && (
        <Card
          title="🩺 フィールド診断サマリー"
          style={{ marginBottom: 24 }}
          extra={(
            <Button type="link" onClick={() => navigate('/upload-schema')}>
              フィールド規約を見る
            </Button>
          )}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Statistic title="学習可能タスク" value={fieldReadyCount} />
            </Col>
            <Col span={8}>
              <Statistic title="ブロック中タスク" value={fieldBlockedEntries.length} />
            </Col>
            <Col span={8}>
              <Statistic title="診断対象タスク数" value={fieldTaskEntries.length} />
            </Col>
          </Row>

          {fieldBlockedEntries.length > 0 ? (
            <>
              <Alert
                style={{ marginTop: 16 }}
                type="warning"
                showIcon
                message="現在、以下のタスクで必須フィールドが不足しています"
              />
              <Collapse
                style={{ marginTop: 12 }}
                size="small"
                items={blockedDetailItems}
                defaultActiveKey={blockedDetailItems.map((item) => item.key)}
              />
            </>
          ) : (
            <Alert
              style={{ marginTop: 16 }}
              type="success"
              showIcon
              message="現在のバージョンは全タスクの学習要件を満たしています"
            />
          )}
        </Card>
      )}

      <Card title="🤖 学習タスクコンソール" style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          {Object.keys(TASK_META).map((taskName) => renderTaskCard(taskName))}
        </Row>
        {polling && (
          <Alert style={{ marginTop: 16 }} type="info" showIcon message="自動学習を実行中" description="WebSocket 切断時はポーリングで状態を同期します" />
        )}
      </Card>

      <Card title="ℹ️ システム情報">
        <p><strong>アップロード日時:</strong> {summary.uploaded_at}</p>
        <p><strong>ファイル名:</strong> {summary.filename}</p>
        <p>
          <strong>タスク状態:</strong>{' '}
          {Object.keys(TASK_META).map((taskName) => (
            <Tag key={`sys-${taskName}`} color={statusColor(trainingInfo[taskName])}>
              {taskName}: {translateStatus(trainingInfo[taskName])}
            </Tag>
          ))}
        </p>
      </Card>
    </div>
  );
};

export default Dashboard;
