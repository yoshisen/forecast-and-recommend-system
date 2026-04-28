export const formatReadinessReason = (reason, reasonJa = null, reasonCode = null) => {
  if (reasonJa) return reasonJa;
  if (reasonCode === 'ok') return '問題ありません';
  if (reasonCode === 'missing_required_sheets') return '必須シート不足';
  if (reasonCode === 'missing_required_fields') return '必須フィールド不足';

  if (!reason) return '必須フィールド不足';
  if (reason === 'ok') return '問題ありません';
  if (reason === 'missing_required_sheets') return '必須シート不足';
  if (reason === 'missing_required_fields') return '必須フィールド不足';

  if (reason.startsWith('missing_required_sheets:')) {
    const value = reason.replace('missing_required_sheets:', '').trim();
    return value ? `必須シート不足: ${value}` : '必須シート不足';
  }

  if (reason.startsWith('missing_required_fields:')) {
    const value = reason.replace('missing_required_fields:', '').trim();
    return value ? `必須フィールド不足: ${value}` : '必須フィールド不足';
  }

  return reason;
};

export default formatReadinessReason;