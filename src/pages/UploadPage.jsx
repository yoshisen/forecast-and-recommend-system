import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, message, Card, Progress, Spin, Alert, Descriptions, Tag, Collapse, Button, Table } from 'antd';
import { InboxOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';
import { uploadExcel } from '../services/api';
import { formatReadinessReason } from '../utils/readinessReason';

const { Dragger } = Upload;

const UploadPage = ({ onUploadSuccess }) => {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadPhase, setUploadPhase] = useState('idle');
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);

  const normalizeUploadFiles = (fileOrFiles) => {
    if (Array.isArray(fileOrFiles)) {
      return fileOrFiles.filter(Boolean);
    }
    return [fileOrFiles].filter(Boolean);
  };

  const handleUpload = async (fileOrFiles) => {
    const uploadFiles = normalizeUploadFiles(fileOrFiles);
    if (uploadFiles.length === 0) {
      return false;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadPhase('uploading');
    setUploadResult(null);

    let processingInterval = null;
    let uploadBytesCompleted = false;

    try {
      processingInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (!uploadBytesCompleted) {
            return prev < 30 ? prev + 1 : prev;
          }

          if (prev >= 95) {
            return 95;
          }
          return prev < 85 ? prev + 2 : prev + 1;
        });
      }, 350);

      const result = await uploadExcel(uploadFiles, {
        onUploadProgress: (event) => {
          if (!event || !event.total || event.total <= 0) {
            return;
          }

          const ratio = event.loaded / event.total;
          const mappedProgress = Math.min(70, Math.max(3, Math.round(ratio * 70)));
          setUploadProgress((prev) => Math.max(prev, mappedProgress));

          if (event.loaded >= event.total) {
            uploadBytesCompleted = true;
            setUploadPhase('processing');
          }
        },
      });

      if (!uploadBytesCompleted) {
        setUploadPhase('processing');
      }

      if (processingInterval) {
        clearInterval(processingInterval);
      }
      setUploadProgress(100);
      
      if (result.success) {
        message.success(`${uploadFiles.length} ファイルのアップロードと解析が成功しました！`);
        setUploadResult(result);
        setError(null);
        // 正常時: 親へ通知して Dashboard へ遷移
        if (onUploadSuccess) {
          try { onUploadSuccess(result.version); } catch (e) { /* 空処理 */ }
        }
        // 少し待ってからリダイレクト（UI 反応演出）
        setTimeout(() => navigate('/dashboard'), 500);
      } else {
        message.error('アップロード失敗');
        setError('バックエンドが success=false を返却しました');
      }
    } catch (error) {
      message.error(`アップロードエラー: ${error.message}`);
      console.error('アップロード処理失敗:', error);
      setError(error.message);
    } finally {
      if (processingInterval) {
        clearInterval(processingInterval);
      }
      setUploading(false);
      setUploadPhase('idle');
    }

    return false; // デフォルトのアップロード処理を無効化
  };

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
  };

  const taskFieldRows = Object.entries(uploadResult?.task_field_readiness || {}).map(([taskName, info]) => ({
    key: taskName,
    task: taskName,
    canTrain: !!info.can_train_with_fields,
    reason: formatReadinessReason(info.reason, info.reason_ja, info.reason_code),
    missingSheets: (info.missing_required_sheets || []).join(', ') || '-',
    missingFields: Object.entries(info.missing_required_fields_by_sheet || {})
      .map(([sheetName, fields]) => `${sheetName}[${fields.join(', ')}]`)
      .join('; ') || '-',
    aliasHints: Object.entries(info.missing_required_field_hints || {})
      .map(([sheetName, hints]) => {
        const renderedHints = (hints || [])
          .map((hint) => `${hint.field}: ${(hint.aliases || []).slice(0, 6).join(', ')}`)
          .join(' | ');
        return `${sheetName} -> ${renderedHints}`;
      })
      .join('; ') || '-',
  }));

  const buildTaskMissingRequirementText = (row) => {
    const lines = [
      `タスク: ${row.task}`,
      `理由: ${row.reason}`,
      `不足シート: ${row.missingSheets}`,
      `不足必須フィールド: ${row.missingFields}`,
    ];
    if (row.aliasHints && row.aliasHints !== '-') {
      lines.push(`認識可能な別名: ${row.aliasHints}`);
    }
    return lines.join('\n');
  };

  const copyTaskMissingRequirement = async (row) => {
    const text = buildTaskMissingRequirementText(row);
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

  const taskFieldColumns = [
    {
      title: 'タスク',
      dataIndex: 'task',
      key: 'task',
      width: 120,
    },
    {
      title: '学習可否',
      dataIndex: 'canTrain',
      key: 'canTrain',
      width: 110,
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
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, row) => (
        <Button size="small" onClick={() => copyTaskMissingRequirement(row)}>
          不足項目をコピー
        </Button>
      ),
    },
  ];

  const renderWarningDescription = (warning) => {
    const suggestedByFile = warning?.suggested_sheet_names_by_file;
    const suggestionRows = Object.entries(suggestedByFile || {}).filter(([, suggestions]) =>
      Array.isArray(suggestions) && suggestions.length > 0
    );

    if (warning?.type !== 'zip_skipped_files' || suggestionRows.length === 0) {
      return warning?.impact;
    }

    return (
      <div>
        <div>{warning.impact}</div>
        <div style={{ marginTop: 6, fontSize: 12, color: '#595959' }}>候補シート名:</div>
        <ul style={{ marginTop: 4, marginBottom: 0, paddingLeft: 20 }}>
          {suggestionRows.map(([fileName, suggestions]) => (
            <li key={fileName}>
              {fileName}: {suggestions.join(', ')}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card title="📊 データファイルアップロード" style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 12 }}>
          <Button type="link" onClick={() => navigate('/upload-schema')}>
            アップロード項目規約を見る（必須・推奨項目）
          </Button>
        </div>
        <Dragger {...uploadProps} disabled={uploading}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">クリックまたはドラッグしてファイルをアップロード</p>
          <p className="ant-upload-hint">
            .xlsx / .xls / .csv / .zip をサポート（最大100MB、複数CSV同時アップロード可）
          </p>
        </Dragger>

        {uploading && (
          <div style={{ marginTop: 24 }}>
            <Spin size="large" />
            <Progress percent={uploadProgress} status="active" style={{ marginTop: 16 }} />
            <p style={{ textAlign: 'center', marginTop: 8 }}>
              {uploadPhase === 'uploading'
                ? 'ファイルをアップロード中...'
                : 'アップロード完了。サーバーで解析・検証中...'}
            </p>
          </div>
        )}
      </Card>

      {error && (
        <Card style={{ marginBottom: 24 }} title={<><WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />アップロードエラー</>}>
          <Alert type="error" message="アップロードに失敗しました" description={error} showIcon />
          <Button style={{ marginTop: 16 }} onClick={() => { setError(null); setUploadResult(null); }}>再試行</Button>
        </Card>
      )}

      {uploadResult && !error && (
        <>
          <Card 
            title={<><CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />解析完了 / 自動訓練を開始しています。ダッシュボードへ遷移します...</>}
            style={{ marginBottom: 24 }}
          >
            <Descriptions bordered column={2}>
              <Descriptions.Item label="バージョン">{uploadResult.version}</Descriptions.Item>
              <Descriptions.Item label="ファイル名">{uploadResult.metadata.filename}</Descriptions.Item>
              <Descriptions.Item label="アップロード時刻">{uploadResult.metadata.timestamp}</Descriptions.Item>
              <Descriptions.Item label="検出シート数">
                {uploadResult.metadata.available_sheets.length}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 16 }}>
              <strong>利用可能なシート:</strong>
              <div style={{ marginTop: 8 }}>
                {uploadResult.metadata.available_sheets.map((sheet) => (
                  <Tag color="blue" key={sheet} style={{ margin: 4 }}>
                    {sheet}
                  </Tag>
                ))}
              </div>
            </div>
          </Card>

          {taskFieldRows.length > 0 && (
            <Card
              title="フィールド診断（タスク別）"
              style={{ marginBottom: 24 }}
            >
              <Table
                columns={taskFieldColumns}
                dataSource={taskFieldRows}
                pagination={false}
                size="small"
                scroll={{ x: 980 }}
              />
            </Card>
          )}

          {uploadResult.warnings && uploadResult.warnings.length > 0 && (
            <Card 
              title={<><WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />注意</>}
              style={{ marginBottom: 24 }}
            >
              {uploadResult.warnings.map((warning, index) => (
                <Alert
                  key={index}
                  message={warning.message}
                  description={renderWarningDescription(warning)}
                  type="warning"
                  showIcon
                  style={{ marginBottom: 8 }}
                />
              ))}
            </Card>
          )}

          <Card title="📋 データ詳細">
            <Collapse
              items={[
                {
                  key: '1',
                  label: '解析レポート',
                  children: (
                    <pre style={{ maxHeight: 300, overflow: 'auto', backgroundColor: '#f5f5f5', padding: 16 }}>
                      {JSON.stringify(uploadResult.parse_report, null, 2)}
                    </pre>
                  ),
                },
                {
                  key: '2',
                  label: '質量レポート',
                  children: (
                    <pre style={{ maxHeight: 300, overflow: 'auto', backgroundColor: '#f5f5f5', padding: 16 }}>
                      {JSON.stringify(uploadResult.quality_report, null, 2)}
                    </pre>
                  ),
                },
                {
                  key: '3',
                  label: 'バリデーション結果',
                  children: (
                    <pre style={{ maxHeight: 300, overflow: 'auto', backgroundColor: '#f5f5f5', padding: 16 }}>
                      {JSON.stringify(uploadResult.validation_result, null, 2)}
                    </pre>
                  ),
                },
                {
                  key: '4',
                  label: '警告 JSON',
                  children: (
                    <pre style={{ maxHeight: 200, overflow: 'auto', backgroundColor: '#fff7e6', padding: 16 }}>
                      {JSON.stringify(uploadResult.warnings, null, 2)}
                    </pre>
                  ),
                },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  );
};

export default UploadPage;
