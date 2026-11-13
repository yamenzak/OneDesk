import vue from '@vitejs/plugin-vue'
import { sheetSeams } from './src/sheet/seams.mjs'
import { docSeams } from './src/doc/seams.mjs'
import { slideSeams } from './src/slide/seams.mjs'

export default {
  plugins: [slideSeams, sheetSeams, docSeams, vue()],
  test: { environment: 'jsdom', include: ['src/**/*.test.{js,ts}'], setupFiles: ['fake-indexeddb/auto'], server: { deps: { inline: ['frappe-ui'] } } },
}
