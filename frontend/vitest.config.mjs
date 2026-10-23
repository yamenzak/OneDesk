import vue from '@vitejs/plugin-vue'
import { sheetSeams } from './src/sheet/seams.mjs'
import { writerSeams } from './src/writer/seams.mjs'

export default {
  plugins: [sheetSeams, writerSeams, vue()],
  test: { environment: 'jsdom', include: ['src/**/*.test.{js,ts}'] },
}
