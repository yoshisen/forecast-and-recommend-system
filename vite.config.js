import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const getPackageName = (normalizedId) => {
  const match = normalizedId.match(/node_modules\/((?:@[^/]+\/)?[^/]+)/);
  return match ? match[1] : null;
};

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
    globals: true,
    css: true,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, "/");
          if (!normalizedId.includes("node_modules")) return;

          const pkgName = getPackageName(normalizedId);
          if (!pkgName) return;

          if (["react", "react-dom", "scheduler"].includes(pkgName)) return "react-vendor";
          if (["react-router", "react-router-dom", "history"].includes(pkgName)) return "router-vendor";

          if (pkgName === "axios") return "http-vendor";

          if (pkgName === "recharts" || pkgName.startsWith("d3-")) {
            return "charts-vendor";
          }

          if (pkgName === "echarts" || pkgName === "zrender") {
            return "echarts-vendor";
          }

          if (pkgName === "antd") return "antd-core";
          if (pkgName.startsWith("@ant-design/")) return "antd-ecosystem";
          if (pkgName.startsWith("rc-")) return "antd-rc";

          return "vendor";
        },
      },
    },
  },
  server: {
    proxy: {
      // プロキシAPIはローカルFastAPIバックエンドに要求します。
      "/analyze": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
