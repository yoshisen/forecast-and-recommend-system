import React, { lazy, Suspense, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import { Layout, Menu, Typography, Tag, Spin } from 'antd';
import {
  ApartmentOutlined,
  ClusterOutlined,
  DotChartOutlined,
  FileTextOutlined,
  HomeOutlined,
  UploadOutlined,
  DashboardOutlined,
  LineChartOutlined,
  GiftOutlined,
} from '@ant-design/icons';
import './App.css';

const HomePage = lazy(() => import('./pages/HomePage'));
const UploadPage = lazy(() => import('./pages/UploadPage'));
const UploadSchemaGuidePage = lazy(() => import('./pages/UploadSchemaGuidePage'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ForecastPage = lazy(() => import('./pages/ForecastPage'));
const RecommendPage = lazy(() => import('./pages/RecommendPage'));
const ClassificationPage = lazy(() => import('./pages/ClassificationPage'));
const AssociationPage = lazy(() => import('./pages/AssociationPage'));
const ClusteringPage = lazy(() => import('./pages/ClusteringPage'));

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const RouteFallback = () => (
  <div style={{ minHeight: 260, display: 'grid', placeItems: 'center' }}>
    <Spin size="large" />
  </div>
);

function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [currentVersion, setCurrentVersion] = useState(null);
  const [selectedKey, setSelectedKey] = useState(location.pathname);

  useEffect(() => {
    setSelectedKey(location.pathname);
  }, [location.pathname]);

  const handleUploadSuccess = (version) => {
    if (typeof version === 'string') {
      setCurrentVersion(version);
    } else if (version && version.version) {
      setCurrentVersion(version.version);
    }
  };

  const menuItems = [
    { key: '/', icon: <HomeOutlined />, label: 'ホーム' },
    { key: '/upload', icon: <UploadOutlined />, label: 'データアップロード' },
    { key: '/upload-schema', icon: <FileTextOutlined />, label: 'アップロード項目規約' },
    { key: '/dashboard', icon: <DashboardOutlined />, label: 'ダッシュボード' },
    { key: '/forecast', icon: <LineChartOutlined />, label: '売上予測' },
    { key: '/recommend', icon: <GiftOutlined />, label: '商品レコメンド' },
    { key: '/classification', icon: <DotChartOutlined />, label: '分類分析' },
    { key: '/association', icon: <ApartmentOutlined />, label: 'アソシエーション分析' },
    { key: '/clustering', icon: <ClusterOutlined />, label: 'クラスタリング分析' },
  ];

  const pageTitleMap = {
    '/': 'AI Excel 分析ワークベンチ',
    '/upload': 'データアップロード',
    '/upload-schema': 'アップロード項目規約',
    '/dashboard': 'トレーニング監視',
    '/forecast': '売上予測分析',
    '/recommend': '商品レコメンド分析',
    '/classification': '顧客分類分析',
    '/association': 'アソシエーション分析',
    '/clustering': 'クラスタリング分析',
    '/timeseries': '売上予測分析',
  };
  const pageTitle = pageTitleMap[selectedKey] || 'AI Excel 分析ワークベンチ';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        className="app-shell-sider"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        collapsedWidth={72}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: 20,
          fontWeight: 'bold'
        }}>
          {collapsed ? '🛒' : '🛒 METADATAS AI'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <Title level={3} style={{ margin: 0 }}>
            {pageTitle}
          </Title>
          {currentVersion && (
            <Tag color="blue">バージョン: {currentVersion}</Tag>
          )}
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#f0f2f5' }}>
          <ErrorBoundary>
            <Suspense fallback={<RouteFallback />}>
              <Routes>
                <Route path="/" element={<HomePage onUploadSuccess={handleUploadSuccess} />} />
                <Route path="/upload" element={<UploadPage onUploadSuccess={handleUploadSuccess} />} />
                <Route path="/upload-schema" element={<UploadSchemaGuidePage />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/forecast" element={<ForecastPage />} />
                <Route path="/recommend" element={<RecommendPage />} />
                <Route path="/classification" element={<ClassificationPage />} />
                <Route path="/association" element={<AssociationPage />} />
                <Route path="/clustering" element={<ClusteringPage />} />
                <Route path="/timeseries" element={<ForecastPage defaultAlgorithm="prophet" />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </Content>
      </Layout>
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

export default App;
