import Components from 'unplugin-vue-components/vite'
import Vue from '@vitejs/plugin-vue'
import Vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'
import Fonts from 'unplugin-fonts/vite'

import path from 'path'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    base: '/',
    plugins: [
      Vue({ template: { transformAssetUrls } }),

      Vuetify({
        autoImport: true,          
        styles: { configFile: 'src/styles/settings.scss' },
        treeshake: true
      }),

      Components({
        dts: false,
      }),

      Fonts({
        google: {
          families: [{ name: 'Overpass', styles: 'w200;w300;w400;w500;w600;w700;w800;w900' }],
          display: 'swap'
        }
      }),
    ],

    optimizeDeps: {
      exclude: ['vuetify'],
    },

    define: { 'process.env': {} },

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      },
      extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
    },

    server: { port: 3000 },

    build: {
      outDir: path.resolve(__dirname, '../lightrag/api/edumind_webui'),
      emptyOutDir: true,
      target: 'es2019',
      minify: 'esbuild',
      sourcemap: false,
      cssCodeSplit: true,
      reportCompressedSize: true,
      chunkSizeWarningLimit: 900,

      esbuild: {
        drop: ['console', 'debugger'],
        legalComments: 'none',
      },

      rollupOptions: {
        output: {
          entryFileNames: 'assets/[name]-[hash].js',
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: ({ name }) => {
            if (/\.(css)$/.test(name ?? '')) return 'assets/[name]-[hash][extname]'
            if (/\.(png|jpe?g|gif|svg|webp|ico)$/.test(name ?? '')) return 'assets/img/[name]-[hash][extname]'
            if (/\.(woff2?|ttf|otf|eot)$/.test(name ?? '')) return 'assets/fonts/[name]-[hash][extname]'
            return 'assets/[name]-[hash][extname]'
          },

          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('/vue/') || id.includes('vue-router')) return 'vue-core'
              if (id.includes('vuetify')) return 'vuetify-vendor'
              if (
                id.includes('sigma') ||
                id.includes('graphology') ||
                id.includes('graphology-communities-louvain') ||
                id.includes('graphology-layout-forceatlas2') ||
                id.includes('@sigma')
              ) {
                return 'graph-vendor'
              }
              if (id.includes('prismjs')) return 'prism-vendor'
              return 'vendor'
            }
          },
        },
      },
    },
  }
})
